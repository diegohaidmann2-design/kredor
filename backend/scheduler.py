"""
Scheduler Automático para Jobs Diários e Semanais
Utiliza APScheduler para executar tarefas em background de forma automática
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone
import asyncio
import socket
from jobs.email_jobs import executar_job_diario, enviar_lembretes_trial, enviar_lembretes_assinatura
from jobs.relatorio_semanal import gerar_relatorio_semanal
from jobs.processar_pagamentos_pendentes import processar_pagamentos_pendentes  # Desativado
from jobs.notificacoes_job import job_verificar_vencimentos_todos, job_verificar_assinaturas, job_resumo_diario_admin
from services.plano_service import verificar_e_corrigir_inconsistencias, gerar_relatorio_reconciliacao
from services.juros_mora_service import atualizar_todas_parcelas_atrasadas
from jobs.whatsapp_fila_job import job_processar_fila_whatsapp
from config import db
from jobs.emprestimos_abertos_job import job_gerar_parcelas_emprestimos_abertos
from jobs.inadimplencia_job import job_inadimplencia
from jobs.resumo_whatsapp_job import job_resumo_semanal_whatsapp
from services.backup_service import criar_backup



# Instância global do scheduler
scheduler = None

# Documento único de status publicado no Mongo. Como o scheduler roda num
# processo separado (container `gestorcred_scheduler`), os workers da API
# leem daqui para responder /admin/scheduler/status.
STATUS_DOC_ID = "singleton"
STATUS_STALE_SECONDS = 180


def _jobs_snapshot():
    """Lista serializável dos jobs registrados no scheduler local."""
    jobs_info = []
    for job in scheduler.get_jobs():
        next_run = job.next_run_time
        jobs_info.append({
            "id": job.id,
            "name": job.name,
            "next_run": next_run.isoformat() if next_run else None,
            "trigger": str(job.trigger),
        })
    return jobs_info


async def publicar_status_scheduler():
    """Publica estado + heartbeat do scheduler no Mongo (observabilidade fora do processo)."""
    if scheduler is None:
        return
    await db.scheduler_status.update_one(
        {"_id": STATUS_DOC_ID},
        {"$set": {
            "status": "running",
            "jobs": _jobs_snapshot(),
            "total_jobs": len(scheduler.get_jobs()),
            "host": socket.gethostname(),
            "heartbeat": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )


async def job_backup_automatico():
    """
    Job para criar backup automático do banco de dados a cada 6 horas
    """
    print("=" * 60)
    print(f"⏰ [Scheduler] Backup automático - {datetime.now().isoformat()}")
    print("=" * 60)
    try:
        from config import db
        import uuid
        from datetime import timezone

        info = await criar_backup(iniciado_por="scheduler")

        # Registrar no log
        await db.backup_logs.insert_one({
            "id": str(uuid.uuid4()),
            "tipo": "automatico",
            "iniciado_por": "scheduler",
            "arquivo": info["nome"],
            "tamanho_mb": info["tamanho_mb"],
            "status": "sucesso",
            "created_at": datetime.now(timezone.utc).isoformat()
        })

        print(f"✅ [Scheduler] Backup automático concluído: {info['nome']} ({info['tamanho_mb']} MB)")
        return {"success": True, "arquivo": info["nome"]}
    except Exception as e:
        print(f"❌ [Scheduler] Erro no backup automático: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


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
    
    # JOB 6: REMOVIDO - Processar pagamentos Stripe desativado
    # Sistema agora usa webhooks automáticos do Asaas e Mercado Pago
    
    
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
    
    # JOB 10: Atualizar juros de mora (a cada 6 horas)
    scheduler.add_job(
        atualizar_todas_parcelas_atrasadas,
        IntervalTrigger(hours=6),
        id='atualizar_juros_mora',
        name='Atualizar juros de mora e multas',
        replace_existing=True,
        misfire_grace_time=3600
    )
    print("   ✅ Job agendado: Atualizar juros de mora (a cada 6 horas)")
    
    # JOB 11: Processar fila de WhatsApp (a cada 2 minutos)
    scheduler.add_job(
        job_processar_fila_whatsapp,
        IntervalTrigger(minutes=2),
        id='processar_fila_whatsapp',
        name='Processar fila de mensagens WhatsApp',
        replace_existing=True,
        misfire_grace_time=120
    )
    print("   ✅ Job agendado: Processar fila WhatsApp (a cada 2 minutos)")
    
    # Job 11: Gerar parcelas para empréstimos sem prazo
    scheduler.add_job(
        job_gerar_parcelas_emprestimos_abertos,
        CronTrigger(hour=0, minute=10),  # Todo dia às 00:10
        id='gerar_parcelas_abertos',
        name='Gerar parcelas para empréstimos abertos',
        replace_existing=True,
        misfire_grace_time=3600
    )
    print("   ✅ Job agendado: Gerar parcelas empréstimos abertos (diariamente 00:10)")

    # JOB 12: Backup automático (a cada 6 horas)
    scheduler.add_job(
        job_backup_automatico,
        IntervalTrigger(hours=6),
        id='backup_automatico',
        name='Backup automático do banco de dados',
        replace_existing=True,
        misfire_grace_time=3600
    )
    print("   ✅ Job agendado: Backup automático (a cada 6 horas)")

    # JOB 13: Recalcular inadimplência (30+ dias de atraso) - diariamente às 00:30
    scheduler.add_job(
        job_inadimplencia,
        CronTrigger(hour=0, minute=30),
        id='recalcular_inadimplencia',
        name='Recalcular status de inadimplência (30+ dias)',
        replace_existing=True,
        misfire_grace_time=3600
    )
    print("   ✅ Job agendado: Recalcular inadimplência (diariamente 00:30)")

    # JOB 14: Resumo semanal via WhatsApp para o gestor (segunda-feira 08:30)
    scheduler.add_job(
        job_resumo_semanal_whatsapp,
        CronTrigger(day_of_week='mon', hour=8, minute=30),
        id='resumo_semanal_whatsapp',
        name='Resumo semanal da carteira via WhatsApp',
        replace_existing=True,
        misfire_grace_time=3600
    )
    print("   ✅ Job agendado: Resumo semanal WhatsApp (segunda-feira 08:30)")

    # JOB interno: publicar heartbeat/status no Mongo (a cada 1 min, 1ª execução imediata)
    scheduler.add_job(
        publicar_status_scheduler,
        IntervalTrigger(minutes=1),
        id='publicar_status_scheduler',
        name='Publicar heartbeat/status do scheduler',
        replace_existing=True,
        misfire_grace_time=60,
        next_run_time=datetime.now(),
    )
    print("   ✅ Job agendado: Heartbeat/status do scheduler (a cada 1 minuto)")

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


async def get_scheduler_status():
    """
    Retorna o status atual do scheduler e seus jobs.

    - Se este processo roda o scheduler (dev / single-instance): reporta direto.
    - Caso contrário (workers da API com RUN_SCHEDULER=false): lê o status
      publicado no Mongo pelo container `gestorcred_scheduler`.
    """
    global scheduler

    if scheduler is not None:
        jobs_info = _jobs_snapshot()
        return {
            "status": "running",
            "jobs": jobs_info,
            "total_jobs": len(jobs_info),
            "source": "in-process",
        }

    doc = await db.scheduler_status.find_one({"_id": STATUS_DOC_ID})
    if not doc:
        return {
            "status": "unknown",
            "jobs": [],
            "total_jobs": 0,
            "source": "mongo",
            "detail": "nenhum heartbeat publicado ainda",
        }

    try:
        hb = datetime.fromisoformat(doc["heartbeat"])
        idade = (datetime.now(timezone.utc) - hb).total_seconds()
        stale = idade > STATUS_STALE_SECONDS
    except (KeyError, ValueError, TypeError):
        stale = True

    return {
        "status": "stale" if stale else doc.get("status", "running"),
        "jobs": doc.get("jobs", []),
        "total_jobs": doc.get("total_jobs", 0),
        "host": doc.get("host"),
        "heartbeat": doc.get("heartbeat"),
        "source": "mongo",
    }


# Para testes manuais
if __name__ == "__main__":
    print("🧪 Modo de teste do Scheduler")
    print("Este módulo deve ser importado no server.py")
    print("Para testar jobs individuais:")
    print("  python -m jobs.email_jobs")
    print("  python -m jobs.relatorio_semanal")
