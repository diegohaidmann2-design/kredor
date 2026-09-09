"""
Script de Teste - Cálculo de Juros de Mora
Demonstra o funcionamento do cálculo automático de juros e multas
"""
import asyncio
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os
import sys

# Adicionar path do backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.juros_mora_service import (
    calcular_juros_mora_parcela,
    atualizar_juros_mora_parcela,
    atualizar_todas_parcelas_atrasadas,
    obter_resumo_juros_mora
)


async def criar_dados_teste():
    """Cria empréstimo e parcela de teste"""
    MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    DB_NAME = os.environ.get('DB_NAME', 'test_database')
    
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("\n" + "="*60)
    print("🧪 TESTE DE JUROS DE MORA - Criando dados de teste")
    print("="*60)
    
    # Buscar um usuário admin
    usuario = await db.usuarios.find_one({"perfil": "admin"})
    if not usuario:
        print("❌ Nenhum usuário encontrado! Execute o seeder primeiro.")
        client.close()
        return None, None, None
    
    usuario_id = usuario["id"]
    print(f"\n✅ Usuário: {usuario['email']}")
    
    # Buscar ou criar um cliente de teste
    cliente = await db.clientes.find_one({"usuario_id": usuario_id})
    if not cliente:
        import uuid
        cliente_id = str(uuid.uuid4())
        cliente_doc = {
            "id": cliente_id,
            "usuario_id": usuario_id,
            "nome": "Cliente Teste Juros",
            "cpf_cnpj": "12345678900",
            "telefone": "11999999999",
            "status": "ativo",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.clientes.insert_one(cliente_doc)
        cliente = cliente_doc
        print(f"✅ Cliente criado: {cliente['nome']}")
    else:
        print(f"✅ Cliente encontrado: {cliente['nome']}")
    
    # Criar empréstimo de teste
    import uuid
    emprestimo_id = str(uuid.uuid4())
    emprestimo = {
        "id": emprestimo_id,
        "usuario_id": usuario_id,
        "cliente_id": cliente["id"],
        "valor_principal_centavos": 1000.00,
        "taxa_juros_mensal": 5.0,
        "prazo_meses": 12,
        "metodo_calculo": "juros_simples",
        "periodo_carencia_meses": 0,
        "taxa_multa_atraso": 2.0,  # 2% de multa
        "taxa_juros_mora_diario": 0.033,  # 0.033% ao dia (1% ao mês)
        "data_inicio": datetime.now(timezone.utc).isoformat(),
        "valor_total_com_juros_centavos": 1600.00,
        "valor_total_juros_centavos": 600.00,
        "status": "ativo",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.emprestimos.insert_one(emprestimo)
    print(f"✅ Empréstimo criado: R$ {emprestimo['valor_principal_centavos']:,.2f}")
    print(f"   Taxa multa: {emprestimo['taxa_multa_atraso']}%")
    print(f"   Taxa mora diária: {emprestimo['taxa_juros_mora_diario']}%")
    
    # Criar parcela VENCIDA (10 dias atrás)
    parcela_id = str(uuid.uuid4())
    data_vencimento = datetime.now(timezone.utc) - timedelta(days=10)
    parcela = {
        "id": parcela_id,
        "usuario_id": usuario_id,
        "emprestimo_id": emprestimo_id,
        "numero_parcela": 1,
        "data_vencimento": data_vencimento.isoformat(),
        "valor_principal_centavos": 83.33,
        "valor_juros_centavos": 50.00,
        "valor_total_centavos": 133.33,
        "valor_pago_centavos": 0.0,
        "valor_multa_centavos": 0.0,
        "valor_juros_mora_centavos": 0.0,
        "dias_atraso": 0,
        "saldo_devedor_centavos": 1000.00,
        "status": "pendente",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.parcelas.insert_one(parcela)
    print(f"✅ Parcela criada: R$ {parcela['valor_total_centavos']:,.2f}")
    print(f"   Vencimento: {data_vencimento.strftime('%d/%m/%Y')} (10 dias atrás)")
    
    client.close()
    return usuario_id, emprestimo_id, parcela_id


async def testar_calculo_juros():
    """Testa o cálculo de juros de mora"""
    print("\n" + "="*60)
    print("🧮 TESTE 1: Cálculo de Juros de Mora")
    print("="*60)
    
    # Criar dados de teste
    usuario_id, emprestimo_id, parcela_id = await criar_dados_teste()
    
    if not parcela_id:
        return
    
    # Calcular juros de mora
    print("\n📊 Calculando juros de mora...")
    valores = await calcular_juros_mora_parcela(parcela_id, usuario_id)
    
    print(f"\n✅ Resultado do cálculo:")
    print(f"   Dias de atraso: {valores['dias_atraso']} dias")
    print(f"   Valor da multa (2%): R$ {valores['valor_multa_centavos']:,.2f}")
    print(f"   Juros de mora (0.033% x {valores['dias_atraso']} dias): R$ {valores['valor_juros_mora_centavos']:,.2f}")
    print(f"   Valor total devido: R$ {valores['valor_total_devido']:,.2f}")
    
    # Atualizar na parcela
    print("\n📝 Atualizando valores na parcela...")
    atualizado = await atualizar_juros_mora_parcela(parcela_id, usuario_id)
    
    if atualizado:
        print("✅ Parcela atualizada com sucesso!")
    else:
        print("⚠️  Parcela não foi atualizada")
    
    # Verificar no banco
    MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    DB_NAME = os.environ.get('DB_NAME', 'test_database')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    parcela_atualizada = await db.parcelas.find_one({"id": parcela_id})
    print(f"\n🔍 Verificando no banco de dados:")
    print(f"   Status: {parcela_atualizada.get('status')}")
    print(f"   Dias atraso: {parcela_atualizada.get('dias_atraso')}")
    print(f"   Valor multa: R$ {parcela_atualizada.get('valor_multa_centavos', 0):,.2f}")
    print(f"   Valor juros mora: R$ {parcela_atualizada.get('valor_juros_mora_centavos', 0):,.2f}")
    
    client.close()


async def testar_atualizacao_massa():
    """Testa atualização em massa de parcelas"""
    print("\n" + "="*60)
    print("🔄 TESTE 2: Atualização em Massa")
    print("="*60)
    
    result = await atualizar_todas_parcelas_atrasadas()
    
    print(f"\n✅ Resultado:")
    print(f"   Parcelas processadas: {result['total_processadas']}")
    print(f"   Parcelas atualizadas: {result['total_atualizadas']}")


async def testar_resumo():
    """Testa resumo de juros de mora"""
    print("\n" + "="*60)
    print("📈 TESTE 3: Resumo de Juros de Mora")
    print("="*60)
    
    # Buscar um usuário
    MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    DB_NAME = os.environ.get('DB_NAME', 'test_database')
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    usuario = await db.usuarios.find_one({"perfil": "admin"})
    if not usuario:
        print("❌ Nenhum usuário encontrado!")
        client.close()
        return
    
    resumo = await obter_resumo_juros_mora(usuario["id"])
    
    print(f"\n✅ Resumo para {usuario['email']}:")
    print(f"   Total de multas: R$ {resumo['total_multas']:,.2f}")
    print(f"   Total de juros de mora: R$ {resumo['total_juros_mora']:,.2f}")
    print(f"   Total geral: R$ {resumo['total_geral']:,.2f}")
    
    client.close()


async def main():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("🚀 SISTEMA DE CÁLCULO DE JUROS DE MORA")
    print("="*60)
    
    try:
        await testar_calculo_juros()
        await testar_atualizacao_massa()
        await testar_resumo()
        
        print("\n" + "="*60)
        print("✅ Todos os testes concluídos com sucesso!")
        print("="*60)
        print("\n💡 Como funciona:")
        print("   1. Quando uma parcela vence, o sistema detecta automaticamente")
        print("   2. Calcula multa de 2% sobre o valor devido")
        print("   3. Calcula juros de mora de 0.033% ao dia")
        print("   4. Atualiza os valores na parcela")
        print("   5. Job automático executa a cada 6 horas")
        print("\n📌 Próximos passos:")
        print("   - Ao listar parcelas pendentes, valores são recalculados")
        print("   - Ao registrar pagamento, considera multa + juros de mora")
        print("   - Scheduler atualiza automaticamente todas as parcelas")
        print()
        
    except Exception as e:
        print(f"\n❌ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
