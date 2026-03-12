"""
Rotas de Configuração do Asaas
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional

from config import db
from models.usuario import Usuario
from services.auth import require_admin
from services.asaas_service import asaas_service

router = APIRouter()


class AsaasConfig(BaseModel):
    habilitado: bool = False
    api_key: str = ""
    ambiente: str = "sandbox"  # sandbox ou producao
    webhook_url: str = ""


# ============ CONFIGURAÇÕES (SUPER ADMIN) ============

@router.get("/config")
async def obter_config_asaas(
    current_user: Usuario = Depends(require_admin)
):
    """Obtém configuração do Asaas (Super Admin) - Integrado com Gateway Config"""
    config = await db.configuracoes.find_one({"tipo": "assinatura_gateway"})
    
    if not config or not config.get("dados"):
        # Retornar config padrão
        return {
            "habilitado": False,
            "api_key": "",
            "ambiente": "sandbox",
            "webhook_url": ""
        }
    
    dados = config["dados"]
    return {
        "habilitado": dados.get("asaas_habilitado", False),
        "api_key": dados.get("asaas_api_key", ""),
        "ambiente": dados.get("asaas_ambiente", "sandbox"),
        "webhook_url": dados.get("asaas_webhook_url", "")
    }


@router.put("/config")
async def atualizar_config_asaas(
    config: AsaasConfig,
    current_user: Usuario = Depends(require_admin)
):
    """Atualiza configuração do Asaas (Super Admin) - Integrado com Gateway Config"""
    try:
        # Atualizar na config de gateway
        await db.configuracoes.update_one(
            {"tipo": "assinatura_gateway"},
            {"$set": {
                "tipo": "assinatura_gateway",
                "dados.asaas_habilitado": config.habilitado,
                "dados.asaas_api_key": config.api_key,
                "dados.asaas_ambiente": config.ambiente,
                "dados.asaas_webhook_url": config.webhook_url,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
        
        return {
            "success": True,
            "message": "Configurações do Asaas atualizadas com sucesso"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar configurações: {str(e)}")


@router.post("/config/testar")
async def testar_config_asaas(
    config: AsaasConfig,
    current_user: Usuario = Depends(require_admin)
):
    """Testa conexão com Asaas (Super Admin)"""
    if not config.api_key:
        raise HTTPException(
            status_code=400, 
            detail="Configure a API Key antes de testar"
        )
    
    try:
        resultado = await asaas_service.testar_conexao(
            api_key=config.api_key,
            ambiente=config.ambiente
        )
        return resultado
    except Exception as e:
        return {
            "success": False,
            "message": f"Erro ao testar: {str(e)}"
        }


@router.get("/status")
async def verificar_status_asaas(
    current_user: Usuario = Depends(require_admin)
):
    """Verifica status da configuração do Asaas"""
    config = await db.configuracoes.find_one({"tipo": "asaas"})
    
    if not config or not config.get("dados"):
        return {
            "configurado": False,
            "habilitado": False,
            "ambiente": None,
            "message": "Asaas não configurado"
        }
    
    dados = config["dados"]
    
    return {
        "configurado": bool(dados.get("api_key")),
        "habilitado": dados.get("habilitado", False),
        "ambiente": dados.get("ambiente", "sandbox"),
        "webhook_url": dados.get("webhook_url", ""),
        "message": "Asaas configurado" if dados.get("api_key") else "API Key não configurada"
    }
