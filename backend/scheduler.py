"""
Scheduler Automático para Jobs Diários e Semanais
Utiliza APScheduler para executar tarefas em background de forma automática
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import asyncio
from jobs.email_jobs import executar_job_diario, enviar_lembretes_trial, enviar_lembretes_assinatura
from jobs.relatorio_semanal import gerar_relatorio_semanal
from jobs.processar_pagamentos_pendentes import processar_pagamentos_pendentes
from jobs.notificacoes_job import job_verificar_vencimentos_todos, job_verificar_assinaturas, job_resumo_diario_admin
from services.plano_service import verificar_e_corrigir_inconsistencias, gerar_relatorio_reconciliacao
from config import db


# Instância global do scheduler
scheduler = None


async def job_verificar_planos_expirados():
    """
    Job para verificar e atualizar planos expirados usando plano_service
    Executa diariamente às 00:00
    """
    print("=" * 60)
    print(f"⏰ [Scheduler] Verificando planos expirados - {datetime.now().isoformat()}")
    print("=" * 60)
    
    try:
        agora = datetime.utcnow()
        usuarios_atualizados = 0
        
        # Buscar usuários com plano ativo
        cursor = db.usuarios.find({
            "plano_ativo": True,
            "$or": [
                {"data_expiracao_plano": {"$exists": True}},
                {"data_fim_trial": {"$exists": True}}
            ]
        })
        
        async for usuario in cursor:
            usuario_id = usuario.get("id")
            plano = usuario.get("plano", "trial")
            
            # Determinar data de expiração
            if plano == "trial":
                data_exp = usuario.get("data_fim_trial")
            else:
                data_exp = usuario.get("data_expiracao_plano") or usuario.get("data_fim_trial")
            
            if not data_exp:
                continue
            
            # Verificar se expirou
            try:
                if isinstance(data_exp, str):
                    data_expiracao = datetime.fromisoformat(data_exp.replace('Z', '+00:00'))
                else:
                    data_expiracao = data_exp
                
                if data_expiracao < agora:
                    # Desativar plano expirado
                    await db.usuarios.update_one(
                        {"id": usuario_id},
                        {"$set": {
                            "plano_ativo": False,
                            "updated_at": agora.isoformat()
                        }}
                    )
                    
                    # Log de auditoria
                    await db.logs_planos.insert_one({
                        "usuario_id": usuario_id,
                        "usuario_email": usuario.get("email"),
                        "acao": "expiracao_automatica",
                        "plano": plano,
                        "data_expiracao": data_exp,
                        "data_acao": agora.isoformat(),
                        "origem": "scheduler"
                    })
                    
                    usuarios_atualizados += 1
                    print(f"   ❌ Plano expirado: {usuario.get('email')} ({plano})")
                    
            except (ValueError, TypeError, AttributeError) as e:
                print(f"   ⚠️ Erro ao processar {usuario.get('email')}: {e}")
        
        print(f"✅ [Scheduler] {usuarios_atualizados} planos expirados desativados")
        print("=" * 60)
        
        return {
            "success": True,
            "usuarios_atualizados": usuarios_atualizados,
            "executado_em": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ [Scheduler] Erro ao verificar planos: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


async def job_reconciliacao_semanal():
    """
    Job para executar reconciliação de dados semanalmente
    Executa toda segunda-feira às 08:00
    """
    print("=" * 60)
    print(f"⏰ [Scheduler] Executando reconciliação semanal - {datetime.now().isoformat()}")
    print("=" * 60)
    
    try:
        # Gerar relatório de reconciliação
        relatorio = await gerar_relatorio_reconciliacao()
        
        total_inconsistencias = len(relatorio.get("inconsistencias", []))
        
        print(f"📊 Relatório de reconciliação gerado:")
        print(f"   Total de inconsistências: {total_inconsistencias}")
        
        if total_inconsistencias > 0:
            print("   Tipos de inconsistências encontradas:")
            tipos = {}
            for inc in relatorio.get("inconsistencias", []):
                tipo = inc.get("tipo", "desconhecido")
                tipos[tipo] = tipos.get(tipo, 0) + 1
            
            for tipo, count in tipos.items():
                print(f"     - {tipo}: {count}")
        
        # Salvar relatório no banco
        await db.relatorios_reconciliacao.insert_one({
            **relatorio,
            "executado_em": datetime.utcnow().isoformat()
        })
        
        print("✅ [Scheduler] Reconciliação concluída")
        print("=" * 60)
        
        return relatorio
        
    except Exception as e:
        print(f"❌ [Scheduler] Erro na reconciliação: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


def setup_scheduler():
    """
    Configura e inicia o scheduler com todos os jobs
    """
    global scheduler
    
    if scheduler is not None:
        print("⚠️ Scheduler já está rodando")
        return scheduler
    
    print("🚀 Iniciando Scheduler de Jobs Automáticos...")
    
    scheduler = AsyncIOScheduler()
    
    # JOB 1: Verificar planos expirados (diariamente às 00:00)
    scheduler.add_job(
        job_verificar_planos_expirados,
        CronTrigger(hour=0, minute=0),
        id='verificar_planos_expirados',
        name='Verificar e desativar planos expirados',
        replace_existing=True,
        misfire_grace_time=3600  # 1 hora de tolerância
    )
    print("   ✅ Job agendado: Verificar planos expirados (diariamente 00:00)")
    
    # JOB 2: Enviar lembretes de trial (diariamente às 09:00)
    scheduler.add_job(
        enviar_lembretes_trial,
        CronTrigger(hour=9, minute=0),
        id='lembretes_trial',
        name='Enviar lembretes de trial expirando',
        replace_existing=True,
        misfire_grace_time=3600
    )
    print("   ✅ Job agendado: Lembretes de trial (diariamente 09:00)")
    
    # JOB 3: Enviar lembretes de assinatura (diariamente às 09:30)
    scheduler.add_job(
        enviar_lembretes_assinatura,
        CronTrigger(hour=9, minute=30),
        id='lembretes_assinatura',
        name='Enviar lembretes de assinatura vencendo',
        replace_existing=True,
        misfire_grace_time=3600
    )
    print("   ✅ Job agendado: Lembretes de assinatura (diariamente 09:30)")
    
    # JOB 4: Relatório semanal (segunda-feira às 08:00)
    scheduler.add_job(
        gerar_relatorio_semanal,
        CronTrigger(day_of_week='mon', hour=8, minute=0),
        id='relatorio_semanal',
        name='Gerar relatório semanal',
        replace_existing=True,
        misfire_grace_time=7200  # 2 horas de tolerância
    )
    print("   ✅ Job agendado: Relatório semanal (segunda-feira 08:00)")
    
    # JOB 5: Reconciliação de dados (segunda-feira às 08:00)
    scheduler.add_job(
        job_reconciliacao_semanal,
        CronTrigger(day_of_week='mon', hour=8, minute=0),
        id='reconciliacao_semanal',
        name='Reconciliação semanal de dados',
        replace_existing=True,
        misfire_grace_time=7200
    )
    print("   ✅ Job agendado: Reconciliação semanal (segunda-feira 08:00)")
    
    # JOB 6: Processar pagamentos pendentes do Stripe (a cada 5 minutos)
    scheduler.add_job(
        processar_pagamentos_pendentes,
        IntervalTrigger(minutes=5),
        id='processar_pagamentos_pendentes',
        name='Processar pagamentos pendentes (Stripe)',
        replace_existing=True,
        misfire_grace_time=300  # 5 minutos de tolerância
    )
    print("   ✅ Job agendado: Processar pagamentos pendentes (a cada 5 minutos)")
    
    # JOB 7: Verificar vencimentos e criar notificações (a cada hora, das 8h às 20h)
    scheduler.add_job(
        job_verificar_vencimentos_todos,
        CronTrigger(hour='8-20', minute=0),
        id='verificar_vencimentos_notificacoes',
        name='Verificar vencimentos e criar notificações',
        replace_existing=True,
        misfire_grace_time=3600
    )
    print("   ✅ Job agendado: Verificar vencimentos (horário comercial, a cada hora)")
    
    # JOB 8: Verificar assinaturas expirando (diariamente às 09:15)
    scheduler.add_job(
        job_verificar_assinaturas,
        CronTrigger(hour=9, minute=15),
        id='verificar_assinaturas_notificacoes',
        name='Verificar assinaturas expirando',
        replace_existing=True,
        misfire_grace_time=3600
    )
    print("   ✅ Job agendado: Verificar assinaturas (diariamente 09:15)")
    
    # JOB 9: Resumo diário para admins (diariamente às 08:00)
    scheduler.add_job(
        job_resumo_diario_admin,
        CronTrigger(hour=8, minute=0),
        id='resumo_diario_admin',
        name='Resumo diário para administradores',
        replace_existing=True,
        misfire_grace_time=3600
    )
    print("   ✅ Job agendado: Resumo diário admin (diariamente 08:00)")
    
    # Iniciar o scheduler
    scheduler.start()
    print("✅ Scheduler iniciado com sucesso!")
    print(f"📅 Total de jobs agendados: {len(scheduler.get_jobs())}")
    
    return scheduler


def shutdown_scheduler():
    """
    Para o scheduler de forma segura
    """
    global scheduler
    
    if scheduler is not None:
        print("🛑 Parando scheduler...")
        scheduler.shutdown(wait=False)
        scheduler = None
        print("✅ Scheduler parado")


def get_scheduler_status():
    """
    Retorna o status atual do scheduler e seus jobs
    """
    global scheduler
    
    if scheduler is None:
        return {
            "status": "stopped",
            "jobs": []
        }
    
    jobs_info = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        jobs_info.append({
            "id": job.id,
            "name": job.name,
            "next_run": next_run.isoformat() if next_run else None,
            "trigger": str(job.trigger)
        })
    
    return {
        "status": "running",
        "jobs": jobs_info,
        "total_jobs": len(jobs_info)
    }


# Para testes manuais
if __name__ == "__main__":
    print("🧪 Modo de teste do Scheduler")
    print("Este módulo deve ser importado no server.py")
    print("Para testar jobs individuais:")
    print("  python -m jobs.email_jobs")
    print("  python -m jobs.relatorio_semanal")
