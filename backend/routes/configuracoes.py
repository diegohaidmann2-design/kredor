"""
Rotas de Configurações
"""
from fastapi import APIRouter, HTTPException, Depends

from config import db
from models.configuracao import LandingConfig, IAConfig
from models.usuario import Usuario
from services.auth import get_current_user, require_admin

router = APIRouter()


@router.get("/landing")
async def obter_configuracoes_landing():
    """Obtém configurações da landing page (público)"""
    config = await db.configuracoes.find_one({"tipo": "landing"}, {"_id": 0})
    
    if not config:
        return LandingConfig().model_dump()
    
    return config.get("dados", LandingConfig().model_dump())


@router.put("/landing")
async def atualizar_configuracoes_landing(
    config: LandingConfig,
    current_user: Usuario = Depends(require_admin)
):
    """Atualiza configurações da landing page (apenas admin)"""
    await db.configuracoes.update_one(
        {"tipo": "landing"},
        {"$set": {"tipo": "landing", "dados": config.model_dump()}},
        upsert=True
    )
    
    return {"message": "Configurações atualizadas com sucesso"}


@router.get("/ia")
async def obter_configuracoes_ia(
    current_user: Usuario = Depends(require_admin)
):
    """Obtém configurações de IA (apenas admin)"""
    config = await db.configuracoes.find_one({"tipo": "ia"}, {"_id": 0})
    
    if not config:
        return IAConfig().model_dump()
    
    return config.get("dados", IAConfig().model_dump())


@router.put("/ia")
async def atualizar_configuracoes_ia(
    config: IAConfig,
    current_user: Usuario = Depends(require_admin)
):
    """Atualiza configurações de IA (apenas admin)"""
    await db.configuracoes.update_one(
        {"tipo": "ia"},
        {"$set": {"tipo": "ia", "dados": config.model_dump()}},
        upsert=True
    )
    
    return {"message": "Configurações de IA atualizadas com sucesso"}

