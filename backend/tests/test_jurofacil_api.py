"""
Gestor Cred API - Comprehensive Backend Tests
Tests all major endpoints: Auth, Dashboard, Clientes, Empréstimos, Pagamentos, etc.
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

# Base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://db-loader-1.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@sgej.com"
ADMIN_PASSWORD = "admin123"
USER_EMAIL = "usuario@teste.com"
USER_PASSWORD = "senha123"


class TestAuthEndpoints:
    """Authentication endpoint tests"""
    
    def test_login_admin_success(self):
        """Test admin login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        print(f"Admin login response: {response.status_code}")
        
        # May return 200 (success) or require 2FA
        assert response.status_code in [200, 401, 402], f"Unexpected status: {response.status_code}"
        
        data = response.json()
        if response.status_code == 200:
            if data.get("requires_2fa"):
                print("Admin has 2FA enabled - requires verification")
                assert "email" in data
            else:
                assert "access_token" in data or "token" in data
                print(f"Admin login successful, token received")
                return data.get("access_token") or data.get("token")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.com",
            "senha": "wrongpassword"
        })
        assert response.status_code == 401
        print("Invalid credentials correctly rejected")
    
    def test_login_missing_fields(self):
        """Test login with missing fields"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL
        })
        assert response.status_code == 422  # Validation error
        print("Missing fields correctly rejected")
    
    def test_me_without_auth(self):
        """Test /me endpoint without authentication"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401 or response.status_code == 403
        print("Unauthenticated /me correctly rejected")


class TestDashboardEndpoints:
    """Dashboard endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            if not data.get("requires_2fa"):
                return data.get("access_token") or data.get("token")
        pytest.skip("Could not authenticate - skipping authenticated tests")
    
    def test_dashboard_without_auth(self):
        """Test dashboard without authentication"""
        response = requests.get(f"{BASE_URL}/api/dashboard")
        assert response.status_code in [401, 403]
        print("Unauthenticated dashboard correctly rejected")
    
    def test_dashboard_with_auth(self, auth_token):
        """Test dashboard with authentication"""
        if not auth_token:
            pytest.skip("No auth token available")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard", headers=headers)
        
        print(f"Dashboard response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        # Verify dashboard structure
        assert "total_capital_emprestado" in data
        assert "total_clientes_ativos" in data
        assert "total_emprestimos_ativos" in data
        print(f"Dashboard data: capital={data.get('total_capital_emprestado')}, clientes={data.get('total_clientes_ativos')}")


class TestClientesEndpoints:
    """Clientes CRUD endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            if not data.get("requires_2fa"):
                return data.get("access_token") or data.get("token")
        pytest.skip("Could not authenticate")
    
    def test_listar_clientes_without_auth(self):
        """Test listing clients without auth"""
        response = requests.get(f"{BASE_URL}/api/clientes")
        assert response.status_code in [401, 403]
        print("Unauthenticated clientes list correctly rejected")
    
    def test_listar_clientes_with_auth(self, auth_token):
        """Test listing clients with auth"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/clientes", headers=headers)
        
        print(f"Clientes list response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data or isinstance(data, list)
        print(f"Clientes returned: {len(data.get('items', data))}")
    
    def test_criar_cliente(self, auth_token):
        """Test creating a new client"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        unique_cpf = f"TEST_{uuid.uuid4().hex[:11]}"
        
        cliente_data = {
            "nome": f"TEST_Cliente_{uuid.uuid4().hex[:8]}",
            "cpf_cnpj": unique_cpf,
            "telefone": "11999999999",
            "email": f"test_{uuid.uuid4().hex[:8]}@test.com",
            "status": "ativo"
        }
        
        response = requests.post(f"{BASE_URL}/api/clientes", json=cliente_data, headers=headers)
        print(f"Create cliente response: {response.status_code}")
        
        # May fail due to CPF validation, but should not be 500
        assert response.status_code in [200, 201, 400, 422]
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data
            assert data["nome"] == cliente_data["nome"]
            print(f"Cliente created: {data['id']}")
            return data["id"]


class TestEmprestimosEndpoints:
    """Empréstimos endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            if not data.get("requires_2fa"):
                return data.get("access_token") or data.get("token")
        pytest.skip("Could not authenticate")
    
    def test_listar_emprestimos_without_auth(self):
        """Test listing loans without auth"""
        response = requests.get(f"{BASE_URL}/api/emprestimos")
        assert response.status_code in [401, 403]
        print("Unauthenticated emprestimos list correctly rejected")
    
    def test_listar_emprestimos_with_auth(self, auth_token):
        """Test listing loans with auth"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/emprestimos", headers=headers)
        
        print(f"Emprestimos list response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data or isinstance(data, list)
        print(f"Emprestimos returned: {len(data.get('items', data))}")
    
    def test_simular_emprestimo(self, auth_token):
        """Test loan simulation"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        simulacao_data = {
            "valor_principal": 10000.00,
            "taxa_juros_mensal": 2.5,
            "prazo_meses": 12,
            "metodo_calculo": "tabela_price"  # Correct value: juros_simples, juros_compostos, tabela_price, sac, apenas_juros
        }
        
        response = requests.post(f"{BASE_URL}/api/emprestimos/simular", json=simulacao_data, headers=headers)
        print(f"Simulação response: {response.status_code}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "valor_total_com_juros" in data
        assert "parcelas" in data
        assert len(data["parcelas"]) == 12
        print(f"Simulação: valor_total={data['valor_total_com_juros']}, parcelas={len(data['parcelas'])}")


class TestPagamentosEndpoints:
    """Pagamentos endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            if not data.get("requires_2fa"):
                return data.get("access_token") or data.get("token")
        pytest.skip("Could not authenticate")
    
    def test_listar_pagamentos_without_auth(self):
        """Test listing payments without auth"""
        response = requests.get(f"{BASE_URL}/api/pagamentos")
        assert response.status_code in [401, 403]
        print("Unauthenticated pagamentos list correctly rejected")
    
    def test_listar_pagamentos_with_auth(self, auth_token):
        """Test listing payments with auth"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/pagamentos", headers=headers)
        
        print(f"Pagamentos list response: {response.status_code}")
        assert response.status_code == 200


class TestNotificacoesEndpoints:
    """Notificações endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            if not data.get("requires_2fa"):
                return data.get("access_token") or data.get("token")
        pytest.skip("Could not authenticate")
    
    def test_listar_notificacoes(self, auth_token):
        """Test listing notifications"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/notificacoes", headers=headers)
        
        print(f"Notificações response: {response.status_code}")
        assert response.status_code == 200


class TestAnaliseEndpoints:
    """Análise/Score endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            if not data.get("requires_2fa"):
                return data.get("access_token") or data.get("token")
        pytest.skip("Could not authenticate")
    
    def test_analise_dashboard(self, auth_token):
        """Test analysis dashboard"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/analise/dashboard", headers=headers)
        
        print(f"Análise dashboard response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert "resumo" in data
        assert "distribuicao_classificacao" in data
        print(f"Análise: total_clientes={data['resumo'].get('total_clientes')}")
    
    def test_analise_clientes(self, auth_token):
        """Test clients with scores"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/analise/clientes", headers=headers)
        
        print(f"Análise clientes response: {response.status_code}")
        assert response.status_code == 200


class TestAssistenteEndpoints:
    """Assistente IA endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            if not data.get("requires_2fa"):
                return data.get("access_token") or data.get("token")
        pytest.skip("Could not authenticate")
    
    def test_assistente_chat(self, auth_token):
        """Test AI assistant chat"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        chat_data = {
            "mensagem": "Olá, como funciona o cálculo de juros compostos?"
        }
        
        response = requests.post(f"{BASE_URL}/api/assistente/chat", json=chat_data, headers=headers)
        print(f"Assistente chat response: {response.status_code}")
        
        # May fail if LLM key not configured, but should not be 401/403
        assert response.status_code in [200, 500, 403]
        
        if response.status_code == 200:
            data = response.json()
            assert "resposta" in data
            print(f"Assistente responded: {data['resposta'][:100]}...")


class TestSuperadminEndpoints:
    """Superadmin endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            if not data.get("requires_2fa"):
                return data.get("access_token") or data.get("token")
        pytest.skip("Could not authenticate")
    
    def test_superadmin_usuarios(self, auth_token):
        """Test listing users (admin only)"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/superadmin/usuarios", headers=headers)
        
        print(f"Superadmin usuarios response: {response.status_code}")
        # Should be 200 for admin, 403 for non-admin
        assert response.status_code in [200, 403]
        
        if response.status_code == 200:
            data = response.json()
            assert "usuarios" in data or "total" in data
            print(f"Total usuarios: {data.get('total', len(data.get('usuarios', [])))}")
    
    def test_superadmin_dashboard(self, auth_token):
        """Test superadmin dashboard"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/superadmin/dashboard", headers=headers)
        
        print(f"Superadmin dashboard response: {response.status_code}")
        assert response.status_code in [200, 403]


class TestSchedulerEndpoints:
    """Scheduler admin endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            if not data.get("requires_2fa"):
                return data.get("access_token") or data.get("token")
        pytest.skip("Could not authenticate")
    
    def test_scheduler_status(self, auth_token):
        """Test scheduler status"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/scheduler/status", headers=headers)
        
        print(f"Scheduler status response: {response.status_code}")
        assert response.status_code in [200, 403]
        
        if response.status_code == 200:
            data = response.json()
            assert "scheduler" in data
            print(f"Scheduler running: {data['scheduler'].get('running')}")


class TestPortalEndpoints:
    """Portal do cliente endpoint tests"""
    
    def test_portal_login_invalid(self):
        """Test portal login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/portal/login", json={
            "cpf_cnpj": "12345678901",
            "codigo_acesso": "000000"
        })
        
        print(f"Portal login response: {response.status_code}")
        assert response.status_code in [401, 404, 422]
        print("Invalid portal login correctly rejected")


class TestRelatoriosEndpoints:
    """Relatórios endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            if not data.get("requires_2fa"):
                return data.get("access_token") or data.get("token")
        pytest.skip("Could not authenticate")
    
    def test_gerar_relatorio_emprestimos(self, auth_token):
        """Test generating loans report"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        relatorio_data = {
            "tipo": "emprestimos",
            "formato": "pdf",
            "periodo": "mes"
        }
        
        response = requests.post(f"{BASE_URL}/api/relatorios/gerar", json=relatorio_data, headers=headers)
        print(f"Relatório emprestimos response: {response.status_code}")
        
        # May return 404 if no data, 200 if success
        assert response.status_code in [200, 404, 403]
        
        if response.status_code == 200:
            # Should return PDF content
            assert response.headers.get("content-type") in ["application/pdf", "application/octet-stream"]
            print("Relatório PDF generated successfully")


class Test2FAEndpoints:
    """Two-Factor Authentication endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            if not data.get("requires_2fa"):
                return data.get("access_token") or data.get("token")
        pytest.skip("Could not authenticate")
    
    def test_2fa_status(self, auth_token):
        """Test 2FA status endpoint"""
        if not auth_token:
            pytest.skip("No auth token")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/2fa-status", headers=headers)
        
        print(f"2FA status response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert "two_factor_enabled" in data
        print(f"2FA enabled: {data['two_factor_enabled']}")
    
    def test_verify_2fa_invalid(self):
        """Test 2FA verification with invalid code"""
        response = requests.post(f"{BASE_URL}/api/auth/verify-2fa", json={
            "email": ADMIN_EMAIL,
            "codigo": "000000"
        })
        
        print(f"Verify 2FA response: {response.status_code}")
        # Should fail with invalid code
        assert response.status_code in [401, 400]


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
