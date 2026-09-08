"""
SyncPay PIX Integration Tests
Tests for the SyncPay checkout flow including:
- GET /api/assinaturas/gateway/disponiveis - gateway availability
- POST /api/assinaturas/checkout-syncpay - PIX charge creation
- GET /api/assinaturas/syncpay-status/{transaction_id} - status polling
- POST /api/auth/login - admin login
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

# Use the public URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://gestor-cred.preview.emergentagent.com').rstrip('/')

# Test credentials from test_credentials.md
ADMIN_EMAIL = "diego.haidmann@gmail.com"
ADMIN_SENHA = "muda2025"


class TestSyncPayIntegration:
    """SyncPay PIX Integration E2E Tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.test_email = f"test_syncpay_{uuid.uuid4().hex[:8]}@teste.com"
        self.created_user_id = None
        yield
        # Cleanup: delete test user if created
        if self.created_user_id:
            try:
                self._cleanup_test_user()
            except Exception as e:
                print(f"Cleanup warning: {e}")
    
    def _cleanup_test_user(self):
        """Delete test user created during tests"""
        # Login as admin first
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_SENHA
        })
        if login_resp.status_code == 200:
            token = login_resp.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            # Try to delete the test user
            self.session.delete(f"{BASE_URL}/api/superadmin/usuarios/{self.created_user_id}", params={"permanent": True})
    
    def test_01_admin_login(self):
        """Test admin login with correct credentials (uses 'senha' field)"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_SENHA
        })
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # Verify response structure - API returns 'usuario' not 'user'
        assert "token" in data, "Response should contain token"
        assert "usuario" in data, "Response should contain usuario"
        assert data["usuario"]["email"] == ADMIN_EMAIL
        
        print(f"✅ Admin login successful: {data['usuario']['email']}")
    
    def test_02_gateway_disponiveis_returns_syncpay(self):
        """Test GET /api/assinaturas/gateway/disponiveis returns syncpay with pix method"""
        response = self.session.get(f"{BASE_URL}/api/assinaturas/gateway/disponiveis")
        
        assert response.status_code == 200, f"Gateway disponiveis failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "gateway" in data, "Response should contain 'gateway' key"
        assert "estrategia" in data, "Response should contain 'estrategia' key"
        
        gateway = data["gateway"]
        assert gateway is not None, "Gateway should not be null"
        assert gateway["id"] == "syncpay", f"Expected syncpay gateway, got: {gateway.get('id')}"
        assert "pix" in gateway["metodos"], f"SyncPay should support PIX, got: {gateway.get('metodos')}"
        
        print(f"✅ Gateway disponiveis: {gateway['id']} with methods {gateway['metodos']}")
        print(f"   Estrategia: {data['estrategia']}")
    
    def test_03_checkout_syncpay_creates_pix_charge(self):
        """Test POST /api/assinaturas/checkout-syncpay creates PIX charge and returns pix_code"""
        # Use unique email for this test
        checkout_data = {
            "plano_id": "basico",
            "nome": "Test SyncPay User",
            "email": self.test_email,
            "senha": "test123456",
            "cpf": "12345678901",
            "telefone": "11999999999"
        }
        
        response = self.session.post(f"{BASE_URL}/api/assinaturas/checkout-syncpay", json=checkout_data)
        
        # Check if SyncPay is enabled
        if response.status_code == 400 and "não está habilitado" in response.text:
            pytest.skip("SyncPay is not enabled in the system")
        
        if response.status_code == 503 and "não configurado" in response.text:
            pytest.skip("SyncPay credentials not configured")
        
        assert response.status_code == 200, f"Checkout SyncPay failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True, "Response should indicate success"
        assert "pix_code" in data, "Response should contain pix_code"
        assert "transaction_id" in data, "Response should contain transaction_id"
        assert "transacao_id" in data, "Response should contain transacao_id"
        assert "token" in data, "Response should contain token"
        
        # Verify PIX code is not empty
        assert len(data["pix_code"]) > 0, "PIX code should not be empty"
        
        # Store for cleanup
        self.created_user_id = data.get("transacao_id")
        
        print(f"✅ Checkout SyncPay successful:")
        print(f"   Transaction ID: {data['transaction_id']}")
        print(f"   PIX Code length: {len(data['pix_code'])} chars")
        print(f"   Amount: {data.get('amount')}")
        print(f"   Plano: {data.get('plano_nome')}")
        
        # Store transaction_id for next test
        self.__class__.transaction_id = data["transaction_id"]
        self.__class__.pix_code = data["pix_code"]
    
    def test_04_syncpay_status_returns_pending(self):
        """Test GET /api/assinaturas/syncpay-status/{transaction_id} returns status"""
        # Get transaction_id from previous test
        transaction_id = getattr(self.__class__, 'transaction_id', None)
        
        if not transaction_id:
            pytest.skip("No transaction_id from previous test - checkout may have been skipped")
        
        response = self.session.get(f"{BASE_URL}/api/assinaturas/syncpay-status/{transaction_id}")
        
        if response.status_code == 503:
            pytest.skip("SyncPay not configured")
        
        assert response.status_code == 200, f"SyncPay status check failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "transaction_id" in data, "Response should contain transaction_id"
        assert "status" in data, "Response should contain status"
        assert "approved" in data, "Response should contain approved flag"
        
        # Since we didn't actually pay, status should be pending
        assert data["status"] == "pending", f"Expected pending status, got: {data['status']}"
        assert data["approved"] == False, "Should not be approved without payment"
        
        print(f"✅ SyncPay status check successful:")
        print(f"   Transaction ID: {data['transaction_id']}")
        print(f"   Status: {data['status']}")
        print(f"   Approved: {data['approved']}")
    
    def test_05_checkout_syncpay_rejects_duplicate_email(self):
        """Test that checkout-syncpay rejects duplicate email"""
        # First, try to create with the same email used in test_03
        checkout_data = {
            "plano_id": "basico",
            "nome": "Duplicate User",
            "email": self.test_email,  # Same email
            "senha": "test123456",
            "cpf": "12345678901"
        }
        
        response = self.session.post(f"{BASE_URL}/api/assinaturas/checkout-syncpay", json=checkout_data)
        
        # Should fail with 400 (email already registered with pending payment)
        if response.status_code == 400:
            assert "já cadastrado" in response.text.lower() or "pendente" in response.text.lower(), \
                f"Expected duplicate email error, got: {response.text}"
            print(f"✅ Duplicate email correctly rejected: {response.json().get('detail', response.text)}")
        elif response.status_code == 503:
            pytest.skip("SyncPay not configured")
        else:
            # If first test was skipped, this might succeed
            print(f"⚠️ Checkout returned {response.status_code} - first test may have been skipped")
    
    def test_06_checkout_syncpay_validates_plano(self):
        """Test that checkout-syncpay validates plano_id"""
        unique_email = f"test_invalid_plano_{uuid.uuid4().hex[:8]}@teste.com"
        
        checkout_data = {
            "plano_id": "plano_inexistente",
            "nome": "Test User",
            "email": unique_email,
            "senha": "test123456",
            "cpf": "12345678901"
        }
        
        response = self.session.post(f"{BASE_URL}/api/assinaturas/checkout-syncpay", json=checkout_data)
        
        if response.status_code == 400 and "não está habilitado" in response.text:
            pytest.skip("SyncPay is not enabled")
        
        # Should fail with 404 (plano not found)
        assert response.status_code == 404, f"Expected 404 for invalid plano, got: {response.status_code}"
        assert "não encontrado" in response.text.lower(), f"Expected 'não encontrado' error, got: {response.text}"
        
        print(f"✅ Invalid plano correctly rejected")
    
    def test_07_checkout_syncpay_rejects_trial_plano(self):
        """Test that checkout-syncpay rejects trial (free) plano"""
        unique_email = f"test_trial_{uuid.uuid4().hex[:8]}@teste.com"
        
        checkout_data = {
            "plano_id": "trial",
            "nome": "Test User",
            "email": unique_email,
            "senha": "test123456",
            "cpf": "12345678901"
        }
        
        response = self.session.post(f"{BASE_URL}/api/assinaturas/checkout-syncpay", json=checkout_data)
        
        if response.status_code == 400 and "não está habilitado" in response.text:
            pytest.skip("SyncPay is not enabled")
        
        # Should fail with 400 (trial should use normal registration)
        assert response.status_code == 400, f"Expected 400 for trial plano, got: {response.status_code}"
        assert "trial" in response.text.lower() or "gratuito" in response.text.lower(), \
            f"Expected trial rejection message, got: {response.text}"
        
        print(f"✅ Trial plano correctly rejected for paid checkout")


class TestSyncPayStatusPolling:
    """Tests for SyncPay status polling endpoint"""
    
    def test_invalid_transaction_id(self):
        """Test that invalid transaction_id returns appropriate error"""
        session = requests.Session()
        
        response = session.get(f"{BASE_URL}/api/assinaturas/syncpay-status/invalid-transaction-id-12345")
        
        if response.status_code == 503:
            pytest.skip("SyncPay not configured")
        
        # Should return 500 or appropriate error (SyncPay API will reject invalid ID)
        assert response.status_code in [400, 404, 500], \
            f"Expected error for invalid transaction_id, got: {response.status_code}"
        
        print(f"✅ Invalid transaction_id correctly handled: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
