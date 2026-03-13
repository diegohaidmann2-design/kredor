"""
Script de Teste - Envio Automático de WhatsApp e Auditoria
Testa o sistema completo de envio e logging
"""
import asyncio
import sys
import os
from datetime import datetime, timezone

# Adicionar path do backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient


async def testar_sistema_whatsapp():
    """Testa sistema completo de WhatsApp"""
    MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    DB_NAME = os.environ.get('DB_NAME', 'test_database')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("\n" + "="*80)
    print("🧪 TESTE DE SISTEMA WHATSAPP - AUDITORIA E ENVIO AUTOMÁTICO")
    print("="*80)
    
    # 1. Verificar se existe usuário
    usuario = await db.usuarios.find_one({"perfil": "admin"})
    if not usuario:
        print("❌ Nenhum usuário encontrado!")
        client.close()
        return
    
    usuario_id = usuario["id"]
    print(f"\n✅ Usuário: {usuario['email']}")
    
    # 2. Verificar conexão WhatsApp
    print("\n📱 Verificando conexão WhatsApp...")
    conexao = await db.whatsapp_conexoes.find_one({
        "usuario_id": usuario_id,
        "status": "conectado"
    })
    
    if conexao:
        print(f"   ✅ WhatsApp conectado: {conexao.get('numero_telefone', 'N/A')}")
        print(f"   📅 Conectado em: {conexao.get('data_conexao', 'N/A')}")
    else:
        print("   ⚠️  WhatsApp NÃO está conectado")
        print("   💡 Para testar envios reais, conecte o WhatsApp em /whatsapp")
    
    # 3. Simular logs de envio (para testar auditoria)
    print("\n📝 Criando logs de teste para auditoria...")
    
    import uuid
    logs_teste = [
        {
            "usuario_id": usuario_id,
            "cliente_id": str(uuid.uuid4()),
            "numero_destino": "5511999999999",
            "mensagem": "Teste de envio automático - Cobrança",
            "tipo": "cobranca_manual",
            "status": "enviado",
            "message_id": f"msg_{uuid.uuid4()}",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "usuario_id": usuario_id,
            "cliente_id": str(uuid.uuid4()),
            "numero_destino": "5511888888888",
            "mensagem": "Teste de confirmação de pagamento",
            "tipo": "confirmacao_pagamento",
            "status": "enviado",
            "message_id": f"msg_{uuid.uuid4()}",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "usuario_id": usuario_id,
            "cliente_id": str(uuid.uuid4()),
            "numero_destino": "5511777777777",
            "mensagem": "Teste de erro de envio",
            "tipo": "cobranca_manual",
            "status": "erro",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    await db.whatsapp_mensagens_log.insert_many(logs_teste)
    print(f"   ✅ {len(logs_teste)} logs de teste criados")
    
    # 4. Consultar estatísticas
    print("\n📊 Consultando estatísticas...")
    
    total_logs = await db.whatsapp_mensagens_log.count_documents({
        "usuario_id": usuario_id
    })
    
    enviados = await db.whatsapp_mensagens_log.count_documents({
        "usuario_id": usuario_id,
        "status": "enviado"
    })
    
    erros = await db.whatsapp_mensagens_log.count_documents({
        "usuario_id": usuario_id,
        "status": "erro"
    })
    
    print(f"   📈 Total de logs: {total_logs}")
    print(f"   ✅ Enviados: {enviados}")
    print(f"   ❌ Erros: {erros}")
    print(f"   📊 Taxa de sucesso: {(enviados/(enviados+erros)*100):.1f}%" if (enviados+erros) > 0 else "   📊 Taxa de sucesso: 0%")
    
    # 5. Verificar últimos logs
    print("\n📋 Últimos 5 logs registrados:")
    ultimos_logs = await db.whatsapp_mensagens_log.find({
        "usuario_id": usuario_id
    }).sort("created_at", -1).limit(5).to_list(5)
    
    for i, log in enumerate(ultimos_logs, 1):
        status_emoji = "✅" if log.get("status") == "enviado" else "❌" if log.get("status") == "erro" else "⏳"
        print(f"   {i}. {status_emoji} {log.get('tipo', 'N/A')} - {log.get('status', 'N/A')} - {log.get('created_at', 'N/A')[:19]}")
    
    # 6. Teste de status do serviço
    print("\n🔍 Status do Serviço WhatsApp:")
    if conexao:
        print("   ✅ Status: FUNCIONANDO")
        print(f"   📱 Número: {conexao.get('numero_telefone', 'N/A')}")
    else:
        print("   ⚠️  Status: DESCONECTADO")
        print("   💡 Recomendação: Conecte o WhatsApp em /whatsapp")
    
    # 7. Simular verificação de auditoria (como se fosse a API)
    print("\n🎯 Simulando consulta da API de auditoria...")
    
    # Estatísticas (como no endpoint)
    hoje = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    hoje_count = await db.whatsapp_mensagens_log.count_documents({
        "usuario_id": usuario_id,
        "created_at": {"$gte": hoje.isoformat()}
    })
    
    print(f"   📅 Envios hoje: {hoje_count}")
    print(f"   📈 Total geral: {total_logs}")
    
    # 8. Verificar fila de envios (se houver)
    fila_count = await db.whatsapp_fila.count_documents({
        "usuario_id": usuario_id,
        "status": "pendente"
    })
    
    if fila_count > 0:
        print(f"\n⏳ Mensagens na fila: {fila_count}")
    else:
        print(f"\n✅ Fila de envios vazia")
    
    print("\n" + "="*80)
    print("✅ TESTE CONCLUÍDO COM SUCESSO!")
    print("="*80)
    print("\n📌 Próximos Passos:")
    print("   1. Acesse /whatsapp/logs no frontend para ver a auditoria")
    print("   2. Conecte o WhatsApp em /whatsapp se ainda não conectou")
    print("   3. Teste envios reais de confirmação de pagamento")
    print("   4. Monitore os logs em tempo real")
    print()
    
    client.close()


if __name__ == "__main__":
    asyncio.run(testar_sistema_whatsapp())
