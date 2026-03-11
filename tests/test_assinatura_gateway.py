"""
Test Suite for Assinatura Gateway (Stripe + Mercado Pago) Feature
Tests the dual payment gateway system for subscriptions
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://build-go.preview.emergentagent.com')


class TestAssinaturaGatewayPublicEndpoints:
    """Tests for public endpoints (no auth required)"""
    
    def test_listar_gateways_disponiveis(self):
        """GET /api/assinaturas/gateway/disponiveis - should return available gateways"""
        response = requests.get(f"{BASE_URL}/api/assinaturas/gateway/disponiveis")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "gateways" in data
        assert "estrategia" in data
        assert isinstance(data["gateways"], list)
        
        # With default config, Stripe should be available
        if len(data["gateways"]) > 0:
            gateway = data["gateways"][0]
            assert "id" in gateway
            assert "nome" in gateway
            assert "descricao" in gateway
            assert "metodos" in gateway
            assert "icone" in gateway
    
    def test_listar_planos(self):
        """GET /api/assinaturas/planos - should return subscription plans"""
        response = requests.get(f"{BASE_URL}/api/assinaturas/planos")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 4  # trial, basico, profissional, enterprise
        
        # Verify plan structure
        for plano in data:
            assert "id" in plano
            assert "nome" in plano
            assert "preco" in plano
            assert "intervalo" in plano
            assert "recursos" in plano
            assert "clientes" in plano
            assert "emprestimos" in plano


class TestAssinaturaGatewayAdminEndpoints:
    """Tests for admin-only endpoints"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@sgej.com", "senha": "admin123"}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    @pytest.fixture
    def auth_headers(self, admin_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {admin_token}"}
    
    def test_obter_gateway_config_sem_auth(self):
        """GET /api/assinaturas/gateway/config without auth should fail"""
        response = requests.get(f"{BASE_URL}/api/assinaturas/gateway/config")
        assert response.status_code in [401, 403]
    
    def test_obter_gateway_config_com_auth(self, auth_headers):
        """GET /api/assinaturas/gateway/config with admin auth should work"""
        response = requests.get(
            f"{BASE_URL}/api/assinaturas/gateway/config",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify config structure
        assert "estrategia" in data
        assert "stripe_habilitado" in data
        assert "mercadopago_habilitado" in data
        assert "mp_cartao_habilitado" in data
        assert "mp_pix_habilitado" in data
        assert "gateway_primario" in data
        
        # Verify estrategia is valid
        assert data["estrategia"] in ["stripe_only", "mercadopago_only", "rotacao", "fallback"]
    
    def test_atualizar_gateway_config_sem_auth(self):
        """PUT /api/assinaturas/gateway/config without auth should fail"""
        response = requests.put(
            f"{BASE_URL}/api/assinaturas/gateway/config",
            json={"estrategia": "stripe_only"}
        )
        assert response.status_code in [401, 403]
    
    def test_atualizar_gateway_config_com_auth(self, auth_headers):
        """PUT /api/assinaturas/gateway/config with admin auth should work"""
        # First get current config
        get_response = requests.get(
            f"{BASE_URL}/api/assinaturas/gateway/config",
            headers=auth_headers
        )
        original_config = get_response.json()
        
        # Update config
        new_config = {
            "estrategia": "stripe_only",
            "stripe_habilitado": True,
            "stripe_api_key": "",
            "mercadopago_habilitado": False,
            "mercadopago_access_token": "",
            "mercadopago_public_key": "",
            "mp_cartao_habilitado": True,
            "mp_pix_habilitado": True,
            "rotacao_contador": 0,
            "gateway_primario": "stripe"
        }
        
        response = requests.put(
            f"{BASE_URL}/api/assinaturas/gateway/config",
            headers=auth_headers,
            json=new_config
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
        # Verify config was updated
        verify_response = requests.get(
            f"{BASE_URL}/api/assinaturas/gateway/config",
            headers=auth_headers
        )
        assert verify_response.status_code == 200
        updated_config = verify_response.json()
        assert updated_config["estrategia"] == "stripe_only"


class TestCheckoutMercadoPago:
    """Tests for Mercado Pago checkout endpoint"""
    
    def test_checkout_mercadopago_quando_desabilitado(self):
        """POST /api/assinaturas/checkout-mercadopago should fail when MP is disabled"""
        response = requests.post(
            f"{BASE_URL}/api/assinaturas/checkout-mercadopago",
            json={
                "plano_id": "basico",
                "nome": "Test User",
                "email": f"test_mp_{os.urandom(4).hex()}@test.com",
                "senha": "test123456",
                "origin_url": "https://build-go.preview.emergentagent.com",
                "metodo_pagamento": "cartao"
            }
        )
        
        # Should return 400 because MP is disabled by default
        assert response.status_code == 400
        data = response.json()
        assert "Mercado Pago não está habilitado" in data.get("detail", "")
    
    def test_checkout_mercadopago_plano_invalido(self):
        """POST /api/assinaturas/checkout-mercadopago with invalid plan should fail"""
        response = requests.post(
            f"{BASE_URL}/api/assinaturas/checkout-mercadopago",
            json={
                "plano_id": "plano_inexistente",
                "nome": "Test User",
                "email": f"test_mp_{os.urandom(4).hex()}@test.com",
                "senha": "test123456",
                "origin_url": "https://build-go.preview.emergentagent.com",
                "metodo_pagamento": "cartao"
            }
        )
        
        # Should return 400 (MP disabled) or 404 (plan not found)
        assert response.status_code in [400, 404]


class TestCheckoutPublicoStripe:
    """Tests for Stripe public checkout endpoint"""
    
    def test_checkout_publico_email_duplicado(self):
        """POST /api/assinaturas/checkout-publico with existing email should fail"""
        # Use admin email which already exists
        response = requests.post(
            f"{BASE_URL}/api/assinaturas/checkout-publico",
            json={
                "plano_id": "basico",
                "nome": "Test User",
                "email": "admin@sgej.com",
                "senha": "test123456",
                "origin_url": "https://build-go.preview.emergentagent.com"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Email já cadastrado" in data.get("detail", "")
    
    def test_checkout_publico_plano_trial(self):
        """POST /api/assinaturas/checkout-publico with trial plan should fail"""
        response = requests.post(
            f"{BASE_URL}/api/assinaturas/checkout-publico",
            json={
                "plano_id": "trial",
                "nome": "Test User",
                "email": f"test_trial_{os.urandom(4).hex()}@test.com",
                "senha": "test123456",
                "origin_url": "https://build-go.preview.emergentagent.com"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "trial" in data.get("detail", "").lower()
    
    def test_checkout_publico_plano_invalido(self):
        """POST /api/assinaturas/checkout-publico with invalid plan should fail"""
        response = requests.post(
            f"{BASE_URL}/api/assinaturas/checkout-publico",
            json={
                "plano_id": "plano_inexistente",
                "nome": "Test User",
                "email": f"test_invalid_{os.urandom(4).hex()}@test.com",
                "senha": "test123456",
                "origin_url": "https://build-go.preview.emergentagent.com"
            }
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "Plano não encontrado" in data.get("detail", "")


class TestGatewayEstrategias:
    """Tests for different gateway strategies"""
    
    @pytest.fixture
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@sgej.com", "senha": "admin123"}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Admin login failed")
    
    @pytest.fixture
    def auth_headers(self, admin_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {admin_token}"}
    
    def test_estrategia_stripe_only(self, auth_headers):
        """Test stripe_only strategy shows only Stripe gateway"""
        # Set strategy to stripe_only
        requests.put(
            f"{BASE_URL}/api/assinaturas/gateway/config",
            headers=auth_headers,
            json={
                "estrategia": "stripe_only",
                "stripe_habilitado": True,
                "mercadopago_habilitado": False,
                "mp_cartao_habilitado": True,
                "mp_pix_habilitado": True,
                "gateway_primario": "stripe"
            }
        )
        
        # Check available gateways
        response = requests.get(f"{BASE_URL}/api/assinaturas/gateway/disponiveis")
        assert response.status_code == 200
        data = response.json()
        
        assert data["estrategia"] == "stripe_only"
        gateway_ids = [g["id"] for g in data["gateways"]]
        assert "stripe" in gateway_ids
        assert "mercadopago" not in gateway_ids
    
    def test_estrategia_mercadopago_only(self, auth_headers):
        """Test mercadopago_only strategy shows only MP gateway when enabled"""
        # Set strategy to mercadopago_only with MP enabled
        requests.put(
            f"{BASE_URL}/api/assinaturas/gateway/config",
            headers=auth_headers,
            json={
                "estrategia": "mercadopago_only",
                "stripe_habilitado": False,
                "mercadopago_habilitado": True,
                "mercadopago_access_token": "test_token",
                "mercadopago_public_key": "test_key",
                "mp_cartao_habilitado": True,
                "mp_pix_habilitado": True,
                "gateway_primario": "mercadopago"
            }
        )
        
        # Check available gateways
        response = requests.get(f"{BASE_URL}/api/assinaturas/gateway/disponiveis")
        assert response.status_code == 200
        data = response.json()
        
        assert data["estrategia"] == "mercadopago_only"
        gateway_ids = [g["id"] for g in data["gateways"]]
        assert "mercadopago" in gateway_ids
        
        # Reset to stripe_only
        requests.put(
            f"{BASE_URL}/api/assinaturas/gateway/config",
            headers=auth_headers,
            json={
                "estrategia": "stripe_only",
                "stripe_habilitado": True,
                "mercadopago_habilitado": False,
                "gateway_primario": "stripe"
            }
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
