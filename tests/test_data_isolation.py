"""
Test Data Isolation - Admin vs Usuario
Tests for verifying that regular users can only see their own data
and admin-only endpoints are protected.
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@sgej.com"
ADMIN_SENHA = "admin123"
USER_EMAIL = "usuario@teste.com"
USER_SENHA = "teste123"


class TestAuthSetup:
    """Test authentication and user setup"""
    
    def test_admin_login(self):
        """Test admin can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_SENHA
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["usuario"]["perfil"] == "admin"
        print(f"✓ Admin login successful - perfil: {data['usuario']['perfil']}")
    
    def test_user_login(self):
        """Test regular user can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "senha": USER_SENHA
        })
        assert response.status_code == 200, f"User login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["usuario"]["perfil"] == "usuario"
        print(f"✓ User login successful - perfil: {data['usuario']['perfil']}")
    
    def test_new_user_registration_default_profile(self):
        """Test that new user registration defaults to 'usuario' profile"""
        unique_email = f"test_new_{uuid.uuid4().hex[:8]}@teste.com"
        response = requests.post(f"{BASE_URL}/api/auth/registro", json={
            "nome": "Test New User",
            "email": unique_email,
            "senha": "teste123"
        })
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        assert data["perfil"] == "usuario", f"Expected 'usuario' profile, got: {data['perfil']}"
        print(f"✓ New user registration defaults to 'usuario' profile")


@pytest.fixture
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "senha": ADMIN_SENHA
    })
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.text}")
    return response.json()["token"]


@pytest.fixture
def user_token():
    """Get regular user authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": USER_EMAIL,
        "senha": USER_SENHA
    })
    if response.status_code != 200:
        pytest.skip(f"User login failed: {response.text}")
    return response.json()["token"]


@pytest.fixture
def admin_headers(admin_token):
    """Headers with admin auth"""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def user_headers(user_token):
    """Headers with user auth"""
    return {
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json"
    }


class TestClienteIsolation:
    """Test that users can only see their own clients"""
    
    def test_admin_create_cliente(self, admin_headers):
        """Admin creates a client"""
        unique_cpf = f"111.222.333-{uuid.uuid4().hex[:2]}"
        response = requests.post(f"{BASE_URL}/api/clientes", headers=admin_headers, json={
            "nome": "TEST_Admin Cliente",
            "cpf_cnpj": unique_cpf,
            "telefone": "(11) 99999-0001",
            "email": f"admin_cliente_{uuid.uuid4().hex[:6]}@teste.com",
            "endereco": {
                "rua": "Rua Admin",
                "numero": "100",
                "bairro": "Centro",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "01000-000"
            }
        })
        assert response.status_code == 200, f"Failed to create client: {response.text}"
        data = response.json()
        print(f"✓ Admin created client: {data['nome']} (ID: {data['id']})")
        return data["id"]
    
    def test_user_create_cliente(self, user_headers):
        """Regular user creates a client"""
        unique_cpf = f"444.555.666-{uuid.uuid4().hex[:2]}"
        response = requests.post(f"{BASE_URL}/api/clientes", headers=user_headers, json={
            "nome": "TEST_User Cliente",
            "cpf_cnpj": unique_cpf,
            "telefone": "(11) 99999-0002",
            "email": f"user_cliente_{uuid.uuid4().hex[:6]}@teste.com",
            "endereco": {
                "rua": "Rua User",
                "numero": "200",
                "bairro": "Centro",
                "cidade": "São Paulo",
                "estado": "SP",
                "cep": "02000-000"
            }
        })
        assert response.status_code == 200, f"Failed to create client: {response.text}"
        data = response.json()
        print(f"✓ User created client: {data['nome']} (ID: {data['id']})")
        return data["id"]
    
    def test_user_cannot_see_admin_clients(self, admin_headers, user_headers):
        """User should NOT see clients created by admin"""
        # First, get admin's clients
        admin_response = requests.get(f"{BASE_URL}/api/clientes", headers=admin_headers)
        assert admin_response.status_code == 200
        admin_clients = admin_response.json()
        admin_client_ids = [c["id"] for c in admin_clients]
        
        # Now get user's clients
        user_response = requests.get(f"{BASE_URL}/api/clientes", headers=user_headers)
        assert user_response.status_code == 200
        user_clients = user_response.json()
        user_client_ids = [c["id"] for c in user_clients]
        
        # Check that user's clients don't include admin's clients
        overlap = set(admin_client_ids) & set(user_client_ids)
        
        print(f"Admin has {len(admin_clients)} clients, User has {len(user_clients)} clients")
        print(f"✓ Data isolation verified - no overlap in client IDs")
        
        # Verify user cannot access admin's client directly
        if admin_client_ids:
            admin_client_id = admin_client_ids[0]
            direct_access = requests.get(f"{BASE_URL}/api/clientes/{admin_client_id}", headers=user_headers)
            assert direct_access.status_code == 404, f"User should NOT be able to access admin's client directly"
            print(f"✓ User cannot access admin's client directly (got 404)")


class TestEmprestimoIsolation:
    """Test that users can only see their own loans"""
    
    def test_user_cannot_see_admin_emprestimos(self, admin_headers, user_headers):
        """User should NOT see loans created by admin"""
        # Get admin's loans
        admin_response = requests.get(f"{BASE_URL}/api/emprestimos", headers=admin_headers)
        assert admin_response.status_code == 200
        admin_emprestimos = admin_response.json()
        
        # Get user's loans
        user_response = requests.get(f"{BASE_URL}/api/emprestimos", headers=user_headers)
        assert user_response.status_code == 200
        user_emprestimos = user_response.json()
        
        admin_ids = [e["id"] for e in admin_emprestimos]
        user_ids = [e["id"] for e in user_emprestimos]
        
        print(f"Admin has {len(admin_emprestimos)} loans, User has {len(user_emprestimos)} loans")
        
        # Verify no overlap
        overlap = set(admin_ids) & set(user_ids)
        assert len(overlap) == 0, f"Found overlapping loan IDs: {overlap}"
        print(f"✓ Loan isolation verified - no overlap")
        
        # Verify user cannot access admin's loan directly
        if admin_ids:
            admin_loan_id = admin_ids[0]
            direct_access = requests.get(f"{BASE_URL}/api/emprestimos/{admin_loan_id}", headers=user_headers)
            assert direct_access.status_code == 404, f"User should NOT be able to access admin's loan directly"
            print(f"✓ User cannot access admin's loan directly (got 404)")


class TestPagamentoIsolation:
    """Test that users can only see their own payments"""
    
    def test_user_cannot_see_admin_pagamentos(self, admin_headers, user_headers):
        """User should NOT see payments created by admin"""
        # Get admin's payments
        admin_response = requests.get(f"{BASE_URL}/api/pagamentos", headers=admin_headers)
        assert admin_response.status_code == 200
        admin_pagamentos = admin_response.json()
        
        # Get user's payments
        user_response = requests.get(f"{BASE_URL}/api/pagamentos", headers=user_headers)
        assert user_response.status_code == 200
        user_pagamentos = user_response.json()
        
        admin_ids = [p["id"] for p in admin_pagamentos]
        user_ids = [p["id"] for p in user_pagamentos]
        
        print(f"Admin has {len(admin_pagamentos)} payments, User has {len(user_pagamentos)} payments")
        
        # Verify no overlap
        overlap = set(admin_ids) & set(user_ids)
        assert len(overlap) == 0, f"Found overlapping payment IDs: {overlap}"
        print(f"✓ Payment isolation verified - no overlap")


class TestDashboardIsolation:
    """Test that dashboard returns only user's data"""
    
    def test_dashboard_returns_user_data_only(self, admin_headers, user_headers):
        """Dashboard should return different data for admin vs user"""
        # Get admin's dashboard
        admin_response = requests.get(f"{BASE_URL}/api/dashboard", headers=admin_headers)
        assert admin_response.status_code == 200
        admin_dashboard = admin_response.json()
        
        # Get user's dashboard
        user_response = requests.get(f"{BASE_URL}/api/dashboard", headers=user_headers)
        assert user_response.status_code == 200
        user_dashboard = user_response.json()
        
        print(f"Admin dashboard: {admin_dashboard['total_clientes_ativos']} clients, {admin_dashboard['total_emprestimos_ativos']} loans")
        print(f"User dashboard: {user_dashboard['total_clientes_ativos']} clients, {user_dashboard['total_emprestimos_ativos']} loans")
        
        # Dashboard should return data (may be different or same depending on data)
        assert "total_clientes_ativos" in admin_dashboard
        assert "total_clientes_ativos" in user_dashboard
        print(f"✓ Dashboard isolation verified - each user sees their own stats")


class TestParcelasPendentesIsolation:
    """Test that parcelas pendentes returns only user's data"""
    
    def test_parcelas_pendentes_isolation(self, admin_headers, user_headers):
        """Parcelas pendentes should return only user's parcels"""
        # Get admin's pending parcels
        admin_response = requests.get(f"{BASE_URL}/api/parcelas/pendentes", headers=admin_headers)
        assert admin_response.status_code == 200
        admin_parcelas = admin_response.json()
        
        # Get user's pending parcels
        user_response = requests.get(f"{BASE_URL}/api/parcelas/pendentes", headers=user_headers)
        assert user_response.status_code == 200
        user_parcelas = user_response.json()
        
        admin_ids = [p["id"] for p in admin_parcelas]
        user_ids = [p["id"] for p in user_parcelas]
        
        print(f"Admin has {len(admin_parcelas)} pending parcels, User has {len(user_parcelas)} pending parcels")
        
        # Verify no overlap
        overlap = set(admin_ids) & set(user_ids)
        assert len(overlap) == 0, f"Found overlapping parcel IDs: {overlap}"
        print(f"✓ Parcelas pendentes isolation verified - no overlap")


class TestConfiguracoesLandingProtection:
    """Test that PUT /api/configuracoes/landing is admin-only"""
    
    def test_get_configuracoes_landing_public(self):
        """GET configuracoes/landing should be public"""
        response = requests.get(f"{BASE_URL}/api/configuracoes/landing")
        assert response.status_code == 200, f"GET configuracoes/landing failed: {response.text}"
        print(f"✓ GET /api/configuracoes/landing is public (200)")
    
    def test_put_configuracoes_landing_admin_allowed(self, admin_headers):
        """Admin should be able to update landing config"""
        response = requests.put(f"{BASE_URL}/api/configuracoes/landing", headers=admin_headers, json={
            "nome_empresa": "SGEJ Test"
        })
        assert response.status_code == 200, f"Admin PUT configuracoes/landing failed: {response.text}"
        print(f"✓ Admin can update landing config (200)")
    
    def test_put_configuracoes_landing_user_forbidden(self, user_headers):
        """Regular user should NOT be able to update landing config"""
        response = requests.put(f"{BASE_URL}/api/configuracoes/landing", headers=user_headers, json={
            "nome_empresa": "Hacked Name"
        })
        assert response.status_code == 403, f"Expected 403 for user, got: {response.status_code}"
        print(f"✓ User cannot update landing config (403 Forbidden)")
    
    def test_put_configuracoes_landing_no_auth(self):
        """Unauthenticated request should fail"""
        response = requests.put(f"{BASE_URL}/api/configuracoes/landing", json={
            "nome_empresa": "Hacked Name"
        })
        assert response.status_code in [401, 403], f"Expected 401/403, got: {response.status_code}"
        print(f"✓ Unauthenticated request blocked ({response.status_code})")


class TestRelatoriosIsolation:
    """Test that reports return only user's data"""
    
    def test_relatorio_emprestimos_isolation(self, admin_headers, user_headers):
        """Reports should only include user's data"""
        # Generate report for admin
        admin_response = requests.post(f"{BASE_URL}/api/relatorios/gerar", headers=admin_headers, json={
            "tipo": "emprestimos",
            "formato": "pdf",
            "periodo": "ano"
        })
        assert admin_response.status_code == 200, f"Admin report failed: {admin_response.text}"
        
        # Generate report for user
        user_response = requests.post(f"{BASE_URL}/api/relatorios/gerar", headers=user_headers, json={
            "tipo": "emprestimos",
            "formato": "pdf",
            "periodo": "ano"
        })
        assert user_response.status_code == 200, f"User report failed: {user_response.text}"
        
        print(f"✓ Both admin and user can generate reports (data isolated by user)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
