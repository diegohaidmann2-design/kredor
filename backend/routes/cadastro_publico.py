"""
Cadastro Público de Clientes + Fluxo de Aprovação.
- O dono gera um link público (token).
- O cliente preenche a ficha sem login.
- O dono revisa e aprova (vira cliente) ou rejeita.
- Anexos (selfie, doc frente/verso, assinatura) são coletados no cadastro
  público via multipart e servidos apenas ao dono (isolamento por usuario_id).
"""
import asyncio
import io
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pymongo.errors import DuplicateKeyError

from config import db, APP_URL
from models.usuario import Usuario
from services.auth import get_current_user
from services.auth_utils import get_user_context
from services.auditoria import registrar_auditoria
from services.logging_service import get_logger
from utils.validators import (
    sanitize_html, validate_cpf_cnpj, normalize_cpf_cnpj,
    validate_phone, normalize_phone,
)
from services.notificacao_service import criar_notificacao
from services.portal_service import PortalService
from services.object_storage import put_object, get_object, APP_NAME
from services.ficha_cadastral_pdf import gerar_ficha_cadastral_pdf

router = APIRouter()
logger = get_logger("gestorcred.cadastro_publico")


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------

class EnderecoIn(BaseModel):
    rua: Optional[str] = Field(default="", max_length=200)
    numero: Optional[str] = Field(default="", max_length=20)
    complemento: Optional[str] = Field(default="", max_length=100)
    bairro: Optional[str] = Field(default="", max_length=100)
    cidade: Optional[str] = Field(default="", max_length=100)
    estado: Optional[str] = Field(default="", max_length=2)
    cep: Optional[str] = Field(default="", max_length=10)


class SolicitacaoIn(BaseModel):
    nome: str = Field(..., min_length=3, max_length=200)
    cpf_cnpj: Optional[str] = Field(None, max_length=18)
    telefone: str = Field(..., min_length=10, max_length=20)
    email: Optional[str] = Field(None, max_length=200)
    endereco: Optional[EnderecoIn] = None
    observacoes: Optional[str] = Field(None, max_length=1000)
    renda_mensal: Optional[str] = Field(None, max_length=50)
    tipo_emprego: Optional[str] = Field(None, max_length=100)
    valor_emprestimo: Optional[str] = Field(None, max_length=50)


class RejeitarIn(BaseModel):
    motivo: Optional[str] = Field(None, max_length=500)


def _link_url(token: str) -> str:
    base = (APP_URL or "").rstrip("/")
    return f"{base}/cadastro/{token}"


# ---------------------------------------------------------------------------
# Constantes de anexos
# ---------------------------------------------------------------------------

# Tipos válidos de anexo (chave no doc + sufixo no storage)
TIPOS_ANEXO = {"selfie", "doc_frente", "doc_verso", "assinatura"}
# Mimes permitidos (assinatura vem como image/png do canvas)
ALLOWED_ANEXO_MIMES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
ALLOWED_ANEXO_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
# Limites — após compressão no browser, mas validados no servidor também
MAX_ANEXO_SIZE = 4 * 1024 * 1024          # 4 MB por foto
MAX_ASSINATURA_SIZE = 500 * 1024          # 500 KB
MAX_MULTIPART_TOTAL = 15 * 1024 * 1024    # 15 MB total

MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
EXT_TO_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

# Versão do termo LGPD exibido no formulário
TERMO_VERSAO = "v1-2026-09"

# Rate limit específico do cadastro público (por IP, janela de 1 min)
CADASTRO_PUBLICO_RATE_LIMIT = 10  # req/min


def _get_client_ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _check_cadastro_rate_limit(request: Request) -> None:
    """Rate limit dedicado para o endpoint público de cadastro (anti-spam de fichas)."""
    ip = _get_client_ip(request)
    now = datetime.now(timezone.utc)
    bucket = int(now.timestamp() // 60)
    key = f"cadastro_publico:{ip}:{bucket}"
    try:
        from pymongo import ReturnDocument
        doc = await db.rate_limits.find_one_and_update(
            {"_id": key},
            {
                "$inc": {"count": 1},
                "$setOnInsert": {
                    "ip": ip,
                    "expire_at": now + timedelta(seconds=120),
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        # Corrige expire_at se timedelta acima falhar por fuso (fallback simples)
        if doc and doc.get("count", 0) > CADASTRO_PUBLICO_RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Muitas solicitações. Aguarde um minuto e tente novamente.")
    except HTTPException:
        raise
    except Exception:
        # Fail-open: não derrubar cadastro por falha no rate limit
        pass


def _validar_imagem_bytes(data: bytes) -> None:
    """Verifica se bytes são imagem real via Pillow (anti MIME spoof)."""
    if not data or len(data) < 16:
        raise HTTPException(status_code=400, detail="Arquivo de imagem inválido ou vazio.")
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        img.verify()
        # verify() consome o arquivo; re-abrir para checar formato se necessário
        img2 = Image.open(io.BytesIO(data))
        fmt = (img2.format or "").upper()
        if fmt not in ("JPEG", "JPG", "PNG", "WEBP"):
            raise HTTPException(status_code=400, detail="Formato de imagem não permitido. Use JPG, PNG ou WEBP.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Arquivo de imagem inválido.")


def _extensao_para_mime(ext: str) -> str:
    return EXT_TO_MIME.get(ext.lower(), "image/jpeg")


def _mime_para_extensao(mime: str) -> str:
    return MIME_TO_EXT.get((mime or "").lower(), ".jpg")


async def _salvar_anexo(usuario_id: str, solicitacao_id: str, tipo: str, data: bytes, content_type: str) -> dict:
    """Persiste um anexo no object_storage e retorna metadados para o doc."""
    if tipo not in TIPOS_ANEXO:
        raise HTTPException(status_code=400, detail=f"Tipo de anexo inválido: {tipo}")
    if content_type not in ALLOWED_ANEXO_MIMES:
        # Tentar inferir pelo conteúdo se mime vier genérico
        if content_type in ("application/octet-stream", "binary/octet-stream", ""):
            content_type = "image/jpeg"
        else:
            raise HTTPException(status_code=400, detail=f"Tipo de arquivo não permitido: {content_type}")
    limite = MAX_ASSINATURA_SIZE if tipo == "assinatura" else MAX_ANEXO_SIZE
    if len(data) > limite:
        raise HTTPException(status_code=400, detail=f"Arquivo {tipo} excede o limite de {limite // 1024}KB.")
    _validar_imagem_bytes(data)
    ext = _mime_para_extensao(content_type)
    # Path determinístico e não-enumerável (uuid já no solicitacao_id)
    storage_path = f"{APP_NAME}/cadastro-publico/{usuario_id}/{solicitacao_id}/{tipo}{ext}"
    # put_object é síncrono (IO em disco ou requests) — rodar em thread
    await asyncio.to_thread(put_object, storage_path, data, content_type)
    return {
        "path": storage_path,
        "content_type": content_type,
        "size": len(data),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


# ==================== DONO: LINK ====================

@router.get("/link")
async def obter_link(current_user: Usuario = Depends(get_current_user)):
    """Obtém (ou cria) o token público do dono e retorna a URL de cadastro."""
    context_id = get_user_context(current_user)
    usuario = await db.usuarios.find_one({"id": context_id})
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    token = usuario.get("cadastro_publico_token")
    if not token:
        token = secrets.token_urlsafe(8)
        await db.usuarios.update_one({"id": context_id}, {"$set": {"cadastro_publico_token": token}})

    return {"token": token, "url": _link_url(token)}


@router.post("/regenerar-link")
async def regenerar_link(current_user: Usuario = Depends(get_current_user)):
    """Gera um novo token, invalidando o link anterior."""
    context_id = get_user_context(current_user)
    token = secrets.token_urlsafe(8)
    await db.usuarios.update_one({"id": context_id}, {"$set": {"cadastro_publico_token": token}})
    return {"token": token, "url": _link_url(token)}


# ==================== PÚBLICO ====================

@router.get("/info/{token}")
async def info_publica(token: str):
    """Retorna dados básicos para renderizar o formulário público (sem auth)."""
    usuario = await db.usuarios.find_one({"cadastro_publico_token": token})
    if not usuario:
        raise HTTPException(status_code=404, detail="Link inválido ou expirado")
    titulo = usuario.get("nome_fantasia") or usuario.get("nome_exibicao") or usuario.get("nome") or "Kredor"
    return {"empresa": titulo, "valido": True}


@router.post("/solicitar/{token}")
async def enviar_solicitacao(token: str, request: Request):
    """
    Recebe a ficha preenchida pelo cliente (sem auth).

    Suporta dois Content-Types:
    - application/json  → fluxo legado (sem anexos)
    - multipart/form-data → com anexos (selfie, doc_frente, doc_verso, assinatura) + consentimento
    """
    # Rate limit antes de qualquer processamento pesado
    await _check_cadastro_rate_limit(request)

    usuario = await db.usuarios.find_one({"cadastro_publico_token": token})
    if not usuario:
        raise HTTPException(status_code=404, detail="Link inválido ou expirado")

    context_id = usuario["id"]
    content_type_header = (request.headers.get("content-type") or "").lower()

    # ------------------------------------------------------------------
    # Parse multipart vs JSON
    # ------------------------------------------------------------------
    anexos_meta: dict = {}
    consentimento_meta = None
    dados_dict: dict

    if "multipart/form-data" in content_type_header:
        # --- MULTIPART (com anexos) ---
        # Verificar tamanho total aproximado via Content-Length
        try:
            clen = int(request.headers.get("content-length") or 0)
            if clen and clen > MAX_MULTIPART_TOTAL:
                raise HTTPException(status_code=413, detail="Ficha muito grande. Reduza o tamanho das fotos.")
        except HTTPException:
            raise
        except Exception:
            pass

        form = await request.form()

        # Campos de texto
        nome = (form.get("nome") or "").strip()
        cpf_cnpj = (form.get("cpf_cnpj") or "").strip() or None
        telefone = (form.get("telefone") or "").strip()
        email = (form.get("email") or "").strip() or None
        rua = (form.get("rua") or "").strip()
        numero = (form.get("numero") or "").strip()
        complemento = (form.get("complemento") or "").strip()
        bairro = (form.get("bairro") or "").strip()
        cidade = (form.get("cidade") or "").strip()
        estado = (form.get("estado") or "").strip()
        cep = (form.get("cep") or "").strip()
        observacoes = (form.get("observacoes") or "").strip() or None
        consentimento_raw = (form.get("consentimento") or "").strip().lower()
        versao_termo = (form.get("versao_termo") or TERMO_VERSAO).strip()[:50]

        dados_dict = {
            "nome": nome,
            "cpf_cnpj": cpf_cnpj,
            "telefone": telefone,
            "email": email,
            "endereco": {
                "rua": rua, "numero": numero, "complemento": complemento,
                "bairro": bairro, "cidade": cidade, "estado": estado, "cep": cep,
            },
            "observacoes": observacoes,
            "renda_mensal": (form.get("renda_mensal") or "").strip() or None,
            "tipo_emprego": (form.get("tipo_emprego") or "").strip() or None,
            "valor_emprestimo": (form.get("valor_emprestimo") or "").strip() or None,
        }

        # Consentimento LGPD — se houver qualquer anexo, consentimento é obrigatório
        consentimento_aceito = consentimento_raw in ("true", "1", "on", "sim", "yes")
        # Guardar temporariamente; validar após saber se há anexos
        _consentimento_aceito = consentimento_aceito
        _versao_termo = versao_termo

        # Arquivos — chaves esperadas: selfie, doc_frente, doc_verso, assinatura
        # form.get retorna UploadFile ou str; filtrar apenas UploadFile com filename
        arquivos = {}
        for tipo in TIPOS_ANEXO:
            maybe = form.get(tipo)
            # Starlette pode retornar string vazia se campo não enviado
            if maybe is not None and hasattr(maybe, "filename") and getattr(maybe, "filename", None):
                arquivos[tipo] = maybe

        # Se houver anexos mas sem consentimento → 400
        if arquivos and not _consentimento_aceito:
            raise HTTPException(status_code=400, detail="É necessário autorizar o uso das imagens e documentos para enviar anexos.")

        # Guardar para persistir após validações de CPF/telefone e criação do doc
        # (precisamos do solicitacao_id antes de salvar no storage)
        _arquivos_pendentes = arquivos
        if _consentimento_aceito:
            consentimento_meta = {
                "aceito": True,
                "versao_termo": _versao_termo,
                "aceito_em": datetime.now(timezone.utc).isoformat(),
                "ip": _get_client_ip(request),
                "user_agent": (request.headers.get("user-agent") or "")[:500],
            }
        else:
            consentimento_meta = None
    else:
        # --- JSON legado ---
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Corpo da requisição inválido.")
        # Validar via Pydantic para manter mensagens consistentes
        try:
            dados_validados = SolicitacaoIn.model_validate(body)
        except Exception as e:
            # Extrair primeira mensagem de validação
            msg = str(e)
            # Tentar pegar detail mais amigável
            if hasattr(e, "errors"):
                try:
                    errs = e.errors()
                    if errs:
                        msg = errs[0].get("msg", msg)
                except Exception:
                    pass
            raise HTTPException(status_code=422, detail=msg)
        dados_dict = {
            "nome": dados_validados.nome,
            "cpf_cnpj": dados_validados.cpf_cnpj,
            "telefone": dados_validados.telefone,
            "email": dados_validados.email,
            "endereco": dados_validados.endereco.model_dump() if dados_validados.endereco else {},
            "observacoes": dados_validados.observacoes,
            "renda_mensal": dados_validados.renda_mensal,
            "tipo_emprego": dados_validados.tipo_emprego,
            "valor_emprestimo": dados_validados.valor_emprestimo,
        }
        _arquivos_pendentes = {}
        consentimento_meta = None

    # ------------------------------------------------------------------
    # Validações de negócio (comuns aos dois fluxos)
    # ------------------------------------------------------------------
    nome_val = dados_dict.get("nome") or ""
    if len(nome_val.strip()) < 3:
        raise HTTPException(status_code=400, detail="Informe o nome completo (mín. 3 letras).")
    cpf = None
    cpf_raw = dados_dict.get("cpf_cnpj")
    if cpf_raw:
        if not validate_cpf_cnpj(cpf_raw):
            raise HTTPException(status_code=400, detail="CPF/CNPJ inválido")
        cpf = normalize_cpf_cnpj(cpf_raw)
    telefone_raw = dados_dict.get("telefone") or ""
    if not validate_phone(telefone_raw):
        raise HTTPException(status_code=400, detail="Telefone inválido")
    telefone = normalize_phone(telefone_raw)

    # Evitar duplicidade de solicitação pendente pelo mesmo CPF
    if cpf:
        dup = await db.solicitacoes_cadastro.find_one({
            "usuario_id": context_id, "cpf_cnpj": cpf, "status": "pendente"
        })
        if dup:
            raise HTTPException(status_code=400, detail="Já existe uma solicitação pendente com este CPF/CNPJ")

    endereco_dict = dados_dict.get("endereco") or {}
    # Normalizar endereco vindo do multipart (flat) vs JSON (nested)
    if isinstance(endereco_dict, dict) and "rua" not in endereco_dict and any(k in endereco_dict for k in ("rua","cidade")):
        pass  # já está no formato correto
    # Se endereco veio como dict com chaves vazias, manter como está

    agora = datetime.now(timezone.utc)
    solicitacao_id = str(uuid.uuid4())

    # ------------------------------------------------------------------
    # Salvar anexos no storage (se houver) — antes de inserir o doc para
    # falhar cedo se algum arquivo for inválido; se falhar, nada foi inserido.
    # ------------------------------------------------------------------
    if "_arquivos_pendentes" in locals() and _arquivos_pendentes:
        for tipo, upfile in _arquivos_pendentes.items():
            try:
                data = await upfile.read()
            except Exception:
                raise HTTPException(status_code=400, detail=f"Não foi possível ler o arquivo {tipo}.")
            # content_type do UploadFile pode vir como None
            ctype = (getattr(upfile, "content_type", None) or "image/jpeg").lower()
            # Normalizar image/jpg → image/jpeg
            if ctype == "image/jpg":
                ctype = "image/jpeg"
            if ctype not in ALLOWED_ANEXO_MIMES:
                # Tentar inferir pela extensão do filename
                import os
                ext = os.path.splitext(getattr(upfile, "filename", "") or "")[1].lower()
                if ext in ALLOWED_ANEXO_EXTS:
                    ctype = _extensao_para_mime(ext)
                else:
                    raise HTTPException(status_code=400, detail=f"Tipo de arquivo não permitido para {tipo}. Use JPG, PNG ou WEBP.")
            meta = await _salvar_anexo(context_id, solicitacao_id, tipo, data, ctype)
            anexos_meta[tipo] = meta

    doc = {
        "id": solicitacao_id,
        "usuario_id": context_id,
        "nome": sanitize_html(nome_val),
        "cpf_cnpj": cpf,
        "telefone": telefone,
        "email": dados_dict.get("email"),
        "endereco": endereco_dict,
        "observacoes": sanitize_html(dados_dict.get("observacoes")) if dados_dict.get("observacoes") else None,
        "renda_mensal": sanitize_html(dados_dict.get("renda_mensal")) if dados_dict.get("renda_mensal") else None,
        "tipo_emprego": sanitize_html(dados_dict.get("tipo_emprego")) if dados_dict.get("tipo_emprego") else None,
        "valor_emprestimo": sanitize_html(dados_dict.get("valor_emprestimo")) if dados_dict.get("valor_emprestimo") else None,
        "status": "pendente",
        "origem": "link_publico",
        "created_at": agora.isoformat(),
        "anexos": anexos_meta if anexos_meta else None,
        "consentimento": consentimento_meta,
    }
    await db.solicitacoes_cadastro.insert_one(doc)

    # Notificar o dono
    try:
        await criar_notificacao(
            usuario_id=context_id,
            tipo="cadastro",
            titulo="Novo cadastro para aprovar",
            mensagem=f"{doc['nome']} enviou uma ficha de cadastro.",
            link="/aprovacoes",
        )
    except Exception as e:
        logger.warning(f"Não foi possível notificar novo cadastro: {e}")

    logger.info("Solicitação de cadastro recebida", data={"usuario_id": context_id, "nome": doc["nome"], "anexos": list(anexos_meta.keys()) if anexos_meta else []})
    return {"message": "Cadastro enviado com sucesso! Aguarde a aprovação.", "id": doc["id"]}


# ==================== DONO: SOLICITAÇÕES ====================

@router.get("/solicitacoes")
async def listar_solicitacoes(status: Optional[str] = None, current_user: Usuario = Depends(get_current_user)):
    """Lista as solicitações de cadastro do dono."""
    context_id = get_user_context(current_user)
    query = {"usuario_id": context_id}
    if status:
        query["status"] = status
    docs = await db.solicitacoes_cadastro.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return docs


@router.get("/solicitacoes/contador")
async def contador_pendentes(current_user: Usuario = Depends(get_current_user)):
    """Conta solicitações pendentes (para badge)."""
    context_id = get_user_context(current_user)
    n = await db.solicitacoes_cadastro.count_documents({"usuario_id": context_id, "status": "pendente"})
    return {"pendentes": n}


@router.get("/solicitacoes/{solicitacao_id}/anexo/{tipo}")
async def obter_anexo(solicitacao_id: str, tipo: str, current_user: Usuario = Depends(get_current_user)):
    """
    Serve um anexo da solicitação. Acesso restrito ao dono (usuario_id).
    Tipo: selfie | doc_frente | doc_verso | assinatura
    """
    if tipo not in TIPOS_ANEXO:
        raise HTTPException(status_code=404, detail="Tipo de anexo não encontrado")
    context_id = get_user_context(current_user)
    sol = await db.solicitacoes_cadastro.find_one({"id": solicitacao_id, "usuario_id": context_id}, {"_id": 0})
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    anexos = sol.get("anexos") or {}
    meta = anexos.get(tipo)
    if not meta or not meta.get("path"):
        raise HTTPException(status_code=404, detail="Anexo não encontrado")
    path = meta["path"]
    try:
        data, content_type = await asyncio.to_thread(get_object, path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    except Exception as e:
        logger.warning(f"Erro ao servir anexo {tipo} de {solicitacao_id}: {e}")
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    # Usar content_type do meta se disponível, senão do storage
    ct = meta.get("content_type") or content_type or "image/jpeg"
    return Response(content=data, media_type=ct, headers={
        "Cache-Control": "private, max-age=3600",
        "Content-Disposition": f'inline; filename="{tipo}{_mime_para_extensao(ct)}"',
    })


@router.get("/clientes/{cliente_id}/anexo/{tipo}")
async def obter_anexo_cliente(cliente_id: str, tipo: str, current_user: Usuario = Depends(get_current_user)):
    """Serve anexo copiado para o cliente após aprovação."""
    if tipo not in TIPOS_ANEXO:
        raise HTTPException(status_code=404, detail="Tipo de anexo não encontrado")
    context_id = get_user_context(current_user)
    cli = await db.clientes.find_one({"id": cliente_id, "usuario_id": context_id}, {"_id": 0})
    if not cli:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    anexos_cadastro = cli.get("anexos_cadastro") or {}
    anexos = anexos_cadastro.get("anexos") or {}
    meta = anexos.get(tipo)
    if not meta or not meta.get("path"):
        raise HTTPException(status_code=404, detail="Anexo não encontrado")
    path = meta["path"]
    try:
        data, content_type = await asyncio.to_thread(get_object, path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    except Exception as e:
        logger.warning(f"Erro ao servir anexo cliente {tipo} de {cliente_id}: {e}")
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    ct = meta.get("content_type") or content_type or "image/jpeg"
    return Response(content=data, media_type=ct, headers={
        "Cache-Control": "private, max-age=3600",
        "Content-Disposition": f'inline; filename="{tipo}{_mime_para_extensao(ct)}"',
    })


@router.post("/solicitacoes/{solicitacao_id}/aprovar")
async def aprovar_solicitacao(solicitacao_id: str, request: Request, current_user: Usuario = Depends(get_current_user)):
    """Aprova a solicitação e cria o cliente."""
    context_id = get_user_context(current_user)
    sol = await db.solicitacoes_cadastro.find_one({"id": solicitacao_id, "usuario_id": context_id})
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    if sol.get("status") != "pendente":
        raise HTTPException(status_code=400, detail="Solicitação já foi processada")

    agora = datetime.now(timezone.utc)
    # Tentar reaproveitar cliente se for o mesmo CPF (mesmo que excluído)
    cliente_id = None
    existing_id = None
    if sol.get("cpf_cnpj"):
        existing = await db.clientes.find_one({
            "cpf_cnpj": sol["cpf_cnpj"],
            "usuario_id": context_id,
        })
        if existing:
            if not existing.get("deleted"):
                 raise HTTPException(status_code=400, detail="Já existe um cliente ativo com este CPF/CNPJ")
            # Se estava deletado, vamos reativar e atualizar com os dados novos da ficha
            existing_id = existing["id"]
            cliente_id = existing_id

    if not cliente_id:
        cliente_id = str(uuid.uuid4())

    cliente_doc = {
        "id": cliente_id,
        "usuario_id": context_id,
        "nome": sol.get("nome"),
        "cpf_cnpj": sol.get("cpf_cnpj"),
        "telefone": sol.get("telefone"),
        "email": sol.get("email"),
        "endereco": sol.get("endereco") or {},
        "observacoes": sol.get("observacoes"),
        # Campos financeiros preenchidos no cadastro público
        "renda_mensal": sol.get("renda_mensal"),
        "tipo_emprego": sol.get("tipo_emprego"),
        "valor_emprestimo": sol.get("valor_emprestimo"),
        "status": "ativo",
        "created_at": agora.isoformat() if not existing_id else existing.get("created_at"),
        "updated_at": agora.isoformat(),
        "created_by": sol.get("created_by") if existing_id else current_user.email,
        "origem": "cadastro_publico",
        "deleted": False,
    }
    # Copiar referência dos anexos (sem duplicar bytes) se existirem
    if sol.get("anexos"):
        cliente_doc["anexos_cadastro"] = {
            "solicitacao_id": solicitacao_id,
            "anexos": sol.get("anexos"),
            "consentimento": sol.get("consentimento"),
        }
    try:
        if existing_id:
            await db.clientes.replace_one({"id": existing_id, "usuario_id": context_id}, cliente_doc)
        else:
            await db.clientes.insert_one(cliente_doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Já existe um cliente ativo com este CPF/CNPJ")

    await db.solicitacoes_cadastro.update_one(
        {"id": solicitacao_id},
        {"$set": {"status": "aprovado", "cliente_id": cliente_id, "processado_em": agora.isoformat(), "processado_por": current_user.email}},
    )

    # Gerar código de portal (não bloqueante)
    try:
        await PortalService(db).criar_ou_atualizar_codigo(cliente_id=cliente_id, usuario_id=context_id)
    except Exception as e:
        logger.warning(f"Erro ao gerar código de portal na aprovação: {e}")

    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="aprovar",
        entidade="cadastro_publico",
        entidade_id=solicitacao_id,
        detalhes=f"Aprovou cadastro público: {sol.get('nome')}",
        dados_novos={"cliente_id": cliente_id, "anexos": list((sol.get("anexos") or {}).keys())},
        ip=request.client.host if request.client else None,
    )
    return {"message": "Cadastro aprovado e cliente criado!", "cliente_id": cliente_id}


@router.post("/solicitacoes/{solicitacao_id}/rejeitar")
async def rejeitar_solicitacao(solicitacao_id: str, dados: RejeitarIn, request: Request, current_user: Usuario = Depends(get_current_user)):
    """Rejeita a solicitação."""
    context_id = get_user_context(current_user)
    sol = await db.solicitacoes_cadastro.find_one({"id": solicitacao_id, "usuario_id": context_id})
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    if sol.get("status") != "pendente":
        raise HTTPException(status_code=400, detail="Solicitação já foi processada")

    agora = datetime.now(timezone.utc)
    await db.solicitacoes_cadastro.update_one(
        {"id": solicitacao_id},
        {"$set": {"status": "rejeitado", "motivo_rejeicao": sanitize_html(dados.motivo) if dados.motivo else None,
                  "processado_em": agora.isoformat(), "processado_por": current_user.email}},
    )
    return {"message": "Cadastro rejeitado"}


@router.delete("/solicitacoes/{solicitacao_id}")
async def excluir_solicitacao(solicitacao_id: str, current_user: Usuario = Depends(get_current_user)):
    """Remove uma solicitação (limpeza)."""
    context_id = get_user_context(current_user)
    res = await db.solicitacoes_cadastro.delete_one({"id": solicitacao_id, "usuario_id": context_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    return {"message": "Solicitação removida"}


@router.get("/solicitacoes/{solicitacao_id}/pdf")
async def exportar_solicitacao_pdf(solicitacao_id: str, current_user: Usuario = Depends(get_current_user)):
    """
    Gera e exporta a Ficha Cadastral completa da solicitação em PDF.
    Acesso restrito ao dono / membro com permissão.
    """
    context_id = get_user_context(current_user)
    sol = await db.solicitacoes_cadastro.find_one({"id": solicitacao_id, "usuario_id": context_id}, {"_id": 0})
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")

    usuario = await db.usuarios.find_one({"id": context_id}, {"_id": 0, "nome": 1})
    empresa_nome = (usuario or {}).get("nome") or "Kredor"

    try:
        pdf_bytes = await asyncio.to_thread(gerar_ficha_cadastral_pdf, sol, empresa_nome)
    except Exception as e:
        logger.error(f"Erro ao gerar PDF da solicitação {solicitacao_id}: {e}")
        raise HTTPException(status_code=500, detail="Não foi possível gerar a ficha em PDF")

    nome_seguro = "".join(c for c in sol.get("nome", "cliente") if c.isalnum() or c in ("-", "_")).strip() or "cliente"
    filename = f"ficha-cadastral-{nome_seguro}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Cache-Control": "private, no-cache",
            "Content-Disposition": f'inline; filename="{filename}"',
        }
    )


@router.get("/clientes/{cliente_id}/ficha-pdf")
async def exportar_ficha_cliente_pdf(cliente_id: str, current_user: Usuario = Depends(get_current_user)):
    """
    Gera e exporta a Ficha Cadastral em PDF para um cliente aprovado.
    """
    context_id = get_user_context(current_user)
    cli = await db.clientes.find_one({"id": cliente_id, "usuario_id": context_id}, {"_id": 0})
    if not cli:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    anexos_cad = cli.get("anexos_cadastro") or {}
    sol_synth = {
        "id": anexos_cad.get("solicitacao_id") or cli.get("id"),
        "nome": cli.get("nome"),
        "cpf_cnpj": cli.get("cpf_cnpj"),
        "telefone": cli.get("telefone"),
        "email": cli.get("email"),
        "endereco": cli.get("endereco") or {},
        "observacoes": cli.get("observacoes"),
        "status": "aprovado",
        "origem": cli.get("origem") or "Cadastro",
        "created_at": cli.get("created_at"),
        "anexos": anexos_cad.get("anexos") or {},
        "consentimento": anexos_cad.get("consentimento") or {},
    }

    usuario = await db.usuarios.find_one({"id": context_id}, {"_id": 0, "nome": 1})
    empresa_nome = (usuario or {}).get("nome") or "Kredor"

    try:
        pdf_bytes = await asyncio.to_thread(gerar_ficha_cadastral_pdf, sol_synth, empresa_nome)
    except Exception as e:
        logger.error(f"Erro ao gerar PDF do cliente {cliente_id}: {e}")
        raise HTTPException(status_code=500, detail="Não foi possível gerar a ficha em PDF")

    nome_seguro = "".join(c for c in cli.get("nome", "cliente") if c.isalnum() or c in ("-", "_")).strip() or "cliente"
    filename = f"ficha-cadastral-{nome_seguro}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Cache-Control": "private, no-cache",
            "Content-Disposition": f'inline; filename="{filename}"',
        }
    )

