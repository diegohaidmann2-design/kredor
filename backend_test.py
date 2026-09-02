#!/usr/bin/env python3
"""
Teste Backend - Verificação do fix de agrupamento de parcelas por cliente
Testando se cliente_id está sendo retornado corretamente na API /api/parcelas/pendentes
"""

import requests
import sys
import json
from datetime import datetime

class ParcelasAPITester:
    def __init__(self, base_url="https://db-loader-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=test_headers, timeout=30)

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_login(self, email, password):
        """Test login and get token"""
        print(f"\n🔐 Attempting login with: {email}")
        success, response = self.run_test(
            "Login",
            "POST",
            "auth/login",
            200,
            data={"email": email, "senha": password}
        )
        if success and isinstance(response, dict) and 'access_token' in response:
            self.token = response['access_token']
            print(f"✅ Login successful, token obtained")
            return True
        elif success and isinstance(response, dict) and 'token' in response:
            self.token = response['token']
            print(f"✅ Login successful, token obtained")
            return True
        else:
            print(f"❌ Login failed - No token in response: {response}")
            return False

    def test_parcelas_pendentes(self):
        """Test parcelas pendentes endpoint and verify cliente_id is present"""
        print(f"\n📋 Testing parcelas pendentes endpoint...")
        success, response = self.run_test(
            "Listar Parcelas Pendentes",
            "GET",
            "parcelas/pendentes",
            200
        )
        
        if not success:
            return False, []
        
        if not isinstance(response, list):
            print(f"❌ Expected list, got: {type(response)}")
            return False, []
        
        print(f"📊 Found {len(response)} parcelas pendentes")
        
        # Verificar se todas as parcelas têm cliente_id
        parcelas_sem_cliente_id = []
        clientes_encontrados = set()
        
        for i, parcela in enumerate(response):
            if not parcela.get('cliente_id'):
                parcelas_sem_cliente_id.append(i)
                print(f"❌ Parcela {i} sem cliente_id: {parcela.get('id', 'ID não encontrado')}")
            else:
                clientes_encontrados.add(parcela['cliente_id'])
                print(f"✅ Parcela {i}: cliente_id = {parcela['cliente_id']}, cliente_nome = {parcela.get('cliente_nome', 'N/A')}")
        
        if parcelas_sem_cliente_id:
            print(f"❌ {len(parcelas_sem_cliente_id)} parcelas sem cliente_id")
            return False, response
        else:
            print(f"✅ Todas as parcelas têm cliente_id")
            print(f"📊 Total de clientes únicos: {len(clientes_encontrados)}")
            return True, response

    def analyze_client_grouping(self, parcelas):
        """Analyze client grouping in the parcelas data"""
        print(f"\n🔍 Analyzing client grouping...")
        
        # Agrupar por cliente
        clientes = {}
        for parcela in parcelas:
            cliente_id = parcela.get('cliente_id')
            cliente_nome = parcela.get('cliente_nome', 'Nome não encontrado')
            
            if cliente_id not in clientes:
                clientes[cliente_id] = {
                    'nome': cliente_nome,
                    'emprestimos': {},
                    'total_parcelas': 0
                }
            
            # Agrupar por empréstimo dentro do cliente
            emprestimo_id = parcela.get('emprestimo_id')
            if emprestimo_id not in clientes[cliente_id]['emprestimos']:
                clientes[cliente_id]['emprestimos'][emprestimo_id] = []
            
            clientes[cliente_id]['emprestimos'][emprestimo_id].append(parcela)
            clientes[cliente_id]['total_parcelas'] += 1
        
        print(f"\n📊 Análise de Agrupamento por Cliente:")
        print(f"=" * 60)
        
        maria_santos_found = False
        diego_santos_found = False
        
        for cliente_id, dados in clientes.items():
            nome = dados['nome']
            total_parcelas = dados['total_parcelas']
            total_emprestimos = len(dados['emprestimos'])
            
            print(f"\n👤 Cliente: {nome} (ID: {cliente_id})")
            print(f"   📋 Total de parcelas: {total_parcelas}")
            print(f"   🏦 Total de empréstimos: {total_emprestimos}")
            
            # Verificar casos específicos
            if 'Maria Santos' in nome:
                maria_santos_found = True
                print(f"   ✅ Maria Santos encontrada!")
                if total_parcelas == 6 and total_emprestimos == 1:
                    print(f"   ✅ Maria Santos: 1 empréstimo com 6 parcelas - CORRETO")
                else:
                    print(f"   ❌ Maria Santos: Esperado 1 empréstimo com 6 parcelas, encontrado {total_emprestimos} empréstimos com {total_parcelas} parcelas")
            
            if 'Diego Santos' in nome:
                diego_santos_found = True
                print(f"   ✅ Diego Santos encontrado!")
                if total_parcelas == 2 and total_emprestimos == 1:
                    print(f"   ✅ Diego Santos: 1 empréstimo com 2 parcelas - CORRETO")
                else:
                    print(f"   ❌ Diego Santos: Esperado 1 empréstimo com 2 parcelas, encontrado {total_emprestimos} empréstimos com {total_parcelas} parcelas")
            
            # Detalhar empréstimos
            for emp_id, parcelas_emp in dados['emprestimos'].items():
                print(f"     💳 Empréstimo {emp_id}: {len(parcelas_emp)} parcelas")
                for parcela in parcelas_emp:
                    status = parcela.get('status', 'N/A')
                    numero = parcela.get('numero_parcela', 'N/A')
                    total = parcela.get('total_parcelas', 'N/A')
                    print(f"       - Parcela {numero}/{total} - Status: {status}")
        
        # Verificar se os casos específicos foram encontrados
        if not maria_santos_found:
            print(f"\n❌ Maria Santos não encontrada nos dados!")
        
        if not diego_santos_found:
            print(f"\n❌ Diego Santos não encontrado nos dados!")
        
        return clientes

def main():
    print("🚀 Iniciando testes do backend - Fix de agrupamento de parcelas")
    print("=" * 70)
    
    # Setup
    tester = ParcelasAPITester()
    
    # Credenciais de teste
    email = "diego.haidmann@gmail.com"
    password = "muda2025"
    
    # Test 1: Login
    if not tester.test_login(email, password):
        print("❌ Login failed, stopping tests")
        return 1
    
    # Test 2: Parcelas Pendentes API
    success, parcelas = tester.test_parcelas_pendentes()
    if not success:
        print("❌ Parcelas pendentes API failed, stopping tests")
        return 1
    
    # Test 3: Analyze client grouping
    if parcelas:
        clientes = tester.analyze_client_grouping(parcelas)
    
    # Print final results
    print(f"\n" + "=" * 70)
    print(f"📊 RESULTADOS FINAIS:")
    print(f"   Tests executados: {tester.tests_run}")
    print(f"   Tests aprovados: {tester.tests_passed}")
    print(f"   Taxa de sucesso: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print(f"✅ Todos os testes passaram!")
        return 0
    else:
        print(f"❌ {tester.tests_run - tester.tests_passed} testes falharam")
        return 1

if __name__ == "__main__":
    sys.exit(main())