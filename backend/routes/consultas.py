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
    consultar_cpf, consultar_cpf_premium, consultar_cnpj, consultar_telefone, consultar_nome,
    consultar_cpf_dividas, consultar_cnpj_dividas, consultar_facial, LosDadosError,
)
from services.consulta_pdf import gerar_pdf_consulta
from services.carteira_service import (
    verificar_saldo_para_consulta, debitar_consulta, estornar_consulta,
)


async def _cobrar_ou_bloquear(current_user, tipo_consulta: str):
    """Verifica saldo antes de chamar a API externa. 402 se insuficiente."""
    pode, msg, info = await verificar_saldo_para_consulta(current_user, tipo_consulta)
    if not pode:
        raise HTTPException(
            status_code=402,
            detail={"message": msg, **(info or {}), "code": "SALDO_INSUFICIENTE"},
        )
    return info


async def _debitar_seguro(current_user, tipo_consulta: str, consulta_id: str):
    """Debita a consulta. Se falhar por saldo, remove a consulta do histórico."""
    try:
        return await debitar_consulta(current_user, tipo_consulta, consulta_id)
    except ValueError:
        # Corrida rara: saldo mudou entre check e débito. Remove consulta e sinaliza.
        await db.consultas.update_one(
            {"id": consulta_id},
            {"$set": {"deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat(),
                      "deleted_reason": "saldo_insuficiente_no_debito"}},
        )
        raise HTTPException(
            status_code=402,
            detail={"message": "Saldo insuficiente na carteira.", "code": "SALDO_INSUFICIENTE"},
        )

router = APIRouter()


class ConsultaCPFRequest(BaseModel):
    cpf: str


class ConsultaCNPJRequest(BaseModel):
    cnpj: str


class ConsultaTelefoneRequest(BaseModel):
    telefone: str


class ConsultaNomeRequest(BaseModel):
    nome: str


class ConsultaDividasCPFRequest(BaseModel):
    cpf: str


class ConsultaDividasCNPJRequest(BaseModel):
    cnpj: str


class ConsultaFacialRequest(BaseModel):
    foto: str


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


def _resumo_cpf_premium(data: dict) -> dict:
    """Resumo leve do CPF Premium para o histórico."""
    dados = (data or {}).get("dados") or {}
    return {
        "nome": dados.get("nome"),
        "nascimento": dados.get("nascimento"),
        "situacao": dados.get("situacao_cadastral"),
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


def _resumo_nome(data: dict, termo: str) -> dict:
    """Resumo leve de busca por nome para o histórico."""
    lista = (data or {}).get("data")
    if not isinstance(lista, list):
        lista = []
    return {"nome": termo, "total": len(lista)}


def _resumo_dividas(data: dict) -> dict:
    """Resumo leve de dívidas (CPF/CNPJ) para o histórico."""
    dc = (data or {}).get("dados_consulta") or {}
    aval = dc.get("avaliacao_preliminar_credito") or {}
    inner = ((dc.get("dados_consulta") or {}).get("data") or {})
    saida = inner.get("saida") or {}
    blocos = inner.get("blocos") or {}
    nome = (saida.get("identificacao") or {}).get("nome") or (blocos.get("identificacao_empresa") or {}).get("razao_social")
    return {
        "nome": nome or "Consulta de dívidas",
        "score": aval.get("score_risco"),
        "nivel_risco": aval.get("nivel_risco"),
        "sugestao": aval.get("sugestao_negocio"),
    }


def _resumo_facial(data: dict) -> dict:
    """Resumo leve de reconhecimento facial para o histórico."""
    sr = (data or {}).get("SERVICE_RESPONSE") or {}
    resultados = sr.get("results")
    if not isinstance(resultados, list):
        resultados = []
    primeiro = resultados[0].get("nome") if resultados and isinstance(resultados[0], dict) else None
    return {
        "nome": primeiro or "Reconhecimento facial",
        "total": len(resultados),
        "match": bool(sr.get("match_found")),
        "score": sr.get("best_score"),
    }


@router.post("/cpf")
async def consulta_cpf(
    body: ConsultaCPFRequest,
    current_user: Usuario = Depends(verificar_plano_ativo),
):
    """Realiza uma consulta de CPF e salva no histórico do usuário."""
    context_id = get_user_context(current_user)
    await _cobrar_ou_bloquear(current_user, "cpf")
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
        "cached": payload.get("cached", False),
        "created_at": agora,
        "created_by": current_user.email,
        "cliente_id": None,
        "cliente_nome": None,
        "emprestimo_id": None,
        "deleted": False,
    }
    await db.consultas.insert_one(doc)
    debito = await _debitar_seguro(current_user, "cpf", consulta_id)

    return {
        "id": consulta_id,
        "tipo": "cpf",
        "resumo": resumo,
        "data": data,
        "cached": payload.get("cached", False),
        "created_at": agora,
        "carteira": debito,
    }


@router.post("/cpf-premium")
async def consulta_cpf_premium(
    body: ConsultaCPFRequest,
    current_user: Usuario = Depends(verificar_plano_ativo),
):
    """Consulta CPF Premium (dossiê completo) e salva no histórico do usuário."""
    context_id = get_user_context(current_user)
    await _cobrar_ou_bloquear(current_user, "cpf-premium")
    try:
        payload = await consultar_cpf_premium(body.cpf)
    except LosDadosError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    data = payload.get("data") or {}
    # A API premium sinaliza falha via sucesso=False / erro
    if isinstance(data, dict) and data.get("sucesso") is False:
        raise HTTPException(status_code=404, detail=str(data.get("erro") or "CPF não encontrado."))
    if not (isinstance(data, dict) and data.get("dados")):
        raise HTTPException(status_code=404, detail="Nenhum dado encontrado para este CPF.")

    resumo = _resumo_cpf_premium(data)
    consulta_id = str(uuid.uuid4())
    agora = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": consulta_id,
        "usuario_id": context_id,
        "tipo": "cpf-premium",
        "documento": "".join(c for c in body.cpf if c.isdigit()),
        "resumo": resumo,
        "data": data,
        "cached": payload.get("cached", False),
        "created_at": agora,
        "created_by": current_user.email,
        "cliente_id": None,
        "cliente_nome": None,
        "emprestimo_id": None,
        "deleted": False,
    }
    await db.consultas.insert_one(doc)
    debito = await _debitar_seguro(current_user, "cpf-premium", consulta_id)

    return {
        "id": consulta_id,
        "tipo": "cpf-premium",
        "resumo": resumo,
        "data": data,
        "cached": payload.get("cached", False),
        "created_at": agora,
        "carteira": debito,
    }


@router.post("/cnpj")
async def consulta_cnpj(
    body: ConsultaCNPJRequest,
    current_user: Usuario = Depends(verificar_plano_ativo),
):
    """Realiza uma consulta de CNPJ e salva no histórico do usuário."""
    context_id = get_user_context(current_user)
    await _cobrar_ou_bloquear(current_user, "cnpj")
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
        "cached": payload.get("cached", False),
        "created_at": agora,
        "created_by": current_user.email,
        "cliente_id": None,
        "cliente_nome": None,
        "emprestimo_id": None,
        "deleted": False,
    }
    await db.consultas.insert_one(doc)
    debito = await _debitar_seguro(current_user, "cnpj", consulta_id)

    return {
        "id": consulta_id,
        "tipo": "cnpj",
        "resumo": resumo,
        "data": data,
        "cached": payload.get("cached", False),
        "created_at": agora,
        "carteira": debito,
    }


@router.post("/telefone")
async def consulta_telefone(
    body: ConsultaTelefoneRequest,
    current_user: Usuario = Depends(verificar_plano_ativo),
):
    """Realiza uma consulta de Telefone e salva no histórico do usuário."""
    context_id = get_user_context(current_user)
    await _cobrar_ou_bloquear(current_user, "telefone")
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
        "cached": payload.get("cached", False),
        "created_at": agora,
        "created_by": current_user.email,
        "cliente_id": None,
        "cliente_nome": None,
        "emprestimo_id": None,
        "deleted": False,
    }
    await db.consultas.insert_one(doc)
    debito = await _debitar_seguro(current_user, "telefone", consulta_id)

    return {
        "id": consulta_id,
        "tipo": "telefone",
        "resumo": resumo,
        "data": data,
        "cached": payload.get("cached", False),
        "created_at": agora,
        "carteira": debito,
    }


@router.post("/nome")
async def consulta_nome(
    body: ConsultaNomeRequest,
    current_user: Usuario = Depends(verificar_plano_ativo),
):
    """Realiza uma consulta por Nome e salva no histórico do usuário."""
    context_id = get_user_context(current_user)
    await _cobrar_ou_bloquear(current_user, "nome")
    try:
        payload = await consultar_nome(body.nome)
    except LosDadosError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    data = payload.get("data") or {}
    if isinstance(data, dict) and data.get("err") and len(data) == 1:
        raise HTTPException(status_code=404, detail=str(data.get("err")))

    termo = " ".join((body.nome or "").split()).strip()
    resumo = _resumo_nome(data, termo)
    consulta_id = str(uuid.uuid4())
    agora = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": consulta_id,
        "usuario_id": context_id,
        "tipo": "nome",
        "documento": termo,
        "resumo": resumo,
        "data": data,
        "cached": payload.get("cached", False),
        "created_at": agora,
        "created_by": current_user.email,
        "cliente_id": None,
        "cliente_nome": None,
        "emprestimo_id": None,
        "deleted": False,
    }
    await db.consultas.insert_one(doc)
    debito = await _debitar_seguro(current_user, "nome", consulta_id)

    return {
        "id": consulta_id,
        "tipo": "nome",
        "resumo": resumo,
        "data": data,
        "cached": payload.get("cached", False),
        "created_at": agora,
        "carteira": debito,
    }


@router.post("/cpf-dividas")
async def consulta_cpf_dividas(
    body: ConsultaDividasCPFRequest,
    current_user: Usuario = Depends(verificar_plano_ativo),
):
    """Consulta de dívidas/restrições por CPF (Boa Vista) e salva no histórico."""
    context_id = get_user_context(current_user)
    await _cobrar_ou_bloquear(current_user, "cpf-dividas")
    try:
        payload = await consultar_cpf_dividas(body.cpf)
    except LosDadosError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    data = payload.get("data") or {}
    resumo = _resumo_dividas(data)
    consulta_id = str(uuid.uuid4())
    agora = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": consulta_id, "usuario_id": context_id, "tipo": "cpf-dividas",
        "documento": "".join(c for c in body.cpf if c.isdigit()),
        "resumo": resumo, "data": data,
        "cached": payload.get("cached", False), "created_at": agora,
        "created_by": current_user.email, "cliente_id": None, "cliente_nome": None,
        "emprestimo_id": None, "deleted": False,
    }
    await db.consultas.insert_one(doc)
    debito = await _debitar_seguro(current_user, "cpf-dividas", consulta_id)
    return {"id": consulta_id, "tipo": "cpf-dividas", "resumo": resumo, "data": data,
            "cached": payload.get("cached", False), "created_at": agora,
            "carteira": debito}


@router.post("/cnpj-dividas")
async def consulta_cnpj_dividas(
    body: ConsultaDividasCNPJRequest,
    current_user: Usuario = Depends(verificar_plano_ativo),
):
    """Consulta de dívidas/restrições por CNPJ (Boa Vista) e salva no histórico."""
    context_id = get_user_context(current_user)
    await _cobrar_ou_bloquear(current_user, "cnpj-dividas")
    try:
        payload = await consultar_cnpj_dividas(body.cnpj)
    except LosDadosError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    data = payload.get("data") or {}
    resumo = _resumo_dividas(data)
    consulta_id = str(uuid.uuid4())
    agora = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": consulta_id, "usuario_id": context_id, "tipo": "cnpj-dividas",
        "documento": "".join(c for c in body.cnpj if c.isdigit()),
        "resumo": resumo, "data": data,
        "cached": payload.get("cached", False), "created_at": agora,
        "created_by": current_user.email, "cliente_id": None, "cliente_nome": None,
        "emprestimo_id": None, "deleted": False,
    }
    await db.consultas.insert_one(doc)
    debito = await _debitar_seguro(current_user, "cnpj-dividas", consulta_id)
    return {"id": consulta_id, "tipo": "cnpj-dividas", "resumo": resumo, "data": data,
            "cached": payload.get("cached", False), "created_at": agora,
            "carteira": debito}


@router.post("/reconhecimento-facial")
async def consulta_facial(
    body: ConsultaFacialRequest,
    current_user: Usuario = Depends(verificar_plano_ativo),
):
    """Reconhecimento facial (foto base64) e salva no histórico."""
    context_id = get_user_context(current_user)
    await _cobrar_ou_bloquear(current_user, "facial")
    try:
        payload = await consultar_facial(body.foto)
    except LosDadosError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    data = payload.get("data") or {}
    if isinstance(data, dict) and data.get("err") and len(data) == 1:
        raise HTTPException(status_code=404, detail=str(data.get("err")))

    resumo = _resumo_facial(data)
    consulta_id = str(uuid.uuid4())
    agora = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": consulta_id, "usuario_id": context_id, "tipo": "facial",
        "documento": None, "resumo": resumo, "data": data,
        "cached": payload.get("cached", False), "created_at": agora,
        "created_by": current_user.email, "cliente_id": None, "cliente_nome": None,
        "emprestimo_id": None, "deleted": False,
    }
    await db.consultas.insert_one(doc)
    debito = await _debitar_seguro(current_user, "facial", consulta_id)
    return {"id": consulta_id, "tipo": "facial", "resumo": resumo, "data": data,
            "cached": payload.get("cached", False), "created_at": agora,
            "carteira": debito}


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
