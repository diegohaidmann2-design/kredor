"""
Aceite de Empréstimo (link público, sem login).

- O dono gera um link de aceite para um empréstimo já cadastrado.
- O cliente abre o link, confere seus dados (reaproveitados da ficha/cliente),
  revê as condições do empréstimo (valor, parcelas, juros, vencimentos), confirma
  os dados e assina digitalmente.
- O aceite (assinatura + carimbo LGPD) fica registrado no empréstimo. O empréstimo
  passa de "aguardando aceite" para "aceito" após a assinatura.

Reaproveita as peças do cadastro público: token, assinatura em canvas, Turnstile
e o object storage. Não altera o campo `status` do empréstimo (usado em cálculos):
o estado do aceite vive em `emprestimo.aceite.status`.
"""
import asyncio
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from config import db, APP_URL
from models.usuario import Usuario
from services.auth import get_current_user
from services.auth_utils import get_user_context
from services.auditoria import registrar_auditoria
from services.logging_service import get_logger
from services.object_storage import put_object, get_object, APP_NAME
from services.turnstile_service import verificar_turnstile, turnstile_habilitado

router = APIRouter()
logger = get_logger("gestorcred.aceite_emprestimo")

TERMO_ACEITE_VERSAO = "aceite-v1-2026-06"
MAX_ASSINATURA_SIZE = 500 * 1024  # 500 KB


def _link_url(token: str) -> str:
    base = (APP_URL or "").rstrip("/")
    return f"{base}/aceite/{token}"


def _get_client_ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _centavos_para_reais(v) -> float:
    return round(int(v or 0) / 100, 2)


async def _enviar_link_aceite_whatsapp(emp: dict, url: str, context_id: str) -> dict:
    """Tenta enviar o link de aceite ao cliente por WhatsApp. Não bloqueia se falhar.

    Retorna {"enviado": bool, "motivo"?: str, "numero"?: str}. Motivos possíveis quando
    não enviado: cliente_sem_telefone, whatsapp_nao_conectado, evolution_nao_configurada,
    erro_envio, erro_geral.
    """
    try:
        cliente = await db.clientes.find_one(
            {"id": emp.get("cliente_id"), "usuario_id": context_id},
            {"_id": 0, "nome": 1, "telefone": 1},
        )
        telefone = (cliente or {}).get("telefone")
        if not telefone:
            return {"enviado": False, "motivo": "cliente_sem_telefone"}

        usuario = await db.usuarios.find_one({"id": context_id}, {"_id": 0, "nome": 1})
        empresa = (usuario or {}).get("nome") or "Kredor"
        nome_cliente = (cliente or {}).get("nome") or "Cliente"
        valor = _centavos_para_reais(
            emp.get("valor_total_com_juros_centavos") or emp.get("valor_principal_centavos")
        )
        valor_txt = f" no valor de R$ {valor:.2f}".replace(".", ",") if valor else ""

        mensagem = (
            f"Olá, {nome_cliente}! 👋\n\n"
            f"Você recebeu um link para revisar e *assinar* o seu empréstimo{valor_txt}.\n\n"
            f"Confira seus dados e as condições e assine com segurança:\n{url}\n\n"
            f"Enviado por {empresa}."
        )

        from services.whatsapp_service import enviar_mensagem_whatsapp
        resultado = await enviar_mensagem_whatsapp(context_id, telefone, mensagem)
        if resultado.get("success"):
            logger.info("Link de aceite enviado por WhatsApp", data={"emprestimo_id": emp.get("id")})
            return {"enviado": True, "numero": resultado.get("numero_enviado")}
        return {"enviado": False, "motivo": resultado.get("error") or "erro_envio"}
    except Exception as e:
        logger.warning(f"Falha ao enviar link de aceite por WhatsApp: {e}")
        return {"enviado": False, "motivo": "erro_geral"}


# ==================== DONO: GERAR LINK ====================

@router.post("/gerar/{emprestimo_id}")
async def gerar_link_aceite(emprestimo_id: str, current_user: Usuario = Depends(get_current_user)):
    """Gera (ou reaproveita) o token de aceite do empréstimo e marca como 'aguardando'."""
    context_id = get_user_context(current_user)
    emp = await db.emprestimos.find_one({"id": emprestimo_id, "usuario_id": context_id, "deleted": {"$ne": True}})
    if not emp:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")

    aceite = emp.get("aceite") or {}
    if aceite.get("status") == "aceito":
        raise HTTPException(status_code=400, detail="Este empréstimo já foi aceito pelo cliente.")

    token = aceite.get("token") or secrets.token_urlsafe(9)
    novo_aceite = {
        "status": "aguardando",
        "token": token,
        "solicitado_em": datetime.now(timezone.utc).isoformat(),
        "solicitado_por": current_user.email,
    }
    await db.emprestimos.update_one(
        {"id": emprestimo_id, "usuario_id": context_id},
        {"$set": {"aceite": novo_aceite}},
    )
    url = _link_url(token)
    whatsapp = await _enviar_link_aceite_whatsapp(emp, url, context_id)
    return {"token": token, "url": url, "status": "aguardando", "whatsapp": whatsapp}


@router.post("/regenerar/{emprestimo_id}")
async def regenerar_link_aceite(emprestimo_id: str, current_user: Usuario = Depends(get_current_user)):
    """Gera um novo token, invalidando o link anterior (apenas se ainda não aceito)."""
    context_id = get_user_context(current_user)
    emp = await db.emprestimos.find_one({"id": emprestimo_id, "usuario_id": context_id, "deleted": {"$ne": True}})
    if not emp:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    if (emp.get("aceite") or {}).get("status") == "aceito":
        raise HTTPException(status_code=400, detail="Este empréstimo já foi aceito e não pode gerar novo link.")
    token = secrets.token_urlsafe(9)
    await db.emprestimos.update_one(
        {"id": emprestimo_id, "usuario_id": context_id},
        {"$set": {"aceite": {
            "status": "aguardando", "token": token,
            "solicitado_em": datetime.now(timezone.utc).isoformat(),
            "solicitado_por": current_user.email,
        }}},
    )
    url = _link_url(token)
    whatsapp = await _enviar_link_aceite_whatsapp(emp, url, context_id)
    return {"token": token, "url": url, "status": "aguardando", "whatsapp": whatsapp}


# ==================== PÚBLICO ====================

async def _montar_resumo(emp: dict) -> dict:
    """Monta o resumo público do empréstimo + dados do cliente + parcelas."""
    usuario_id = emp["usuario_id"]
    cliente = await db.clientes.find_one({"id": emp.get("cliente_id"), "usuario_id": usuario_id}, {"_id": 0})
    usuario = await db.usuarios.find_one({"id": usuario_id}, {"_id": 0, "nome": 1})

    parcelas_docs = await db.parcelas.find(
        {"emprestimo_id": emp["id"], "usuario_id": usuario_id, "deleted": {"$ne": True}},
        {"_id": 0, "numero_parcela": 1, "data_vencimento": 1, "valor_total_centavos": 1},
    ).sort("numero_parcela", 1).to_list(500)

    parcelas = [{
        "numero_parcela": p.get("numero_parcela"),
        "data_vencimento": p.get("data_vencimento"),
        "valor_total": _centavos_para_reais(p.get("valor_total_centavos")),
    } for p in parcelas_docs]

    aceite = emp.get("aceite") or {}
    endereco = (cliente or {}).get("endereco") or {}

    return {
        "empresa": (usuario or {}).get("nome") or "Kredor",
        "cliente": {
            "nome": (cliente or {}).get("nome") or "",
            "cpf_cnpj": (cliente or {}).get("cpf_cnpj") or "",
            "telefone": (cliente or {}).get("telefone") or "",
            "email": (cliente or {}).get("email") or "",
            "endereco": {
                "rua": endereco.get("rua") or "",
                "numero": endereco.get("numero") or "",
                "bairro": endereco.get("bairro") or "",
                "cidade": endereco.get("cidade") or "",
                "estado": endereco.get("estado") or "",
                "cep": endereco.get("cep") or "",
            },
        },
        "emprestimo": {
            "valor_principal": _centavos_para_reais(emp.get("valor_principal_centavos")),
            "valor_total_com_juros": _centavos_para_reais(emp.get("valor_total_com_juros_centavos")),
            "valor_total_juros": _centavos_para_reais(emp.get("valor_total_juros_centavos")),
            "taxa_juros_mensal": emp.get("taxa_juros_mensal"),
            "taxa_juros_semanal": emp.get("taxa_juros_semanal"),
            "prazo_meses": emp.get("prazo_meses"),
            "prazo_semanas": emp.get("prazo_semanas"),
            "periodicidade": emp.get("periodicidade") or "mensal",
            "metodo_calculo": emp.get("metodo_calculo"),
            "sem_prazo": bool(emp.get("sem_prazo")),
            "data_inicio": emp.get("data_inicio"),
        },
        "parcelas": parcelas,
        "aceite": {
            "status": aceite.get("status") or "aguardando",
            "assinado_em": aceite.get("assinado_em"),
            "versao_termo": TERMO_ACEITE_VERSAO,
        },
    }


@router.get("/info/{token}")
async def info_aceite(token: str):
    """Dados públicos para renderizar a tela de aceite (sem auth)."""
    emp = await db.emprestimos.find_one({"aceite.token": token, "deleted": {"$ne": True}})
    if not emp:
        raise HTTPException(status_code=404, detail="Link inválido ou expirado")
    return await _montar_resumo(emp)


@router.post("/confirmar/{token}")
async def confirmar_aceite(token: str, request: Request):
    """
    Recebe o aceite do cliente (sem auth): confirmação dos dados + assinatura + consentimento.
    Espera multipart/form-data com: assinatura (png), consentimento, confirmou_dados, turnstile_token.
    """
    emp = await db.emprestimos.find_one({"aceite.token": token, "deleted": {"$ne": True}})
    if not emp:
        raise HTTPException(status_code=404, detail="Link inválido ou expirado")

    aceite = emp.get("aceite") or {}
    if aceite.get("status") == "aceito":
        raise HTTPException(status_code=400, detail="Este empréstimo já foi aceito.")

    form = await request.form()
    consentimento = (form.get("consentimento") or "").strip().lower() in ("true", "1", "on", "sim", "yes")
    confirmou_dados = (form.get("confirmou_dados") or "").strip().lower() in ("true", "1", "on", "sim", "yes")
    turnstile_token = (form.get("turnstile_token") or "").strip()
    assinatura = form.get("assinatura")

    # Proteção anti-bot
    if turnstile_habilitado():
        ok_ts, erros_ts = await verificar_turnstile(turnstile_token, _get_client_ip(request))
        if not ok_ts:
            logger.warning("Aceite bloqueado pelo Turnstile", data={"erros": erros_ts})
            raise HTTPException(status_code=400, detail="Verificação anti-robô falhou. Recarregue a página e tente novamente.")

    if not confirmou_dados:
        raise HTTPException(status_code=400, detail="Confirme que revisou e concorda com seus dados e as condições.")
    if not consentimento:
        raise HTTPException(status_code=400, detail="É necessário autorizar o registro do aceite e da assinatura.")
    if not (assinatura is not None and hasattr(assinatura, "filename") and getattr(assinatura, "filename", None)):
        raise HTTPException(status_code=400, detail="Assine no campo indicado antes de confirmar o aceite.")

    data = await assinatura.read()
    if not data or len(data) < 16:
        raise HTTPException(status_code=400, detail="Assinatura inválida.")
    if len(data) > MAX_ASSINATURA_SIZE:
        raise HTTPException(status_code=400, detail="Assinatura muito grande.")
    try:
        from PIL import Image
        import io
        Image.open(io.BytesIO(data)).verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Arquivo de assinatura inválido.")

    storage_path = f"{APP_NAME}/aceite-emprestimo/{emp['usuario_id']}/{emp['id']}/assinatura.png"
    await asyncio.to_thread(put_object, storage_path, data, "image/png")

    agora = datetime.now(timezone.utc)
    novo_aceite = {
        **aceite,
        "status": "aceito",
        "assinado_em": agora.isoformat(),
        "ip": _get_client_ip(request),
        "user_agent": (request.headers.get("user-agent") or "")[:500],
        "versao_termo": TERMO_ACEITE_VERSAO,
        "assinatura_path": storage_path,
        "confirmou_dados": True,
    }
    await db.emprestimos.update_one(
        {"id": emp["id"], "usuario_id": emp["usuario_id"]},
        {"$set": {"aceite": novo_aceite}},
    )

    try:
        from services.notificacao_service import criar_notificacao
        await criar_notificacao(
            usuario_id=emp["usuario_id"],
            tipo="aceite",
            titulo="Empréstimo aceito pelo cliente",
            mensagem="O cliente confirmou os dados e assinou o aceite do empréstimo.",
            link=f"/emprestimos/{emp['id']}",
        )
    except Exception as e:
        logger.warning(f"Não foi possível notificar aceite: {e}")

    logger.info("Aceite de empréstimo registrado", data={"emprestimo_id": emp["id"], "usuario_id": emp["usuario_id"]})
    return {"message": "Aceite registrado com sucesso!", "status": "aceito"}


# ==================== DONO: ASSINATURA & CONTRATO ====================

@router.get("/{emprestimo_id}/assinatura")
async def obter_assinatura(emprestimo_id: str, current_user: Usuario = Depends(get_current_user)):
    """Serve a imagem da assinatura do aceite. Restrito ao dono."""
    context_id = get_user_context(current_user)
    emp = await db.emprestimos.find_one({"id": emprestimo_id, "usuario_id": context_id}, {"_id": 0, "aceite": 1})
    if not emp:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    path = ((emp.get("aceite") or {}).get("assinatura_path"))
    if not path:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")
    try:
        data, content_type = await asyncio.to_thread(get_object, path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    except Exception as e:
        logger.warning(f"Erro ao servir assinatura de aceite {emprestimo_id}: {e}")
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return Response(content=data, media_type=content_type or "image/png", headers={
        "Cache-Control": "private, max-age=3600",
    })


@router.get("/contrato-pdf/{token}")
async def baixar_contrato_publico_pdf(token: str):
    """Gera e baixa o PDF do contrato assinado pelo link público (após aceite)."""
    emp = await db.emprestimos.find_one({"aceite.token": token, "deleted": {"$ne": True}})
    if not emp:
        raise HTTPException(status_code=404, detail="Link inválido ou expirado")

    aceite = emp.get("aceite") or {}
    if aceite.get("status") != "aceito":
        raise HTTPException(status_code=400, detail="Este contrato ainda não foi assinado.")

    usuario_id = emp["usuario_id"]
    cliente = await db.clientes.find_one({"id": emp.get("cliente_id"), "usuario_id": usuario_id}, {"_id": 0})
    credor = await db.usuarios.find_one({"id": usuario_id}, {"_id": 0})

    parcelas_docs = await db.parcelas.find(
        {"emprestimo_id": emp["id"], "usuario_id": usuario_id, "deleted": {"$ne": True}},
        {"_id": 0}
    ).sort("numero_parcela", 1).to_list(500)

    from services.contrato_aceite_pdf import gerar_contrato_assinado_pdf

    try:
        pdf_bytes = await asyncio.to_thread(
            gerar_contrato_assinado_pdf,
            emprestimo=emp,
            cliente=cliente or {},
            credor=credor or {},
            parcelas=parcelas_docs,
        )
    except Exception as e:
        logger.exception(f"Erro ao gerar contrato PDF do aceite token {token}: {e}")
        raise HTTPException(status_code=500, detail="Erro ao gerar contrato em PDF.")

    nome_arquivo = f"contrato_assinado_{token}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{nome_arquivo}"',
            "Cache-Control": "private, no-cache, no-store",
        }
    )


@router.get("/{emprestimo_id}/contrato-assinado-pdf")
async def baixar_contrato_assinado_admin(emprestimo_id: str, current_user: Usuario = Depends(get_current_user)):
    """Gera e baixa o PDF do contrato assinado na visão administrativa."""
    context_id = get_user_context(current_user)
    emp = await db.emprestimos.find_one({"id": emprestimo_id, "usuario_id": context_id, "deleted": {"$ne": True}})
    if not emp:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")

    aceite = emp.get("aceite") or {}
    if aceite.get("status") != "aceito":
        raise HTTPException(status_code=400, detail="Este contrato ainda não foi assinado pelo cliente.")

    cliente = await db.clientes.find_one({"id": emp.get("cliente_id"), "usuario_id": context_id}, {"_id": 0})
    credor = await db.usuarios.find_one({"id": context_id}, {"_id": 0})

    parcelas_docs = await db.parcelas.find(
        {"emprestimo_id": emp["id"], "usuario_id": context_id, "deleted": {"$ne": True}},
        {"_id": 0}
    ).sort("numero_parcela", 1).to_list(500)

    from services.contrato_aceite_pdf import gerar_contrato_assinado_pdf

    try:
        pdf_bytes = await asyncio.to_thread(
            gerar_contrato_assinado_pdf,
            emprestimo=emp,
            cliente=cliente or {},
            credor=credor or {},
            parcelas=parcelas_docs,
        )
    except Exception as e:
        logger.exception(f"Erro ao gerar contrato PDF do empréstimo {emprestimo_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro ao gerar contrato em PDF.")

    nome_arquivo = f"contrato_assinado_{emprestimo_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{nome_arquivo}"',
            "Cache-Control": "private, no-cache, no-store",
        }
    )

