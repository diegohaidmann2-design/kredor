"""
Seeder Avançado - Popular banco de dados com dados realistas
Execute: python -m seeds.popular_dados
"""
import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
import uuid
import random

# Adicionar o diretório backend ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient

# Configurações
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

# ==================== DADOS FAKE REALISTAS ====================
NOMES = [
    "João Silva Santos", "Maria Oliveira Costa", "José Carlos Ferreira",
    "Ana Paula Rodrigues", "Pedro Henrique Alves", "Juliana Santos Lima",
    "Carlos Eduardo Souza", "Fernanda Cristina Dias", "Ricardo Almeida Nunes",
    "Patrícia Martins Rocha"
]

ENDERECOS = [
    "Rua das Flores, 123, Centro",
    "Av. Paulista, 456, Bela Vista",
    "Rua Augusta, 789, Consolação",
    "Rua Oscar Freire, 321, Jardins",
    "Av. Brigadeiro Faria Lima, 654, Pinheiros",
    "Rua Consolação, 987, Higienópolis",
    "Av. Rebouças, 147, Pinheiros",
    "Rua Estados Unidos, 258, Jardim América",
    "Av. Ibirapuera, 369, Moema",
    "Rua Vergueiro, 753, Vila Mariana"
]

CIDADES = ["São Paulo", "Campinas", "Santos", "São Bernardo do Campo", "Santo André"]

def gerar_cpf():
    """Gera um CPF fake mas formatado"""
    return f"{random.randint(100, 999)}.{random.randint(100, 999)}.{random.randint(100, 999)}-{random.randint(10, 99)}"

def gerar_telefone():
    """Gera um telefone fake"""
    return f"(11) 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"

def gerar_email(nome):
    """Gera um email baseado no nome"""
    nome_limpo = nome.lower().replace(" ", ".").split(".")[0:2]
    return f"{'.'.join(nome_limpo)}@email.com"


async def criar_clientes(db, usuario_id, quantidade=10):
    """Cria clientes fake"""
    print(f"\n📦 Criando {quantidade} clientes...")
    
    clientes_ids = []
    
    for i in range(quantidade):
        nome = NOMES[i]
        
        # Gerar score e calcular classificação baseada no score
        score_atual = random.randint(300, 900)
        
        # Classificação baseada no score (A, B, C, D, E)
        if score_atual >= 850:
            classificacao = 'A'  # Excelente
        elif score_atual >= 700:
            classificacao = 'B'  # Bom
        elif score_atual >= 500:
            classificacao = 'C'  # Regular
        elif score_atual >= 300:
            classificacao = 'D'  # Risco
        else:
            classificacao = 'E'  # Alto Risco
        
        cliente = {
            'id': str(uuid.uuid4()),
            'usuario_id': usuario_id,
            'nome': nome,
            'cpf_cnpj': gerar_cpf(),
            'email': gerar_email(nome),
            'telefone': gerar_telefone(),
            'endereco': ENDERECOS[i],
            'cidade': random.choice(CIDADES),
            'estado': 'SP',
            'cep': f"{random.randint(10000, 99999)}-{random.randint(100, 999)}",
            'tipo': 'PF',
            'score_atual': score_atual,
            'classificacao': classificacao,
            'status': 'ativo',
            'observacoes': f'Cliente cadastrado via seed - {nome}',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'deleted': False
        }
        
        await db.clientes.insert_one(cliente)
        clientes_ids.append(cliente['id'])
        
        print(f"   ✅ Cliente {i+1}/10: {nome} - Score: {score_atual} ({classificacao})")
    
    return clientes_ids


async def criar_emprestimos_e_parcelas(db, usuario_id, clientes_ids):
    """Cria empréstimos e parcelas para cada cliente"""
    print(f"\n📦 Criando empréstimos e parcelas...")
    
    tipos_juros = ['simples', 'composto']
    total_emprestimos = 0
    total_parcelas = 0
    
    for idx, cliente_id in enumerate(clientes_ids):
        # Criar 2 empréstimos por cliente
        for emp_num in range(2):
            total_emprestimos += 1
            
            # Dados do empréstimo
            valor_principal = random.choice([1000, 2000, 3000, 5000, 10000])
            taxa_juros_mensal = random.choice([2.5, 3.0, 3.5, 4.0, 5.0])
            prazo_meses = random.choice([6, 10, 12, 18, 24])
            metodo_calculo = random.choice(['juros_simples', 'juros_compostos', 'tabela_price', 'sac'])
            
            # Data de início (alguns empréstimos mais antigos)
            dias_atras = random.randint(60, 180)
            data_inicio = datetime.now(timezone.utc) - timedelta(days=dias_atras)
            
            # Calcular valor total com juros (simplificado)
            if metodo_calculo == 'juros_simples':
                montante = valor_principal * (1 + (taxa_juros_mensal/100) * prazo_meses)
            else:
                montante = valor_principal * ((1 + taxa_juros_mensal/100) ** prazo_meses)
            
            valor_total_juros = montante - valor_principal
            valor_parcela = montante / prazo_meses
            
            emprestimo_id = str(uuid.uuid4())
            
            emprestimo = {
                'id': emprestimo_id,
                'usuario_id': usuario_id,
                'cliente_id': cliente_id,
                'valor_principal': valor_principal,
                'taxa_juros_mensal': taxa_juros_mensal,
                'prazo_meses': prazo_meses,
                'metodo_calculo': metodo_calculo,
                'periodo_carencia_meses': 0,
                'taxa_multa_atraso': 2.0,
                'taxa_juros_mora_diario': 0.033,
                'data_inicio': data_inicio.isoformat(),
                'valor_total_com_juros': round(montante, 2),
                'valor_total_juros': round(valor_total_juros, 2),
                'status': 'ativo',
                'observacoes': f'Empréstimo #{emp_num+1} - {metodo_calculo}',
                'created_at': data_inicio.isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'deleted': False
            }
            
            await db.emprestimos.insert_one(emprestimo)
            
            # Criar parcelas
            parcelas_criadas = await criar_parcelas(
                db, usuario_id, emprestimo_id, cliente_id,
                prazo_meses, valor_parcela, data_inicio
            )
            
            total_parcelas += parcelas_criadas
            
            # Criar alguns pagamentos para parcelas pagas
            await criar_pagamentos(db, usuario_id, emprestimo_id, cliente_id)
        
        print(f"   ✅ Cliente {idx+1}/10: 2 empréstimos criados")
    
    print(f"\n   📊 Total: {total_emprestimos} empréstimos, {total_parcelas} parcelas")
    return total_emprestimos, total_parcelas


async def criar_parcelas(db, usuario_id, emprestimo_id, cliente_id, 
                         numero_parcelas, valor_parcela, data_inicio):
    """Cria parcelas com diferentes status"""
    
    parcelas_pagas = random.randint(0, min(3, numero_parcelas))  # 0 a 3 parcelas pagas
    parcelas_vencidas = random.randint(1, min(3, numero_parcelas - parcelas_pagas))  # 1 a 3 vencidas
    
    for num in range(1, numero_parcelas + 1):
        # Calcular data de vencimento (30 dias entre parcelas)
        data_vencimento = data_inicio + timedelta(days=30 * num)
        
        # Determinar status da parcela
        if num <= parcelas_pagas:
            status = 'paga'
            data_pagamento = data_vencimento - timedelta(days=random.randint(0, 5))
            valor_pago = valor_parcela
        elif num <= (parcelas_pagas + parcelas_vencidas) and data_vencimento < datetime.now(timezone.utc):
            status = 'atrasado'  # Mudado de 'vencida' para 'atrasado'
            data_pagamento = None
            valor_pago = 0.0
            # Adicionar juros de mora para parcelas atrasadas
            dias_atraso = (datetime.now(timezone.utc) - data_vencimento).days
            valor_parcela_vencida = valor_parcela * (1 + (0.02 * dias_atraso))  # 2% ao dia
        else:
            status = 'pendente'
            data_pagamento = None
            valor_pago = 0.0
        
        # Calcular valor_total (valor_parcela + juros de mora se atrasado)
        if status == 'atrasado':
            dias_atraso = (datetime.now(timezone.utc) - data_vencimento).days
            valor_total = round(valor_parcela * (1 + (0.02 * dias_atraso)), 2)
        else:
            valor_total = round(valor_parcela, 2)
        
        parcela = {
            'id': str(uuid.uuid4()),
            'usuario_id': usuario_id,
            'emprestimo_id': emprestimo_id,
            'cliente_id': cliente_id,
            'numero_parcela': num,
            'valor_parcela': round(valor_parcela, 2),
            'valor_total': valor_total,  # Valor com juros de mora (se aplicável)
            'valor_pago': round(valor_pago, 2) if status == 'paga' else 0.0,
            'data_vencimento': data_vencimento.isoformat(),
            'data_pagamento': data_pagamento.isoformat() if data_pagamento else None,
            'status': status,
            'dias_atraso': (datetime.now(timezone.utc) - data_vencimento).days if status == 'atrasado' else 0,
            'created_at': data_inicio.isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'deleted': False
        }
        
        await db.parcelas.insert_one(parcela)
    
    return numero_parcelas


async def criar_pagamentos(db, usuario_id, emprestimo_id, cliente_id):
    """Cria registros de pagamentos para parcelas pagas"""
    
    parcelas_pagas = await db.parcelas.find({
        'emprestimo_id': emprestimo_id,
        'status': 'paga'
    }).to_list(100)
    
    for parcela in parcelas_pagas:
        pagamento = {
            'id': str(uuid.uuid4()),
            'usuario_id': usuario_id,
            'emprestimo_id': emprestimo_id,
            'cliente_id': cliente_id,
            'parcela_id': parcela['id'],
            'valor_pago': parcela['valor_pago'],
            'data_pagamento': parcela['data_pagamento'],
            'metodo_pagamento': random.choice(['pix', 'dinheiro', 'transferencia', 'cartao']),
            'forma_pagamento': random.choice(['pix', 'dinheiro', 'transferencia', 'cartao']),
            'comprovante': None,
            'observacoes': 'Pagamento registrado via seed',
            'created_at': parcela['data_pagamento'],
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'deleted': False
        }
        
        await db.pagamentos.insert_one(pagamento)


async def criar_notificacoes(db, usuario_id):
    """Cria notificações de vencimentos"""
    print(f"\n📦 Criando notificações...")
    
    # Buscar parcelas vencidas
    parcelas_vencidas = await db.parcelas.find({
        'usuario_id': usuario_id,
        'status': 'vencida'
    }).to_list(100)
    
    notificacoes_criadas = 0
    
    for parcela in parcelas_vencidas[:10]:  # Criar até 10 notificações
        # Buscar nome do cliente
        cliente = await db.clientes.find_one({'id': parcela['cliente_id']})
        
        if cliente:
            notificacao = {
                'id': str(uuid.uuid4()),
                'usuario_id': usuario_id,
                'tipo': 'vencimento',
                'titulo': f"Parcela vencida - {cliente['nome']}",
                'mensagem': f"A parcela {parcela['numero_parcela']} está vencida há {parcela['dias_atraso']} dias. Valor: R$ {parcela['valor_parcela']:.2f}",
                'lida': random.choice([True, False]),
                'link': f"/emprestimos/{parcela['emprestimo_id']}",
                'created_at': (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 10))).isoformat()
            }
            
            await db.notificacoes.insert_one(notificacao)
            notificacoes_criadas += 1
    
    print(f"   ✅ {notificacoes_criadas} notificações criadas")


async def gerar_estatisticas(db, usuario_id):
    """Gera estatísticas dos dados criados"""
    print(f"\n" + "="*60)
    print("📊 ESTATÍSTICAS DOS DADOS CRIADOS")
    print("="*60)
    
    total_clientes = await db.clientes.count_documents({'usuario_id': usuario_id, 'deleted': False})
    total_emprestimos = await db.emprestimos.count_documents({'usuario_id': usuario_id, 'deleted': False})
    total_parcelas = await db.parcelas.count_documents({'usuario_id': usuario_id, 'deleted': False})
    
    parcelas_pagas = await db.parcelas.count_documents({'usuario_id': usuario_id, 'status': 'paga'})
    parcelas_pendentes = await db.parcelas.count_documents({'usuario_id': usuario_id, 'status': 'pendente'})
    parcelas_vencidas = await db.parcelas.count_documents({'usuario_id': usuario_id, 'status': 'vencida'})
    
    total_pagamentos = await db.pagamentos.count_documents({'usuario_id': usuario_id, 'deleted': False})
    
    # Calcular valores
    pipeline_valores = [
        {'$match': {'usuario_id': usuario_id, 'deleted': False}},
        {'$group': {
            '_id': None,
            'total_principal': {'$sum': '$valor_principal'},
            'total_montante': {'$sum': '$montante'}
        }}
    ]
    
    resultado = await db.emprestimos.aggregate(pipeline_valores).to_list(1)
    
    if resultado:
        total_principal = resultado[0]['total_principal']
        total_montante = resultado[0]['total_montante']
        total_juros = total_montante - total_principal
    else:
        total_principal = 0
        total_montante = 0
        total_juros = 0
    
    print(f"\n👥 Clientes: {total_clientes}")
    print(f"💰 Empréstimos: {total_emprestimos}")
    print(f"📋 Parcelas: {total_parcelas}")
    print(f"   ✅ Pagas: {parcelas_pagas}")
    print(f"   ⏳ Pendentes: {parcelas_pendentes}")
    print(f"   ❌ Vencidas: {parcelas_vencidas}")
    print(f"💵 Pagamentos Registrados: {total_pagamentos}")
    print(f"\n💸 Valores:")
    print(f"   Principal Emprestado: R$ {total_principal:,.2f}")
    print(f"   Total com Juros: R$ {total_montante:,.2f}")
    print(f"   Juros Totais: R$ {total_juros:,.2f}")


async def run_popular():
    """Executa o script de população"""
    print("=" * 60)
    print("🌱 Gestor Cred - Popular Banco de Dados")
    print("=" * 60)
    print(f"\n📌 Conectando ao MongoDB: {MONGO_URL}")
    print(f"📌 Banco de dados: {DB_NAME}")
    
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Testar conexão
        await client.admin.command('ping')
        print("✅ Conexão com MongoDB estabelecida!\n")
        
        # Buscar o primeiro usuário admin
        usuario = await db.usuarios.find_one({'perfil': 'admin'})
        
        if not usuario:
            print("❌ Erro: Nenhum usuário admin encontrado!")
            print("   Execute primeiro: python -m seeds.seeder")
            return
        
        usuario_id = usuario['id']
        print(f"👤 Usando usuário: {usuario['nome']} ({usuario['email']})")
        print(f"🆔 ID: {usuario_id}\n")
        
        # Confirmar antes de prosseguir
        print("⚠️  Este script irá criar:")
        print("   • 10 clientes")
        print("   • 20 empréstimos (2 por cliente)")
        print("   • ~240 parcelas (média de 12 por empréstimo)")
        print("   • Pagamentos para parcelas pagas")
        print("   • Notificações de vencimentos\n")
        
        confirmar = input("Digite 'SIM' para continuar: ")
        if confirmar.upper() != 'SIM':
            print("❌ Operação cancelada.")
            return
        
        print("\n🚀 Iniciando população do banco de dados...\n")
        
        # Criar dados
        clientes_ids = await criar_clientes(db, usuario_id, quantidade=10)
        await criar_emprestimos_e_parcelas(db, usuario_id, clientes_ids)
        await criar_notificacoes(db, usuario_id)
        
        # Gerar estatísticas
        await gerar_estatisticas(db, usuario_id)
        
        print("\n" + "=" * 60)
        print("🎉 População do banco concluída com sucesso!")
        print("=" * 60)
        print("\n✅ Agora você pode:")
        print("   • Fazer login no sistema")
        print("   • Visualizar clientes e empréstimos")
        print("   • Testar todas as funcionalidades")
        print("   • Ver parcelas vencidas e notificações\n")
        
        client.close()
        
    except Exception as e:
        print(f"\n❌ Erro ao popular banco: {e}")
        import traceback
        traceback.print_exc()
        raise e


if __name__ == "__main__":
    asyncio.run(run_popular())
