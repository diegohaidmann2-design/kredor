"""
Script para gerar clientes e empréstimos realistas
Uso: python -m seeds.gerar_clientes_emprestimos [quantidade]
"""
import asyncio
import sys
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Adicionar o diretório backend ao path
sys.path.append(str(Path(__file__).parent.parent))

from config import db
import uuid

# Listas de dados realistas para geração
NOMES = [
    "João Silva", "Maria Santos", "Pedro Oliveira", "Ana Costa", "Carlos Souza",
    "Julia Ferreira", "Lucas Almeida", "Beatriz Lima", "Rafael Pereira", "Camila Rodrigues",
    "Fernando Martins", "Patricia Carvalho", "Rodrigo Barbosa", "Amanda Ribeiro", "Diego Mendes",
    "Larissa Araújo", "Bruno Cardoso", "Gabriela Fernandes", "Thiago Castro", "Mariana Gomes",
    "Felipe Rocha", "Isabella Dias", "Gabriel Monteiro", "Juliana Freitas", "Vinicius Correia",
    "Leticia Nascimento", "Gustavo Pinto", "Carolina Moreira", "Eduardo Azevedo", "Renata Cunha",
    "Ricardo Duarte", "Daniela Teixeira", "Marcelo Nunes", "Tatiana Vieira", "Alexandre Ramos",
    "Fernanda Castro", "Paulo Barros", "Adriana Sousa", "Marcos Nogueira", "Claudia Campos",
    "Anderson Lopes", "Priscila Farias", "Leandro Cavalcanti", "Vanessa Moura", "Sergio Pires",
    "Monica Rezende", "Fabio Miranda", "Simone Batista", "Roberto Gonçalves", "Luciana Melo"
]

CIDADES_ESTADOS = [
    ("São Paulo", "SP"), ("Rio de Janeiro", "RJ"), ("Belo Horizonte", "MG"),
    ("Brasília", "DF"), ("Curitiba", "PR"), ("Porto Alegre", "RS"),
    ("Salvador", "BA"), ("Fortaleza", "CE"), ("Recife", "PE"),
    ("Manaus", "AM"), ("Goiânia", "GO"), ("Belém", "PA"),
    ("Campinas", "SP"), ("São Bernardo", "SP"), ("Santos", "SP"),
    ("Florianópolis", "SC"), ("Vitória", "ES"), ("Campo Grande", "MS")
]

RUAS = [
    "Rua das Flores", "Av. Paulista", "Rua Augusta", "Av. Brasil",
    "Rua da Paz", "Rua do Comércio", "Av. Central", "Rua São João",
    "Rua Principal", "Av. Independência", "Rua Santos Dumont", "Av. Getúlio Vargas",
    "Rua 7 de Setembro", "Av. Rio Branco", "Rua Coronel Silva", "Rua Barão do Rio Branco"
]

def gerar_cpf():
    """Gera um CPF válido aleatório"""
    cpf = [random.randint(0, 9) for _ in range(9)]
    
    # Calcula primeiro dígito verificador
    soma = sum((10 - i) * cpf[i] for i in range(9))
    digito1 = 11 - (soma % 11)
    digito1 = 0 if digito1 > 9 else digito1
    cpf.append(digito1)
    
    # Calcula segundo dígito verificador
    soma = sum((11 - i) * cpf[i] for i in range(10))
    digito2 = 11 - (soma % 11)
    digito2 = 0 if digito2 > 9 else digito2
    cpf.append(digito2)
    
    return ''.join(map(str, cpf))

def gerar_telefone():
    """Gera um telefone celular aleatório"""
    ddd = random.choice([11, 21, 31, 41, 51, 61, 71, 81, 85, 91])
    numero = f"9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
    return f"({ddd}) {numero}"

def gerar_cep():
    """Gera um CEP aleatório"""
    return f"{random.randint(10000, 99999)}-{random.randint(100, 999)}"

def calcular_parcela_price(valor_principal, taxa_mensal, prazo_meses):
    """Calcula o valor da parcela usando a Tabela Price"""
    if taxa_mensal == 0:
        return valor_principal / prazo_meses
    
    taxa = taxa_mensal / 100
    parcela = valor_principal * (taxa * (1 + taxa) ** prazo_meses) / ((1 + taxa) ** prazo_meses - 1)
    return round(parcela, 2)

async def gerar_clientes_emprestimos(quantidade=10):
    """
    Gera clientes e empréstimos realistas
    
    Args:
        quantidade: Número de clientes a serem gerados
    """
    print(f"🌱 Gerando {quantidade} clientes e seus empréstimos...")
    print("="*80)
    
    # Buscar o primeiro usuário disponível
    usuario = await db.usuarios.find_one({})
    if not usuario:
        print("❌ Nenhum usuário encontrado! Execute o seeder de usuários primeiro.")
        return
    
    usuario_id = usuario['id']
    usuario_email = usuario['email']
    print(f"✅ Usando usuário: {usuario['nome']} ({usuario_email})\n")
    
    clientes_criados = 0
    emprestimos_criados = 0
    parcelas_criadas = 0
    
    # Usar nomes existentes se quantidade for maior
    nomes_disponiveis = NOMES.copy()
    
    for i in range(quantidade):
        # Gerar dados do cliente
        if nomes_disponiveis:
            nome = nomes_disponiveis.pop(random.randint(0, len(nomes_disponiveis) - 1))
        else:
            nome = f"{random.choice(['João', 'Maria', 'Pedro', 'Ana'])} {random.choice(['Silva', 'Santos', 'Costa'])}"
        
        cliente_id = str(uuid.uuid4())
        cpf = gerar_cpf()
        telefone = gerar_telefone()
        email = nome.lower().replace(" ", ".") + "@email.com"
        cidade, estado = random.choice(CIDADES_ESTADOS)
        rua = random.choice(RUAS)
        numero = random.randint(10, 9999)
        
        # Criar cliente
        cliente = {
            'id': cliente_id,
            'nome': nome,
            'cpf': cpf,
            'telefone': telefone,
            'email': email,
            'endereco': f"{rua}, {numero}",
            'cidade': cidade,
            'estado': estado,
            'cep': gerar_cep(),
            'status': 'ativo',
            'usuario_id': usuario_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'deleted': False
        }
        
        await db.clientes.insert_one(cliente)
        clientes_criados += 1
        print(f"✅ Cliente {i+1}/{quantidade}: {nome} - {cidade}/{estado}")
        
        # Decidir quantos empréstimos criar para este cliente (1-3)
        num_emprestimos = random.choices([1, 2, 3], weights=[60, 30, 10])[0]
        
        for j in range(num_emprestimos):
            # Gerar dados do empréstimo
            emprestimo_id = str(uuid.uuid4())
            
            # Valores realistas baseados em faixas
            faixas_valor = [
                (1000, 5000, 40),    # Pequenos empréstimos
                (5000, 15000, 35),   # Médios empréstimos
                (15000, 50000, 20),  # Grandes empréstimos
                (50000, 100000, 5)   # Muito grandes
            ]
            
            min_val, max_val, _ = random.choices(
                faixas_valor,
                weights=[f[2] for f in faixas_valor]
            )[0]
            
            valor_principal = round(random.uniform(min_val, max_val), 2)
            
            # Taxa de juros realista (0.5% a 8% ao mês)
            taxa_juros_mensal = round(random.uniform(0.5, 8.0), 2)
            
            # Prazo realista (6 a 60 meses)
            prazos_comuns = [6, 12, 18, 24, 36, 48, 60]
            prazo_meses = random.choice(prazos_comuns)
            
            # Calcular valores
            if random.random() < 0.7:  # 70% Tabela Price
                metodo_calculo = "tabela_price"
                parcela_valor = calcular_parcela_price(valor_principal, taxa_juros_mensal, prazo_meses)
                valor_total_com_juros = parcela_valor * prazo_meses
            else:  # 30% Juros Simples
                metodo_calculo = "juros_simples"
                valor_total_juros = valor_principal * (taxa_juros_mensal / 100) * prazo_meses
                valor_total_com_juros = valor_principal + valor_total_juros
            
            valor_total_juros = valor_total_com_juros - valor_principal
            
            # Definir status do empréstimo com probabilidades realistas
            status_opcoes = ["ativo", "quitado", "inadimplente"]
            status_pesos = [70, 20, 10]  # 70% ativo, 20% quitado, 10% inadimplente
            status = random.choices(status_opcoes, weights=status_pesos)[0]
            
            # Data de início varia conforme status
            if status == "quitado":
                # Quitados são mais antigos
                dias_atras = random.randint(180, 730)  # 6 meses a 2 anos
            elif status == "inadimplente":
                # Inadimplentes são recentes
                dias_atras = random.randint(90, 365)  # 3 meses a 1 ano
            else:
                # Ativos variam
                dias_atras = random.randint(0, 365)  # 0 a 1 ano
            
            data_inicio = datetime.now(timezone.utc) - timedelta(days=dias_atras)
            
            # Periodicidade
            periodicidade = random.choices(
                ["mensal", "quinzenal", "semanal"],
                weights=[80, 15, 5]
            )[0]
            
            # Criar empréstimo
            emprestimo = {
                'id': emprestimo_id,
                'cliente_id': cliente_id,
                'valor_principal': valor_principal,
                'valor_total_com_juros': round(valor_total_com_juros, 2),
                'valor_total_juros': round(valor_total_juros, 2),
                'taxa_juros_mensal': taxa_juros_mensal,
                'prazo_meses': prazo_meses,
                'metodo_calculo': metodo_calculo,
                'status': status,
                'periodicidade': periodicidade,
                'data_inicio': data_inicio.isoformat(),
                'usuario_id': usuario_id,
                'created_by': usuario_email,
                'created_at': data_inicio.isoformat(),
                'deleted': False,
                'sem_prazo': False
            }
            
            await db.emprestimos.insert_one(emprestimo)
            emprestimos_criados += 1
            
            # Gerar parcelas para o empréstimo
            valor_parcela = round(valor_total_com_juros / prazo_meses, 2)
            saldo_devedor = valor_total_com_juros
            
            # Calcular intervalo baseado na periodicidade
            if periodicidade == "mensal":
                intervalo_dias = 30
            elif periodicidade == "quinzenal":
                intervalo_dias = 15
            else:  # semanal
                intervalo_dias = 7
            
            for p in range(prazo_meses):
                parcela_id = str(uuid.uuid4())
                data_vencimento = data_inicio + timedelta(days=intervalo_dias * (p + 1))
                
                # Ajustar última parcela para fechar o valor
                if p == prazo_meses - 1:
                    valor_parcela = round(saldo_devedor, 2)
                
                # Calcular proporção de juros e principal
                proporcao_juros = valor_total_juros / valor_total_com_juros
                valor_juros_parcela = round(valor_parcela * proporcao_juros, 2)
                valor_principal_parcela = round(valor_parcela - valor_juros_parcela, 2)
                
                # Determinar status da parcela
                hoje = datetime.now(timezone.utc)
                
                if status == "quitado":
                    # Todas as parcelas pagas
                    parcela_status = "pago"
                    valor_pago = valor_parcela
                    data_pagamento = data_vencimento + timedelta(days=random.randint(-5, 5))
                    dias_atraso = 0
                elif status == "inadimplente":
                    # Várias parcelas atrasadas
                    if data_vencimento < hoje:
                        parcela_status = "atrasado"
                        valor_pago = 0
                        data_pagamento = None
                        dias_atraso = (hoje - data_vencimento).days
                    else:
                        parcela_status = "pendente"
                        valor_pago = 0
                        data_pagamento = None
                        dias_atraso = 0
                else:  # ativo
                    # Algumas pagas, algumas pendentes
                    if data_vencimento < hoje:
                        if random.random() < 0.8:  # 80% pagas em dia
                            parcela_status = "pago"
                            valor_pago = valor_parcela
                            data_pagamento = data_vencimento + timedelta(days=random.randint(-2, 3))
                            dias_atraso = 0
                        else:  # 20% atrasadas
                            parcela_status = "atrasado"
                            valor_pago = 0
                            data_pagamento = None
                            dias_atraso = (hoje - data_vencimento).days
                    else:
                        parcela_status = "pendente"
                        valor_pago = 0
                        data_pagamento = None
                        dias_atraso = 0
                
                # Calcular multa e juros de mora para parcelas atrasadas
                valor_multa = 0
                valor_juros_mora = 0
                if parcela_status == "atrasado" and dias_atraso > 0:
                    valor_multa = round(valor_parcela * 0.02, 2)  # 2% de multa
                    valor_juros_mora = round(valor_parcela * 0.001 * dias_atraso, 2)  # 0.1% ao dia
                
                parcela = {
                    'id': parcela_id,
                    'emprestimo_id': emprestimo_id,
                    'numero_parcela': p + 1,
                    'data_vencimento': data_vencimento.isoformat(),
                    'valor_principal': valor_principal_parcela,
                    'valor_juros': valor_juros_parcela,
                    'valor_total': valor_parcela,
                    'valor_pago': valor_pago,
                    'valor_multa': valor_multa,
                    'valor_juros_mora': valor_juros_mora,
                    'dias_atraso': dias_atraso,
                    'saldo_devedor': round(saldo_devedor, 2),
                    'total_parcelas': prazo_meses,
                    'status': parcela_status,
                    'data_pagamento': data_pagamento.isoformat() if data_pagamento else None,
                    'created_at': data_inicio.isoformat(),
                    'usuario_id': usuario_id
                }
                
                await db.parcelas.insert_one(parcela)
                parcelas_criadas += 1
                saldo_devedor -= valor_parcela
            
            print(f"   💰 Empréstimo {j+1}: R$ {valor_principal:,.2f} - {prazo_meses}x - Status: {status}")
    
    print("\n" + "="*80)
    print(f"✅ Geração concluída com sucesso!")
    print(f"   📊 {clientes_criados} clientes criados")
    print(f"   💰 {emprestimos_criados} empréstimos criados")
    print(f"   📅 {parcelas_criadas} parcelas criadas")
    print("="*80)

async def main():
    """Função principal"""
    quantidade = 10  # Padrão
    
    if len(sys.argv) > 1:
        try:
            quantidade = int(sys.argv[1])
        except ValueError:
            print("❌ Quantidade inválida. Use: python -m seeds.gerar_clientes_emprestimos [número]")
            return
    
    print("\n")
    print("╔══════════════════════════════════════════════════════════════════════════════╗")
    print("║              🌱 GERADOR DE CLIENTES E EMPRÉSTIMOS REALISTAS                  ║")
    print("╚══════════════════════════════════════════════════════════════════════════════╝")
    print(f"\nQuantidade a gerar: {quantidade} clientes")
    print("Cada cliente terá de 1 a 3 empréstimos com parcelas completas\n")
    
    await gerar_clientes_emprestimos(quantidade)
    
    print("\n✨ Use este seeder sempre que precisar de dados de teste realistas!")
    print("   Exemplo: python -m seeds.gerar_clientes_emprestimos 50\n")

if __name__ == "__main__":
    asyncio.run(main())
