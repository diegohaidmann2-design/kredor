"""
Job automático para processar pagamentos pendentes do Stripe
Executa a cada 5 minutos e verifica sessões com status 'pending'
"""
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os
import stripe
import asyncio

# from emergentintegrations.payments.stripe.checkout import StripeCheckout

# Configuração do MongoDB
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "test_database")
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")


async def processar_pagamentos_pendentes():
    """
    Verifica e processa pagamentos pendentes do Stripe
    """
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    try:
        print("🔍 Verificando pagamentos pendentes do Stripe...")
        
        # Buscar sessões pendentes (criadas nas últimas 24 horas)
        data_limite = datetime.now(timezone.utc) - timedelta(hours=24)
        
        sessoes_pendentes = await db.checkout_sessions.find({
            "status": "pending",
            "gateway": {"$in": ["stripe", None]},  # Incluir sessões sem gateway especificado
            "created_at": {"$gte": data_limite.isoformat()}
        }).to_list(100)
        
        if not sessoes_pendentes:
            print("   ✅ Nenhum pagamento pendente")
            return
        
        print(f"   📋 Encontradas {len(sessoes_pendentes)} sessão(ões) pendente(s)")
        
        # Inicializar Stripe
        try:
            from routes.assinaturas import get_assinatura_gateway_config
            config_gateway = await get_assinatura_gateway_config()
            stripe.api_key = config_gateway.stripe_api_key or os.getenv("STRIPE_API_KEY")
        except Exception as e:
            print(f"⚠️ Erro ao carregar config do Stripe: {e}")
            stripe.api_key = os.getenv("STRIPE_API_KEY")
        
        if not stripe.api_key:
            print("❌ Stripe API Key não configurada.")
            return
        
        processados = 0
        
        for sessao in sessoes_pendentes:
            session_id = sessao.get("session_id")
            usuario_id = sessao.get("usuario_id")
            plano_id = sessao.get("plano_id")
            
            try:
                # Verificar status no Stripe
                stripe_session = await asyncio.to_thread(stripe.checkout.Session.retrieve, session_id)
                
                if stripe_session.payment_status == "paid":
                    print(f"   💳 Pagamento aprovado: {session_id}")
                    
                    # Buscar plano
                    from routes.assinaturas import get_plano_by_id
                    plano = await get_plano_by_id(plano_id)
                    
                    if not plano:
                        print(f"   ⚠️  Plano não encontrado: {plano_id}")
                        continue
                    
                    # Calcular data de vencimento
                    data_vencimento = datetime.now(timezone.utc) + timedelta(days=30)
                    
                    # Atualizar usuário
                    await db.usuarios.update_one(
                        {"id": usuario_id},
                        {"$set": {
                            "plano": plano_id,
                            "plano_ativo": True,
                            "data_vencimento_assinatura": data_vencimento.isoformat(),
                            "payment_status": "paid"
                        }}
                    )
                    
                    # Atualizar sessão
                    await db.checkout_sessions.update_one(
                        {"session_id": session_id},
                        {"$set": {
                            "status": "paid",
                            "paid_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                    
                    # Criar assinatura
                    await db.assinaturas.insert_one({
                        "usuario_id": usuario_id,
                        "plano_id": plano_id,
                        "session_id": session_id,
                        "status": "ativa",
                        "valor": plano.preco,
                        "data_vencimento": data_vencimento.isoformat(),
                        "gateway": "stripe",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "processado_por": "job_automatico"
                    })
                    
                    processados += 1
                    print(f"   ✅ Assinatura ativada: {usuario_id} -> {plano_id}")
                    
            except Exception as e:
                print(f"   ❌ Erro ao processar {session_id}: {e}")
                continue
        
        if processados > 0:
            print(f"\n✅ Total processado: {processados} pagamento(s)")
        
    except Exception as e:
        print(f"❌ Erro no job de pagamentos pendentes: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(processar_pagamentos_pendentes())
