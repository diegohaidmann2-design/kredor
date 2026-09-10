"""
Serviço da Carteira de Consultas.

Regras:
- Uma carteira por DONO da conta (owner_id). Funcionários compartilham a mesma.
- Cada consulta desconta um valor definido em `consultas_precos`.
- Recargas via gateway registram movimentos do tipo "recarga".
- Todo débito/crédito é atômico (findOneAndUpdate com incremento).
- Bloqueia consulta quando saldo insuficiente (retorna 402 na rota).
"""
from services.logging_service import get_logger
logger = get_logger("gestorcred.carteira_service")

import uuid
import re
from datetime import datetime, timezone
from typing import Optional, Tuple

from config import db
from services.auth_utils import get_user_context
from datetime import timedelta
from services.notificacao_service import criar_notificacao
from services.email_service import enviar_email_async, template_base
import os

# Preços padrão iniciais (em reais) — administrador pode alterar
PRECOS_PADRAO = {
    "cpf": 0.90,
    "cpf-premium": 2.50,
    "cnpj": 0.90,
    "telefone": 0.50,
    "nome": 0.50,
    "cpf-dividas": 2.50,
    "cnpj-dividas": 2.50,
    "facial": 5.00,
}

LABELS_TIPO = {
    "cpf": "Consulta CPF",
    "cpf-premium": "CPF Premium",
    "cnpj": "Consulta CNPJ",
    "telefone": "Consulta Telefone",
    "nome": "Consulta por Nome",
    "cpf-dividas": "Dívidas CPF",
    "cnpj-dividas": "Dívidas CNPJ",
    "facial": "Reconhecimento Facial",
}

BONUS_INICIAL = 5.00  # R$ 5,00 de bônus para nova carteira

ALERTA_SALDO_MINIMO_DEFAULT = 10.00  # threshold padrão para alerta
ALERTA_SALDO_SNOOZE_HORAS = 24  # não reenvia alerta antes disso

TIPOS_MOVIMENTO = {"recarga", "consumo", "bonus", "estorno", "ajuste"}


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def inicializar_precos_padrao() -> None:
    """Cria docs de preço para tipos que ainda não existem."""
    for tipo, valor in PRECOS_PADRAO.items():
        existe = await db.consultas_precos.find_one({"tipo": tipo})
        if not existe:
            await db.consultas_precos.insert_one({
                "tipo": tipo,
                "label": LABELS_TIPO.get(tipo, tipo),
                "valor": valor,
                "ativo": True,
                "created_at": _agora_iso(),
                "updated_at": _agora_iso(),
                "updated_by": "system",
            })


async def listar_precos(apenas_ativos: bool = False) -> list:
    query = {"ativo": True} if apenas_ativos else {}
    cursor = db.consultas_precos.find(query, {"_id": 0}).sort("tipo", 1)
    return await cursor.to_list(50)


async def obter_preco(tipo: str) -> Optional[dict]:
    doc = await db.consultas_precos.find_one({"tipo": tipo}, {"_id": 0})
    if not doc:
        # Fallback para valor padrão se não existir no banco
        if tipo in PRECOS_PADRAO:
            await inicializar_precos_padrao()
            doc = await db.consultas_precos.find_one({"tipo": tipo}, {"_id": 0})
    return doc


async def atualizar_preco(tipo: str, valor: float, ativo: bool, admin_email: str) -> dict:
    if tipo not in PRECOS_PADRAO and not await db.consultas_precos.find_one({"tipo": tipo}):
        raise ValueError(f"Tipo de consulta desconhecido: {tipo}")
    if valor < 0:
        raise ValueError("Valor não pode ser negativo.")
    update = {
        "valor": round(float(valor), 2),
        "ativo": bool(ativo),
        "updated_at": _agora_iso(),
        "updated_by": admin_email,
    }
    # Upsert p/ criar caso admin adicione tipo novo
    await db.consultas_precos.update_one(
        {"tipo": tipo},
        {"$set": update, "$setOnInsert": {
            "tipo": tipo,
            "label": LABELS_TIPO.get(tipo, tipo),
            "created_at": _agora_iso(),
        }},
        upsert=True,
    )
    return await db.consultas_precos.find_one({"tipo": tipo}, {"_id": 0})


async def obter_ou_criar_carteira(owner_id: str) -> dict:
    """Retorna a carteira do dono. Cria (com bônus) se não existir."""
    carteira = await db.carteiras.find_one({"owner_id": owner_id}, {"_id": 0})
    if carteira:
        return carteira

    novo_id = str(uuid.uuid4())
    doc = {
        "id": novo_id,
        "owner_id": owner_id,
        "saldo": 0.0,
        "total_recargas": 0.0,
        "total_consumo": 0.0,
        "alerta_saldo_minimo": ALERTA_SALDO_MINIMO_DEFAULT,
        "alerta_email_habilitado": True,
        "alerta_ultimo_envio": None,
        "created_at": _agora_iso(),
        "updated_at": _agora_iso(),
    }
    await db.carteiras.insert_one(doc)

    # Conceder bônus inicial (uma única vez)
    if BONUS_INICIAL > 0:
        await _aplicar_movimento(
            owner_id=owner_id,
            tipo="bonus",
            valor=BONUS_INICIAL,
            descricao=f"Bônus de boas-vindas: R$ {BONUS_INICIAL:,.2f}",
            usuario_id=owner_id,
            metadata={"origem": "bonus_inicial"},
        )

    return await db.carteiras.find_one({"owner_id": owner_id}, {"_id": 0})


async def _aplicar_movimento(
    owner_id: str,
    tipo: str,
    valor: float,
    descricao: str,
    usuario_id: str,
    consulta_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Aplica um movimento atômico:
    - crédito: valor > 0 (recarga, bonus, ajuste_positivo, estorno)
    - débito: valor < 0 (consumo, ajuste_negativo)

    Retorna dict com movimento e novos saldos.
    """
    if tipo not in TIPOS_MOVIMENTO:
        raise ValueError(f"Tipo de movimento inválido: {tipo}")

    valor = round(float(valor), 2)
    if valor == 0:
        raise ValueError("Valor do movimento não pode ser zero.")

    agora = _agora_iso()
    # Incrementar saldo atomicamente
    inc_fields = {"saldo": valor, "updated_at": None}
    if valor > 0 and tipo in ("recarga", "bonus"):
        inc_fields["total_recargas"] = valor
    if valor < 0 and tipo == "consumo":
        inc_fields["total_consumo"] = -valor  # sempre positivo

    # findOneAndUpdate com $inc; se débito, garantir saldo suficiente
    filtro = {"owner_id": owner_id}
    if valor < 0:
        filtro["saldo"] = {"$gte": abs(valor)}

    update = {"$inc": {k: v for k, v in inc_fields.items() if k != "updated_at" and v is not None},
              "$set": {"updated_at": agora}}

    carteira = await db.carteiras.find_one_and_update(
        filtro, update, return_document=True, projection={"_id": 0}
    )
    if not carteira:
        if valor < 0:
            raise ValueError("Saldo insuficiente para completar a operação.")
        raise ValueError("Carteira não encontrada.")

    saldo_depois = carteira["saldo"]
    saldo_antes = saldo_depois - valor

    movimento = {
        "id": str(uuid.uuid4()),
        "carteira_id": carteira["id"],
        "owner_id": owner_id,
        "tipo": tipo,
        "valor": valor,
        "saldo_antes": round(saldo_antes, 2),
        "saldo_depois": round(saldo_depois, 2),
        "descricao": descricao,
        "usuario_id": usuario_id,
        "consulta_id": consulta_id,
        "metadata": metadata or {},
        "created_at": agora,
    }
    await db.carteira_movimentos.insert_one(movimento)
    movimento.pop("_id", None)
    return {"movimento": movimento, "carteira": carteira}


async def verificar_saldo_para_consulta(usuario, tipo_consulta: str) -> Tuple[bool, str, dict]:
    """
    Verifica se o usuário (usa contexto do dono) tem saldo p/ o tipo de consulta.
    Retorna (pode_consultar, mensagem, info={preco, saldo}).
    """
    owner_id = get_user_context(usuario)

    preco_doc = await obter_preco(tipo_consulta)
    if not preco_doc:
        return False, f"Tipo de consulta não configurado: {tipo_consulta}", {}
    if not preco_doc.get("ativo", True):
        return False, "Este tipo de consulta está desabilitado no momento.", {"preco": preco_doc.get("valor", 0)}

    preco = float(preco_doc.get("valor", 0))

    # Se o preço for 0, permite (consulta grátis)
    if preco <= 0:
        return True, "OK", {"preco": 0, "saldo": None}

    carteira = await obter_ou_criar_carteira(owner_id)
    saldo = float(carteira.get("saldo", 0))

    info = {"preco": preco, "saldo": round(saldo, 2), "tipo": tipo_consulta}

    if saldo < preco:
        return False, (
            f"Saldo insuficiente na carteira. Custo desta consulta: "
            f"R$ {preco:,.2f}. Saldo atual: R$ {saldo:,.2f}. "
            f"Faça uma recarga para continuar."
        ), info

    return True, "OK", info


async def debitar_consulta(usuario, tipo_consulta: str, consulta_id: str) -> dict:
    """Debita o valor da consulta da carteira do dono."""
    owner_id = get_user_context(usuario)
    preco_doc = await obter_preco(tipo_consulta)
    preco = float(preco_doc.get("valor", 0)) if preco_doc else 0

    if preco <= 0:
        return {"debitado": False, "valor": 0}

    label = (preco_doc.get("label") if preco_doc else None) or LABELS_TIPO.get(tipo_consulta, tipo_consulta)
    resultado = await _aplicar_movimento(
        owner_id=owner_id,
        tipo="consumo",
        valor=-preco,
        descricao=f"{label} — R$ {preco:,.2f}",
        usuario_id=usuario.id,
        consulta_id=consulta_id,
        metadata={"tipo_consulta": tipo_consulta},
    )
    # Alerta de saldo baixo (fire-and-forget, não trava a resposta)
    try:
        await _verificar_alerta_saldo_baixo(
            owner_id=owner_id,
            saldo_antes=resultado["movimento"]["saldo_antes"],
            saldo_depois=resultado["movimento"]["saldo_depois"],
        )
    except Exception as e:
        logger.error(f"[carteira] alerta saldo baixo falhou: {e}")

    return {
        "debitado": True,
        "valor": preco,
        "saldo_atual": resultado["carteira"]["saldo"],
        "movimento_id": resultado["movimento"]["id"],
    }


async def _verificar_alerta_saldo_baixo(owner_id: str, saldo_antes: float, saldo_depois: float) -> None:
    """
    Dispara alerta (in-app + e-mail) quando o saldo CRUZA o threshold para baixo.
    Idempotente: só dispara 1x a cada `ALERTA_SALDO_SNOOZE_HORAS`.
    """
    carteira = await db.carteiras.find_one({"owner_id": owner_id}, {"_id": 0})
    if not carteira:
        return
    limite = float(carteira.get("alerta_saldo_minimo") or 0)
    if limite <= 0:
        return  # alerta desativado
    # Só dispara se cruzou o limite (antes >= limite e depois < limite) OU já está abaixo mas não avisou
    if saldo_depois >= limite:
        return
    # Snooze
    ultimo = carteira.get("alerta_ultimo_envio")
    if ultimo:
        try:
            dt_ultimo = datetime.fromisoformat(str(ultimo).replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - dt_ultimo < timedelta(hours=ALERTA_SALDO_SNOOZE_HORAS):
                return
        except (ValueError, TypeError):
            pass

    # Dados do dono
    dono = await db.usuarios.find_one({"id": owner_id}, {"_id": 0})
    if not dono:
        return
    nome = dono.get("nome") or "Cliente"
    email = dono.get("email")

    # 1) Notificação in-app (sino)
    try:
        await criar_notificacao(
            usuario_id=owner_id,
            tipo="carteira_saldo_baixo",
            titulo="⚡ Saldo da carteira está baixo",
            mensagem=(
                f"Seu saldo caiu para R$ {saldo_depois:,.2f} (limite configurado: R$ {limite:,.2f}). "
                "Recarregue para não interromper suas consultas."
            ),
            link="/carteira",
            prioridade="alta",
            dados_referencia={
                "saldo_atual": round(saldo_depois, 2),
                "limite_configurado": round(limite, 2),
            },
        )
    except Exception as e:
        logger.error(f"[carteira] falha criar notificação sino: {e}")

    # 2) E-mail (silencioso se SMTP não configurado)
    if email and carteira.get("alerta_email_habilitado", True):
        try:
            app_url = os.environ.get("APP_URL") or ""
            link_carteira = f"{app_url.rstrip('/')}/carteira" if app_url else "/carteira"
            conteudo = f"""
                <p>Olá, <strong>{nome}</strong>,</p>
                <p>Seu saldo na Carteira de Consultas está abaixo do limite configurado.</p>
                <div style="background:#fff7ed;border:1px solid #fdba74;border-radius:12px;padding:16px;margin:18px 0;">
                    <p style="margin:0 0 6px;color:#9a3412;font-size:13px;text-transform:uppercase;letter-spacing:.5px;">Saldo atual</p>
                    <p style="margin:0;font-size:28px;font-weight:800;color:#7c2d12;">R$ {saldo_depois:,.2f}</p>
                    <p style="margin:8px 0 0;color:#9a3412;font-size:13px;">Limite configurado: R$ {limite:,.2f}</p>
                </div>
                <p>Para evitar que uma consulta seja bloqueada no meio de uma análise, recomendamos recarregar sua carteira agora.</p>
                <p style="color:#64748b;font-size:12px;margin-top:24px;">
                    Você pode ajustar o valor de alerta ou desativar este e-mail na tela da Carteira.
                </p>
            """
            html = template_base(
                titulo="Saldo baixo na sua carteira",
                conteudo=conteudo,
                botao_texto="Recarregar Carteira",
                botao_link=link_carteira,
            )
            await enviar_email_async(
                destinatario=email,
                assunto=f"⚠️ Saldo baixo na sua carteira — R$ {saldo_depois:,.2f}",
                corpo_html=html,
            )
        except Exception as e:
            logger.error(f"[carteira] falha enviar e-mail alerta: {e}")

    # 3) Marcar timestamp para snooze
    await db.carteiras.update_one(
        {"owner_id": owner_id},
        {"$set": {"alerta_ultimo_envio": _agora_iso()}}
    )


async def atualizar_config_alerta(
    owner_id: str, saldo_minimo: float, email_habilitado: bool,
) -> dict:
    """Permite ao dono ajustar o threshold e ligar/desligar e-mail."""
    if saldo_minimo < 0:
        raise ValueError("O valor mínimo do alerta não pode ser negativo.")
    await obter_ou_criar_carteira(owner_id)
    await db.carteiras.update_one(
        {"owner_id": owner_id},
        {"$set": {
            "alerta_saldo_minimo": round(float(saldo_minimo), 2),
            "alerta_email_habilitado": bool(email_habilitado),
            "alerta_ultimo_envio": None,  # reseta snooze ao alterar config
            "updated_at": _agora_iso(),
        }},
    )
    return await db.carteiras.find_one({"owner_id": owner_id}, {"_id": 0})


async def estornar_consulta(usuario, tipo_consulta: str, consulta_id: str, motivo: str = "Estorno de consulta com falha") -> Optional[dict]:
    """Estorna um débito de consulta (usado em falhas pós-débito). Idempotente por consulta_id."""
    owner_id = get_user_context(usuario)
    # Só estorna se houve um débito não estornado
    mov = await db.carteira_movimentos.find_one({
        "owner_id": owner_id, "consulta_id": consulta_id, "tipo": "consumo",
    }, {"_id": 0})
    if not mov:
        return None
    ja_estornou = await db.carteira_movimentos.find_one({
        "owner_id": owner_id, "consulta_id": consulta_id, "tipo": "estorno",
    }, {"_id": 0})
    if ja_estornou:
        return None
    valor = abs(float(mov["valor"]))
    resultado = await _aplicar_movimento(
        owner_id=owner_id, tipo="estorno", valor=valor,
        descricao=motivo, usuario_id=usuario.id, consulta_id=consulta_id,
        metadata={"tipo_consulta": tipo_consulta, "movimento_original": mov["id"]},
    )
    return resultado["movimento"]


async def creditar_recarga(
    owner_id: str, valor: float, gateway: str, payment_id: str,
    metadata: Optional[dict] = None,
) -> Optional[dict]:
    """
    Credita uma recarga confirmada por webhook. Idempotente: se o payment_id já
    foi creditado, retorna None.
    """
    if valor <= 0:
        return None

    # Idempotência: verificar se este payment_id já gerou movimento
    ja_existe = await db.carteira_movimentos.find_one({
        "owner_id": owner_id, "tipo": "recarga",
        "metadata.gateway": gateway, "metadata.payment_id": payment_id,
    }, {"_id": 0})
    if ja_existe:
        return None

    await obter_ou_criar_carteira(owner_id)
    meta = {"gateway": gateway, "payment_id": payment_id, **(metadata or {})}
    resultado = await _aplicar_movimento(
        owner_id=owner_id, tipo="recarga", valor=float(valor),
        descricao=f"Recarga via {gateway.upper()} — R$ {float(valor):,.2f}",
        usuario_id=owner_id, metadata=meta,
    )
    return resultado["movimento"]


async def ajuste_admin(
    owner_id: str, valor: float, motivo: str, admin_email: str,
) -> dict:
    """Ajuste manual do admin (crédito se valor > 0, débito se < 0)."""
    if valor == 0:
        raise ValueError("Valor do ajuste não pode ser zero.")
    await obter_ou_criar_carteira(owner_id)
    resultado = await _aplicar_movimento(
        owner_id=owner_id, tipo="ajuste", valor=float(valor),
        descricao=f"Ajuste manual: {motivo}",
        usuario_id=admin_email,
        metadata={"origem": "ajuste_admin", "motivo": motivo, "admin": admin_email},
    )
    return resultado


async def listar_movimentos(
    owner_id: str, limit: int = 50, skip: int = 0,
    tipo: Optional[str] = None,
) -> dict:
    query = {"owner_id": owner_id}
    if tipo:
        query["tipo"] = tipo
    total = await db.carteira_movimentos.count_documents(query)
    cursor = db.carteira_movimentos.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
    itens = await cursor.to_list(limit)
    return {"itens": itens, "total": total, "limit": limit, "skip": skip}


async def dashboard_admin() -> dict:
    """Estatísticas globais para o painel admin."""
    total_carteiras = await db.carteiras.count_documents({})

    # Saldo total distribuído + totais acumulados
    pipeline_saldos = [{
        "$group": {
            "_id": None,
            "saldo_total": {"$sum": "$saldo"},
            "total_recargas": {"$sum": "$total_recargas"},
            "total_consumo": {"$sum": "$total_consumo"},
        }
    }]
    ag = await db.carteiras.aggregate(pipeline_saldos).to_list(1)
    resumo_carteiras = ag[0] if ag else {"saldo_total": 0, "total_recargas": 0, "total_consumo": 0}

    # Receita últimos 30 dias (recargas)
    inicio_30d = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    pipeline_receita = [
        {"$match": {"tipo": "recarga", "created_at": {"$gte": inicio_30d}}},
        {"$group": {"_id": None, "total": {"$sum": "$valor"}, "qtd": {"$sum": 1}}},
    ]
    ag_rec = await db.carteira_movimentos.aggregate(pipeline_receita).to_list(1)
    receita_30d = ag_rec[0] if ag_rec else {"total": 0, "qtd": 0}

    # Consumo últimos 30 dias por tipo
    pipeline_consumo = [
        {"$match": {"tipo": "consumo", "created_at": {"$gte": inicio_30d}}},
        {"$group": {
            "_id": "$metadata.tipo_consulta",
            "valor_total": {"$sum": {"$abs": "$valor"}},
            "qtd": {"$sum": 1},
        }},
        {"$sort": {"valor_total": -1}},
    ]
    consumo_por_tipo = await db.carteira_movimentos.aggregate(pipeline_consumo).to_list(20)

    return {
        "total_carteiras": total_carteiras,
        "saldo_total": round(float(resumo_carteiras.get("saldo_total", 0)), 2),
        "recargas_acumuladas": round(float(resumo_carteiras.get("total_recargas", 0)), 2),
        "consumo_acumulado": round(float(resumo_carteiras.get("total_consumo", 0)), 2),
        "receita_30d": {
            "total": round(float(receita_30d.get("total", 0)), 2),
            "qtd": receita_30d.get("qtd", 0),
        },
        "consumo_30d_por_tipo": [
            {"tipo": c["_id"] or "desconhecido",
             "valor_total": round(float(c["valor_total"]), 2),
             "qtd": c["qtd"]}
            for c in consumo_por_tipo
        ],
    }


async def listar_carteiras_admin(
    limit: int = 50, skip: int = 0, busca: Optional[str] = None,
    ordenar_por: str = "saldo",
) -> dict:
    """Lista carteiras com dados do dono para o admin."""
    match = {}
    if busca:
        # buscar dono por email/nome primeiro
        regex = {"$regex": re.escape(busca), "$options": "i"}
        usuarios = await db.usuarios.find(
            {"$or": [{"email": regex}, {"nome": regex}]},
            {"_id": 0, "id": 1}
        ).to_list(200)
        ids = [u["id"] for u in usuarios]
        match["owner_id"] = {"$in": ids}

    total = await db.carteiras.count_documents(match)
    sort_field = "saldo" if ordenar_por not in ("saldo", "total_recargas", "total_consumo", "updated_at") else ordenar_por
    cursor = db.carteiras.find(match, {"_id": 0}).sort(sort_field, -1).skip(skip).limit(limit)
    carteiras = await cursor.to_list(limit)

    # Enriquecer com dados do dono
    ids_donos = [c["owner_id"] for c in carteiras]
    donos = await db.usuarios.find(
        {"id": {"$in": ids_donos}},
        {"_id": 0, "id": 1, "nome": 1, "email": 1, "plano": 1, "plano_ativo": 1}
    ).to_list(len(ids_donos))
    mapa = {d["id"]: d for d in donos}

    itens = []
    for c in carteiras:
        dono = mapa.get(c["owner_id"], {})
        itens.append({
            **c,
            "dono": {
                "id": c["owner_id"],
                "nome": dono.get("nome", "—"),
                "email": dono.get("email", "—"),
                "plano": dono.get("plano", "—"),
                "plano_ativo": dono.get("plano_ativo", False),
            }
        })
    return {"itens": itens, "total": total, "limit": limit, "skip": skip}
