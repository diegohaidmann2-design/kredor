#!/usr/bin/env python3
"""
Specific test for loan creation 500 error reported by user
Tests both normal loans (with deadline) and open loans (sem_prazo)
"""

import requests
import sys
import json
from datetime import datetime, timedelta

class EmprestimoErrorTester:
    def __init__(self, base_url="https://gestorcred-preview.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.cliente_id = "1442b64f-298f-4246-a95a-a97bb21d3047"  # Maria Silva

    def log_test(self, name, success, details="", response_data=None, status_code=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            
        result = {
            "test_name": name,
            "success": success,
            "details": details,
            "response_data": response_data,
            "status_code": status_code,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"\n{status} - {name}")
        if details:
            print(f"   Details: {details}")
        if status_code:
            print(f"   Status Code: {status_code}")
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

            print(f"   Status Code: {response.status_code}")
            
            try:
                response_json = response.json()
            except:
                response_json = {"raw_response": response.text}

            success = response.status_code == expected_status
            
            if success:
                self.log_test(name, True, f"Status: {response.status_code}", response_json, response.status_code)
                return True, response_json
            else:
                self.log_test(name, False, f"Expected {expected_status}, got {response.status_code}", response_json, response.status_code)
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

    def test_normal_loan_creation(self):
        """Test creating a normal loan with deadline (should work)"""
        print("\n" + "="*50)
        print("TESTING NORMAL LOAN CREATION (WITH DEADLINE)")
        print("="*50)
        
        normal_loan_data = {
            "cliente_id": self.cliente_id,
            "valor_principal": 10000.0,
            "taxa_juros_mensal": 2.5,
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
        
        success, response = self.run_test(
            "Create Normal Loan (with deadline)",
            "POST",
            "emprestimos",
            200,
            data=normal_loan_data
        )
        
        if success:
            loan_id = response.get('id')
            print(f"   ✅ Normal loan created successfully - ID: {loan_id}")
            return loan_id
        else:
            print(f"   ❌ Normal loan creation failed")
            return None

    def test_open_loan_creation(self):
        """Test creating an open loan (sem_prazo=True) - this is where 500 error occurs"""
        print("\n" + "="*50)
        print("TESTING OPEN LOAN CREATION (SEM_PRAZO=TRUE)")
        print("="*50)
        
        open_loan_data = {
            "cliente_id": self.cliente_id,
            "valor_principal": 5000.0,
            "taxa_juros_mensal": 3.0,
            "metodo_calculo": "apenas_juros",  # Required for open loans
            "periodo_carencia_meses": 0,
            "taxa_multa_atraso": 2.0,
            "taxa_juros_mora_diario": 0.033,
            "periodicidade": "mensal",
            "sem_prazo": True,  # This is the key field for open loans
            "data_inicio": datetime.now().isoformat(),
            "dia_vencimento": 15
        }
        
        print("   📋 Testing open loan with required fields:")
        print(f"      - sem_prazo: {open_loan_data['sem_prazo']}")
        print(f"      - metodo_calculo: {open_loan_data['metodo_calculo']}")
        print(f"      - taxa_juros_mensal: {open_loan_data['taxa_juros_mensal']}")
        print(f"      - NO prazo_meses (should be None for open loans)")
        
        success, response = self.run_test(
            "Create Open Loan (sem_prazo=True)",
            "POST",
            "emprestimos",
            200,
            data=open_loan_data
        )
        
        if success:
            loan_id = response.get('id')
            print(f"   ✅ Open loan created successfully - ID: {loan_id}")
            return loan_id
        else:
            print(f"   ❌ Open loan creation failed - THIS IS THE REPORTED 500 ERROR")
            return None

    def test_field_validation(self):
        """Test field validation for different loan types"""
        print("\n" + "="*50)
        print("TESTING FIELD VALIDATION")
        print("="*50)
        
        # Test 1: Open loan without required taxa_juros_mensal
        print("\n   🧪 Test 1: Open loan without taxa_juros_mensal (should fail with 422)")
        invalid_open_loan = {
            "cliente_id": self.cliente_id,
            "valor_principal": 5000.0,
            "metodo_calculo": "apenas_juros",
            "sem_prazo": True,
            "periodicidade": "mensal"
            # Missing taxa_juros_mensal
        }
        
        success, response = self.run_test(
            "Open Loan - Missing taxa_juros_mensal",
            "POST",
            "emprestimos",
            422,
            data=invalid_open_loan
        )
        
        # Test 2: Open loan with wrong metodo_calculo
        print("\n   🧪 Test 2: Open loan with wrong metodo_calculo (should fail with 422)")
        invalid_method_loan = {
            "cliente_id": self.cliente_id,
            "valor_principal": 5000.0,
            "taxa_juros_mensal": 3.0,
            "metodo_calculo": "tabela_price",  # Should be "apenas_juros" for open loans
            "sem_prazo": True,
            "periodicidade": "mensal"
        }
        
        success, response = self.run_test(
            "Open Loan - Wrong metodo_calculo",
            "POST",
            "emprestimos",
            422,
            data=invalid_method_loan
        )
        
        # Test 3: Normal loan without required prazo_meses
        print("\n   🧪 Test 3: Normal loan without prazo_meses (should fail with 422)")
        invalid_normal_loan = {
            "cliente_id": self.cliente_id,
            "valor_principal": 10000.0,
            "taxa_juros_mensal": 2.5,
            "metodo_calculo": "tabela_price",
            "sem_prazo": False,
            "periodicidade": "mensal"
            # Missing prazo_meses
        }
        
        success, response = self.run_test(
            "Normal Loan - Missing prazo_meses",
            "POST",
            "emprestimos",
            422,
            data=invalid_normal_loan
        )

    def test_loan_listing_after_creation(self):
        """Test listing loans to verify they were created correctly"""
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
            
            # Check for open loans
            open_loans = [loan for loan in loans if loan.get('sem_prazo') == True]
            normal_loans = [loan for loan in loans if loan.get('sem_prazo') == False]
            
            print(f"   📅 Normal loans: {len(normal_loans)}")
            print(f"   🔄 Open loans: {len(open_loans)}")
            
            # Show details of open loans
            if open_loans:
                print("\n   📋 Open loan details:")
                for loan in open_loans:
                    print(f"      - ID: {loan.get('id')}")
                    print(f"      - Value: R$ {loan.get('valor_principal', 0):,.2f}")
                    print(f"      - Method: {loan.get('metodo_calculo')}")
                    print(f"      - Monthly Rate: {loan.get('taxa_juros_mensal', 0)}%")

    def check_backend_logs(self):
        """Check backend logs for 500 errors"""
        print("\n" + "="*50)
        print("CHECKING BACKEND LOGS FOR ERRORS")
        print("="*50)
        
        try:
            # This would be run on the server to check logs
            print("   📋 To check backend logs, run on server:")
            print("   sudo supervisorctl tail -f backend")
            print("   or")
            print("   tail -f /var/log/supervisor/backend.*.log")
        except Exception as e:
            print(f"   ❌ Could not check logs: {e}")

    def generate_report(self):
        """Generate test report"""
        print("\n" + "="*60)
        print("TEST SUMMARY REPORT - LOAN CREATION 500 ERROR")
        print("="*60)
        
        print(f"📊 Tests Run: {self.tests_run}")
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        print("\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {result['test_name']} (Status: {result.get('status_code', 'N/A')})")
            if result['details']:
                print(f"      {result['details']}")
        
        # Identify critical issues
        failed_tests = [r for r in self.test_results if not r['success']]
        if failed_tests:
            print("\n🚨 CRITICAL ISSUES FOUND:")
            for test in failed_tests:
                print(f"   • {test['test_name']}: {test['details']}")
                if test.get('status_code') == 500:
                    print(f"     🔥 500 ERROR DETECTED - Check backend logs!")
        
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
    print("🚀 Starting Loan Creation 500 Error Investigation")
    print("=" * 60)
    
    tester = EmprestimoErrorTester()
    
    # Run authentication test
    if not tester.test_login():
        print("❌ Authentication failed - stopping tests")
        return 1
    
    # Test normal loan creation (should work)
    normal_loan_id = tester.test_normal_loan_creation()
    
    # Test open loan creation (this is where 500 error occurs)
    open_loan_id = tester.test_open_loan_creation()
    
    # Test field validation
    tester.test_field_validation()
    
    # Test loan listing
    tester.test_loan_listing_after_creation()
    
    # Check backend logs
    tester.check_backend_logs()
    
    # Generate final report
    report = tester.generate_report()
    
    # Save detailed report to file
    with open('/app/test_reports/emprestimo_500_error_test.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved to: /app/test_reports/emprestimo_500_error_test.json")
    
    # Return appropriate exit code
    return 0 if report['failed_tests'] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())