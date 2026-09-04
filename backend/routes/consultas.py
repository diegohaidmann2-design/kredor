"""
Rotas de Consultas (CPF, e futuramente CNPJ, telefone, etc.)
Todas as chamadas ao provedor externo são feitas no backend, com a chave
protegida em variável de ambiente. O CPF trafega no corpo (POST) para não
aparecer em logs de acesso/URL.
"""
import uuid
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import db
from models.usuario import Usuario
from services.auth_utils import get_user_context
from services.permissao_service import verificar_plano_ativo
from services.losdados_service import (
    consultar_cpf, consultar_cnpj, consultar_telefone, LosDadosError,
)
from services.consulta_pdf import gerar_pdf_consulta

router = APIRouter()


class ConsultaCPFRequest(BaseModel):
    cpf: str


class ConsultaCNPJRequest(BaseModel):
    cnpj: str


class ConsultaTelefoneRequest(BaseModel):
    telefone: str


class VincularRequest(BaseModel):
    cliente_id: str
    emprestimo_id: str | None = None


def _resumo_cpf(data: dict) -> dict:
    """Extrai um resumo leve para o histórico."""
    basicos = (data or {}).get("dadosBasicos") or {}
    return {
        "nome": basicos.get("nome"),
        "nascimento": basicos.get("dataNasc"),
        "faixaScore": basicos.get("faixaScore"),
    }


def _resumo_cnpj(data: dict) -> dict:
    """Resumo leve de CNPJ para o histórico."""
    emp = (data or {}).get("dadosEmpresa") or {}
    socios = (data or {}).get("socios") or []
    return {
        "nome": emp.get("razaoSocial"),
        "porte": emp.get("porteEmpresa"),
        "natureza": emp.get("naturezaJuridica"),
        "socios": len(socios) if isinstance(socios, list) else None,
    }


def _resumo_telefone(data: dict) -> dict:
    """Resumo leve de telefone para o histórico."""
    lista = (data or {}).get("data")
    if not isinstance(lista, list):
        lista = []
    primeiro = lista[0].get("nome") if lista and isinstance(lista[0], dict) else None
    return {
        "nome": primeiro or (f"{len(lista)} resultado(s)" if lista else "Sem resultados"),
        "total": len(lista),
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
        "cliente_id": None,
        "cliente_nome": None,
        "emprestimo_id": None,
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


@router.post("/cnpj")
async def consulta_cnpj(
    body: ConsultaCNPJRequest,
    current_user: Usuario = Depends(verificar_plano_ativo),
):
    """Realiza uma consulta de CNPJ e salva no histórico do usuário."""
    context_id = get_user_context(current_user)
    try:
        payload = await consultar_cnpj(body.cnpj)
    except LosDadosError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    data = payload.get("data") or {}
    if isinstance(data, dict) and data.get("err") and len(data) == 1:
        raise HTTPException(status_code=404, detail=str(data.get("err")))

    resumo = _resumo_cnpj(data)
    consulta_id = str(uuid.uuid4())
    agora = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": consulta_id,
        "usuario_id": context_id,
        "tipo": "cnpj",
        "documento": "".join(c for c in body.cnpj if c.isdigit()),
        "resumo": resumo,
        "data": data,
        "quota": payload.get("quota"),
        "cached": payload.get("cached", False),
        "created_at": agora,
        "created_by": current_user.email,
        "cliente_id": None,
        "cliente_nome": None,
        "emprestimo_id": None,
        "deleted": False,
    }
    await db.consultas.insert_one(doc)

    return {
        "id": consulta_id,
        "tipo": "cnpj",
        "resumo": resumo,
        "data": data,
        "quota": payload.get("quota"),
        "cached": payload.get("cached", False),
        "created_at": agora,
    }


@router.post("/telefone")
async def consulta_telefone(
    body: ConsultaTelefoneRequest,
    current_user: Usuario = Depends(verificar_plano_ativo),
):
    """Realiza uma consulta de Telefone e salva no histórico do usuário."""
    context_id = get_user_context(current_user)
    try:
        payload = await consultar_telefone(body.telefone)
    except LosDadosError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    data = payload.get("data") or {}
    if isinstance(data, dict) and data.get("err") and len(data) == 1:
        raise HTTPException(status_code=404, detail=str(data.get("err")))

    resumo = _resumo_telefone(data)
    consulta_id = str(uuid.uuid4())
    agora = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": consulta_id,
        "usuario_id": context_id,
        "tipo": "telefone",
        "documento": "".join(c for c in body.telefone if c.isdigit()),
        "resumo": resumo,
        "data": data,
        "quota": payload.get("quota"),
        "cached": payload.get("cached", False),
        "created_at": agora,
        "created_by": current_user.email,
        "cliente_id": None,
        "cliente_nome": None,
        "emprestimo_id": None,
        "deleted": False,
    }
    await db.consultas.insert_one(doc)

    return {
        "id": consulta_id,
        "tipo": "telefone",
        "resumo": resumo,
        "data": data,
        "quota": payload.get("quota"),
        "cached": payload.get("cached", False),
        "created_at": agora,
    }


@router.get("/historico")
async def listar_historico(
    tipo: str = Query(None),
    cliente_id: str = Query(None),
    limit: int = Query(30, ge=1, le=100),
    current_user: Usuario = Depends(verificar_plano_ativo),
):
    """Lista as consultas recentes do usuário (sem o payload completo)."""
    context_id = get_user_context(current_user)
    query = {"usuario_id": context_id, "deleted": {"$ne": True}}
    if tipo:
        query["tipo"] = tipo
    if cliente_id:
        query["cliente_id"] = cliente_id
    cursor = db.consultas.find(
        query,
        {"_id": 0, "id": 1, "tipo": 1, "documento": 1, "resumo": 1, "created_at": 1,
         "cached": 1, "cliente_id": 1, "cliente_nome": 1},
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
        "documento": doc.get("documento"),
        "resumo": doc.get("resumo"),
        "data": doc.get("data"),
        "quota": doc.get("quota"),
        "cached": doc.get("cached", False),
        "created_at": doc.get("created_at"),
        "cliente_id": doc.get("cliente_id"),
        "cliente_nome": doc.get("cliente_nome"),
        "emprestimo_id": doc.get("emprestimo_id"),
    }


@router.post("/{consulta_id}/vincular")
async def vincular_consulta(
    consulta_id: str,
    body: VincularRequest,
    current_user: Usuario = Depends(verificar_plano_ativo),
):
    """Vincula uma consulta a um cliente (e opcionalmente a um empréstimo)."""
    context_id = get_user_context(current_user)
    consulta = await db.consultas.find_one(
        {"id": consulta_id, "usuario_id": context_id, "deleted": {"$ne": True}}, {"_id": 0, "id": 1})
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta não encontrada.")

    cliente = await db.clientes.find_one(
        {"id": body.cliente_id, "usuario_id": context_id, "deleted": {"$ne": True}}, {"_id": 0, "id": 1, "nome": 1})
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    emprestimo_id = None
    if body.emprestimo_id:
        emp = await db.emprestimos.find_one(
            {"id": body.emprestimo_id, "usuario_id": context_id}, {"_id": 0, "id": 1, "cliente_id": 1})
        if not emp:
            raise HTTPException(status_code=404, detail="Empréstimo não encontrado.")
        emprestimo_id = emp["id"]

    await db.consultas.update_one(
        {"id": consulta_id, "usuario_id": context_id},
        {"$set": {"cliente_id": cliente["id"], "cliente_nome": cliente.get("nome"),
                  "emprestimo_id": emprestimo_id,
                  "vinculado_em": datetime.now(timezone.utc).isoformat()}},
    )
    return {"success": True, "cliente_id": cliente["id"], "cliente_nome": cliente.get("nome"), "emprestimo_id": emprestimo_id}


@router.get("/{consulta_id}/pdf")
async def exportar_pdf(
    consulta_id: str,
    current_user: Usuario = Depends(verificar_plano_ativo),
):
    """Gera o PDF do dossiê de uma consulta salva."""
    context_id = get_user_context(current_user)
    doc = await db.consultas.find_one(
        {"id": consulta_id, "usuario_id": context_id, "deleted": {"$ne": True}}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Consulta não encontrada.")
    pdf = gerar_pdf_consulta(doc)
    filename = f"dossie-{doc.get('documento') or 'consulta'}.pdf"
    return StreamingResponse(
        pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})


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
