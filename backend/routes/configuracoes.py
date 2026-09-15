"""
Rotas de Configurações
"""
from fastapi import APIRouter, HTTPException, Depends

from config import db, TRIAL_DIAS
from models.configuracao import LandingConfig, IAConfig
from models.usuario import Usuario
from services.auth import get_current_user, require_admin
from models.configuracao_notificacoes import (
    ConfiguracaoNotificacoes, 
    ConfiguracaoNotificacoesUpdate
)
from services.auth_utils import get_user_context

router = APIRouter()


@router.get("/landing")
async def obter_configuracoes_landing():
    """Obtém configurações da landing page (público)."""
    config = await db.configuracoes.find_one({"tipo": "landing"}, {"_id": 0})
    dados = (config or {}).get("dados") or LandingConfig().model_dump()

    # A duração do trial NÃO vem do valor guardado: quem concede os dias é o código
    # (config.TRIAL_DIAS, usado em models/usuario.data_fim_trial). O valor guardado era uma
    # cópia que ninguém atualizou quando o trial mudou, e a landing anunciava 3 dias enquanto
    # o sistema entregava 7 — na mesma página em que outros quatro trechos diziam 7.
    # Anunciar o que é concedido é o único jeito de os dois não voltarem a divergir.
    dados["plano_trial_dias"] = TRIAL_DIAS
    return dados


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





# ================== CONFIGURAÇÕES DE NOTIFICAÇÕES ==================

@router.get("/notificacoes")
async def obter_configuracoes_notificacoes(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtém configurações de notificações automáticas do usuário
    """
    usuario_id = get_user_context(current_user)
    
    config = await db.configuracoes.find_one({
        "tipo": "notificacoes_vencimento",
        "usuario_id": usuario_id
    }, {"_id": 0})
    
    if not config:
        # Retornar configuração padrão
        return ConfiguracaoNotificacoes().model_dump()
    
    return config.get("dados", ConfiguracaoNotificacoes().model_dump())


@router.put("/notificacoes")
async def atualizar_configuracoes_notificacoes(
    config: ConfiguracaoNotificacoesUpdate,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Atualiza configurações de notificações automáticas do usuário
    """
    usuario_id = get_user_context(current_user)
    
    # Buscar configuração existente
    config_existente = await db.configuracoes.find_one({
        "tipo": "notificacoes_vencimento",
        "usuario_id": usuario_id
    })
    
    if config_existente:
        # Atualizar apenas campos fornecidos
        dados_atuais = config_existente.get("dados", {})
        dados_novos = config.model_dump(exclude_unset=True)
        dados_atuais.update(dados_novos)
    else:
        # Criar nova configuração
        config_padrao = ConfiguracaoNotificacoes()
        dados_atuais = config_padrao.model_dump()
        dados_novos = config.model_dump(exclude_unset=True)
        dados_atuais.update(dados_novos)
    
    # Salvar no banco
    await db.configuracoes.update_one(
        {
            "tipo": "notificacoes_vencimento",
            "usuario_id": usuario_id
        },
        {
            "$set": {
                "tipo": "notificacoes_vencimento",
                "usuario_id": usuario_id,
                "dados": dados_atuais
            }
        },
        upsert=True
    )
    
    return {
        "message": "Configurações de notificações atualizadas com sucesso",
        "dados": dados_atuais
    }


@router.post("/notificacoes/restaurar-padrao")
async def restaurar_configuracoes_padrao(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Restaura configurações de notificações para valores padrão
    """
    usuario_id = get_user_context(current_user)
    
    config_padrao = ConfiguracaoNotificacoes()
    
    await db.configuracoes.update_one(
        {
            "tipo": "notificacoes_vencimento",
            "usuario_id": usuario_id
        },
        {
            "$set": {
                "tipo": "notificacoes_vencimento",
                "usuario_id": usuario_id,
                "dados": config_padrao.model_dump()
            }
        },
        upsert=True
    )
    
    return {
        "message": "Configurações restauradas para o padrão",
        "dados": config_padrao.model_dump()
    }
