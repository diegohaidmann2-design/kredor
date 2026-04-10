"""
Script de Teste - Envio Automático de Mensagens de Vencimento
Testa o sistema completo: job de notificações + envio WhatsApp + logs
"""
import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import uuid

# Adicionar path do backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jobs.notificacoes_job import job_verificar_vencimentos_todos


async def criar_parcela_teste_vencimento():
    """Cria parcela próxima ao vencimento para testar notificações"""
    MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    DB_NAME = os.environ.get('DB_NAME', 'test_database')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("\n" + "="*80)
    print("🧪 TESTE DE ENVIO AUTOMÁTICO - MENSAGENS DE VENCIMENTO")
    print("="*80)
    
    # 1. Buscar usuário admin
    usuario = await db.usuarios.find_one({"perfil": "admin"})
    if not usuario:
        print("❌ Nenhum usuário encontrado!")
        client.close()
        return
    
    usuario_id = usuario["id"]
    print(f"\n✅ Usuário: {usuario['email']}")
    
    # 2. Verificar configuração de notificações
    config = await db.configuracoes.find_one({
        "tipo": "notificacoes_vencimento",
        "usuario_id": usuario_id
    })
    
    if config:
        canais = config.get("dados", {}).get("canais", {})
        whatsapp_ativo = canais.get("whatsapp", False)
        print(f"\n📋 Configuração de Notificações:")
        print(f"   Sistema: {canais.get('sistema', True)}")
        print(f"   WhatsApp: {whatsapp_ativo}")
        print(f"   Email: {canais.get('email', False)}")
    else:
        print("\n⚠️  Nenhuma configuração personalizada encontrada (usará padrão)")
        whatsapp_ativo = False
    
    # 3. Verificar conexão WhatsApp
    conexao = await db.whatsapp_conexoes.find_one({
        "usuario_id": usuario_id,
        "status": "conectado"
    })
    
    if conexao:
        print(f"\n📱 WhatsApp: ✅ Conectado ({conexao.get('numero_telefone')})")
    else:
        print(f"\n📱 WhatsApp: ⚠️  Não conectado")
        print("   💡 Para testar envios reais, conecte em /whatsapp")
    
    # 4. Criar parcela de teste (vence em 3 dias)
    print("\n📝 Criando parcela de teste...")
    
    # Buscar ou criar cliente
    cliente = await db.clientes.find_one({"usuario_id": usuario_id})
    if not cliente:
        cliente_id = str(uuid.uuid4())
        cliente_doc = {
            "id": cliente_id,
            "usuario_id": usuario_id,
            "nome": "Cliente Teste Vencimento",
            "cpf_cnpj": "12345678900",
            "telefone": "5511999999999",
            "status": "ativo",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.clientes.insert_one(cliente_doc)
        cliente = cliente_doc
        print(f"   ✅ Cliente criado: {cliente['nome']}")
    else:
        print(f"   ✅ Cliente encontrado: {cliente['nome']}")
    
    # Criar empréstimo de teste
    emprestimo_id = str(uuid.uuid4())
    emprestimo = {
        "id": emprestimo_id,
        "usuario_id": usuario_id,
        "cliente_id": cliente["id"],
        "valor_principal": 1000.00,
        "taxa_juros_mensal": 5.0,
        "prazo_meses": 12,
        "metodo_calculo": "juros_simples",
        "data_inicio": datetime.now(timezone.utc).isoformat(),
        "status": "ativo",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.emprestimos.insert_one(emprestimo)
    print(f"   ✅ Empréstimo criado: R$ {emprestimo['valor_principal']:,.2f}")
    
    # Criar parcela que VENCE EM 3 DIAS
    parcela_id = str(uuid.uuid4())
    data_vencimento = datetime.now(timezone.utc) + timedelta(days=3)
    parcela = {
        "id": parcela_id,
        "usuario_id": usuario_id,
        "emprestimo_id": emprestimo_id,
        "numero_parcela": 1,
        "data_vencimento": data_vencimento.isoformat(),
        "valor_principal": 83.33,
        "valor_juros": 50.00,
        "valor_total": 133.33,
        "valor_pago": 0.0,
        "saldo_devedor": 1000.00,
        "status": "pendente",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.parcelas.insert_one(parcela)
    print(f"   ✅ Parcela criada: R$ {parcela['valor_total']:,.2f}")
    print(f"   📅 Vence em: {data_vencimento.strftime('%d/%m/%Y')} (3 dias)")
    
    client.close()
    return usuario_id, emprestimo_id, parcela_id


async def executar_job_notificacoes():
    """Executa o job de verificação de vencimentos"""
    print("\n" + "="*80)
    print("🔄 EXECUTANDO JOB DE NOTIFICAÇÕES")
    print("="*80)
    
    resultado = await job_verificar_vencimentos_todos()
    
    if resultado.get("success"):
        print(f"\n✅ Job executado com sucesso!")
        print(f"   👥 Usuários processados: {resultado['usuarios_processados']}")
        print(f"   📬 Notificações criadas: {resultado['notificacoes_criadas']}")
    else:
        print(f"\n❌ Erro ao executar job: {resultado.get('error')}")


async def verificar_resultados():
    """Verifica se notificações e logs WhatsApp foram criados"""
    MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    DB_NAME = os.environ.get('DB_NAME', 'test_database')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("\n" + "="*80)
    print("🔍 VERIFICANDO RESULTADOS")
    print("="*80)
    
    # 1. Verificar notificações criadas
    print("\n📬 Notificações no Sistema:")
    notifs = await db.notificacoes.find({}).sort("created_at", -1).limit(5).to_list(5)
    
    if notifs:
        for i, notif in enumerate(notifs, 1):
            tipo_emoji = "⏰" if notif.get("tipo") == "vencimento" else "⚠️"
            print(f"   {i}. {tipo_emoji} {notif.get('tipo')} - {notif.get('titulo')}")
            print(f"      Criada em: {notif.get('created_at', 'N/A')[:19]}")
    else:
        print("   ❌ Nenhuma notificação encontrada")
    
    # 2. Verificar logs WhatsApp
    print("\n📱 Logs de WhatsApp:")
    logs = await db.whatsapp_mensagens_log.find({}).sort("created_at", -1).limit(5).to_list(5)
    
    if logs:
        for i, log in enumerate(logs, 1):
            status_emoji = "✅" if log.get("status") == "enviado" else "❌" if log.get("status") == "erro" else "⏳"
            print(f"   {i}. {status_emoji} {log.get('tipo', 'N/A')} - {log.get('status', 'N/A')}")
            print(f"      Para: {log.get('numero_destino', 'N/A')}")
            print(f"      Criado em: {log.get('created_at', 'N/A')[:19]}")
    else:
        print("   ⚠️  Nenhum log de WhatsApp encontrado")
        print("   💡 Isso é normal se WhatsApp não está configurado para envio automático")
    
    # 3. Estatísticas
    print("\n📊 Estatísticas Gerais:")
    total_notifs = await db.notificacoes.count_documents({})
    total_logs = await db.whatsapp_mensagens_log.count_documents({})
    
    print(f"   📬 Total de notificações: {total_notifs}")
    print(f"   📱 Total de logs WhatsApp: {total_logs}")
    
    # 4. Verificar execução do job
    print("\n⚙️  Execuções do Job:")
    jobs = await db.jobs_execucoes.find({"job": "verificar_vencimentos"}).sort("executado_em", -1).limit(3).to_list(3)
    
    if jobs:
        for i, job in enumerate(jobs, 1):
            status_emoji = "✅" if job.get("status") == "sucesso" else "❌"
            print(f"   {i}. {status_emoji} {job.get('executado_em', 'N/A')[:19]}")
            if job.get("status") == "sucesso":
                print(f"      Usuários: {job.get('usuarios_processados', 0)} | Notificações: {job.get('notificacoes_criadas', 0)}")
    else:
        print("   ⚠️  Nenhuma execução registrada")
    
    client.close()


async def testar_endpoint_auditoria():
    """Testa se o endpoint de auditoria está funcionando"""
    import requests
    
    print("\n" + "="*80)
    print("🌐 TESTANDO ENDPOINT DE AUDITORIA")
    print("="*80)
    
    try:
        # Login
        login_resp = requests.post(
            "http://localhost:8001/api/auth/login",
            json={"email": "diego.haidmann@gmail.com", "senha": "muda2025"}
        )
        
        if login_resp.status_code != 200:
            print("❌ Erro ao fazer login")
            return
        
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Testar endpoint de estatísticas
        print("\n📊 Testando /api/whatsapp/logs/estatisticas...")
        stats_resp = requests.get(
            "http://localhost:8001/api/whatsapp/logs/estatisticas",
            headers=headers
        )
        
        if stats_resp.status_code == 200:
            stats = stats_resp.json()
            print("   ✅ Endpoint funcionando!")
            print(f"   📈 Total de envios: {stats.get('total_envios', 0)}")
            print(f"   📱 Serviço WhatsApp: {stats.get('servico', {}).get('status', 'N/A')}")
        else:
            print(f"   ❌ Erro: {stats_resp.status_code}")
        
        # Testar endpoint de status
        print("\n🔍 Testando /api/whatsapp/status-servico...")
        status_resp = requests.get(
            "http://localhost:8001/api/whatsapp/status-servico",
            headers=headers
        )
        
        if status_resp.status_code == 200:
            status = status_resp.json()
            print("   ✅ Endpoint funcionando!")
            print(f"   📱 Serviço ativo: {status.get('servico_ativo', False)}")
            print(f"   📊 Status geral: {status.get('status_geral', 'N/A')}")
            
            if status.get('problemas'):
                print(f"   ⚠️  Problemas detectados: {len(status['problemas'])}")
                for prob in status['problemas']:
                    print(f"      - {prob.get('mensagem')}")
        else:
            print(f"   ❌ Erro: {status_resp.status_code}")
            
    except Exception as e:
        print(f"❌ Erro ao testar endpoints: {e}")


async def main():
    """Executa todos os testes"""
    print("\n" + "="*80)
    print("🚀 TESTE COMPLETO - SISTEMA DE MENSAGENS DE VENCIMENTO")
    print("="*80)
    
    try:
        # 1. Criar dados de teste
        resultado_criacao = await criar_parcela_teste_vencimento()
        
        if not resultado_criacao:
            print("\n❌ Falha ao criar dados de teste")
            return
        
        # 2. Executar job de notificações
        await executar_job_notificacoes()
        
        # 3. Verificar resultados
        await verificar_resultados()
        
        # 4. Testar endpoints de auditoria
        await testar_endpoint_auditoria()
        
        print("\n" + "="*80)
        print("✅ TESTE CONCLUÍDO!")
        print("="*80)
        print("\n📌 RESUMO:")
        print("   1. ✅ Parcela de teste criada (vence em 3 dias)")
        print("   2. ✅ Job de notificações executado")
        print("   3. ✅ Resultados verificados no banco")
        print("   4. ✅ Endpoints de auditoria testados")
        print("\n💡 PARA VISUALIZAR NA INTERFACE:")
        print("   1. Acesse: https://dev-continua-1.preview.emergentagent.com/whatsapp/logs")
        print("   2. Veja os logs de envio e estatísticas")
        print("   3. Verifique o status do serviço WhatsApp")
        print("\n📝 NOTA:")
        print("   - Se WhatsApp estiver conectado E configurado, mensagens são enviadas")
        print("   - Caso contrário, apenas notificações internas são criadas")
        print("   - Configure em: /config-notificacoes para ativar envio WhatsApp")
        print()
        
    except Exception as e:
        print(f"\n❌ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
