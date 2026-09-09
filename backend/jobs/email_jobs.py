"""
Job automático para enviar emails de cobrança e lembretes
Deve ser executado diariamente via cron
"""
from datetime import datetime, timezone, timedelta
from config import db
from services.email_service import (
    enviar_email,
    email_trial_expirando,
    email_trial_expirado,
    email_assinatura_vencendo,
    email_assinatura_vencida
)


async def enviar_lembretes_trial():
    """Envia lembretes para usuários com trial expirando"""
    print("🔄 Verificando trials expirando...")
    
    agora = datetime.now(timezone.utc)
    usuarios_count = 0
    emails_enviados = 0
    
    # Buscar usuários em trial
    cursor = db.usuarios.find({"plano": "trial", "email_verificado": True})
    
    async for usuario_doc in cursor:
        usuarios_count += 1
        
        data_fim = datetime.fromisoformat(usuario_doc["data_fim_trial"])
        dias_restantes = (data_fim - agora).days
        
        # Enviar avisos em 3 dias, 1 dia antes, e no dia que expirou
        if dias_restantes == 3 or dias_restantes == 1:
            try:
                html, texto = email_trial_expirando(usuario_doc["nome"], dias_restantes)
                sucesso = enviar_email(
                    usuario_doc["email"],
                    f"Seu trial do Kredor acaba em {dias_restantes} {'dia' if dias_restantes == 1 else 'dias'}!",
                    html,
                    texto
                )
                if sucesso:
                    emails_enviados += 1
            except Exception as e:
                print(f"Erro ao enviar email para {usuario_doc['email']}: {e}")
        
        elif dias_restantes < 0:  # Trial já expirou
            # Enviar email de trial expirado (apenas uma vez por dia)
            try:
                html, texto = email_trial_expirado(usuario_doc["nome"])
                sucesso = enviar_email(
                    usuario_doc["email"],
                    "Seu trial do Kredor expirou",
                    html,
                    texto
                )
                if sucesso:
                    emails_enviados += 1
                    
                # Bloquear acesso
                await db.usuarios.update_one(
                    {"_id": usuario_doc["_id"]},
                    {"$set": {"plano_ativo": False}}
                )
            except Exception as e:
                print(f"Erro ao processar trial expirado para {usuario_doc['email']}: {e}")
    
    print(f"✅ Verificados {usuarios_count} trials, enviados {emails_enviados} emails")
    return {"usuarios_verificados": usuarios_count, "emails_enviados": emails_enviados}


async def enviar_lembretes_assinatura():
    """Envia lembretes para usuários com assinatura vencendo"""
    print("🔄 Verificando assinaturas vencendo...")
    
    agora = datetime.now(timezone.utc)
    usuarios_count = 0
    emails_enviados = 0
    
    # Buscar usuários com assinatura paga
    cursor = db.usuarios.find({
        "plano": {"$ne": "trial"},
        "email_verificado": True,
        "data_vencimento_assinatura": {"$exists": True}
    })
    
    async for usuario_doc in cursor:
        usuarios_count += 1
        
        data_venc = datetime.fromisoformat(usuario_doc["data_vencimento_assinatura"])
        dias_restantes = (data_venc - agora).days
        
        # Enviar avisos em 7, 3, 1 dia antes
        if dias_restantes in [7, 3, 1]:
            try:
                html, texto = email_assinatura_vencendo(
                    usuario_doc["nome"],
                    usuario_doc["plano"],
                    dias_restantes,
                    data_venc.strftime("%d/%m/%Y")
                )
                sucesso = enviar_email(
                    usuario_doc["email"],
                    f"Sua assinatura do Kredor vence em {dias_restantes} {'dia' if dias_restantes == 1 else 'dias'}",
                    html,
                    texto
                )
                if sucesso:
                    emails_enviados += 1
            except Exception as e:
                print(f"Erro ao enviar email para {usuario_doc['email']}: {e}")
        
        elif dias_restantes < 0:  # Assinatura vencida
            try:
                html, texto = email_assinatura_vencida(
                    usuario_doc["nome"],
                    usuario_doc["plano"]
                )
                sucesso = enviar_email(
                    usuario_doc["email"],
                    "Sua assinatura do Kredor venceu",
                    html,
                    texto
                )
                if sucesso:
                    emails_enviados += 1
                
                # Bloquear acesso
                await db.usuarios.update_one(
                    {"_id": usuario_doc["_id"]},
                    {"$set": {"plano_ativo": False}}
                )
            except Exception as e:
                print(f"Erro ao processar assinatura vencida para {usuario_doc['email']}: {e}")
    
    print(f"✅ Verificadas {usuarios_count} assinaturas, enviados {emails_enviados} emails")
    return {"usuarios_verificados": usuarios_count, "emails_enviados": emails_enviados}


async def executar_job_diario():
    """Executa todos os jobs diários"""
    print("=" * 60)
    print(f"⏰ Executando job diário - {datetime.now().isoformat()}")
    print("=" * 60)
    
    resultado_trial = await enviar_lembretes_trial()
    resultado_assinatura = await enviar_lembretes_assinatura()
    
    print("=" * 60)
    print("✅ Job diário concluído!")
    print(f"Total de emails enviados: {resultado_trial['emails_enviados'] + resultado_assinatura['emails_enviados']}")
    print("=" * 60)
    
    return {
        "executado_em": datetime.now().isoformat(),
        "trial": resultado_trial,
        "assinatura": resultado_assinatura
    }


if __name__ == "__main__":
    # Para testar manualmente
    import asyncio
    asyncio.run(executar_job_diario())
