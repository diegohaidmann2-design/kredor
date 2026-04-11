"""
Teste rápido para verificar dados do PDF de empréstimo
"""
import requests

BASE_URL = "http://localhost:8001/api"

# 1. Login
print("1. Fazendo login...")
login_response = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": "admin@gestorcerd.com", "senha": "admin123"}
)
token = login_response.json()["access_token"]
print(f"✅ Token obtido")

# 2. Buscar empréstimos
print("\n2. Buscando empréstimos...")
headers = {"Authorization": f"Bearer {token}"}
emprestimos_response = requests.get(f"{BASE_URL}/emprestimos", headers=headers)
emprestimos = emprestimos_response.json()

if not emprestimos:
    print("❌ Nenhum empréstimo encontrado")
    exit(1)

emprestimo_id = emprestimos[0]["id"]
print(f"✅ Usando empréstimo: {emprestimo_id[:8]}...")

# 3. Buscar parcelas
print("\n3. Buscando parcelas...")
parcelas_response = requests.get(
    f"{BASE_URL}/parcelas",
    headers=headers,
    params={"emprestimo_id": emprestimo_id}
)
parcelas = parcelas_response.json()
print(f"✅ {len(parcelas)} parcelas encontradas")

if parcelas:
    print("\n📋 Parcelas:")
    total_parcelas = 0
    for p in parcelas:
        print(f"   Parcela {p['numero_parcela']}: R$ {p['valor_total']:,.2f} - {p['status']}")
        total_parcelas += p['valor_total']
    
    print(f"\n💰 Total a Pagar (soma das parcelas): R$ {total_parcelas:,.2f}")
    print(f"💰 Valor Principal: R$ {emprestimos[0]['valor_principal']:,.2f}")
    print(f"💰 Total de Juros: R$ {total_parcelas - emprestimos[0]['valor_principal']:,.2f}")
else:
    print("❌ Nenhuma parcela encontrada - PDF vai estar zerado!")

print("\n✅ Agora tente gerar o PDF novamente pelo frontend!")
print(f"   Empréstimo ID: {emprestimo_id}")
