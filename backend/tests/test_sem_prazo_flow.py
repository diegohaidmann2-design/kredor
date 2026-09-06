"""
Test Suite for Sem Prazo (Open-Ended Loan) Flow
Tests: Create, Update, Quitar, Parcelas generation for sem_prazo loans
"""
import pytest
import requests
import os
from datetime import datetime

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://gestorcred-dev.preview.emergentagent.com').rstrip('/')

# Test credentials - using diego.haidmann@gmail.com as per requirements
TEST_EMAIL = "diego.haidmann@gmail.com"
TEST_SENHA = "muda2025"

# Known sem_prazo loan IDs from requirements
SEM_PRAZO_MENSAL_ATIVO = "bfd4c015"  # mensal, ativo
SEM_PRAZO_SEMANAL_ATIVO = "257570a4"  # semanal, ativo
SEM_PRAZO_QUITADO = "ff867942"  # mensal, quitado

# Known client IDs
CLIENT_ADENILSON = "0d515bb3"
CLIENT_JONAS = "4d89d1cd"
CLIENT_DIEGO = "d9eefb77"


class TestSemPrazoAuthentication:
    """Test authentication for sem_prazo flow"""
    
    def test_login_success(self):
        """Test login with diego.haidmann@gmail.com / muda2025"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "senha": TEST_SENHA
        })
        print(f"Login response status: {response.status_code}")
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        print(f"Login successful, token received")
        return data["access_token"]


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for all tests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "senha": TEST_SENHA
    })
    if response.status_code == 200:
        data = response.json()
        if "access_token" in data:
            return data["access_token"]
    pytest.skip("Could not authenticate - skipping tests")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestSemPrazoLoanRetrieval:
    """Test retrieving sem_prazo loans"""
    
    def test_list_emprestimos(self, auth_headers):
        """Test listing all emprestimos"""
        response = requests.get(f"{BASE_URL}/api/emprestimos", headers=auth_headers)
        print(f"List emprestimos response: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        
        # Find sem_prazo loans
        sem_prazo_loans = [e for e in data["items"] if e.get("sem_prazo") == True]
        print(f"Found {len(sem_prazo_loans)} sem_prazo loans out of {len(data['items'])} total")
        
        return sem_prazo_loans
    
    def test_get_sem_prazo_mensal_ativo(self, auth_headers):
        """Test getting the known sem_prazo mensal ativo loan"""
        # Find the loan by partial ID
        response = requests.get(f"{BASE_URL}/api/emprestimos", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        loan = None
        for e in data["items"]:
            if e["id"].startswith(SEM_PRAZO_MENSAL_ATIVO) and e.get("sem_prazo"):
                loan = e
                break
        
        if loan:
            print(f"Found sem_prazo mensal ativo loan: {loan['id']}")
            print(f"  - Status: {loan.get('status')}")
            print(f"  - Periodicidade: {loan.get('periodicidade')}")
            print(f"  - Valor Principal: {loan.get('valor_principal')}")
            print(f"  - Taxa Juros Mensal: {loan.get('taxa_juros_mensal')}")
            
            assert loan.get("sem_prazo") == True
            assert loan.get("periodicidade") == "mensal"
            assert loan.get("metodo_calculo") == "apenas_juros"
            return loan
        else:
            pytest.skip(f"Loan starting with {SEM_PRAZO_MENSAL_ATIVO} not found")
    
    def test_get_sem_prazo_semanal_ativo(self, auth_headers):
        """Test getting the known sem_prazo semanal ativo loan"""
        response = requests.get(f"{BASE_URL}/api/emprestimos", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        loan = None
        for e in data["items"]:
            if e["id"].startswith(SEM_PRAZO_SEMANAL_ATIVO) and e.get("sem_prazo"):
                loan = e
                break
        
        if loan:
            print(f"Found sem_prazo semanal ativo loan: {loan['id']}")
            print(f"  - Status: {loan.get('status')}")
            print(f"  - Periodicidade: {loan.get('periodicidade')}")
            print(f"  - Taxa Juros Semanal: {loan.get('taxa_juros_semanal')}")
            
            assert loan.get("sem_prazo") == True
            assert loan.get("periodicidade") == "semanal"
            return loan
        else:
            pytest.skip(f"Loan starting with {SEM_PRAZO_SEMANAL_ATIVO} not found")


class TestSemPrazoParcelas:
    """Test parcelas for sem_prazo loans"""
    
    def test_list_parcelas_sem_prazo_mensal(self, auth_headers):
        """Test listing parcelas for sem_prazo mensal loan"""
        # First find the loan
        response = requests.get(f"{BASE_URL}/api/emprestimos", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        loan = None
        for e in data["items"]:
            if e["id"].startswith(SEM_PRAZO_MENSAL_ATIVO) and e.get("sem_prazo"):
                loan = e
                break
        
        if not loan:
            pytest.skip("Sem prazo mensal loan not found")
        
        # Get parcelas
        response = requests.get(f"{BASE_URL}/api/emprestimos/{loan['id']}/parcelas", headers=auth_headers)
        print(f"Parcelas response: {response.status_code}")
        
        assert response.status_code == 200
        parcelas = response.json()
        
        print(f"Found {len(parcelas)} parcelas for sem_prazo mensal loan")
        
        for p in parcelas[:5]:  # Show first 5
            print(f"  - Parcela #{p['numero_parcela']}: R${p['valor_total']:.2f} - Status: {p['status']} - Venc: {p['data_vencimento'][:10]}")
        
        # Verify parcela structure for sem_prazo
        if parcelas:
            first_parcela = parcelas[0]
            assert "numero_parcela" in first_parcela
            assert "valor_total" in first_parcela
            assert "status" in first_parcela
            # For sem_prazo, valor_principal should be 0 (only interest)
            assert first_parcela.get("valor_principal") == 0.0, "Sem prazo parcela should have valor_principal=0"
        
        return parcelas
    
    def test_list_parcelas_sem_prazo_semanal(self, auth_headers):
        """Test listing parcelas for sem_prazo semanal loan"""
        response = requests.get(f"{BASE_URL}/api/emprestimos", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        loan = None
        for e in data["items"]:
            if e["id"].startswith(SEM_PRAZO_SEMANAL_ATIVO) and e.get("sem_prazo"):
                loan = e
                break
        
        if not loan:
            pytest.skip("Sem prazo semanal loan not found")
        
        response = requests.get(f"{BASE_URL}/api/emprestimos/{loan['id']}/parcelas", headers=auth_headers)
        print(f"Parcelas semanal response: {response.status_code}")
        
        assert response.status_code == 200
        parcelas = response.json()
        
        print(f"Found {len(parcelas)} parcelas for sem_prazo semanal loan")
        
        # Check for overdue parcelas (atrasado status)
        atrasadas = [p for p in parcelas if p.get("status") == "atrasado"]
        print(f"  - Parcelas atrasadas: {len(atrasadas)}")
        
        return parcelas


class TestSemPrazoUpdate:
    """Test updating sem_prazo loans - prazo field should NOT be required"""
    
    def test_update_sem_prazo_without_prazo_field(self, auth_headers):
        """Test that updating sem_prazo loan does NOT require prazo_meses or prazo_semanas"""
        # Find a sem_prazo loan
        response = requests.get(f"{BASE_URL}/api/emprestimos", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        loan = None
        for e in data["items"]:
            if e.get("sem_prazo") and e.get("status") == "ativo":
                loan = e
                break
        
        if not loan:
            pytest.skip("No active sem_prazo loan found")
        
        print(f"Testing update on sem_prazo loan: {loan['id']}")
        print(f"  - Current periodicidade: {loan.get('periodicidade')}")
        
        # Update WITHOUT prazo_meses or prazo_semanas - this should work for sem_prazo
        update_data = {
            "taxa_multa_atraso": 2.5,  # Just update a non-financial field
            "sem_prazo": True  # Keep sem_prazo flag
        }
        
        response = requests.put(
            f"{BASE_URL}/api/emprestimos/{loan['id']}", 
            json=update_data, 
            headers=auth_headers
        )
        
        print(f"Update response: {response.status_code}")
        print(f"Response body: {response.text[:500]}")
        
        # Should succeed - sem_prazo loans don't need prazo
        assert response.status_code == 200, f"Update failed: {response.text}"
        
        updated = response.json()
        assert updated.get("sem_prazo") == True
        print("✅ Update sem_prazo loan without prazo field: SUCCESS")
    
    def test_update_sem_prazo_mensal_taxa_juros(self, auth_headers):
        """Test updating taxa_juros_mensal for sem_prazo mensal loan"""
        response = requests.get(f"{BASE_URL}/api/emprestimos", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        loan = None
        for e in data["items"]:
            if e["id"].startswith(SEM_PRAZO_MENSAL_ATIVO) and e.get("sem_prazo"):
                loan = e
                break
        
        if not loan:
            pytest.skip("Sem prazo mensal loan not found")
        
        original_taxa = loan.get("taxa_juros_mensal")
        print(f"Original taxa_juros_mensal: {original_taxa}")
        
        # Update taxa - should work without prazo_meses
        update_data = {
            "taxa_juros_mensal": original_taxa,  # Keep same value
            "sem_prazo": True
        }
        
        response = requests.put(
            f"{BASE_URL}/api/emprestimos/{loan['id']}", 
            json=update_data, 
            headers=auth_headers
        )
        
        print(f"Update taxa response: {response.status_code}")
        assert response.status_code == 200, f"Update failed: {response.text}"
        print("✅ Update sem_prazo mensal taxa_juros: SUCCESS")


class TestSemPrazoQuitar:
    """Test quitar (quit/close) endpoint for sem_prazo loans"""
    
    def test_quitar_endpoint_exists(self, auth_headers):
        """Test that /quitar endpoint exists and rejects non-sem_prazo loans"""
        # First, find a regular (non-sem_prazo) loan to test rejection
        response = requests.get(f"{BASE_URL}/api/emprestimos", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        regular_loan = None
        for e in data["items"]:
            if not e.get("sem_prazo") and e.get("status") == "ativo":
                regular_loan = e
                break
        
        if regular_loan:
            # Try to quitar a regular loan - should fail
            response = requests.post(
                f"{BASE_URL}/api/emprestimos/{regular_loan['id']}/quitar",
                headers=auth_headers
            )
            print(f"Quitar regular loan response: {response.status_code}")
            assert response.status_code == 400, "Should reject non-sem_prazo loan"
            print("✅ Quitar correctly rejects non-sem_prazo loans")
    
    def test_quitar_already_quitado_loan(self, auth_headers):
        """Test that quitar rejects already quitado loans"""
        response = requests.get(f"{BASE_URL}/api/emprestimos", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        quitado_loan = None
        for e in data["items"]:
            if e["id"].startswith(SEM_PRAZO_QUITADO) and e.get("sem_prazo"):
                quitado_loan = e
                break
        
        if not quitado_loan:
            # Try to find any quitado sem_prazo loan
            for e in data["items"]:
                if e.get("sem_prazo") and e.get("status") == "quitado":
                    quitado_loan = e
                    break
        
        if quitado_loan:
            response = requests.post(
                f"{BASE_URL}/api/emprestimos/{quitado_loan['id']}/quitar",
                headers=auth_headers
            )
            print(f"Quitar already quitado loan response: {response.status_code}")
            assert response.status_code == 400, "Should reject already quitado loan"
            print("✅ Quitar correctly rejects already quitado loans")
        else:
            pytest.skip("No quitado sem_prazo loan found")
    
    def test_quitar_sem_prazo_loan_structure(self, auth_headers):
        """Test the structure of quitar response (without actually quitting a loan)"""
        # This test verifies the endpoint exists and returns proper error for invalid cases
        response = requests.post(
            f"{BASE_URL}/api/emprestimos/invalid-id-12345/quitar",
            headers=auth_headers
        )
        print(f"Quitar invalid ID response: {response.status_code}")
        assert response.status_code == 404, "Should return 404 for invalid loan ID"
        print("✅ Quitar returns 404 for invalid loan ID")


class TestSemPrazoCreate:
    """Test creating new sem_prazo loans"""
    
    def test_create_sem_prazo_mensal_loan(self, auth_headers):
        """Test creating a new sem_prazo mensal loan"""
        # Find a client to use
        response = requests.get(f"{BASE_URL}/api/clientes", headers=auth_headers)
        assert response.status_code == 200
        
        clientes = response.json()
        if isinstance(clientes, dict):
            clientes = clientes.get("items", [])
        
        if not clientes:
            pytest.skip("No clients found")
        
        cliente_id = clientes[0]["id"]
        print(f"Using client: {clientes[0].get('nome')} ({cliente_id})")
        
        # Create sem_prazo mensal loan
        loan_data = {
            "cliente_id": cliente_id,
            "valor_principal": 5000.00,
            "taxa_juros_mensal": 5.0,
            "metodo_calculo": "apenas_juros",
            "periodicidade": "mensal",
            "sem_prazo": True,
            "dia_vencimento": 15
        }
        
        response = requests.post(
            f"{BASE_URL}/api/emprestimos",
            json=loan_data,
            headers=auth_headers
        )
        
        print(f"Create sem_prazo mensal response: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        assert response.status_code in [200, 201], f"Create failed: {response.text}"
        
        created = response.json()
        assert created.get("sem_prazo") == True
        assert created.get("periodicidade") == "mensal"
        assert created.get("metodo_calculo") == "apenas_juros"
        assert created.get("status") == "ativo"
        
        print(f"✅ Created sem_prazo mensal loan: {created['id']}")
        
        # Verify first parcela was auto-generated
        response = requests.get(
            f"{BASE_URL}/api/emprestimos/{created['id']}/parcelas",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        parcelas = response.json()
        assert len(parcelas) >= 1, "First parcela should be auto-generated"
        
        first_parcela = parcelas[0]
        assert first_parcela["numero_parcela"] == 1
        assert first_parcela["valor_principal"] == 0.0, "Sem prazo parcela should have valor_principal=0"
        
        expected_juros = 5000.00 * (5.0 / 100)  # 250.00
        assert abs(first_parcela["valor_juros"] - expected_juros) < 0.01, f"Expected juros {expected_juros}, got {first_parcela['valor_juros']}"
        
        print(f"✅ First parcela auto-generated: R${first_parcela['valor_total']:.2f}")
        
        return created["id"]
    
    def test_create_sem_prazo_semanal_loan(self, auth_headers):
        """Test creating a new sem_prazo semanal loan"""
        response = requests.get(f"{BASE_URL}/api/clientes", headers=auth_headers)
        assert response.status_code == 200
        
        clientes = response.json()
        if isinstance(clientes, dict):
            clientes = clientes.get("items", [])
        
        if not clientes:
            pytest.skip("No clients found")
        
        cliente_id = clientes[0]["id"]
        
        # Create sem_prazo semanal loan
        loan_data = {
            "cliente_id": cliente_id,
            "valor_principal": 2000.00,
            "taxa_juros_semanal": 2.0,
            "metodo_calculo": "apenas_juros",
            "periodicidade": "semanal",
            "sem_prazo": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/emprestimos",
            json=loan_data,
            headers=auth_headers
        )
        
        print(f"Create sem_prazo semanal response: {response.status_code}")
        
        assert response.status_code in [200, 201], f"Create failed: {response.text}"
        
        created = response.json()
        assert created.get("sem_prazo") == True
        assert created.get("periodicidade") == "semanal"
        
        print(f"✅ Created sem_prazo semanal loan: {created['id']}")
        
        # Verify first parcela
        response = requests.get(
            f"{BASE_URL}/api/emprestimos/{created['id']}/parcelas",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        parcelas = response.json()
        assert len(parcelas) >= 1
        
        expected_juros = 2000.00 * (2.0 / 100)  # 40.00
        assert abs(parcelas[0]["valor_juros"] - expected_juros) < 0.01
        
        print(f"✅ First parcela auto-generated: R${parcelas[0]['valor_total']:.2f}")
        
        return created["id"]


class TestSemPrazoValidation:
    """Test validation rules for sem_prazo loans"""
    
    def test_sem_prazo_requires_apenas_juros(self, auth_headers):
        """Test that sem_prazo loans must use metodo_calculo='apenas_juros'"""
        response = requests.get(f"{BASE_URL}/api/clientes", headers=auth_headers)
        clientes = response.json()
        if isinstance(clientes, dict):
            clientes = clientes.get("items", [])
        
        if not clientes:
            pytest.skip("No clients found")
        
        # Try to create sem_prazo with wrong metodo_calculo
        loan_data = {
            "cliente_id": clientes[0]["id"],
            "valor_principal": 1000.00,
            "taxa_juros_mensal": 5.0,
            "metodo_calculo": "tabela_price",  # Wrong - should be apenas_juros
            "periodicidade": "mensal",
            "sem_prazo": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/emprestimos",
            json=loan_data,
            headers=auth_headers
        )
        
        print(f"Create sem_prazo with wrong metodo: {response.status_code}")
        assert response.status_code == 422, "Should reject sem_prazo with non-apenas_juros method"
        print("✅ Correctly rejects sem_prazo with wrong metodo_calculo")
    
    def test_sem_prazo_mensal_requires_taxa_mensal(self, auth_headers):
        """Test that sem_prazo mensal requires taxa_juros_mensal"""
        response = requests.get(f"{BASE_URL}/api/clientes", headers=auth_headers)
        clientes = response.json()
        if isinstance(clientes, dict):
            clientes = clientes.get("items", [])
        
        if not clientes:
            pytest.skip("No clients found")
        
        # Try to create sem_prazo mensal without taxa_juros_mensal
        loan_data = {
            "cliente_id": clientes[0]["id"],
            "valor_principal": 1000.00,
            # Missing taxa_juros_mensal
            "metodo_calculo": "apenas_juros",
            "periodicidade": "mensal",
            "sem_prazo": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/emprestimos",
            json=loan_data,
            headers=auth_headers
        )
        
        print(f"Create sem_prazo mensal without taxa: {response.status_code}")
        assert response.status_code == 422, "Should reject sem_prazo mensal without taxa_juros_mensal"
        print("✅ Correctly rejects sem_prazo mensal without taxa_juros_mensal")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
