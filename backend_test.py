#!/usr/bin/env python3
"""
Teste de Backend - Sistema de Gestão de Empréstimos
Foco: Verificar integridade de dados e agrupamento por cliente
"""

import requests
import sys
import json
from datetime import datetime

class LoanSystemTester:
    def __init__(self, base_url="https://project-launch-67.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.issues_found = []

    def log_issue(self, severity, description, details=None):
        """Log an issue found during testing"""
        issue = {
            "severity": severity,  # CRITICAL, HIGH, MEDIUM, LOW
            "description": description,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        self.issues_found.append(issue)
        print(f"🚨 {severity}: {description}")
        if details:
            print(f"   Details: {details}")

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
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json() if response.content else {}
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                    return False, error_detail
                except:
                    print(f"   Error: {response.text}")
                    return False, {"error": response.text}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {"error": str(e)}

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
        if success and 'access_token' in response:
            self.token = response['access_token']
            print(f"✅ Login successful, token obtained")
            return True
        else:
            self.log_issue("CRITICAL", "Login failed", {"email": email, "response": response})
            return False

    def test_parcelas_pendentes(self):
        """Test the /api/parcelas/pendentes endpoint"""
        print(f"\n📋 Testing parcelas pendentes endpoint...")
        success, response = self.run_test(
            "Parcelas Pendentes",
            "GET",
            "parcelas/pendentes",
            200
        )
        
        if not success:
            self.log_issue("CRITICAL", "Failed to fetch pending installments", response)
            return []
        
        parcelas = response if isinstance(response, list) else []
        print(f"📊 Found {len(parcelas)} pending installments")
        
        # Analyze data integrity
        self.analyze_client_grouping(parcelas)
        return parcelas

    def analyze_client_grouping(self, parcelas):
        """Analyze client grouping integrity"""
        print(f"\n🔍 Analyzing client grouping integrity...")
        
        # Group by cliente_id
        clients = {}
        emprestimo_to_client = {}  # Track which client each loan belongs to
        
        for parcela in parcelas:
            cliente_id = parcela.get('cliente_id')
            cliente_nome = parcela.get('cliente_nome')
            emprestimo_id = parcela.get('emprestimo_id')
            
            if not cliente_id:
                self.log_issue("HIGH", "Parcela without cliente_id found", {
                    "parcela_id": parcela.get('id'),
                    "emprestimo_id": emprestimo_id
                })
                continue
            
            # Track client info
            if cliente_id not in clients:
                clients[cliente_id] = {
                    "nome": cliente_nome,
                    "emprestimos": set(),
                    "parcelas": []
                }
            
            clients[cliente_id]["emprestimos"].add(emprestimo_id)
            clients[cliente_id]["parcelas"].append(parcela)
            
            # Check for loan ownership conflicts
            if emprestimo_id in emprestimo_to_client:
                if emprestimo_to_client[emprestimo_id] != cliente_id:
                    self.log_issue("CRITICAL", "Loan ownership conflict detected", {
                        "emprestimo_id": emprestimo_id,
                        "original_client": emprestimo_to_client[emprestimo_id],
                        "conflicting_client": cliente_id,
                        "original_client_name": self.get_client_name(clients, emprestimo_to_client[emprestimo_id]),
                        "conflicting_client_name": cliente_nome
                    })
            else:
                emprestimo_to_client[emprestimo_id] = cliente_id
        
        # Report findings
        print(f"\n📈 Client Grouping Analysis:")
        print(f"   Total clients: {len(clients)}")
        print(f"   Total loans: {len(emprestimo_to_client)}")
        
        # Check for specific reported issue: Maria Santos vs Diego Santos
        maria_data = None
        diego_data = None
        
        for cliente_id, data in clients.items():
            nome = data["nome"]
            if nome and "maria" in nome.lower() and "santos" in nome.lower():
                maria_data = (cliente_id, data)
                print(f"   📋 Found Maria Santos: {len(data['emprestimos'])} loans, {len(data['parcelas'])} installments")
            elif nome and "diego" in nome.lower() and "santos" in nome.lower():
                diego_data = (cliente_id, data)
                print(f"   📋 Found Diego Santos: {len(data['emprestimos'])} loans, {len(data['parcelas'])} installments")
        
        # Detailed analysis for Maria and Diego
        if maria_data:
            self.analyze_client_details("Maria Santos", maria_data[0], maria_data[1])
        if diego_data:
            self.analyze_client_details("Diego Santos", diego_data[0], diego_data[1])
        
        # Check for the specific reported issue
        if maria_data and diego_data:
            self.check_cross_client_contamination(maria_data, diego_data)

    def get_client_name(self, clients, cliente_id):
        """Get client name by ID"""
        return clients.get(cliente_id, {}).get("nome", "Unknown")

    def analyze_client_details(self, client_name, cliente_id, data):
        """Analyze details for a specific client"""
        print(f"\n🔍 Detailed analysis for {client_name} (ID: {cliente_id}):")
        print(f"   Loans: {list(data['emprestimos'])}")
        
        for parcela in data['parcelas']:
            print(f"   Installment {parcela.get('numero_parcela')}/{parcela.get('total_parcelas')} - "
                  f"R${parcela.get('valor_total', 0):.2f} - "
                  f"Loan: {parcela.get('emprestimo_id')} - "
                  f"Status: {parcela.get('status')}")

    def check_cross_client_contamination(self, maria_data, diego_data):
        """Check if there's cross-contamination between Maria and Diego"""
        maria_id, maria_info = maria_data
        diego_id, diego_info = diego_data
        
        print(f"\n🔍 Cross-contamination check:")
        
        # Check if any of Maria's loans appear in Diego's data
        maria_loans = maria_info['emprestimos']
        diego_loans = diego_info['emprestimos']
        
        overlap = maria_loans.intersection(diego_loans)
        if overlap:
            self.log_issue("CRITICAL", "Loan ownership overlap detected", {
                "maria_id": maria_id,
                "diego_id": diego_id,
                "overlapping_loans": list(overlap)
            })
        
        # Check for the specific reported issue: 2/2 - R$200 installment
        for parcela in maria_info['parcelas']:
            if (parcela.get('numero_parcela') == 2 and 
                parcela.get('total_parcelas') == 2 and 
                abs(parcela.get('valor_total', 0) - 200.0) < 0.01):
                
                print(f"🎯 Found reported installment 2/2 - R$200.00 under Maria Santos")
                print(f"   Loan ID: {parcela.get('emprestimo_id')}")
                print(f"   Client ID in data: {parcela.get('cliente_id')}")
                
                # This should belong to Diego according to the report
                self.log_issue("HIGH", "Reported misattribution found", {
                    "description": "2/2 - R$200 installment found under Maria Santos",
                    "should_belong_to": "Diego Santos",
                    "parcela_id": parcela.get('id'),
                    "emprestimo_id": parcela.get('emprestimo_id'),
                    "current_cliente_id": parcela.get('cliente_id')
                })

    def test_emprestimos_endpoint(self):
        """Test the loans endpoint to verify data integrity"""
        print(f"\n🏦 Testing loans endpoint...")
        success, response = self.run_test(
            "List Loans",
            "GET",
            "emprestimos",
            200
        )
        
        if not success:
            self.log_issue("HIGH", "Failed to fetch loans", response)
            return []
        
        loans = response.get('items', []) if isinstance(response, dict) else response
        print(f"📊 Found {len(loans)} loans")
        return loans

    def cross_reference_data(self, parcelas, emprestimos):
        """Cross-reference parcelas and emprestimos data"""
        print(f"\n🔗 Cross-referencing installments and loans...")
        
        # Create loan lookup
        loan_lookup = {loan.get('id'): loan for loan in emprestimos}
        
        mismatches = []
        for parcela in parcelas:
            emprestimo_id = parcela.get('emprestimo_id')
            parcela_cliente_id = parcela.get('cliente_id')
            
            if emprestimo_id in loan_lookup:
                loan = loan_lookup[emprestimo_id]
                loan_cliente_id = loan.get('cliente_id')
                
                if parcela_cliente_id != loan_cliente_id:
                    mismatch = {
                        "parcela_id": parcela.get('id'),
                        "emprestimo_id": emprestimo_id,
                        "parcela_cliente_id": parcela_cliente_id,
                        "loan_cliente_id": loan_cliente_id,
                        "parcela_cliente_nome": parcela.get('cliente_nome'),
                        "numero_parcela": parcela.get('numero_parcela'),
                        "valor": parcela.get('valor_total')
                    }
                    mismatches.append(mismatch)
                    
                    self.log_issue("CRITICAL", "Client ID mismatch between installment and loan", mismatch)
        
        if not mismatches:
            print("✅ No client ID mismatches found between installments and loans")
        else:
            print(f"❌ Found {len(mismatches)} client ID mismatches")

    def generate_report(self):
        """Generate final test report"""
        print(f"\n" + "="*60)
        print(f"📊 FINAL TEST REPORT")
        print(f"="*60)
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "N/A")
        print(f"Issues found: {len(self.issues_found)}")
        
        if self.issues_found:
            print(f"\n🚨 ISSUES SUMMARY:")
            critical = [i for i in self.issues_found if i['severity'] == 'CRITICAL']
            high = [i for i in self.issues_found if i['severity'] == 'HIGH']
            medium = [i for i in self.issues_found if i['severity'] == 'MEDIUM']
            
            print(f"   Critical: {len(critical)}")
            print(f"   High: {len(high)}")
            print(f"   Medium: {len(medium)}")
            
            print(f"\n📋 DETAILED ISSUES:")
            for i, issue in enumerate(self.issues_found, 1):
                print(f"\n{i}. [{issue['severity']}] {issue['description']}")
                if issue['details']:
                    for key, value in issue['details'].items():
                        print(f"   {key}: {value}")
        else:
            print(f"\n✅ No issues found!")
        
        return len(critical) == 0 and len(high) == 0

def main():
    """Main test execution"""
    print("🚀 Starting Loan Management System Backend Tests")
    print("Focus: Client grouping integrity and data consistency")
    
    tester = LoanSystemTester()
    
    # Test credentials from the review request
    email = "diego.haidmann@gmail.com"
    password = "muda2025"
    
    # Login
    if not tester.test_login(email, password):
        print("❌ Cannot proceed without authentication")
        return 1
    
    # Test pending installments endpoint
    parcelas = tester.test_parcelas_pendentes()
    
    # Test loans endpoint
    emprestimos = tester.test_emprestimos_endpoint()
    
    # Cross-reference data
    if parcelas and emprestimos:
        tester.cross_reference_data(parcelas, emprestimos)
    
    # Generate final report
    success = tester.generate_report()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())