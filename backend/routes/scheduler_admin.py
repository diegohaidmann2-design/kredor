"""
Rotas administrativas para gerenciar o scheduler de jobs
"""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import Dict, Any

from services.auth import get_current_user, require_admin
from models.usuario import Usuario
from scheduler import get_scheduler_status
from jobs.email_jobs import executar_job_diario, enviar_lembretes_trial, enviar_lembretes_assinatura
from jobs.relatorio_semanal import gerar_relatorio_semanal
from services.plano_service import gerar_relatorio_reconciliacao, verificar_e_corrigir_inconsistencias
from config import db
from utils.timezone_utils import now_utc  # 🆕 Importar timezone
from jobs.notificacoes_job import job_verificar_vencimentos_todos
from scheduler import job_verificar_planos_expirados
from scheduler import job_reconciliacao_semanal
from datetime import timedelta

router = APIRouter(prefix="/scheduler", tags=["Scheduler Admin"])


@router.get("/status")
async def get_status(usuario: Usuario = Depends(require_admin)):
    """
    Retorna o status atual do scheduler e lista de jobs agendados
    """
    status = await get_scheduler_status()

    return {
        "success": True,
        "scheduler": status,
        "timestamp": now_utc().isoformat()  # 🆕 Usar timezone UTC com timezone info
    }


@router.post("/jobs/verificar-vencimentos/executar")
async def executar_job_verificar_vencimentos(usuario: Usuario = Depends(require_admin)):
    """Executa manualmente a verificação de vencimentos (notificações de parcelas).

    A tela /admin/scheduler já oferecia este botão, mas a rota não existia e o clique
    respondia 404. O job é o mesmo que o scheduler roda no horário.
    """
    resultado = await job_verificar_vencimentos_todos()

    return {
        "success": True,
        "job": "verificar_vencimentos",
        "executado_em": now_utc().isoformat(),
        "resultado": resultado,
    }


@router.post("/jobs/verificar-planos/executar")
async def executar_job_verificar_planos(usuario: Usuario = Depends(require_admin)):
    """
    Executa manualmente o job de verificação de planos expirados
    """
    
    resultado = await job_verificar_planos_expirados()
    
    return {
        "success": True,
        "job": "verificar_planos_expirados",
        "executado_em": datetime.utcnow().isoformat(),
        "resultado": resultado
    }


@router.post("/jobs/lembretes-trial/executar")
async def executar_job_lembretes_trial(usuario: Usuario = Depends(require_admin)):
    """
    Executa manualmente o job de lembretes de trial
    """
    resultado = await enviar_lembretes_trial()
    
    return {
        "success": True,
        "job": "lembretes_trial",
        "executado_em": datetime.utcnow().isoformat(),
        "resultado": resultado
    }


@router.post("/jobs/lembretes-assinatura/executar")
async def executar_job_lembretes_assinatura(usuario: Usuario = Depends(require_admin)):
    """
    Executa manualmente o job de lembretes de assinatura
    """
    resultado = await enviar_lembretes_assinatura()
    
    return {
        "success": True,
        "job": "lembretes_assinatura",
        "executado_em": datetime.utcnow().isoformat(),
        "resultado": resultado
    }


@router.post("/jobs/relatorio-semanal/executar")
async def executar_job_relatorio_semanal(usuario: Usuario = Depends(require_admin)):
    """
    Executa manualmente o job de relatório semanal
    """
    resultado = await gerar_relatorio_semanal()
    
    return {
        "success": True,
        "job": "relatorio_semanal",
        "executado_em": datetime.utcnow().isoformat(),
        "resultado": resultado
    }


@router.post("/jobs/reconciliacao/executar")
async def executar_job_reconciliacao(usuario: Usuario = Depends(require_admin)):
    """
    Executa manualmente o job de reconciliação de dados
    """
    
    resultado = await job_reconciliacao_semanal()
    
    return {
        "success": True,
        "job": "reconciliacao_semanal",
        "executado_em": datetime.utcnow().isoformat(),
        "resultado": resultado
    }


@router.get("/jobs/historico")
async def listar_historico_jobs(
    limit: int = 50,
    usuario: Usuario = Depends(require_admin)
):
    """
    Lista o histórico de execuções de jobs
    """
    # Buscar logs de execução de jobs
    jobs_logs = await db.jobs_execucoes.find(
        {},
        {"_id": 0}
    ).sort("executado_em", -1).limit(limit).to_list(limit)
    
    # Buscar logs de planos
    planos_logs = await db.logs_planos.find(
        {"acao": {"$in": ["expiracao_automatica", "correcao_inconsistencia"]}},
        {"_id": 0}
    ).sort("data_acao", -1).limit(limit).to_list(limit)
    
    return {
        "success": True,
        "jobs_execucoes": jobs_logs,
        "logs_planos": planos_logs,
        "total_jobs": len(jobs_logs),
        "total_logs_planos": len(planos_logs)
    }


@router.get("/relatorios/reconciliacao")
async def listar_relatorios_reconciliacao(
    limit: int = 10,
    usuario: Usuario = Depends(require_admin)
):
    """
    Lista os relatórios de reconciliação gerados
    """
    relatorios = await db.relatorios_reconciliacao.find(
        {},
        {"_id": 0}
    ).sort("executado_em", -1).limit(limit).to_list(limit)
    
    return {
        "success": True,
        "relatorios": relatorios,
        "total": len(relatorios)
    }


@router.post("/planos/corrigir-inconsistencia/{usuario_id}")
async def corrigir_inconsistencia_usuario(
    usuario_id: str,
    usuario: Usuario = Depends(require_admin)
):
    """
    Corrige manualmente inconsistências no plano de um usuário específico
    """
    resultado = await verificar_e_corrigir_inconsistencias(usuario_id)
    
    return {
        "success": True,
        "usuario_id": usuario_id,
        "resultado": resultado,
        "executado_em": datetime.utcnow().isoformat()
    }


@router.get("/estatisticas")
async def obter_estatisticas(usuario: Usuario = Depends(require_admin)):
    """
    Retorna estatísticas gerais sobre jobs e planos
    """
    # Contar execuções de jobs nas últimas 24h
    
    h24_atras = datetime.utcnow() - timedelta(hours=24)
    
    jobs_24h = await db.jobs_execucoes.count_documents({
        "executado_em": {"$gte": h24_atras.isoformat()}
    })
    
    # Contar logs de planos nas últimas 24h
    planos_24h = await db.logs_planos.count_documents({
        "data_acao": {"$gte": h24_atras.isoformat()}
    })
    
    # Contar planos expirados automaticamente nos últimos 7 dias
    d7_atras = datetime.utcnow() - timedelta(days=7)
    
    expiracoes_7d = await db.logs_planos.count_documents({
        "acao": "expiracao_automatica",
        "data_acao": {"$gte": d7_atras.isoformat()}
    })
    
    # Contar correções automáticas nos últimos 7 dias
    correcoes_7d = await db.logs_planos.count_documents({
        "acao": "correcao_inconsistencia",
        "data_acao": {"$gte": d7_atras.isoformat()}
    })
    
    # Status do scheduler
    scheduler_status = await get_scheduler_status()
    
    return {
        "success": True,
        "scheduler": scheduler_status,
        "estatisticas": {
            "jobs_executados_24h": jobs_24h,
            "logs_planos_24h": planos_24h,
            "planos_expirados_7d": expiracoes_7d,
            "correcoes_automaticas_7d": correcoes_7d
        },
        "timestamp": now_utc().isoformat()  # 🆕 Usar timezone UTC com timezone info
    }
