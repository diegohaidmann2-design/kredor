"""
Rotas para gerenciar sistema Anti-Spam do WhatsApp
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime

from config import db
from models.usuario import Usuario
from services.auth import get_current_user
from services.whatsapp_anti_spam_service import WhatsAppAntiSpamService
from services.whatsapp_fila_service import WhatsAppFilaService

router = APIRouter()


@router.get("/anti-spam/config")
async def get_config_anti_spam(current_user: Usuario = Depends(get_current_user)):
    """Retorna configuração anti-spam do usuário"""
    service = WhatsAppAntiSpamService(db)
    config = await service.get_config(current_user.id)
    
    # Remover campos internos
    if "_id" in config:
        del config["_id"]
    
    return config


@router.put("/anti-spam/config")
async def atualizar_config_anti_spam(
    tier_atual: Optional[int] = None,
    limite_diario: Optional[int] = None,
    delay_minimo: Optional[int] = None,
    delay_maximo: Optional[int] = None,
    horario_inicio: Optional[str] = None,
    horario_fim: Optional[str] = None,
    enviar_fora_horario: Optional[bool] = None,
    current_user: Usuario = Depends(get_current_user)
):
    """Atualiza configuração anti-spam"""
    updates = {}
    
    if tier_atual is not None:
        updates["tier_atual"] = tier_atual
    if limite_diario is not None:
        updates["limite_diario"] = limite_diario
    if delay_minimo is not None:
        updates["delay_minimo"] = delay_minimo
    if delay_maximo is not None:
        updates["delay_maximo"] = delay_maximo
    if horario_inicio is not None:
        updates["horario_inicio"] = horario_inicio
    if horario_fim is not None:
        updates["horario_fim"] = horario_fim
    if enviar_fora_horario is not None:
        updates["enviar_fora_horario"] = enviar_fora_horario
    
    if updates:
        await db.configuracoes.update_one(
            {"tipo": "whatsapp_anti_spam", "usuario_id": current_user.id},
            {"$set": updates}
        )
    
    return {"success": True, "message": "Configuração atualizada"}


@router.post("/anti-spam/warming-up/ativar")
async def ativar_warming_up(current_user: Usuario = Depends(get_current_user)):
    """Ativa modo warming up (aquecimento gradual)"""
    service = WhatsAppAntiSpamService(db)
    await service.ativar_warming_up(current_user.id)
    
    return {
        "success": True,
        "message": "Warming up ativado",
        "info": "O sistema vai aumentar gradualmente o limite de envios nos próximos 14 dias"
    }


@router.post("/anti-spam/warming-up/desativar")
async def desativar_warming_up(current_user: Usuario = Depends(get_current_user)):
    """Desativa modo warming up"""
    service = WhatsAppAntiSpamService(db)
    await service.desativar_warming_up(current_user.id)
    
    return {"success": True, "message": "Warming up desativado"}


@router.get("/anti-spam/status")
async def verificar_status_anti_spam(current_user: Usuario = Depends(get_current_user)):
    """Verifica se pode enviar mensagem agora"""
    service = WhatsAppAntiSpamService(db)
    resultado = await service.pode_enviar(current_user.id)
    
    config = await service.get_config(current_user.id)
    
    return {
        **resultado,
        "contador_hoje": config.get("contador_hoje", 0),
        "limite_diario": config.get("limite_diario", 1000),
        "contador_hora": config.get("contador_hora", 0),
        "limite_por_hora": config.get("limite_por_hora", 100),
        "taxa_qualidade": config.get("taxa_qualidade", 100.0)
    }


@router.get("/fila/estatisticas")
async def obter_estatisticas_fila(current_user: Usuario = Depends(get_current_user)):
    """Retorna estatísticas da fila de mensagens"""
    service = WhatsAppFilaService(db)
    stats = await service.obter_estatisticas_fila(current_user.id)
    
    return stats


@router.post("/fila/processar")
async def processar_fila_manual(
    limite: int = 100,
    current_user: Usuario = Depends(get_current_user)
):
    """Processa fila de mensagens manualmente"""
    service = WhatsAppFilaService(db)
    resultado = await service.processar_fila(current_user.id, limite)
    
    return {
        "success": True,
        "message": "Fila processada",
        **resultado
    }


@router.delete("/fila/{fila_id}")
async def cancelar_mensagem_fila(
    fila_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Cancela uma mensagem na fila"""
    service = WhatsAppFilaService(db)
    cancelado = await service.cancelar_mensagem(fila_id, current_user.id)
    
    if not cancelado:
        raise HTTPException(404, "Mensagem não encontrada ou já foi processada")
    
    return {"success": True, "message": "Mensagem cancelada"}


@router.post("/fila/reprocessar-falhadas")
async def reprocessar_falhadas(current_user: Usuario = Depends(get_current_user)):
    """Recoloca mensagens falhadas na fila"""
    service = WhatsAppFilaService(db)
    count = await service.reprocessar_falhadas(current_user.id)
    
    return {
        "success": True,
        "message": f"{count} mensagens recolocadas na fila"
    }


@router.get("/fila/lista")
async def listar_fila(
    status: Optional[str] = None,
    limite: int = 50,
    current_user: Usuario = Depends(get_current_user)
):
    """Lista mensagens na fila"""
    filtro = {"usuario_id": current_user.id}
    
    if status:
        filtro["status"] = status
    
    mensagens = await db.whatsapp_fila.find(filtro).sort("created_at", -1).limit(limite).to_list(limite)
    
    # Remover _id
    for msg in mensagens:
        if "_id" in msg:
            msg["_id"] = str(msg["_id"])
    
    return {
        "mensagens": mensagens,
        "total": len(mensagens)
    }
