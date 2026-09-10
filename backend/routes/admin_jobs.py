"""
Rotas administrativas para gerenciar jobs e envios de email
"""
from fastapi import APIRouter, Depends, HTTPException
from models.usuario import Usuario
from services.auth import require_admin
from jobs.email_jobs import executar_job_diario
from datetime import datetime, timezone
from config import db

router = APIRouter()


@router.post("/executar-job-emails")
async def executar_job_emails(current_user: Usuario = Depends(require_admin)):
    """Executa manualmente o job de envio de emails (apenas admin)"""
    resultado = await executar_job_diario()
    
    return {
        "message": "Job executado com sucesso",
        "resultado": resultado
    }


@router.get("/status-jobs")
async def status_jobs(current_user: Usuario = Depends(require_admin)):
    """Retorna informações sobre jobs pendentes (apenas admin)"""
    
    
    agora = datetime.now(timezone.utc)
    
    # Trials expirando
    trials_expirando = await db.usuarios.count_documents({
        "plano": "trial",
        "email_verificado": True,
        "data_fim_trial": {
            "$gte": agora.isoformat(),
            "$lte": (agora + timezone.utc.localize(datetime.timedelta(days=3))).isoformat()
        }
    })
    
    # Assinaturas vencendo
    assinaturas_vencendo = await db.usuarios.count_documents({
        "plano": {"$ne": "trial"},
        "email_verificado": True,
        "data_vencimento_assinatura": {
            "$gte": agora.isoformat(),
            "$lte": (agora + timezone.utc.localize(datetime.timedelta(days=7))).isoformat()
        }
    })
    
    # Trials expirados
    trials_expirados = await db.usuarios.count_documents({
        "plano": "trial",
        "data_fim_trial": {"$lt": agora.isoformat()},
        "plano_ativo": True
    })
    
    # Assinaturas vencidas
    assinaturas_vencidas = await db.usuarios.count_documents({
        "plano": {"$ne": "trial"},
        "data_vencimento_assinatura": {"$lt": agora.isoformat()},
        "plano_ativo": True
    })
    
    return {
        "trials_expirando_3_dias": trials_expirando,
        "assinaturas_vencendo_7_dias": assinaturas_vencendo,
        "trials_expirados_nao_bloqueados": trials_expirados,
        "assinaturas_vencidas_nao_bloqueadas": assinaturas_vencidas,
        "total_pendente": trials_expirando + assinaturas_vencendo + trials_expirados + assinaturas_vencidas
    }
