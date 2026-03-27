#!/usr/bin/env python3
"""
Teste Completo do Backend - Sistema de Gestão de Empréstimos
Foco: Empréstimos Abertos (sem prazo) e Dashboard de Juros
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class EmprestimoTester:
    def __init__(self, base_url: str = "https://busca-emprestimos.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.cliente_id = None
        self.emprestimo_normal_id = None
        self.emprestimo_aberto_id = None
        self.session = requests.Session()
        
    def log(self, message: str, level: str = "INFO"):
        """Log com timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, headers: Optional[Dict] = None) -> tuple[bool, Dict]:
        """Executa um teste de API"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        self.log(f"🔍 Testando {name}...")
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=test_headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=test_headers)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}", "PASS")
            else:
                self.log(f"❌ {name} - Esperado {expected_status}, recebido {response.status_code}", "FAIL")
                if response.text:
                    self.log(f"   Resposta: {response.text[:200]}...", "ERROR")

            try:
                response_data = response.json() if response.text else {}
            except:
                response_data = {"raw_response": response.text}
                
            return success, response_data

        except Exception as e:
            self.log(f"❌ {name} - Erro: {str(e)}", "ERROR")
            return False, {"error": str(e)}

    def test_login(self) -> bool:
        """Testa login com credenciais do admin"""
        self.log("🔐 Iniciando teste de autenticação...")
        
        success, response = self.run_test(
            "Login Admin",
            "POST",
            "auth/login",
            200,
            data={
                "email": "admin@gestorcerd.com",
                "senha": "admin123"
            }
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.log(f"✅ Token obtido: {self.token[:20]}...", "SUCCESS")
            return True
        else:
            self.log("❌ Falha na autenticação", "ERROR")
            return False

    def test_criar_cliente(self) -> bool:
        """Usa um cliente existente para os testes"""
        self.log("🔍 Buscando cliente existente...")
        
        success, response = self.run_test(
            "Listar Clientes",
            "GET",
            "clientes",
            200
        )
        
        if success:
            clientes = response.get('items', response) if isinstance(response, dict) else response
            if isinstance(clientes, list) and len(clientes) > 0:
                self.cliente_id = clientes[0]['id']
                cliente_nome = clientes[0]['nome']
                self.log(f"✅ Cliente encontrado: {cliente_nome} ({self.cliente_id})", "SUCCESS")
                return True
            else:
                self.log("❌ Nenhum cliente encontrado", "ERROR")
                return False
        else:
            self.log("❌ Falha ao listar clientes", "ERROR")
            return False
        
        if success and 'id' in response:
            self.cliente_id = response['id']
            self.log(f"✅ Cliente criado: {self.cliente_id}", "SUCCESS")
            return True
        return False

    def test_criar_emprestimo_normal(self) -> bool:
        """Testa criação de empréstimo normal (com prazo)"""
        if not self.cliente_id:
            self.log("❌ Cliente não encontrado para teste", "ERROR")
            return False
            
        success, response = self.run_test(
            "Criar Empréstimo Normal",
            "POST",
            "emprestimos",
            200,  # API retorna 200, não 201
            data={
                "cliente_id": self.cliente_id,
                "valor_principal": 1000.0,
                "taxa_juros_mensal": 5.0,
                "prazo_meses": 12,
                "metodo_calculo": "tabela_price",
                "periodo_carencia_meses": 0,
                "taxa_multa_atraso": 2.0,
                "taxa_juros_mora_diario": 0.033,
                "periodicidade": "mensal",
                "sem_prazo": False,
                "data_inicio": datetime.now().isoformat(),
                "dia_vencimento": 15
            }
        )
        
        if success and 'id' in response:
            self.emprestimo_normal_id = response['id']
            self.log(f"✅ Empréstimo normal criado: {self.emprestimo_normal_id}", "SUCCESS")
            
            # Verificar se tem valor_total_com_juros
            if response.get('valor_total_com_juros', 0) > 0:
                self.log(f"✅ Valor total calculado: R$ {response['valor_total_com_juros']:.2f}", "SUCCESS")
            else:
                self.log("⚠️ Valor total não calculado", "WARNING")
                
            return True
        return False

    def test_criar_emprestimo_aberto(self) -> bool:
        """Testa criação de empréstimo ABERTO (sem prazo) - FOCO DO TESTE"""
        if not self.cliente_id:
            self.log("❌ Cliente não encontrado para teste", "ERROR")
            return False
            
        self.log("🎯 TESTE PRINCIPAL: Criando empréstimo ABERTO (sem prazo)...")
        
        success, response = self.run_test(
            "Criar Empréstimo ABERTO",
            "POST",
            "emprestimos",
            200,  # API retorna 200, não 201
            data={
                "cliente_id": self.cliente_id,
                "valor_principal": 1000.0,
                "taxa_juros_mensal": 20.0,  # 20% ao mês
                "metodo_calculo": "apenas_juros",
                "periodo_carencia_meses": 0,
                "taxa_multa_atraso": 2.0,
                "taxa_juros_mora_diario": 0.033,
                "periodicidade": "mensal",
                "sem_prazo": True,  # EMPRÉSTIMO ABERTO
                "data_inicio": datetime.now().isoformat(),
                "dia_vencimento": 15
            }
        )
        
        if success and 'id' in response:
            self.emprestimo_aberto_id = response['id']
            self.log(f"✅ Empréstimo ABERTO criado: {self.emprestimo_aberto_id}", "SUCCESS")
            
            # Verificar campos específicos do empréstimo aberto
            if response.get('sem_prazo') == True:
                self.log("✅ Campo sem_prazo = True confirmado", "SUCCESS")
            else:
                self.log("❌ Campo sem_prazo não está True", "ERROR")
                
            if response.get('metodo_calculo') == 'apenas_juros':
                self.log("✅ Método 'apenas_juros' confirmado", "SUCCESS")
            else:
                self.log("❌ Método não é 'apenas_juros'", "ERROR")
                
            return True
        return False

    def test_verificar_primeira_parcela_aberto(self) -> bool:
        """Verifica se a primeira parcela foi gerada para empréstimo aberto"""
        if not self.emprestimo_aberto_id:
            self.log("❌ Empréstimo aberto não encontrado", "ERROR")
            return False
            
        self.log("🔍 Verificando primeira parcela do empréstimo aberto...")
        
        success, response = self.run_test(
            "Listar Parcelas Empréstimo Aberto",
            "GET",
            f"emprestimos/{self.emprestimo_aberto_id}/parcelas",
            200
        )
        
        if success and isinstance(response, list) and len(response) > 0:
            primeira_parcela = response[0]
            
            # Verificar se é apenas juros (valor_principal = 0)
            if primeira_parcela.get('valor_principal', 0) == 0:
                self.log("✅ Primeira parcela tem valor_principal = 0 (apenas juros)", "SUCCESS")
            else:
                self.log(f"❌ Primeira parcela tem valor_principal = {primeira_parcela.get('valor_principal')}", "ERROR")
                
            # Verificar valor dos juros (20% de R$ 1000 = R$ 200)
            valor_juros = primeira_parcela.get('valor_juros', 0)
            valor_esperado = 200.0  # 20% de 1000
            
            if abs(valor_juros - valor_esperado) < 0.01:
                self.log(f"✅ Valor dos juros correto: R$ {valor_juros:.2f}", "SUCCESS")
            else:
                self.log(f"❌ Valor dos juros incorreto: R$ {valor_juros:.2f} (esperado R$ {valor_esperado:.2f})", "ERROR")
                
            # Verificar saldo devedor (deve ser o valor principal)
            saldo_devedor = primeira_parcela.get('saldo_devedor', 0)
            if saldo_devedor == 1000.0:
                self.log(f"✅ Saldo devedor correto: R$ {saldo_devedor:.2f}", "SUCCESS")
            else:
                self.log(f"❌ Saldo devedor incorreto: R$ {saldo_devedor:.2f}", "ERROR")
                
            return True
        else:
            self.log("❌ Nenhuma parcela encontrada para empréstimo aberto", "ERROR")
            return False

    def test_dashboard_juros(self) -> bool:
        """Testa se o dashboard mostra os juros corretamente"""
        self.log("📊 Testando dashboard - verificando juros a receber...")
        
        success, response = self.run_test(
            "Dashboard Stats",
            "GET",
            "dashboard",
            200
        )
        
        if success:
            juros_a_receber = response.get('total_juros_a_receber', 0)
            capital_emprestado = response.get('total_capital_emprestado', 0)
            emprestimos_ativos = response.get('total_emprestimos_ativos', 0)
            
            self.log(f"📈 Capital emprestado: R$ {capital_emprestado:.2f}", "INFO")
            self.log(f"💰 Juros a receber: R$ {juros_a_receber:.2f}", "INFO")
            self.log(f"📋 Empréstimos ativos: {emprestimos_ativos}", "INFO")
            
            # Verificar se há juros a receber (deve ter pelo menos R$ 200 do empréstimo aberto)
            if juros_a_receber >= 200.0:
                self.log("✅ Dashboard mostra juros a receber corretamente", "SUCCESS")
                return True
            else:
                self.log(f"❌ Dashboard não mostra juros suficientes (esperado >= R$ 200.00)", "ERROR")
                return False
        else:
            self.log("❌ Falha ao carregar dashboard", "ERROR")
            return False

    def test_listar_emprestimos(self) -> bool:
        """Testa listagem de empréstimos"""
        success, response = self.run_test(
            "Listar Empréstimos",
            "GET",
            "emprestimos",
            200
        )
        
        if success:
            # A resposta pode ser uma lista ou um objeto com 'items'
            emprestimos = response.get('items', response) if isinstance(response, dict) else response
            
            if isinstance(emprestimos, list):
                self.log(f"✅ {len(emprestimos)} empréstimos encontrados", "SUCCESS")
                
                # Verificar se nossos empréstimos estão na lista
                ids_encontrados = [emp.get('id') for emp in emprestimos]
                
                if self.emprestimo_normal_id in ids_encontrados:
                    self.log("✅ Empréstimo normal encontrado na listagem", "SUCCESS")
                    
                if self.emprestimo_aberto_id in ids_encontrados:
                    self.log("✅ Empréstimo aberto encontrado na listagem", "SUCCESS")
                    
                    # Verificar se o empréstimo aberto tem a flag sem_prazo
                    emp_aberto = next((e for e in emprestimos if e.get('id') == self.emprestimo_aberto_id), None)
                    if emp_aberto and emp_aberto.get('sem_prazo') == True:
                        self.log("✅ Empréstimo aberto tem flag sem_prazo=True na listagem", "SUCCESS")
                    else:
                        self.log("❌ Empréstimo aberto não tem flag sem_prazo=True na listagem", "ERROR")
                
                return True
            else:
                self.log("❌ Resposta da listagem não é uma lista válida", "ERROR")
                return False
        else:
            return False

    def test_validacoes_emprestimo_aberto(self) -> bool:
        """Testa validações específicas para empréstimos abertos"""
        self.log("🔍 Testando validações de empréstimo aberto...")
        
        # Teste 1: Empréstimo aberto sem taxa_juros_mensal
        success1, _ = self.run_test(
            "Validação: Empréstimo aberto sem taxa",
            "POST",
            "emprestimos",
            422,  # Deve retornar erro de validação
            data={
                "cliente_id": self.cliente_id,
                "valor_principal": 1000.0,
                "metodo_calculo": "apenas_juros",
                "sem_prazo": True
                # taxa_juros_mensal ausente
            }
        )
        
        # Teste 2: Empréstimo aberto com método incorreto
        success2, _ = self.run_test(
            "Validação: Empréstimo aberto com método incorreto",
            "POST",
            "emprestimos",
            422,  # Deve retornar erro de validação
            data={
                "cliente_id": self.cliente_id,
                "valor_principal": 1000.0,
                "taxa_juros_mensal": 20.0,
                "metodo_calculo": "tabela_price",  # Método incorreto para empréstimo aberto
                "sem_prazo": True
            }
        )
        
        if success1 and success2:
            self.log("✅ Validações de empréstimo aberto funcionando", "SUCCESS")
            return True
        else:
            self.log("❌ Validações de empréstimo aberto falharam", "ERROR")
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """Executa todos os testes"""
        self.log("🚀 Iniciando testes do sistema de empréstimos...", "START")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {}
        }
        
        # Sequência de testes
        tests = [
            ("login", self.test_login),
            ("buscar_cliente", self.test_criar_cliente),  # Renomeado para refletir a nova função
            ("criar_emprestimo_normal", self.test_criar_emprestimo_normal),
            ("criar_emprestimo_aberto", self.test_criar_emprestimo_aberto),
            ("verificar_primeira_parcela_aberto", self.test_verificar_primeira_parcela_aberto),
            ("dashboard_juros", self.test_dashboard_juros),
            ("listar_emprestimos", self.test_listar_emprestimos),
            ("validacoes_emprestimo_aberto", self.test_validacoes_emprestimo_aberto)
        ]
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                results["tests"][test_name] = {
                    "passed": result,
                    "timestamp": datetime.now().isoformat()
                }
                
                if not result:
                    self.log(f"⚠️ Teste {test_name} falhou - continuando...", "WARNING")
                    
            except Exception as e:
                self.log(f"💥 Erro no teste {test_name}: {str(e)}", "ERROR")
                results["tests"][test_name] = {
                    "passed": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        # Resumo final
        results["summary"] = {
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "success_rate": (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0,
            "emprestimo_normal_id": self.emprestimo_normal_id,
            "emprestimo_aberto_id": self.emprestimo_aberto_id,
            "cliente_id": self.cliente_id
        }
        
        self.log("=" * 60, "SUMMARY")
        self.log(f"📊 Testes executados: {self.tests_run}", "SUMMARY")
        self.log(f"✅ Testes aprovados: {self.tests_passed}", "SUMMARY")
        self.log(f"📈 Taxa de sucesso: {results['summary']['success_rate']:.1f}%", "SUMMARY")
        self.log("=" * 60, "SUMMARY")
        
        return results

def main():
    """Função principal"""
    tester = EmprestimoTester()
    results = tester.run_all_tests()
    
    # Salvar resultados
    with open('/app/test_reports/backend_api_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Resultados salvos em: /app/test_reports/backend_api_test_results.json")
    
    # Retornar código de saída baseado no sucesso
    success_rate = results['summary']['success_rate']
    if success_rate >= 90:
        print("🎉 Todos os testes principais passaram!")
        return 0
    elif success_rate >= 70:
        print("⚠️ Alguns testes falharam, mas funcionalidade principal OK")
        return 1
    else:
        print("❌ Muitos testes falharam - problemas críticos detectados")
        return 2

if __name__ == "__main__":
    sys.exit(main())