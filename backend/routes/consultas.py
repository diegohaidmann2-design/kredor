"""
Rotas de Consultas (CPF, e futuramente CNPJ, telefone, etc.)
Todas as chamadas ao provedor externo são feitas no backend, com a chave
protegida em variável de ambiente. O CPF trafega no corpo (POST) para não
aparecer em logs de acesso/URL.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from config import db
from models.usuario import Usuario
from services.auth_utils import get_user_context
from services.permissao_service import verificar_plano_ativo
from services.losdados_service import consultar_cpf, LosDadosError

router = APIRouter()


class ConsultaCPFRequest(BaseModel):
    cpf: str


def _resumo_cpf(data: dict) -> dict:
    """Extrai um resumo leve para o histórico."""
    basicos = (data or {}).get("dadosBasicos") or {}
    return {
        "nome": basicos.get("nome"),
        "nascimento": basicos.get("dataNasc"),
        "faixaScore": basicos.get("faixaScore"),
    }


@router.post("/cpf")
async def consulta_cpf(
    body: ConsultaCPFRequest,
    current_user: Usuario = Depends(verificar_plano_ativo),
):
    """Realiza uma consulta de CPF e salva no histórico do usuário."""
    context_id = get_user_context(current_user)
    try:
        payload = await consultar_cpf(body.cpf)
    except LosDadosError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    data = payload.get("data") or {}
    # A API retorna {"data": {"err": "..."}} quando não encontra / inválido
    if isinstance(data, dict) and data.get("err") and len(data) == 1:
        raise HTTPException(status_code=404, detail=str(data.get("err")))

    resumo = _resumo_cpf(data)
    consulta_id = str(uuid.uuid4())
    agora = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": consulta_id,
        "usuario_id": context_id,
        "tipo": "cpf",
        "documento": "".join(c for c in body.cpf if c.isdigit()),
        "resumo": resumo,
        "data": data,
        "quota": payload.get("quota"),
        "cached": payload.get("cached", False),
        "created_at": agora,
        "created_by": current_user.email,
        "deleted": False,
    }
    await db.consultas.insert_one(doc)

    return {
        "id": consulta_id,
        "tipo": "cpf",
        "resumo": resumo,
        "data": data,
        "quota": payload.get("quota"),
        "cached": payload.get("cached", False),
        "created_at": agora,
    }


@router.get("/historico")
async def listar_historico(
    tipo: str = Query(None),
    limit: int = Query(30, ge=1, le=100),
    current_user: Usuario = Depends(verificar_plano_ativo),
):
    """Lista as consultas recentes do usuário (sem o payload completo)."""
    context_id = get_user_context(current_user)
    query = {"usuario_id": context_id, "deleted": {"$ne": True}}
    if tipo:
        query["tipo"] = tipo
    cursor = db.consultas.find(
        query,
        {"_id": 0, "id": 1, "tipo": 1, "documento": 1, "resumo": 1, "created_at": 1, "cached": 1},
    ).sort("created_at", -1).limit(limit)
    itens = await cursor.to_list(limit)
    return {"itens": itens, "total": len(itens)}


@router.get("/{consulta_id}")
async def obter_consulta(
    consulta_id: str,
    current_user: Usuario = Depends(verificar_plano_ativo),
):
    """Retorna uma consulta salva (payload completo) do próprio usuário."""
    context_id = get_user_context(current_user)
    doc = await db.consultas.find_one(
        {"id": consulta_id, "usuario_id": context_id, "deleted": {"$ne": True}},
        {"_id": 0},
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Consulta não encontrada.")
    return {
        "id": doc["id"],
        "tipo": doc.get("tipo"),
        "resumo": doc.get("resumo"),
        "data": doc.get("data"),
        "quota": doc.get("quota"),
        "cached": doc.get("cached", False),
        "created_at": doc.get("created_at"),
    }


@router.delete("/{consulta_id}")
async def excluir_consulta(
    consulta_id: str,
    current_user: Usuario = Depends(verificar_plano_ativo),
):
    """Remove (soft delete) uma consulta do histórico do usuário."""
    context_id = get_user_context(current_user)
    res = await db.consultas.update_one(
        {"id": consulta_id, "usuario_id": context_id},
        {"$set": {"deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat()}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Consulta não encontrada.")
    return {"success": True}
