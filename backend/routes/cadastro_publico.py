"""
Cadastro Público de Clientes + Fluxo de Aprovação.
- O dono gera um link público (token).
- O cliente preenche a ficha sem login.
- O dono revisa e aprova (vira cliente) ou rejeita.
"""
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional

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

router = APIRouter()
logger = get_logger("gestorcred.cadastro_publico")


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


class RejeitarIn(BaseModel):
    motivo: Optional[str] = Field(None, max_length=500)


def _link_url(token: str) -> str:
    base = (APP_URL or "").rstrip("/")
    return f"{base}/cadastro/{token}"


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
    return {"empresa": usuario.get("nome") or "Kredor", "valido": True}


@router.post("/solicitar/{token}")
async def enviar_solicitacao(token: str, dados: SolicitacaoIn, request: Request):
    """Recebe a ficha preenchida pelo cliente (sem auth)."""
    usuario = await db.usuarios.find_one({"cadastro_publico_token": token})
    if not usuario:
        raise HTTPException(status_code=404, detail="Link inválido ou expirado")

    context_id = usuario["id"]

    # Validações
    cpf = None
    if dados.cpf_cnpj:
        if not validate_cpf_cnpj(dados.cpf_cnpj):
            raise HTTPException(status_code=400, detail="CPF/CNPJ inválido")
        cpf = normalize_cpf_cnpj(dados.cpf_cnpj)
    if not validate_phone(dados.telefone):
        raise HTTPException(status_code=400, detail="Telefone inválido")
    telefone = normalize_phone(dados.telefone)

    # Evitar duplicidade de solicitação pendente pelo mesmo CPF
    if cpf:
        dup = await db.solicitacoes_cadastro.find_one({
            "usuario_id": context_id, "cpf_cnpj": cpf, "status": "pendente"
        })
        if dup:
            raise HTTPException(status_code=400, detail="Já existe uma solicitação pendente com este CPF/CNPJ")

    agora = datetime.now(timezone.utc)
    doc = {
        "id": str(uuid.uuid4()),
        "usuario_id": context_id,
        "nome": sanitize_html(dados.nome),
        "cpf_cnpj": cpf,
        "telefone": telefone,
        "email": dados.email,
        "endereco": dados.endereco.model_dump() if dados.endereco else {},
        "observacoes": sanitize_html(dados.observacoes) if dados.observacoes else None,
        "status": "pendente",
        "origem": "link_publico",
        "created_at": agora.isoformat(),
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

    logger.info("Solicitação de cadastro recebida", data={"usuario_id": context_id, "nome": doc["nome"]})
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


@router.post("/solicitacoes/{solicitacao_id}/aprovar")
async def aprovar_solicitacao(solicitacao_id: str, request: Request, current_user: Usuario = Depends(get_current_user)):
    """Aprova a solicitação e cria o cliente."""
    context_id = get_user_context(current_user)
    sol = await db.solicitacoes_cadastro.find_one({"id": solicitacao_id, "usuario_id": context_id})
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")
    if sol.get("status") != "pendente":
        raise HTTPException(status_code=400, detail="Solicitação já foi processada")

    # Verificar CPF duplicado nos clientes existentes
    if sol.get("cpf_cnpj"):
        existing = await db.clientes.find_one({
            "cpf_cnpj": sol["cpf_cnpj"],
            "usuario_id": context_id,
            "$or": [{"deleted": {"$exists": False}}, {"deleted": False}],
        })
        if existing:
            raise HTTPException(status_code=400, detail="Já existe um cliente com este CPF/CNPJ")

    agora = datetime.now(timezone.utc)
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
        "status": "ativo",
        "created_at": agora.isoformat(),
        "created_by": current_user.email,
        "origem": "cadastro_publico",
        "deleted": False,
    }
    await db.clientes.insert_one(cliente_doc)

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
        dados_novos={"cliente_id": cliente_id},
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
