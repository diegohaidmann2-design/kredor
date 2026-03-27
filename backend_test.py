#!/usr/bin/env python3
"""
Backend API Testing for Loan Management System
Tests both monthly and weekly loan creation functionality
"""

import requests
import sys
import json
from datetime import datetime, timedelta

class LoanAPITester:
    def __init__(self, base_url="https://projeto-em-progresso.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.cliente_id = None

    def log_test(self, name, success, details="", response_data=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            
        result = {
            "test_name": name,
            "success": success,
            "details": details,
            "response_data": response_data,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"\n{status} - {name}")
        if details:
            print(f"   Details: {details}")
        if response_data and not success:
            print(f"   Response: {json.dumps(response_data, indent=2)}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            test_headers.update(headers)

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        if data:
            print(f"   Payload: {json.dumps(data, indent=2)}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            print(f"   Status Code: {response.status_code}")
            
            try:
                response_json = response.json()
            except:
                response_json = {"raw_response": response.text}

            success = response.status_code == expected_status
            
            if success:
                self.log_test(name, True, f"Status: {response.status_code}", response_json)
                return True, response_json
            else:
                self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}", response_json)
                return False, response_json

        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            print(f"   Error: {error_msg}")
            self.log_test(name, False, error_msg)
            return False, {"error": error_msg}

    def test_login(self):
        """Test login and get authentication token"""
        print("\n" + "="*50)
        print("TESTING AUTHENTICATION")
        print("="*50)
        
        login_data = {
            "email": "admin@gestorcerd.com",
            "senha": "admin123"
        }
        
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data=login_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            print(f"   ✅ Token obtained: {self.token[:20]}...")
            return True
        else:
            print(f"   ❌ Login failed: {response}")
            return False

    def test_get_clients(self):
        """Get available clients for testing"""
        print("\n" + "="*50)
        print("TESTING CLIENT RETRIEVAL")
        print("="*50)
        
        success, response = self.run_test(
            "Get Clients List",
            "GET",
            "clientes",
            200
        )
        
        if success:
            clients = response.get('items', response) if isinstance(response, dict) else response
            if clients and len(clients) > 0:
                # Look for Maria Silva or use first available client
                maria_client = None
                for client in clients:
                    if 'Maria Silva' in client.get('nome', ''):
                        maria_client = client
                        break
                
                if maria_client:
                    self.cliente_id = maria_client['id']
                    print(f"   ✅ Found Maria Silva - ID: {self.cliente_id}")
                else:
                    self.cliente_id = clients[0]['id']
                    print(f"   ✅ Using first client - ID: {self.cliente_id}, Name: {clients[0].get('nome', 'N/A')}")
                return True
            else:
                print("   ❌ No clients found")
                return False
        return False

    def test_monthly_loan_creation(self):
        """Test creating a monthly loan (should work - retrocompatibility)"""
        print("\n" + "="*50)
        print("TESTING MONTHLY LOAN CREATION")
        print("="*50)
        
        if not self.cliente_id:
            self.log_test("Monthly Loan Creation", False, "No client ID available")
            return False
            
        monthly_loan_data = {
            "cliente_id": self.cliente_id,
            "valor_principal": 10000.0,
            "taxa_juros_mensal": 2.5,
            "prazo_meses": 12,
            "metodo_calculo": "tabela_price",
            "periodo_carencia_meses": 0,
            "taxa_multa_atraso": 2.0,
            "taxa_juros_mora_diario": 0.033,
            "periodicidade": "mensal",
            "data_inicio": datetime.now().isoformat(),
            "dia_vencimento": 15
        }
        
        success, response = self.run_test(
            "Create Monthly Loan",
            "POST",
            "emprestimos",
            200,  # Changed from 201 to 200
            data=monthly_loan_data
        )
        
        if success:
            loan_id = response.get('id')
            print(f"   ✅ Monthly loan created successfully - ID: {loan_id}")
            return loan_id
        else:
            print(f"   ❌ Monthly loan creation failed")
            return None

    def test_weekly_loan_creation(self):
        """Test creating a weekly loan (currently failing with 422)"""
        print("\n" + "="*50)
        print("TESTING WEEKLY LOAN CREATION")
        print("="*50)
        
        if not self.cliente_id:
            self.log_test("Weekly Loan Creation", False, "No client ID available")
            return False
            
        weekly_loan_data = {
            "cliente_id": self.cliente_id,
            "valor_principal": 5000.0,
            "taxa_juros_semanal": 1.0,
            "prazo_semanas": 24,
            "metodo_calculo": "tabela_price",
            "periodo_carencia_meses": 0,
            "taxa_multa_atraso": 2.0,
            "taxa_juros_mora_diario": 0.033,
            "periodicidade": "semanal",
            "data_inicio": datetime.now().isoformat(),
            "dia_vencimento": None
        }
        
        print("   📋 Testing weekly loan with required fields:")
        print(f"      - periodicidade: {weekly_loan_data['periodicidade']}")
        print(f"      - taxa_juros_semanal: {weekly_loan_data['taxa_juros_semanal']}")
        print(f"      - prazo_semanas: {weekly_loan_data['prazo_semanas']}")
        
        success, response = self.run_test(
            "Create Weekly Loan",
            "POST",
            "emprestimos",
            200,  # Changed from 201 to 200
            data=weekly_loan_data
        )
        
        if success:
            loan_id = response.get('id')
            print(f"   ✅ Weekly loan created successfully - ID: {loan_id}")
            return loan_id
        else:
            print(f"   ❌ Weekly loan creation failed")
            # Let's try with additional fields that might be missing
            return self.test_weekly_loan_with_monthly_fields()

    def test_weekly_loan_with_monthly_fields(self):
        """Test weekly loan creation including monthly fields (debugging)"""
        print("\n   🔧 DEBUGGING: Testing weekly loan with monthly fields included...")
        
        weekly_loan_data_with_monthly = {
            "cliente_id": self.cliente_id,
            "valor_principal": 5000.0,
            "taxa_juros_mensal": 10.0,  # Adding monthly rate
            "prazo_meses": 6,           # Adding monthly term
            "taxa_juros_semanal": 1.0,
            "prazo_semanas": 24,
            "metodo_calculo": "tabela_price",
            "periodo_carencia_meses": 0,
            "taxa_multa_atraso": 2.0,
            "taxa_juros_mora_diario": 0.033,
            "periodicidade": "semanal",
            "data_inicio": datetime.now().isoformat(),
            "dia_vencimento": None
        }
        
        success, response = self.run_test(
            "Create Weekly Loan (with monthly fields)",
            "POST",
            "emprestimos",
            200,  # Changed from 201 to 200
            data=weekly_loan_data_with_monthly
        )
        
        if success:
            loan_id = response.get('id')
            print(f"   ✅ Weekly loan with monthly fields created - ID: {loan_id}")
            return loan_id
        else:
            print(f"   ❌ Weekly loan with monthly fields also failed")
            return None

    def test_loan_simulation(self):
        """Test loan simulation endpoints"""
        print("\n" + "="*50)
        print("TESTING LOAN SIMULATION")
        print("="*50)
        
        # Test monthly simulation
        monthly_sim_data = {
            "valor_principal": 10000.0,
            "taxa_juros_mensal": 2.5,
            "prazo_meses": 12,
            "metodo_calculo": "tabela_price",
            "periodo_carencia_meses": 0,
            "periodicidade": "mensal"
        }
        
        success, response = self.run_test(
            "Monthly Loan Simulation",
            "POST",
            "emprestimos/simular",
            200,
            data=monthly_sim_data
        )
        
        # Test weekly simulation
        weekly_sim_data = {
            "valor_principal": 5000.0,
            "taxa_juros_semanal": 1.0,
            "prazo_semanas": 24,
            "metodo_calculo": "tabela_price",
            "periodo_carencia_meses": 0,
            "periodicidade": "semanal"
        }
        
        success, response = self.run_test(
            "Weekly Loan Simulation",
            "POST",
            "emprestimos/simular",
            200,
            data=weekly_sim_data
        )

    def test_list_loans(self):
        """Test listing loans"""
        print("\n" + "="*50)
        print("TESTING LOAN LISTING")
        print("="*50)
        
        success, response = self.run_test(
            "List All Loans",
            "GET",
            "emprestimos",
            200
        )
        
        if success:
            loans = response.get('items', response) if isinstance(response, dict) else response
            print(f"   📊 Found {len(loans) if loans else 0} loans")
            
            # Check for weekly loans
            weekly_loans = [loan for loan in loans if loan.get('periodicidade') == 'semanal']
            monthly_loans = [loan for loan in loans if loan.get('periodicidade') == 'mensal']
            
            print(f"   📅 Monthly loans: {len(monthly_loans)}")
            print(f"   📆 Weekly loans: {len(weekly_loans)}")

    def generate_report(self):
        """Generate test report"""
        print("\n" + "="*60)
        print("TEST SUMMARY REPORT")
        print("="*60)
        
        print(f"📊 Tests Run: {self.tests_run}")
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        print("\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {result['test_name']}")
            if result['details']:
                print(f"      {result['details']}")
        
        # Identify critical issues
        failed_tests = [r for r in self.test_results if not r['success']]
        if failed_tests:
            print("\n🚨 CRITICAL ISSUES FOUND:")
            for test in failed_tests:
                print(f"   • {test['test_name']}: {test['details']}")
        
        return {
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "failed_tests": self.tests_run - self.tests_passed,
            "success_rate": (self.tests_passed/self.tests_run*100) if self.tests_run > 0 else 0,
            "detailed_results": self.test_results,
            "critical_issues": failed_tests
        }

def main():
    """Main test execution"""
    print("🚀 Starting Loan Management System API Tests")
    print("=" * 60)
    
    tester = LoanAPITester()
    
    # Run authentication test
    if not tester.test_login():
        print("❌ Authentication failed - stopping tests")
        return 1
    
    # Get clients for testing
    if not tester.test_get_clients():
        print("❌ Could not retrieve clients - stopping tests")
        return 1
    
    # Test loan simulation
    tester.test_loan_simulation()
    
    # Test loan creation
    monthly_loan_id = tester.test_monthly_loan_creation()
    weekly_loan_id = tester.test_weekly_loan_creation()
    
    # Test loan listing
    tester.test_list_loans()
    
    # Generate final report
    report = tester.generate_report()
    
    # Save detailed report to file
    with open('/app/test_reports/backend_api_test_results.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: /app/test_reports/backend_api_test_results.json")
    
    # Return appropriate exit code
    return 0 if report['failed_tests'] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())