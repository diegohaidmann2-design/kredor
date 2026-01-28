"""
Test Suite: Sistema de Permissões Gestor Cred
Tests permission-based access control for different user profiles (admin vs trial user)

Test Coverage:
- Admin has unrestricted access to all endpoints
- Trial user blocked (HTTP 403) from premium resources: assistente_ia, exportacao, relatorios_avancados
- Trial user can access basic resources: dashboard, clientes, emprestimos
- /api/auth/permissoes returns correct limits for each profile
- Client creation works for both profiles
- Advanced reports (inadimplencia, fluxo_caixa) require advanced plan
"""
import pytest
import requests
import os
import uuid
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@sgej.com"
ADMIN_SENHA = "admin123"
TRIAL_EMAIL = "usuario@teste.com"
TRIAL_SENHA = "senha123"

# Token cache to avoid rate limiting
_token_cache = {}


def get_token(email, senha, cache_key):
    """Get authentication token with caching to avoid rate limiting"""
    if cache_key in _token_cache:
        return _token_cache[cache_key]
    
    # Add delay to avoid rate limiting
    time.sleep(0.5)
    
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": email,
        "senha": senha
    })
    
    if response.status_code == 429:
        # Rate limited - wait and retry
        retry_after = response.json().get("retry_after", 60)
        print(f"Rate limited, waiting {retry_after} seconds...")
        time.sleep(retry_after + 1)
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "senha": senha
        })
    
    if response.status_code == 200:
        token = response.json().get("token")
        _token_cache[cache_key] = token
        return token
    return None


def get_admin_token():
    """Get admin authentication token"""
    return get_token(ADMIN_EMAIL, ADMIN_SENHA, "admin")


def get_trial_token():
    """Get trial user authentication token"""
    return get_token(TRIAL_EMAIL, TRIAL_SENHA, "trial")


@pytest.fixture(scope="module")
def admin_token():
    """Module-scoped admin token fixture"""
    token = get_admin_token()
    if not token:
        pytest.skip("Failed to get admin token")
    return token


@pytest.fixture(scope="module")
def trial_token():
    """Module-scoped trial token fixture"""
    token = get_trial_token()
    if not token:
        pytest.skip("Failed to get trial token")
    return token


class TestAuthLogin:
    """Test authentication endpoints"""
    
    def test_admin_login_success(self):
        """Admin should be able to login successfully"""
        time.sleep(0.5)
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_SENHA
        })
        
        if response.status_code == 429:
            pytest.skip("Rate limited")
        
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not returned"
        assert "usuario" in data, "Usuario not returned"
        assert data["usuario"]["email"] == ADMIN_EMAIL
        assert data["usuario"]["perfil"] in ["admin", "superadmin"], f"Expected admin profile, got {data['usuario']['perfil']}"
        
        # Cache the token
        _token_cache["admin"] = data["token"]
    
    def test_trial_user_login_success(self):
        """Trial user should be able to login successfully"""
        time.sleep(0.5)
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TRIAL_EMAIL,
            "senha": TRIAL_SENHA
        })
        
        if response.status_code == 429:
            pytest.skip("Rate limited")
        
        assert response.status_code == 200, f"Trial user login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not returned"
        assert "usuario" in data, "Usuario not returned"
        assert data["usuario"]["email"] == TRIAL_EMAIL
        assert data["usuario"]["plano"] == "trial", f"Expected trial plan, got {data['usuario']['plano']}"
        
        # Cache the token
        _token_cache["trial"] = data["token"]
    
    def test_invalid_credentials(self):
        """Invalid credentials should return 401"""
        time.sleep(0.5)
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@email.com",
            "senha": "wrongpassword"
        })
        
        if response.status_code == 429:
            pytest.skip("Rate limited")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestPermissoesEndpoint:
    """Test /api/auth/permissoes endpoint returns correct limits"""
    
    def test_admin_permissoes(self, admin_token):
        """Admin should have unlimited access to all resources"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/permissoes", headers=headers)
        
        assert response.status_code == 200, f"Failed to get admin permissions: {response.text}"
        data = response.json()
        
        # Admin should be flagged as admin
        assert data["is_admin"] == True, "Admin should have is_admin=True"
        assert data["perfil"] in ["admin", "superadmin"], f"Expected admin profile, got {data['perfil']}"
        
        # Admin should have unlimited limits (-1)
        assert data["uso"]["clientes"]["ilimitado"] == True, "Admin should have unlimited clients"
        assert data["uso"]["emprestimos"]["ilimitado"] == True, "Admin should have unlimited loans"
        
        # Admin should have access to all resources
        recursos = data["recursos"]
        assert recursos["relatorios_basicos"] == True
        assert recursos["relatorios_avancados"] == True
        assert recursos["assistente_ia"] == True
        assert recursos["contratos_pdf"] == True
        assert recursos["contratos_personalizados"] == True
        assert recursos["api_acesso"] == True
        assert recursos["multi_usuarios"] == True
        assert recursos["notificacoes_email"] == True
        assert recursos["notificacoes_whatsapp"] == True
        assert recursos["suporte_prioritario"] == True
        assert recursos["suporte_24_7"] == True
    
    def test_trial_user_permissoes(self, trial_token):
        """Trial user should have limited access according to trial plan"""
        headers = {"Authorization": f"Bearer {trial_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/permissoes", headers=headers)
        
        assert response.status_code == 200, f"Failed to get trial permissions: {response.text}"
        data = response.json()
        
        # Trial user should NOT be admin
        assert data["is_admin"] == False, "Trial user should have is_admin=False"
        assert data["plano"]["slug"] == "trial", f"Expected trial plan, got {data['plano']['slug']}"
        
        # Trial user should have limited resources (as per PLANOS_PADRAO)
        recursos = data["recursos"]
        assert recursos["relatorios_basicos"] == True, "Trial should have basic reports"
        assert recursos["relatorios_avancados"] == False, "Trial should NOT have advanced reports"
        assert recursos["assistente_ia"] == False, "Trial should NOT have AI assistant"
        assert recursos["contratos_pdf"] == False, "Trial should NOT have PDF contracts (per plan config)"
        assert recursos["contratos_personalizados"] == False, "Trial should NOT have custom contracts"
        assert recursos["api_acesso"] == False, "Trial should NOT have API access"
        assert recursos["multi_usuarios"] == False, "Trial should NOT have multi-users"
        
        # Trial should have limited clients/loans
        assert data["uso"]["clientes"]["ilimitado"] == False, "Trial should have limited clients"
        assert data["uso"]["emprestimos"]["ilimitado"] == False, "Trial should have limited loans"
        assert data["uso"]["clientes"]["limite"] == 5, "Trial should have 5 client limit"
        assert data["uso"]["emprestimos"]["limite"] == 10, "Trial should have 10 loan limit"


class TestAdminUnrestrictedAccess:
    """Test that admin has unrestricted access to all endpoints"""
    
    def test_admin_dashboard_access(self, admin_token):
        """Admin should access dashboard"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard", headers=headers)
        assert response.status_code == 200, f"Admin dashboard access failed: {response.text}"
    
    def test_admin_clientes_access(self, admin_token):
        """Admin should access clientes"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/clientes", headers=headers)
        assert response.status_code == 200, f"Admin clientes access failed: {response.text}"
    
    def test_admin_emprestimos_access(self, admin_token):
        """Admin should access emprestimos"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/emprestimos", headers=headers)
        assert response.status_code == 200, f"Admin emprestimos access failed: {response.text}"
    
    def test_admin_assistente_ia_access(self, admin_token):
        """Admin should access assistente IA (premium resource)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/assistente/chat", 
            headers=headers,
            json={"mensagem": "Olá, teste de acesso admin"}
        )
        # Should not return 403 (may return 200 or 500 if LLM fails, but not 403)
        assert response.status_code != 403, f"Admin should not be blocked from assistente IA: {response.text}"
    
    def test_admin_exportacao_access(self, admin_token):
        """Admin should access exportacao (premium resource)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/exportacao/exportar",
            headers=headers,
            json={"entidades": ["clientes"], "formato": "json"}
        )
        # Should not return 403
        assert response.status_code != 403, f"Admin should not be blocked from exportacao: {response.text}"
    
    def test_admin_relatorios_inadimplencia_access(self, admin_token):
        """Admin should access advanced reports (inadimplencia)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/relatorios/gerar",
            headers=headers,
            json={"tipo": "inadimplencia", "periodo": "mes", "formato": "pdf"}
        )
        # Should not return 403 (may return 404 if no data, but not 403)
        assert response.status_code != 403, f"Admin should not be blocked from inadimplencia report: {response.text}"
    
    def test_admin_relatorios_fluxo_caixa_access(self, admin_token):
        """Admin should access advanced reports (fluxo_caixa)"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/relatorios/gerar",
            headers=headers,
            json={"tipo": "fluxo_caixa", "periodo": "mes", "formato": "pdf"}
        )
        # Should not return 403
        assert response.status_code != 403, f"Admin should not be blocked from fluxo_caixa report: {response.text}"


class TestTrialUserBasicAccess:
    """Test that trial user can access basic resources"""
    
    def test_trial_dashboard_access(self, trial_token):
        """Trial user should access dashboard"""
        headers = {"Authorization": f"Bearer {trial_token}"}
        response = requests.get(f"{BASE_URL}/api/dashboard", headers=headers)
        assert response.status_code == 200, f"Trial user dashboard access failed: {response.text}"
    
    def test_trial_clientes_list_access(self, trial_token):
        """Trial user should access clientes list"""
        headers = {"Authorization": f"Bearer {trial_token}"}
        response = requests.get(f"{BASE_URL}/api/clientes", headers=headers)
        assert response.status_code == 200, f"Trial user clientes access failed: {response.text}"
    
    def test_trial_emprestimos_list_access(self, trial_token):
        """Trial user should access emprestimos list"""
        headers = {"Authorization": f"Bearer {trial_token}"}
        response = requests.get(f"{BASE_URL}/api/emprestimos", headers=headers)
        assert response.status_code == 200, f"Trial user emprestimos access failed: {response.text}"
    
    def test_trial_basic_report_access(self, trial_token):
        """Trial user should access basic reports (clientes, emprestimos, pagamentos)"""
        headers = {"Authorization": f"Bearer {trial_token}"}
        
        # Test clientes report (basic report type)
        response = requests.post(f"{BASE_URL}/api/relatorios/gerar",
            headers=headers,
            json={"tipo": "clientes", "periodo": "mes", "formato": "pdf"}
        )
        # Should not return 403 (may return 404 if no data)
        assert response.status_code != 403, f"Trial user should access basic clientes report: {response.text}"


class TestTrialUserPremiumBlocked:
    """Test that trial user is blocked (HTTP 403) from premium resources"""
    
    def test_trial_assistente_ia_blocked(self, trial_token):
        """Trial user should be blocked from assistente IA"""
        headers = {"Authorization": f"Bearer {trial_token}"}
        response = requests.post(f"{BASE_URL}/api/assistente/chat",
            headers=headers,
            json={"mensagem": "Olá, teste de acesso trial"}
        )
        assert response.status_code == 403, f"Trial user should be blocked from assistente IA, got {response.status_code}: {response.text}"
        # Verify error message mentions plan upgrade
        data = response.json()
        assert "detail" in data, "Error response should have detail"
    
    def test_trial_exportacao_blocked(self, trial_token):
        """Trial user should be blocked from exportacao"""
        headers = {"Authorization": f"Bearer {trial_token}"}
        response = requests.post(f"{BASE_URL}/api/exportacao/exportar",
            headers=headers,
            json={"entidades": ["clientes"], "formato": "json"}
        )
        assert response.status_code == 403, f"Trial user should be blocked from exportacao, got {response.status_code}: {response.text}"
    
    def test_trial_relatorios_inadimplencia_blocked(self, trial_token):
        """Trial user should be blocked from inadimplencia report (advanced)"""
        headers = {"Authorization": f"Bearer {trial_token}"}
        response = requests.post(f"{BASE_URL}/api/relatorios/gerar",
            headers=headers,
            json={"tipo": "inadimplencia", "periodo": "mes", "formato": "pdf"}
        )
        assert response.status_code == 403, f"Trial user should be blocked from inadimplencia report, got {response.status_code}: {response.text}"
    
    def test_trial_relatorios_fluxo_caixa_blocked(self, trial_token):
        """Trial user should be blocked from fluxo_caixa report (advanced)"""
        headers = {"Authorization": f"Bearer {trial_token}"}
        response = requests.post(f"{BASE_URL}/api/relatorios/gerar",
            headers=headers,
            json={"tipo": "fluxo_caixa", "periodo": "mes", "formato": "pdf"}
        )
        assert response.status_code == 403, f"Trial user should be blocked from fluxo_caixa report, got {response.status_code}: {response.text}"


class TestClientCreation:
    """Test client creation for both profiles"""
    
    def test_admin_create_client(self, admin_token):
        """Admin should be able to create clients"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        unique_cpf = f"TEST_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(f"{BASE_URL}/api/clientes",
            headers=headers,
            json={
                "nome": "TEST_Cliente Admin",
                "cpf_cnpj": unique_cpf,
                "telefone": "11999999999",
                "email": f"test_admin_{uuid.uuid4().hex[:6]}@test.com"
            }
        )
        assert response.status_code in [200, 201], f"Admin client creation failed: {response.text}"
        data = response.json()
        assert data["nome"] == "TEST_Cliente Admin"
        
        # Cleanup - delete the test client
        if "id" in data:
            requests.delete(f"{BASE_URL}/api/clientes/{data['id']}", headers=headers)
    
    def test_trial_create_client(self, trial_token):
        """Trial user should be able to create clients (within limits)"""
        headers = {"Authorization": f"Bearer {trial_token}"}
        unique_cpf = f"TEST_{uuid.uuid4().hex[:8]}"
        
        response = requests.post(f"{BASE_URL}/api/clientes",
            headers=headers,
            json={
                "nome": "TEST_Cliente Trial",
                "cpf_cnpj": unique_cpf,
                "telefone": "11888888888",
                "email": f"test_trial_{uuid.uuid4().hex[:6]}@test.com"
            }
        )
        # Should succeed (200/201) or fail with 403 if limit reached
        assert response.status_code in [200, 201, 403], f"Unexpected status: {response.status_code}: {response.text}"
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert data["nome"] == "TEST_Cliente Trial"
            # Cleanup
            if "id" in data:
                requests.delete(f"{BASE_URL}/api/clientes/{data['id']}", headers=headers)
        else:
            # 403 means limit reached - this is acceptable for trial
            data = response.json()
            assert "limite" in data.get("detail", "").lower() or "limit" in data.get("detail", "").lower(), \
                f"403 should mention limit: {data}"


class TestExportacaoResumo:
    """Test exportacao resumo endpoint (should be accessible to all authenticated users)"""
    
    def test_admin_exportacao_resumo(self, admin_token):
        """Admin should access exportacao resumo"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/exportacao/resumo", headers=headers)
        assert response.status_code == 200, f"Admin exportacao resumo failed: {response.text}"
        data = response.json()
        assert "clientes" in data
        assert "emprestimos" in data
    
    def test_trial_exportacao_resumo(self, trial_token):
        """Trial user should access exportacao resumo (read-only)"""
        headers = {"Authorization": f"Bearer {trial_token}"}
        response = requests.get(f"{BASE_URL}/api/exportacao/resumo", headers=headers)
        assert response.status_code == 200, f"Trial user exportacao resumo failed: {response.text}"


class TestUnauthenticatedAccess:
    """Test that unauthenticated requests are blocked"""
    
    def test_dashboard_requires_auth(self):
        """Dashboard should require authentication"""
        response = requests.get(f"{BASE_URL}/api/dashboard")
        assert response.status_code in [401, 403], f"Dashboard should require auth, got {response.status_code}"
    
    def test_clientes_requires_auth(self):
        """Clientes should require authentication"""
        response = requests.get(f"{BASE_URL}/api/clientes")
        assert response.status_code in [401, 403], f"Clientes should require auth, got {response.status_code}"
    
    def test_permissoes_requires_auth(self):
        """Permissoes should require authentication"""
        response = requests.get(f"{BASE_URL}/api/auth/permissoes")
        assert response.status_code in [401, 403], f"Permissoes should require auth, got {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
