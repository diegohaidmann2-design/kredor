"""
Test Suite for Checkout and Gateway Configuration Features
Tests:
- Gateway configuration API (GET/PUT /api/checkout/config)
- Payment creation API (/api/checkout/criar-pagamento)
- Payment status API (/api/checkout/status/{payment_id})
- Payment history API (/api/checkout/historico)
- Admin-only access control for gateway config
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_CREDENTIALS = {"email": "admin@sgej.com", "senha": "admin123"}
USER_CREDENTIALS = {"email": "usuario@teste.com", "senha": "senha123"}


class TestAuth:
    """Authentication tests"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["usuario"]["perfil"] == "admin"
        print(f"✓ Admin login successful: {data['usuario']['email']}")
        return data["token"]
    
    def test_user_login(self):
        """Test regular user login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=USER_CREDENTIALS)
        # User may not exist, so we handle both cases
        if response.status_code == 200:
            data = response.json()
            assert "token" in data
            print(f"✓ User login successful: {data['usuario']['email']}")
            return data["token"]
        else:
            print(f"⚠ User login failed (user may not exist): {response.status_code}")
            return None


class TestGatewayConfig:
    """Gateway configuration API tests (admin only)"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture
    def user_token(self):
        """Get regular user token (if exists)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=USER_CREDENTIALS)
        if response.status_code == 200:
            return response.json()["token"]
        return None
    
    def test_get_gateway_config_admin(self, admin_token):
        """Test GET /api/checkout/config as admin"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/checkout/config", headers=headers)
        assert response.status_code == 200, f"Failed to get config: {response.text}"
        
        data = response.json()
        # Verify expected fields exist
        expected_fields = [
            "habilitado", "mercadopago_access_token", "mercadopago_public_key",
            "pagseguro_email", "pagseguro_token", "modo_gateway",
            "pix_habilitado", "cartao_habilitado", "rotacao_contador"
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"✓ GET /api/checkout/config - Admin access OK")
        print(f"  - habilitado: {data['habilitado']}")
        print(f"  - modo_gateway: {data['modo_gateway']}")
        print(f"  - pix_habilitado: {data['pix_habilitado']}")
        print(f"  - cartao_habilitado: {data['cartao_habilitado']}")
        return data
    
    def test_get_gateway_config_unauthorized(self):
        """Test GET /api/checkout/config without token"""
        response = requests.get(f"{BASE_URL}/api/checkout/config")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ GET /api/checkout/config - Unauthorized access blocked ({response.status_code})")
    
    def test_get_gateway_config_non_admin(self, user_token):
        """Test GET /api/checkout/config as non-admin user"""
        if user_token is None:
            pytest.skip("User does not exist")
        
        headers = {"Authorization": f"Bearer {user_token}"}
        response = requests.get(f"{BASE_URL}/api/checkout/config", headers=headers)
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print(f"✓ GET /api/checkout/config - Non-admin access blocked (403)")
    
    def test_put_gateway_config_admin(self, admin_token):
        """Test PUT /api/checkout/config as admin"""
        headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
        
        # First get current config
        get_response = requests.get(f"{BASE_URL}/api/checkout/config", headers=headers)
        current_config = get_response.json()
        
        # Update config
        new_config = {
            "habilitado": True,
            "mercadopago_access_token": "TEST_ACCESS_TOKEN_MP",
            "mercadopago_public_key": "TEST_PUBLIC_KEY_MP",
            "pagseguro_email": "test@pagseguro.com",
            "pagseguro_token": "TEST_TOKEN_PS",
            "modo_gateway": "mercadopago",
            "pix_habilitado": True,
            "cartao_habilitado": True,
            "rotacao_contador": 0
        }
        
        response = requests.put(f"{BASE_URL}/api/checkout/config", headers=headers, json=new_config)
        assert response.status_code == 200, f"Failed to update config: {response.text}"
        
        data = response.json()
        assert "message" in data
        print(f"✓ PUT /api/checkout/config - Config updated successfully")
        
        # Verify update persisted
        verify_response = requests.get(f"{BASE_URL}/api/checkout/config", headers=headers)
        verify_data = verify_response.json()
        assert verify_data["habilitado"] == True
        assert verify_data["modo_gateway"] == "mercadopago"
        assert verify_data["pix_habilitado"] == True
        assert verify_data["cartao_habilitado"] == True
        print(f"✓ Config update verified - persisted correctly")
    
    def test_put_gateway_config_unauthorized(self):
        """Test PUT /api/checkout/config without token"""
        new_config = {"habilitado": True, "modo_gateway": "mercadopago"}
        response = requests.put(f"{BASE_URL}/api/checkout/config", json=new_config)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ PUT /api/checkout/config - Unauthorized update blocked ({response.status_code})")
    
    def test_put_gateway_config_non_admin(self, user_token):
        """Test PUT /api/checkout/config as non-admin user"""
        if user_token is None:
            pytest.skip("User does not exist")
        
        headers = {"Authorization": f"Bearer {user_token}", "Content-Type": "application/json"}
        new_config = {"habilitado": True, "modo_gateway": "mercadopago"}
        response = requests.put(f"{BASE_URL}/api/checkout/config", headers=headers, json=new_config)
        assert response.status_code == 403, f"Expected 403 for non-admin, got {response.status_code}"
        print(f"✓ PUT /api/checkout/config - Non-admin update blocked (403)")
    
    def test_gateway_mode_options(self, admin_token):
        """Test different gateway mode options"""
        headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
        
        modes = ["mercadopago", "pagseguro", "rotacao"]
        for mode in modes:
            config = {
                "habilitado": True,
                "mercadopago_access_token": "TEST_TOKEN",
                "mercadopago_public_key": "",
                "pagseguro_email": "test@test.com",
                "pagseguro_token": "TEST_TOKEN",
                "modo_gateway": mode,
                "pix_habilitado": True,
                "cartao_habilitado": True,
                "rotacao_contador": 0
            }
            response = requests.put(f"{BASE_URL}/api/checkout/config", headers=headers, json=config)
            assert response.status_code == 200, f"Failed to set mode {mode}: {response.text}"
            
            # Verify
            verify = requests.get(f"{BASE_URL}/api/checkout/config", headers=headers)
            assert verify.json()["modo_gateway"] == mode
            print(f"✓ Gateway mode '{mode}' set successfully")


class TestCheckoutPayment:
    """Checkout payment creation tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_criar_pagamento_pix_without_gateway_keys(self, admin_token):
        """Test PIX payment creation (will fail without real gateway keys)"""
        headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
        
        # First enable gateway with test keys
        config = {
            "habilitado": True,
            "mercadopago_access_token": "TEST_INVALID_TOKEN",
            "mercadopago_public_key": "",
            "pagseguro_email": "",
            "pagseguro_token": "",
            "modo_gateway": "mercadopago",
            "pix_habilitado": True,
            "cartao_habilitado": True,
            "rotacao_contador": 0
        }
        requests.put(f"{BASE_URL}/api/checkout/config", headers=headers, json=config)
        
        # Try to create PIX payment
        payment_data = {
            "valor": 100.00,
            "descricao": "Test PIX Payment",
            "metodo": "pix",
            "nome": "Test User",
            "email": "test@test.com",
            "cpf": "12345678901"
        }
        
        response = requests.post(f"{BASE_URL}/api/checkout/criar-pagamento", headers=headers, json=payment_data)
        # Expected to fail with 400 because gateway keys are invalid
        # But the endpoint should be accessible and return proper error
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code} - {response.text}"
        
        if response.status_code == 400:
            data = response.json()
            assert "detail" in data
            print(f"✓ POST /api/checkout/criar-pagamento (PIX) - Returned expected error: {data['detail']}")
        else:
            print(f"✓ POST /api/checkout/criar-pagamento (PIX) - Payment created successfully")
    
    def test_criar_pagamento_cartao_without_gateway_keys(self, admin_token):
        """Test Card payment creation (will fail without real gateway keys)"""
        headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
        
        payment_data = {
            "valor": 150.00,
            "descricao": "Test Card Payment",
            "metodo": "cartao",
            "nome": "Test User",
            "email": "test@test.com",
            "cpf": "12345678901",
            "cartao_numero": "4111111111111111",
            "cartao_validade": "12/25",
            "cartao_cvv": "123",
            "cartao_titular": "TEST USER"
        }
        
        response = requests.post(f"{BASE_URL}/api/checkout/criar-pagamento", headers=headers, json=payment_data)
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code} - {response.text}"
        
        if response.status_code == 400:
            data = response.json()
            assert "detail" in data
            print(f"✓ POST /api/checkout/criar-pagamento (Cartão) - Returned expected error: {data['detail']}")
        else:
            print(f"✓ POST /api/checkout/criar-pagamento (Cartão) - Payment created successfully")
    
    def test_criar_pagamento_gateway_disabled(self, admin_token):
        """Test payment creation when gateway is disabled"""
        headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
        
        # Disable gateway
        config = {
            "habilitado": False,
            "mercadopago_access_token": "",
            "mercadopago_public_key": "",
            "pagseguro_email": "",
            "pagseguro_token": "",
            "modo_gateway": "mercadopago",
            "pix_habilitado": True,
            "cartao_habilitado": True,
            "rotacao_contador": 0
        }
        requests.put(f"{BASE_URL}/api/checkout/config", headers=headers, json=config)
        
        payment_data = {
            "valor": 100.00,
            "descricao": "Test Payment",
            "metodo": "pix",
            "nome": "Test User",
            "email": "test@test.com",
            "cpf": "12345678901"
        }
        
        response = requests.post(f"{BASE_URL}/api/checkout/criar-pagamento", headers=headers, json=payment_data)
        assert response.status_code == 400, f"Expected 400 when gateway disabled, got {response.status_code}"
        
        data = response.json()
        assert "Gateway de pagamento não habilitado" in data.get("detail", "")
        print(f"✓ Payment blocked when gateway disabled: {data['detail']}")
    
    def test_criar_pagamento_pix_disabled(self, admin_token):
        """Test PIX payment when PIX is disabled"""
        headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
        
        # Enable gateway but disable PIX
        config = {
            "habilitado": True,
            "mercadopago_access_token": "TEST_TOKEN",
            "mercadopago_public_key": "",
            "pagseguro_email": "",
            "pagseguro_token": "",
            "modo_gateway": "mercadopago",
            "pix_habilitado": False,
            "cartao_habilitado": True,
            "rotacao_contador": 0
        }
        requests.put(f"{BASE_URL}/api/checkout/config", headers=headers, json=config)
        
        payment_data = {
            "valor": 100.00,
            "descricao": "Test PIX Payment",
            "metodo": "pix",
            "nome": "Test User",
            "email": "test@test.com",
            "cpf": "12345678901"
        }
        
        response = requests.post(f"{BASE_URL}/api/checkout/criar-pagamento", headers=headers, json=payment_data)
        assert response.status_code == 400, f"Expected 400 when PIX disabled, got {response.status_code}"
        
        data = response.json()
        assert "PIX não habilitado" in data.get("detail", "")
        print(f"✓ PIX payment blocked when disabled: {data['detail']}")
    
    def test_criar_pagamento_cartao_disabled(self, admin_token):
        """Test Card payment when Card is disabled"""
        headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
        
        # Enable gateway but disable Card
        config = {
            "habilitado": True,
            "mercadopago_access_token": "TEST_TOKEN",
            "mercadopago_public_key": "",
            "pagseguro_email": "",
            "pagseguro_token": "",
            "modo_gateway": "mercadopago",
            "pix_habilitado": True,
            "cartao_habilitado": False,
            "rotacao_contador": 0
        }
        requests.put(f"{BASE_URL}/api/checkout/config", headers=headers, json=config)
        
        payment_data = {
            "valor": 100.00,
            "descricao": "Test Card Payment",
            "metodo": "cartao",
            "nome": "Test User",
            "email": "test@test.com",
            "cpf": "12345678901",
            "cartao_numero": "4111111111111111",
            "cartao_validade": "12/25",
            "cartao_cvv": "123"
        }
        
        response = requests.post(f"{BASE_URL}/api/checkout/criar-pagamento", headers=headers, json=payment_data)
        assert response.status_code == 400, f"Expected 400 when Card disabled, got {response.status_code}"
        
        data = response.json()
        assert "Cartão não habilitado" in data.get("detail", "")
        print(f"✓ Card payment blocked when disabled: {data['detail']}")
    
    def test_criar_pagamento_unauthorized(self):
        """Test payment creation without token"""
        payment_data = {
            "valor": 100.00,
            "descricao": "Test Payment",
            "metodo": "pix",
            "nome": "Test User",
            "email": "test@test.com",
            "cpf": "12345678901"
        }
        
        response = requests.post(f"{BASE_URL}/api/checkout/criar-pagamento", json=payment_data)
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Payment creation blocked without auth ({response.status_code})")


class TestCheckoutHistory:
    """Checkout payment history tests"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDENTIALS)
        assert response.status_code == 200
        return response.json()["token"]
    
    def test_historico_pagamentos(self, admin_token):
        """Test GET /api/checkout/historico"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/checkout/historico", headers=headers)
        assert response.status_code == 200, f"Failed to get history: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/checkout/historico - Returned {len(data)} payments")
    
    def test_historico_unauthorized(self):
        """Test GET /api/checkout/historico without token"""
        response = requests.get(f"{BASE_URL}/api/checkout/historico")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ GET /api/checkout/historico - Unauthorized access blocked ({response.status_code})")


class TestWebhooks:
    """Webhook endpoint tests"""
    
    def test_webhook_mercadopago(self):
        """Test POST /api/checkout/webhook/mercadopago"""
        webhook_data = {
            "type": "payment",
            "data": {"id": "12345"},
            "action": "payment.created"
        }
        
        response = requests.post(f"{BASE_URL}/api/checkout/webhook/mercadopago", json=webhook_data)
        # Webhook should accept the request even without valid payment
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        
        data = response.json()
        assert data.get("status") in ["ok", "error"]
        print(f"✓ POST /api/checkout/webhook/mercadopago - Webhook received")
    
    def test_webhook_pagseguro(self):
        """Test POST /api/checkout/webhook/pagseguro"""
        webhook_data = {
            "id": "CHAR_12345",
            "status": "PAID"
        }
        
        response = requests.post(f"{BASE_URL}/api/checkout/webhook/pagseguro", json=webhook_data)
        assert response.status_code == 200, f"Webhook failed: {response.text}"
        
        data = response.json()
        assert data.get("status") in ["ok", "error"]
        print(f"✓ POST /api/checkout/webhook/pagseguro - Webhook received")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
