"""
Script de teste para prorrogação de empréstimos
Execute: python test_prorrogacao.py
"""
import requests
import json
from datetime import datetime

# Configurações
BASE_URL = "http://localhost:8001/api"
EMAIL = "admin@gestorcerd.com"
SENHA = "admin123"

def fazer_login():
    """Faz login e retorna o token"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": EMAIL, "senha": SENHA}
    )
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Login realizado: {data['usuario']['nome']}")
        return data['access_token']
    else:
        print(f"❌ Erro no login: {response.text}")
        return None

def criar_emprestimo_teste(token):
    """Cria um empréstimo de teste com apenas_juros"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Primeiro, buscar um cliente existente
    clientes_response = requests.get(f"{BASE_URL}/clientes", headers=headers)
    if clientes_response.status_code == 200:
        clientes = clientes_response.json()
        if not clientes:
            print("❌ Nenhum cliente encontrado. Crie um cliente primeiro.")
            return None
        cliente_id = clientes[0]['id']
        print(f"✅ Usando cliente: {clientes[0]['nome']}")
    else:
        print(f"❌ Erro ao buscar clientes: {clientes_response.text}")
        return None
    
    # Criar empréstimo com método apenas_juros
    emprestimo_data = {
        "cliente_id": cliente_id,
        "valor_principal": 10000.00,
        "taxa_juros_mensal": 10.0,
        "prazo_meses": 3,
        "metodo_calculo": "apenas_juros",
        "periodicidade": "mensal",
        "dia_vencimento": 10
    }
    
    response = requests.post(
        f"{BASE_URL}/emprestimos",
        headers=headers,
        json=emprestimo_data
    )
    
    if response.status_code == 200:
        emprestimo = response.json()
        print(f"✅ Empréstimo criado: ID {emprestimo['id'][:8]}...")
        return emprestimo['id']
    else:
        print(f"❌ Erro ao criar empréstimo: {response.text}")
        return None

def listar_parcelas(token, emprestimo_id):
    """Lista as parcelas do empréstimo"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/parcelas?emprestimo_id={emprestimo_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        parcelas = response.json()
        print(f"\n📋 Parcelas do Empréstimo ({len(parcelas)} parcelas):")
        print("-" * 80)
        for p in parcelas:
            tipo = "CAPITAL+JUROS" if p['valor_principal'] > 0 else "APENAS JUROS"
            print(f"  Parcela {p['numero_parcela']}/{p.get('total_parcelas', '?')}: "
                  f"R$ {p['valor_total']:,.2f} - {tipo} - "
                  f"Venc: {p['data_vencimento'][:10]} - Status: {p['status']}")
        print("-" * 80)
        return parcelas
    else:
        print(f"❌ Erro ao listar parcelas: {response.text}")
        return []

def prorrogar_emprestimo(token, emprestimo_id, periodos):
    """Prorroga o empréstimo"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/emprestimos/{emprestimo_id}/prorrogar",
        headers=headers,
        json={"periodos": periodos}
    )
    
    if response.status_code == 200:
        resultado = response.json()
        print(f"\n✅ {resultado['mensagem']}")
        print(f"   📊 Novo total de parcelas: {resultado['novo_total_parcelas']}")
        print(f"\n   📋 Novas parcelas criadas:")
        for p in resultado['novas_parcelas_criadas']:
            print(f"      Parcela {p['numero_parcela']}: "
                  f"R$ {p['valor_total']:,.2f} - {p['tipo']} - "
                  f"Venc: {p['data_vencimento'][:10]}")
        return resultado
    else:
        print(f"\n❌ Erro ao prorrogar: {response.text}")
        return None

def main():
    """Executa o teste completo"""
    print("=" * 80)
    print("🧪 TESTE DE PRORROGAÇÃO DE EMPRÉSTIMOS")
    print("=" * 80)
    
    # 1. Login
    print("\n📍 Passo 1: Fazendo login...")
    token = fazer_login()
    if not token:
        return
    
    # 2. Criar empréstimo de teste
    print("\n📍 Passo 2: Criando empréstimo teste (apenas_juros)...")
    emprestimo_id = criar_emprestimo_teste(token)
    if not emprestimo_id:
        return
    
    # 3. Listar parcelas originais
    print("\n📍 Passo 3: Listando parcelas originais...")
    parcelas_antes = listar_parcelas(token, emprestimo_id)
    
    # 4. Prorrogar empréstimo
    print("\n📍 Passo 4: Prorrogando empréstimo por 2 meses...")
    input("Pressione ENTER para continuar com a prorrogação...")
    resultado = prorrogar_emprestimo(token, emprestimo_id, periodos=2)
    if not resultado:
        return
    
    # 5. Listar parcelas após prorrogação
    print("\n📍 Passo 5: Listando parcelas após prorrogação...")
    parcelas_depois = listar_parcelas(token, emprestimo_id)
    
    # 6. Resumo
    print("\n" + "=" * 80)
    print("📊 RESUMO DO TESTE")
    print("=" * 80)
    print(f"✅ Parcelas antes: {len(parcelas_antes)}")
    print(f"✅ Parcelas depois: {len(parcelas_depois)}")
    print(f"✅ Parcelas adicionadas: {len(parcelas_depois) - len(parcelas_antes)}")
    print(f"✅ Empréstimo ID: {emprestimo_id[:8]}...")
    print("=" * 80)
    
    print("\n💡 Você pode:")
    print("   1. Acessar o frontend e visualizar o empréstimo")
    print("   2. Prorrogar novamente usando o mesmo emprestimo_id")
    print("   3. Verificar a auditoria em /api/auditoria")

if __name__ == "__main__":
    main()
