"""
Script para popular o banco de dados com dados de teste realistas
Cria clientes, empréstimos, parcelas e pagamentos com nomes de campo corretos.
"""
import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta, timezone
import uuid
import random
from dotenv import load_dotenv
load_dotenv()

NOMES = [
    "João Silva", "Maria Santos", "Pedro Oliveira", "Ana Costa",
    "Carlos Souza", "Juliana Lima", "Roberto Alves", "Fernanda Rocha",
    "Paulo Mendes", "Camila Ferreira", "Lucas Barbosa", "Beatriz Martins",
    "Rafael Gomes", "Larissa Ribeiro", "Diego Cardoso", "Patrícia Araújo",
    "Felipe Nunes", "Mariana Dias", "Thiago Pereira", "Amanda Carvalho",
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
]


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


async def criar_dados_teste():
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    db = client[os.environ.get('DB_NAME', 'test_database')]

    print("=" * 60)
    print("🌱 POPULANDO BANCO COM DADOS DE TESTE")
    print("=" * 60)

    admin_email = os.environ.get('SEED_ADMIN_EMAIL', 'diego.haidmann@gmail.com')
    usuario = await db.usuarios.find_one({'email': admin_email})
    if not usuario:
        print(f"❌ Usuário {admin_email} não encontrado")
        return
    usuario_id = usuario['id']
    print(f"✅ Usuário admin encontrado: {usuario['email']}")

    # Limpa dados antigos deste usuário
    print("\n🧹 Limpando dados de teste anteriores...")
    for col in ['clientes', 'emprestimos', 'parcelas', 'pagamentos']:
        res = await db[col].delete_many({'usuario_id': usuario_id})
        print(f"  - {col}: {res.deleted_count} removidos")

    agora = datetime.now(timezone.utc)

    # ==================== CLIENTES ====================
    print("\n👥 Criando clientes...")
    clientes_criados = []
    for i in range(20):
        nome = NOMES[i]
        cpf = f"{random.randint(100, 999)}.{random.randint(100, 999)}.{random.randint(100, 999)}-{random.randint(10, 99)}"
        telefone = TELEFONES_BASE[i % len(TELEFONES_BASE)]
        cliente = {
            'id': str(uuid.uuid4()),
            'usuario_id': usuario_id,
            'nome': nome,
            'cpf_cnpj': cpf,
            'telefone': telefone,
            'email': f"cliente{i+1}@teste.com",
            'endereco': random.choice(ENDERECOS),
            'status': 'ativo',
            'score_atual': random.randint(300, 900),
            'classificacao': random.choice(['A', 'B', 'C']),
            'created_at': iso(agora - timedelta(days=random.randint(30, 365))),
            'deleted': False,
        }
        await db.clientes.insert_one(cliente)
        clientes_criados.append(cliente)
    print(f"  ✓ {len(clientes_criados)} clientes")

    # ==================== EMPRÉSTIMOS + PARCELAS + PAGAMENTOS ====================
    print("\n💰 Criando empréstimos, parcelas e pagamentos...")
    emprestimos_criados = []
    parcelas_criadas = []
    pagamentos_criados = []

    for i, cliente in enumerate(clientes_criados):
        num_emprestimos = random.randint(1, 3)
        for j in range(num_emprestimos):
            valor_principal_centavos = random.choice([500, 1000, 1500, 2000, 3000, 5000, 7500, 10000])
            taxa_juros_mensal = random.choice([3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0])
            metodo_calculo = random.choice(['simples', 'composto', 'price'])
            prazo_meses = random.choice([3, 6, 10, 12, 18, 24])
            data_inicio = agora - timedelta(days=random.randint(0, 180))
            data_primeiro_venc = data_inicio + timedelta(days=30)

            emprestimo_id = str(uuid.uuid4())

            # Valor total com juros
            if metodo_calculo == 'simples':
                juros_total = valor_principal_centavos * (taxa_juros_mensal / 100) * prazo_meses
                valor_total_com_juros_centavos = valor_principal_centavos + juros_total
            else:
                valor_total_com_juros_centavos = valor_principal_centavos * ((1 + taxa_juros_mensal / 100) ** prazo_meses)

            valor_parcela = valor_total_com_juros_centavos / prazo_meses
            juros_por_parcela = (valor_total_com_juros_centavos - valor_principal_centavos) / prazo_meses
            principal_por_parcela = valor_principal_centavos / prazo_meses

            emprestimo = {
                'id': emprestimo_id,
                'usuario_id': usuario_id,
                'cliente_id': cliente['id'],
                'cliente_nome': cliente['nome'],
                'cliente_cpf': cliente['cpf_cnpj'],
                'cliente_telefone': cliente['telefone'],
                'valor_principal_centavos': valor_principal_centavos,
                'taxa_juros_mensal': taxa_juros_mensal,
                'metodo_calculo': metodo_calculo,
                'prazo_meses': prazo_meses,
                'data_inicio': iso(data_inicio),
                'data_primeiro_vencimento': iso(data_primeiro_venc),
                'dia_vencimento': data_primeiro_venc.day,
                'periodicidade': 'mensal',
                'sem_prazo': False,
                'valor_total_com_juros_centavos': round(valor_total_com_juros_centavos, 2),
                'valor_total_juros_centavos': round(valor_total_com_juros_centavos - valor_principal_centavos, 2),
                'status': 'ativo',
                'created_at': iso(data_inicio),
                'deleted': False,
            }
            await db.emprestimos.insert_one(emprestimo)
            emprestimos_criados.append(emprestimo)

            # Criar parcelas
            qtd_pagas_emp = 0
            qtd_atrasadas_emp = 0
            for k in range(prazo_meses):
                data_vencimento = data_primeiro_venc + timedelta(days=30 * k)
                dias_atraso_calc = (agora - data_vencimento).days

                if dias_atraso_calc > 0:
                    # Vencida no passado
                    if random.random() < 0.65:
                        status = 'pago'
                        valor_pago_centavos = round(valor_parcela, 2)
                        qtd_pagas_emp += 1
                    else:
                        status = 'atrasado'
                        valor_pago_centavos = 0.0
                        qtd_atrasadas_emp += 1
                elif dias_atraso_calc > -7:
                    # Próxima do vencimento
                    if random.random() < 0.25:
                        status = 'parcial'
                        valor_pago_centavos = round(valor_parcela * random.uniform(0.3, 0.7), 2)
                    else:
                        status = 'pendente'
                        valor_pago_centavos = 0.0
                else:
                    status = 'pendente'
                    valor_pago_centavos = 0.0

                # Multa e juros mora (parcelas atrasadas)
                valor_multa_centavos = 0.0
                valor_juros_mora_centavos = 0.0
                if status == 'atrasado' and dias_atraso_calc > 0:
                    valor_multa_centavos = round(valor_parcela * 0.02, 2)  # 2% multa
                    valor_juros_mora_centavos = round(valor_parcela * 0.01 * (dias_atraso_calc / 30), 2)  # 1%/mes

                parcela_id = str(uuid.uuid4())
                parcela = {
                    'id': parcela_id,
                    'usuario_id': usuario_id,
                    'emprestimo_id': emprestimo_id,
                    'numero_parcela': k + 1,
                    'total_parcelas': prazo_meses,
                    'valor_principal_centavos': round(principal_por_parcela, 2),
                    'valor_juros_centavos': round(juros_por_parcela, 2),
                    'valor_total_centavos': round(valor_parcela, 2),
                    'valor_pago_centavos': valor_pago_centavos,
                    'valor_multa_centavos': valor_multa_centavos,
                    'valor_juros_mora_centavos': valor_juros_mora_centavos,
                    'saldo_devedor_centavos': round(valor_principal_centavos * (1 - (k + 1) / prazo_meses), 2),
                    'data_vencimento': iso(data_vencimento),
                    'status': status,
                    'dias_atraso': max(0, dias_atraso_calc) if status in ('atrasado', 'parcial') else 0,
                    'created_at': iso(data_inicio),
                    'deleted': False,
                }
                if status == 'pago':
                    parcela['data_pagamento'] = iso(data_vencimento + timedelta(days=random.randint(0, 5)))
                await db.parcelas.insert_one(parcela)
                parcelas_criadas.append(parcela)

                # Pagamento correspondente
                if status == 'pago':
                    data_pag = data_vencimento + timedelta(days=random.randint(0, 5))
                    pagamento = {
                        'id': str(uuid.uuid4()),
                        'usuario_id': usuario_id,
                        'parcela_id': parcela_id,
                        'emprestimo_id': emprestimo_id,
                        'cliente_id': cliente['id'],
                        'cliente_nome': cliente['nome'],
                        'cliente_telefone': cliente['telefone'],
                        'valor_pago_centavos': round(valor_parcela, 2),
                        'metodo_pagamento': random.choice(['pix', 'transferencia', 'dinheiro', 'cartao']),
                        'data_pagamento': iso(data_pag),
                        'tipo': 'pagamento',
                        'observacoes': None,
                        'numero_parcela': k + 1,
                        'total_parcelas': prazo_meses,
                        'created_at': iso(data_pag),
                        'deleted': False,
                    }
                    await db.pagamentos.insert_one(pagamento)
                    pagamentos_criados.append(pagamento)
                elif status == 'parcial':
                    data_pag = data_vencimento - timedelta(days=random.randint(1, 5))
                    pagamento = {
                        'id': str(uuid.uuid4()),
                        'usuario_id': usuario_id,
                        'parcela_id': parcela_id,
                        'emprestimo_id': emprestimo_id,
                        'cliente_id': cliente['id'],
                        'cliente_nome': cliente['nome'],
                        'cliente_telefone': cliente['telefone'],
                        'valor_pago_centavos': valor_pago_centavos,
                        'metodo_pagamento': random.choice(['pix', 'transferencia']),
                        'data_pagamento': iso(data_pag),
                        'tipo': 'pagamento',
                        'observacoes': 'Pagamento parcial',
                        'numero_parcela': k + 1,
                        'total_parcelas': prazo_meses,
                        'created_at': iso(data_pag),
                        'deleted': False,
                    }
                    await db.pagamentos.insert_one(pagamento)
                    pagamentos_criados.append(pagamento)

            # Marcar empréstimo como inadimplente se tiver 3+ parcelas atrasadas
            if qtd_atrasadas_emp >= 3:
                await db.emprestimos.update_one(
                    {'id': emprestimo_id},
                    {'$set': {'status': 'inadimplente'}}
                )

    print(f"\n✅ {len(emprestimos_criados)} empréstimos")
    print(f"✅ {len(parcelas_criadas)} parcelas")
    print(f"✅ {len(pagamentos_criados)} pagamentos")

    # Estatísticas
    pagas = sum(1 for p in parcelas_criadas if p['status'] == 'pago')
    pendentes = sum(1 for p in parcelas_criadas if p['status'] == 'pendente')
    atrasadas = sum(1 for p in parcelas_criadas if p['status'] == 'atrasado')
    parciais = sum(1 for p in parcelas_criadas if p['status'] == 'parcial')

    print("\n" + "=" * 60)
    print("📊 ESTATÍSTICAS")
    print("=" * 60)
    print(f"👥 Clientes: {len(clientes_criados)}")
    print(f"💰 Empréstimos: {len(emprestimos_criados)}")
    print(f"📋 Parcelas: {len(parcelas_criadas)}")
    print(f"   ✅ Pagas: {pagas}")
    print(f"   📅 Pendentes: {pendentes}")
    print(f"   ⚠️ Atrasadas: {atrasadas}")
    print(f"   ⏳ Parciais: {parciais}")
    print(f"💳 Pagamentos: {len(pagamentos_criados)}")

    total_emp = sum(e['valor_principal_centavos'] for e in emprestimos_criados)
    total_recebido = sum(p['valor_pago_centavos'] for p in pagamentos_criados)
    print(f"\n💵 Capital emprestado: R$ {total_emp:,.2f}")
    print(f"✅ Total recebido: R$ {total_recebido:,.2f}")

    client.close()
    print("\n🎉 DONE!")


if __name__ == "__main__":
    asyncio.run(criar_dados_teste())
