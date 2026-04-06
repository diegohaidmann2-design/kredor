"""
Script para popular o banco de dados com dados de teste realistas
Cria clientes, empréstimos, parcelas e pagamentos
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import uuid
import random

# Dados realistas para clientes
NOMES = [
    "João Silva", "Maria Santos", "Pedro Oliveira", "Ana Costa",
    "Carlos Souza", "Juliana Lima", "Roberto Alves", "Fernanda Rocha",
    "Paulo Mendes", "Camila Ferreira", "Lucas Barbosa", "Beatriz Martins",
    "Rafael Gomes", "Larissa Ribeiro", "Diego Cardoso", "Patrícia Araújo",
    "Felipe Nunes", "Mariana Dias", "Thiago Pereira", "Amanda Carvalho",
    "Bruno Rodrigues", "Gabriela Castro", "Matheus Correia", "Isabela Freitas"
]

TELEFONES_BASE = [
    "11987654321", "11976543210", "11965432109", "11954321098",
    "21987654321", "21976543210", "31987654321", "31976543210",
    "41987654321", "41976543210", "51987654321", "51976543210",
    "61987654321", "71987654321", "81987654321", "85987654321"
]

ENDERECOS = [
    "Rua das Flores, 123 - Centro",
    "Av. Paulista, 456 - Bela Vista",
    "Rua Augusta, 789 - Consolação",
    "Av. Brasil, 321 - Jardim América",
    "Rua XV de Novembro, 654 - Centro",
    "Av. Atlântica, 987 - Copacabana",
    "Rua da Praia, 147 - Centro",
    "Av. Getúlio Vargas, 258 - Centro",
    "Rua Direita, 369 - Centro",
    "Av. Independência, 741 - Cidade Baixa"
]

async def criar_dados_teste():
    """Cria dados de teste no banco"""
    
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['test_database']
    
    print("=" * 60)
    print("🌱 POPULANDO BANCO COM DADOS DE TESTE")
    print("=" * 60)
    
    # Pegar usuário admin
    usuario = await db.usuarios.find_one({'email': 'admin@gestorcerd.com'})
    if not usuario:
        print("❌ Usuário admin não encontrado")
        return
    
    usuario_id = usuario['id']
    print(f"✅ Usuário admin encontrado: {usuario['email']}")
    print()
    
    clientes_criados = []
    emprestimos_criados = []
    parcelas_criadas = []
    pagamentos_criados = []
    
    # Criar 20 clientes
    print("👥 Criando clientes...")
    for i in range(20):
        cliente_id = str(uuid.uuid4())
        nome = NOMES[i] if i < len(NOMES) else f"Cliente {i+1}"
        
        # Gerar CPF fictício
        cpf = f"{random.randint(100, 999)}.{random.randint(100, 999)}.{random.randint(100, 999)}-{random.randint(10, 99)}"
        
        # Telefone
        telefone = TELEFONES_BASE[i % len(TELEFONES_BASE)]
        telefone = telefone[:-4] + str(random.randint(1000, 9999))
        
        cliente = {
            'id': cliente_id,
            'usuario_id': usuario_id,
            'nome': nome,
            'cpf': cpf,
            'telefone': telefone,
            'email': f"cliente{i+1}@teste.com",
            'endereco': random.choice(ENDERECOS),
            'ativo': True,
            'created_at': datetime.utcnow() - timedelta(days=random.randint(30, 365)),
            'deleted_at': None
        }
        
        await db.clientes.insert_one(cliente)
        clientes_criados.append(cliente)
        print(f"  ✓ Cliente {i+1}: {nome}")
    
    print(f"\n✅ {len(clientes_criados)} clientes criados!")
    print()
    
    # Criar empréstimos para os clientes
    print("💰 Criando empréstimos...")
    
    for i, cliente in enumerate(clientes_criados):
        # Cada cliente terá de 1 a 3 empréstimos
        num_emprestimos = random.randint(1, 3)
        
        for j in range(num_emprestimos):
            emprestimo_id = str(uuid.uuid4())
            
            # Valores variados
            valores_possiveis = [500, 1000, 1500, 2000, 3000, 5000, 7500, 10000]
            valor_emprestimo = random.choice(valores_possiveis)
            
            # Taxa de juros entre 3% e 10%
            taxa_juros = random.choice([3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0])
            
            # Tipo de juros
            tipo_juros = random.choice(['simples', 'composto'])
            
            # Número de parcelas
            numero_parcelas = random.choice([3, 6, 10, 12, 18, 24])
            
            # Data do empréstimo (entre 6 meses atrás e hoje)
            data_emprestimo = datetime.utcnow() - timedelta(days=random.randint(0, 180))
            
            # Data do primeiro vencimento
            data_primeiro_vencimento = data_emprestimo + timedelta(days=30)
            
            emprestimo = {
                'id': emprestimo_id,
                'usuario_id': usuario_id,
                'cliente_id': cliente['id'],
                'cliente_nome': cliente['nome'],
                'valor_emprestimo': valor_emprestimo,
                'taxa_juros': taxa_juros,
                'tipo_juros': tipo_juros,
                'numero_parcelas': numero_parcelas,
                'data_emprestimo': data_emprestimo,
                'data_primeiro_vencimento': data_primeiro_vencimento,
                'prazo_dias': 30,
                'tipo': 'parcelado',
                'status': 'ativo',
                'ativo': True,
                'created_at': data_emprestimo,
                'deleted_at': None
            }
            
            await db.emprestimos.insert_one(emprestimo)
            emprestimos_criados.append(emprestimo)
            print(f"  ✓ Empréstimo {len(emprestimos_criados)}: {cliente['nome']} - R$ {valor_emprestimo:,.2f} em {numero_parcelas}x")
            
            # Criar parcelas para este empréstimo
            # Calcular valor da parcela
            if tipo_juros == 'simples':
                juros_total = valor_emprestimo * (taxa_juros / 100) * numero_parcelas
                valor_total = valor_emprestimo + juros_total
            else:  # composto
                valor_total = valor_emprestimo * ((1 + taxa_juros / 100) ** numero_parcelas)
            
            valor_parcela = valor_total / numero_parcelas
            
            for k in range(numero_parcelas):
                parcela_id = str(uuid.uuid4())
                
                # Data de vencimento
                data_vencimento = data_primeiro_vencimento + timedelta(days=30 * k)
                
                # Calcular status da parcela
                dias_desde_vencimento = (datetime.utcnow() - data_vencimento).days
                
                if dias_desde_vencimento > 0:
                    # Parcela vencida - 70% chance de estar paga, 30% atrasada
                    if random.random() < 0.7:
                        status = 'pago'
                        pago = True
                        valor_pago = valor_parcela
                    else:
                        status = 'atrasado'
                        pago = False
                        valor_pago = 0.0
                elif dias_desde_vencimento > -5:
                    # Parcela próxima do vencimento - algumas podem ter pagamento parcial
                    if random.random() < 0.3:
                        status = 'parcial'
                        pago = False
                        valor_pago = valor_parcela * random.uniform(0.3, 0.7)
                    else:
                        status = 'pendente'
                        pago = False
                        valor_pago = 0.0
                else:
                    # Parcela futura
                    status = 'pendente'
                    pago = False
                    valor_pago = 0.0
                
                # Calcular multa e juros de mora para parcelas atrasadas
                valor_multa = 0.0
                valor_juros_mora = 0.0
                
                if status == 'atrasado' and dias_desde_vencimento > 0:
                    # Multa de 2%
                    valor_multa = valor_parcela * 0.02
                    # Juros de mora de 1% ao mês (proporcional aos dias)
                    valor_juros_mora = valor_parcela * 0.01 * (dias_desde_vencimento / 30)
                
                parcela = {
                    'id': parcela_id,
                    'usuario_id': usuario_id,
                    'emprestimo_id': emprestimo_id,
                    'cliente_id': cliente['id'],
                    'cliente_nome': cliente['nome'],
                    'cliente_telefone': cliente['telefone'],
                    'numero_parcela': k + 1,
                    'total_parcelas': numero_parcelas,
                    'valor_parcela': round(valor_parcela, 2),
                    'valor_total': round(valor_parcela, 2),
                    'valor_pago': round(valor_pago, 2),
                    'valor_multa': round(valor_multa, 2),
                    'valor_juros_mora': round(valor_juros_mora, 2),
                    'data_vencimento': data_vencimento,
                    'status': status,
                    'dias_atraso': max(0, dias_desde_vencimento),
                    'valor_emprestimo': valor_emprestimo,
                    'taxa_juros': taxa_juros,
                    'pago': pago,
                    'ativo': True,
                    'created_at': data_emprestimo,
                    'deleted_at': None
                }
                
                await db.parcelas.insert_one(parcela)
                parcelas_criadas.append(parcela)
                
                # Se a parcela está paga, criar registro de pagamento
                if status == 'pago':
                    pagamento_id = str(uuid.uuid4())
                    
                    # Data do pagamento (entre vencimento e hoje)
                    data_pagamento = data_vencimento + timedelta(days=random.randint(0, 5))
                    
                    metodos = ['pix', 'transferencia', 'dinheiro', 'cartao']
                    
                    pagamento = {
                        'id': pagamento_id,
                        'usuario_id': usuario_id,
                        'parcela_id': parcela_id,
                        'emprestimo_id': emprestimo_id,
                        'cliente_id': cliente['id'],
                        'cliente_nome': cliente['nome'],
                        'cliente_telefone': cliente['telefone'],
                        'valor_pago': round(valor_parcela, 2),
                        'metodo_pagamento': random.choice(metodos),
                        'data_pagamento': data_pagamento,
                        'observacoes': None,
                        'numero_parcela': k + 1,
                        'total_parcelas': numero_parcelas,
                        'valor_emprestimo': valor_emprestimo,
                        'created_at': data_pagamento,
                        'deleted_at': None
                    }
                    
                    await db.pagamentos.insert_one(pagamento)
                    pagamentos_criados.append(pagamento)
    
    print(f"\n✅ {len(emprestimos_criados)} empréstimos criados!")
    print(f"✅ {len(parcelas_criadas)} parcelas criadas!")
    print(f"✅ {len(pagamentos_criados)} pagamentos registrados!")
    print()
    
    # Estatísticas
    print("=" * 60)
    print("📊 ESTATÍSTICAS DOS DADOS CRIADOS")
    print("=" * 60)
    
    parcelas_pagas = len([p for p in parcelas_criadas if p['status'] == 'pago'])
    parcelas_pendentes = len([p for p in parcelas_criadas if p['status'] == 'pendente'])
    parcelas_atrasadas = len([p for p in parcelas_criadas if p['status'] == 'atrasado'])
    parcelas_parciais = len([p for p in parcelas_criadas if p['status'] == 'parcial'])
    
    print(f"👥 Clientes: {len(clientes_criados)}")
    print(f"💰 Empréstimos: {len(emprestimos_criados)}")
    print(f"📋 Parcelas: {len(parcelas_criadas)}")
    print(f"   ✅ Pagas: {parcelas_pagas}")
    print(f"   📅 Pendentes: {parcelas_pendentes}")
    print(f"   ⚠️ Atrasadas: {parcelas_atrasadas}")
    print(f"   ⏳ Parciais: {parcelas_parciais}")
    print(f"💳 Pagamentos: {len(pagamentos_criados)}")
    
    valor_total_emprestado = sum([e['valor_emprestimo'] for e in emprestimos_criados])
    valor_total_pago = sum([p['valor_pago'] for p in pagamentos_criados])
    valor_total_pendente = sum([p['valor_total'] - p['valor_pago'] for p in parcelas_criadas if not p['pago']])
    
    print()
    print(f"💵 Valor total emprestado: R$ {valor_total_emprestado:,.2f}")
    print(f"✅ Valor total recebido: R$ {valor_total_pago:,.2f}")
    print(f"📊 Valor total pendente: R$ {valor_total_pendente:,.2f}")
    
    print()
    print("=" * 60)
    print("🎉 DADOS CRIADOS COM SUCESSO!")
    print("=" * 60)
    
    client.close()

if __name__ == "__main__":
    asyncio.run(criar_dados_teste())
