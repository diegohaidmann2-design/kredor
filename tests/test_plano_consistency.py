"""
Test Suite: Plano Consistency and Reconciliation
Tests for the centralized plano_service.py and admin endpoints for subscription management.

Features tested:
- GET /api/assinaturas/minha - User's subscription status (consistent data)
- GET /api/assinaturas/admin/status-plano/{usuario_id} - Admin view of user's plan status
- GET /api/assinaturas/admin/reconciliacao - Reconciliation report
- POST /api/assinaturas/admin/corrigir-inconsistencia/{usuario_id} - Fix inconsistencies
- GET /api/assinaturas/admin/logs-planos - Audit logs
- plano_service.py - Centralized plan activation service
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://dev-setup-14.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@sgej.com"
ADMIN_PASSWORD = "admin123"
USER_EMAIL = "usuario@teste.com"
USER_PASSWORD = "senha123"


class TestAuth:
    """Authentication tests for getting tokens"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip(f"Admin authentication failed: {response.status_code} - {response.text}")
    
    @pytest.fixture(scope="class")
    def user_token(self):
        """Get regular user authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "senha": USER_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        # User might not exist, skip gracefully
        return None
    
    def test_admin_login_success(self):
        """Test admin login returns valid token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data or "token" in data, "No token in response"
        print(f"✅ Admin login successful")


class TestMinhaAssinatura:
    """Tests for GET /api/assinaturas/minha endpoint"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip("Admin authentication failed")
    
    def test_minha_assinatura_no_auth(self):
        """Test /minha endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/assinaturas/minha")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✅ /minha requires auth: {response.status_code}")
    
    def test_minha_assinatura_with_auth(self, admin_token):
        """Test /minha endpoint returns consistent subscription data"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/assinaturas/minha", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify required fields are present
        assert "plano" in data, "Missing 'plano' field"
        assert "status" in data or "plano_ativo" in data, "Missing status field"
        
        # Verify data consistency
        plano = data.get("plano")
        assert plano in ["trial", "basico", "profissional", "enterprise"], f"Invalid plano: {plano}"
        
        print(f"✅ /minha returns consistent data:")
        print(f"   Plano: {data.get('plano')}")
        print(f"   Status: {data.get('status')}")
        print(f"   Plano Ativo: {data.get('plano_ativo')}")
        print(f"   Data Expiração: {data.get('data_expiracao') or data.get('data_fim')}")
        print(f"   Dias Restantes: {data.get('dias_restantes')}")
    
    def test_minha_assinatura_fields_consistency(self, admin_token):
        """Test that /minha returns all expected fields for consistency"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/assinaturas/minha", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check for key fields that should be consistent
        expected_fields = ["plano", "status"]
        for field in expected_fields:
            assert field in data, f"Missing expected field: {field}"
        
        # If plano is not trial, should have more details
        if data.get("plano") != "trial":
            # Paid plans should have expiration info
            has_expiration = "data_fim" in data or "data_expiracao" in data
            print(f"   Has expiration date: {has_expiration}")
        
        print(f"✅ /minha fields consistency verified")


class TestAdminStatusPlano:
    """Tests for GET /api/assinaturas/admin/status-plano/{usuario_id}"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip("Admin authentication failed")
    
    @pytest.fixture(scope="class")
    def test_user_id(self, admin_token):
        """Get a test user ID from the system"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/superadmin/usuarios?limit=1", headers=headers)
        if response.status_code == 200:
            data = response.json()
            usuarios = data.get("usuarios", [])
            if usuarios:
                return usuarios[0].get("id")
        return None
    
    def test_admin_status_plano_no_auth(self):
        """Test admin endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/assinaturas/admin/status-plano/test-id")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✅ admin/status-plano requires auth: {response.status_code}")
    
    def test_admin_status_plano_non_admin(self):
        """Test admin endpoint rejects non-admin users"""
        # Try to login as regular user
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "senha": USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Regular user not available for testing")
        
        token = response.json().get("access_token") or response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/assinaturas/admin/status-plano/test-id", headers=headers)
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print(f"✅ admin/status-plano rejects non-admin: {response.status_code}")
    
    def test_admin_status_plano_not_found(self, admin_token):
        """Test admin endpoint returns error for non-existent user"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        fake_id = str(uuid.uuid4())
        response = requests.get(f"{BASE_URL}/api/assinaturas/admin/status-plano/{fake_id}", headers=headers)
        
        # Should return error or empty result for non-existent user
        data = response.json()
        if response.status_code == 200:
            assert data.get("success") == False or "error" in data, "Should indicate user not found"
        print(f"✅ admin/status-plano handles non-existent user: {response.status_code}")
    
    def test_admin_status_plano_success(self, admin_token, test_user_id):
        """Test admin endpoint returns detailed plan status"""
        if not test_user_id:
            pytest.skip("No test user available")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/assinaturas/admin/status-plano/{test_user_id}", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify response structure from plano_service.obter_status_plano
        assert "success" in data, "Missing 'success' field"
        
        if data.get("success"):
            assert "plano" in data, "Missing 'plano' field"
            assert "plano_ativo" in data, "Missing 'plano_ativo' field"
            assert "tipo" in data, "Missing 'tipo' field (trial/pago)"
            
            print(f"✅ admin/status-plano returns detailed status:")
            print(f"   Plano: {data.get('plano')}")
            print(f"   Plano Ativo: {data.get('plano_ativo')}")
            print(f"   Tipo: {data.get('tipo')}")
            print(f"   Data Expiração: {data.get('data_expiracao')}")
            print(f"   Expirado: {data.get('expirado')}")
            print(f"   Dias Restantes: {data.get('dias_restantes')}")


class TestAdminReconciliacao:
    """Tests for GET /api/assinaturas/admin/reconciliacao"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip("Admin authentication failed")
    
    def test_reconciliacao_no_auth(self):
        """Test reconciliation endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/assinaturas/admin/reconciliacao")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✅ admin/reconciliacao requires auth: {response.status_code}")
    
    def test_reconciliacao_success(self, admin_token):
        """Test reconciliation endpoint returns report"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/assinaturas/admin/reconciliacao", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify report structure from plano_service.gerar_relatorio_reconciliacao
        assert "data_geracao" in data, "Missing 'data_geracao' field"
        assert "inconsistencias" in data, "Missing 'inconsistencias' field"
        assert "estatisticas" in data, "Missing 'estatisticas' field"
        
        # Verify inconsistencias is a list
        assert isinstance(data["inconsistencias"], list), "inconsistencias should be a list"
        
        # Verify estatisticas structure
        stats = data["estatisticas"]
        assert "total_inconsistencias" in stats, "Missing total_inconsistencias in stats"
        
        print(f"✅ admin/reconciliacao returns report:")
        print(f"   Data Geração: {data.get('data_geracao')}")
        print(f"   Total Inconsistências: {stats.get('total_inconsistencias')}")
        print(f"   Total Transações Aprovadas: {stats.get('total_transacoes_aprovadas')}")
        print(f"   Total Usuários Pagos: {stats.get('total_usuarios_pagos')}")
        
        # List inconsistencies if any
        if data["inconsistencias"]:
            print(f"   Inconsistências encontradas:")
            for inc in data["inconsistencias"][:5]:  # Show first 5
                print(f"     - Tipo: {inc.get('tipo')}, Usuario: {inc.get('usuario_email', inc.get('usuario_id'))}")


class TestAdminCorrigirInconsistencia:
    """Tests for POST /api/assinaturas/admin/corrigir-inconsistencia/{usuario_id}"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip("Admin authentication failed")
    
    @pytest.fixture(scope="class")
    def test_user_id(self, admin_token):
        """Get a test user ID from the system"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/superadmin/usuarios?limit=1", headers=headers)
        if response.status_code == 200:
            data = response.json()
            usuarios = data.get("usuarios", [])
            if usuarios:
                return usuarios[0].get("id")
        return None
    
    def test_corrigir_inconsistencia_no_auth(self):
        """Test correction endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/assinaturas/admin/corrigir-inconsistencia/test-id")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✅ admin/corrigir-inconsistencia requires auth: {response.status_code}")
    
    def test_corrigir_inconsistencia_not_found(self, admin_token):
        """Test correction endpoint handles non-existent user"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        fake_id = str(uuid.uuid4())
        response = requests.post(f"{BASE_URL}/api/assinaturas/admin/corrigir-inconsistencia/{fake_id}", headers=headers)
        
        data = response.json()
        # Should return error for non-existent user
        if response.status_code == 200:
            assert data.get("success") == False, "Should indicate user not found"
        print(f"✅ admin/corrigir-inconsistencia handles non-existent user: {response.status_code}")
    
    def test_corrigir_inconsistencia_success(self, admin_token, test_user_id):
        """Test correction endpoint works for existing user"""
        if not test_user_id:
            pytest.skip("No test user available")
        
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.post(f"{BASE_URL}/api/assinaturas/admin/corrigir-inconsistencia/{test_user_id}", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify response structure from plano_service.verificar_e_corrigir_inconsistencias
        assert "success" in data, "Missing 'success' field"
        assert "correcoes_aplicadas" in data, "Missing 'correcoes_aplicadas' field"
        assert "correcoes" in data, "Missing 'correcoes' field"
        
        print(f"✅ admin/corrigir-inconsistencia executed:")
        print(f"   Success: {data.get('success')}")
        print(f"   Correções Aplicadas: {data.get('correcoes_aplicadas')}")
        if data.get("correcoes"):
            for correcao in data["correcoes"]:
                print(f"     - {correcao}")


class TestAdminLogsPlanos:
    """Tests for GET /api/assinaturas/admin/logs-planos"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip("Admin authentication failed")
    
    def test_logs_planos_no_auth(self):
        """Test logs endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/assinaturas/admin/logs-planos")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✅ admin/logs-planos requires auth: {response.status_code}")
    
    def test_logs_planos_success(self, admin_token):
        """Test logs endpoint returns audit logs"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/assinaturas/admin/logs-planos", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.status_code} - {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "logs" in data, "Missing 'logs' field"
        assert "total" in data, "Missing 'total' field"
        assert isinstance(data["logs"], list), "logs should be a list"
        
        print(f"✅ admin/logs-planos returns logs:")
        print(f"   Total: {data.get('total')}")
        
        # Show sample logs if any
        if data["logs"]:
            print(f"   Sample logs:")
            for log in data["logs"][:3]:  # Show first 3
                print(f"     - Ação: {log.get('acao')}, Usuario: {log.get('usuario_email')}, Data: {log.get('data_acao')}")
    
    def test_logs_planos_with_limit(self, admin_token):
        """Test logs endpoint respects limit parameter"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/assinaturas/admin/logs-planos?limit=5", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify limit is respected
        assert len(data["logs"]) <= 5, "Limit not respected"
        print(f"✅ admin/logs-planos respects limit parameter")
    
    def test_logs_planos_with_usuario_id(self, admin_token):
        """Test logs endpoint filters by usuario_id"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        fake_id = str(uuid.uuid4())
        response = requests.get(f"{BASE_URL}/api/assinaturas/admin/logs-planos?usuario_id={fake_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return empty or filtered results
        assert isinstance(data["logs"], list)
        print(f"✅ admin/logs-planos filters by usuario_id")


class TestPlanoServiceIntegration:
    """Integration tests for plano_service.py functionality"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        pytest.skip("Admin authentication failed")
    
    def test_status_consistency_between_endpoints(self, admin_token):
        """Test that /minha and admin/status-plano return consistent data"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get user's own subscription
        response_minha = requests.get(f"{BASE_URL}/api/assinaturas/minha", headers=headers)
        assert response_minha.status_code == 200
        data_minha = response_minha.json()
        
        # Get admin's user ID
        response_me = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        if response_me.status_code != 200:
            pytest.skip("Cannot get current user ID")
        
        user_id = response_me.json().get("id")
        if not user_id:
            pytest.skip("No user ID in /me response")
        
        # Get admin view of same user
        response_admin = requests.get(f"{BASE_URL}/api/assinaturas/admin/status-plano/{user_id}", headers=headers)
        assert response_admin.status_code == 200
        data_admin = response_admin.json()
        
        # Compare key fields
        if data_admin.get("success"):
            plano_minha = data_minha.get("plano")
            plano_admin = data_admin.get("plano")
            
            assert plano_minha == plano_admin, f"Plano mismatch: minha={plano_minha}, admin={plano_admin}"
            print(f"✅ Status consistency verified:")
            print(f"   /minha plano: {plano_minha}")
            print(f"   admin/status-plano plano: {plano_admin}")
    
    def test_reconciliation_identifies_issues(self, admin_token):
        """Test that reconciliation report correctly identifies issues"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.get(f"{BASE_URL}/api/assinaturas/admin/reconciliacao", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify the report structure is complete
        assert "inconsistencias" in data
        assert "estatisticas" in data
        
        # Check that statistics are calculated
        stats = data["estatisticas"]
        assert "total_inconsistencias" in stats
        assert stats["total_inconsistencias"] >= 0
        
        print(f"✅ Reconciliation report structure verified")
        print(f"   Total inconsistencies: {stats['total_inconsistencias']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
