"""
Rotas administrativas da Carteira de Consultas.
Base: /api/admin/carteiras
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from config import db
from models.usuario import Usuario
from services.auth import get_current_user
from services.carteira_service import (
    dashboard_admin, listar_carteiras_admin, listar_precos, atualizar_preco,
    listar_movimentos, obter_ou_criar_carteira, ajuste_admin, PRECOS_PADRAO,
    LABELS_TIPO,
)

router = APIRouter()


def _garantir_admin(user: Usuario):
    if user.perfil not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Apenas administradores podem acessar.")


class PrecoUpdate(BaseModel):
    valor: float = Field(..., ge=0)
    ativo: bool = True


class AjusteRequest(BaseModel):
    valor: float
    motivo: str = Field(..., min_length=3, max_length=200)


@router.get("/dashboard")
async def admin_dashboard(current_user: Usuario = Depends(get_current_user)):
    _garantir_admin(current_user)
    return await dashboard_admin()


@router.get("/precos")
async def admin_listar_precos(current_user: Usuario = Depends(get_current_user)):
    _garantir_admin(current_user)
    itens = await listar_precos(apenas_ativos=False)
    # Garantir que todos os tipos padrão apareçam mesmo se ainda não persistidos
    existentes = {i["tipo"] for i in itens}
    for tipo, valor in PRECOS_PADRAO.items():
        if tipo not in existentes:
            itens.append({
                "tipo": tipo, "label": LABELS_TIPO.get(tipo, tipo),
                "valor": valor, "ativo": True, "created_at": None, "updated_at": None,
                "updated_by": None,
            })
    itens.sort(key=lambda x: x["tipo"])
    return {"itens": itens}


@router.put("/precos/{tipo}")
async def admin_atualizar_preco(
    tipo: str,
    body: PrecoUpdate,
    current_user: Usuario = Depends(get_current_user),
):
    _garantir_admin(current_user)
    try:
        doc = await atualizar_preco(tipo, body.valor, body.ativo, current_user.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return doc


@router.get("/")
async def admin_listar_carteiras(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    busca: str = Query(None),
    ordenar_por: str = Query("saldo"),
    current_user: Usuario = Depends(get_current_user),
):
    _garantir_admin(current_user)
    return await listar_carteiras_admin(limit=limit, skip=skip, busca=busca, ordenar_por=ordenar_por)


@router.get("/{owner_id}")
async def admin_detalhes_carteira(
    owner_id: str,
    current_user: Usuario = Depends(get_current_user),
):
    _garantir_admin(current_user)
    dono = await db.usuarios.find_one(
        {"id": owner_id}, {"_id": 0, "id": 1, "nome": 1, "email": 1, "plano": 1, "plano_ativo": 1, "telefone": 1}
    )
    if not dono:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    carteira = await obter_ou_criar_carteira(owner_id)
    movs = await listar_movimentos(owner_id, limit=30, skip=0)
    return {"dono": dono, "carteira": carteira, "movimentos": movs}


@router.get("/{owner_id}/movimentos")
async def admin_movimentos(
    owner_id: str,
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
    tipo: str = Query(None),
    current_user: Usuario = Depends(get_current_user),
):
    _garantir_admin(current_user)
    return await listar_movimentos(owner_id, limit=limit, skip=skip, tipo=tipo)


@router.post("/{owner_id}/ajuste")
async def admin_ajuste_carteira(
    owner_id: str,
    body: AjusteRequest,
    current_user: Usuario = Depends(get_current_user),
):
    _garantir_admin(current_user)
    dono = await db.usuarios.find_one({"id": owner_id}, {"_id": 0, "id": 1})
    if not dono:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    try:
        resultado = await ajuste_admin(
            owner_id=owner_id, valor=float(body.valor), motivo=body.motivo,
            admin_email=current_user.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "carteira": resultado["carteira"],
        "movimento": resultado["movimento"],
    }
