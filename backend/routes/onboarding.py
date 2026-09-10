"""
Rotas de Onboarding - API para gerenciar o onboarding de usuários
"""
from services.logging_service import get_logger
logger = get_logger("gestorcred.onboarding")

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from config import db
from services.auth import get_current_user
from services.onboarding_service import OnboardingService

router = APIRouter()


class UpdateTourStepRequest(BaseModel):
    step: int


class UpdateTaskRequest(BaseModel):
    task_key: str
    completed: bool


class SkipOnboardingRequest(BaseModel):
    skip: bool = True


@router.get("/status")
async def get_onboarding_status(usuario=Depends(get_current_user)):
    """
    Obtém o status completo do onboarding do usuário
    Verifica automaticamente tarefas completadas
    """
    try:
        # Buscar dados atualizados do usuário
        usuario_db = await db.usuarios.find_one({"id": usuario.id})
        
        if not usuario_db:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        # ✅ NOVO: Verificar automaticamente tarefas completadas
        tasks_updated = await OnboardingService.auto_check_all_tasks(usuario_db, db)
        usuario_db["onboarding_tasks"] = tasks_updated
        
        status = OnboardingService.get_onboarding_status(usuario_db)
        
        return {
            "success": True,
            "onboarding": status
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter status do onboarding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tour-steps")
async def get_tour_steps(usuario=Depends(get_current_user)):
    """
    Retorna os steps do tour interativo
    """
    return {
        "success": True,
        "steps": OnboardingService.TOUR_STEPS
    }


@router.post("/start")
async def start_onboarding(usuario=Depends(get_current_user)):
    """
    Marca o início do onboarding
    """
    try:
        
        
        await db.usuarios.update_one(
            {"id": usuario.id},
            {"$set": {
                "onboarding_started_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {
            "success": True,
            "message": "Onboarding iniciado"
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar onboarding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tour/update-step")
async def update_tour_step(
    request: UpdateTourStepRequest,
    usuario=Depends(get_current_user)
):
    """
    Atualiza o step atual do tour
    """
    try:
        
        
        await db.usuarios.update_one(
            {"id": usuario.id},
            {"$set": {
                "onboarding_step": request.step
            }}
        )
        
        return {
            "success": True,
            "step": request.step
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar step do tour: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tour/finish")
async def finish_tour(usuario=Depends(get_current_user)):
    """
    Marca o tour como finalizado
    """
    try:
        
        
        await db.usuarios.update_one(
            {"id": usuario.id},
            {"$set": {
                "onboarding_tour_finished": True
            }}
        )
        
        return {
            "success": True,
            "message": "Tour finalizado"
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao finalizar tour: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/task/update")
async def update_task(
    request: UpdateTaskRequest,
    usuario=Depends(get_current_user)
):
    """
    Atualiza o status de uma tarefa do onboarding
    """
    try:
        
        
        # Verificar se a task existe
        if request.task_key not in OnboardingService.TASKS:
            raise HTTPException(status_code=400, detail="Tarefa inválida")
        
        # Atualizar a tarefa específica
        update_field = f"onboarding_tasks.{request.task_key}"
        
        await db.usuarios.update_one(
            {"id": usuario.id},
            {"$set": {
                update_field: request.completed
            }}
        )
        
        # Buscar usuário atualizado para verificar se completou 100%
        usuario_db = await db.usuarios.find_one({"id": usuario.id})
        tasks = usuario_db.get("onboarding_tasks", {})
        progress = OnboardingService.calculate_progress(tasks)
        
        # Se completou 100%, marcar onboarding como completo
        if progress == 100 and not usuario_db.get("onboarding_completed"):
            await db.usuarios.update_one(
                {"id": usuario.id},
                {"$set": {
                    "onboarding_completed": True,
                    "onboarding_completed_at": datetime.now(timezone.utc).isoformat()
                }}
            )
        
        return {
            "success": True,
            "task": request.task_key,
            "completed": request.completed,
            "progress": progress
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar tarefa: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/skip")
async def skip_onboarding(
    request: SkipOnboardingRequest,
    usuario=Depends(get_current_user)
):
    """
    Permite ao usuário pular o onboarding
    """
    try:
        
        
        await db.usuarios.update_one(
            {"id": usuario.id},
            {"$set": {
                "onboarding_completed": True,
                "onboarding_tour_finished": True,
                "onboarding_completed_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {
            "success": True,
            "message": "Onboarding pulado"
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao pular onboarding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_onboarding(usuario=Depends(get_current_user)):
    """
    Reseta o onboarding do usuário (útil para testes ou reativar)
    """
    try:
        
        
        await db.usuarios.update_one(
            {"id": usuario.id},
            {"$set": {
                "onboarding_completed": False,
                "onboarding_step": 0,
                "onboarding_tasks": {
                    "perfil_completo": False,
                    "primeiro_cliente": False,
                    "primeiro_emprestimo": False,
                    "primeiro_pagamento": False,
                    "primeiro_contrato": False,
                    "configuracoes": False
                },
                "onboarding_tour_finished": False,
                "onboarding_started_at": None,
                "onboarding_completed_at": None
            }}
        )
        
        return {
            "success": True,
            "message": "Onboarding resetado"
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao resetar onboarding: {e}")
        raise HTTPException(status_code=500, detail=str(e))
