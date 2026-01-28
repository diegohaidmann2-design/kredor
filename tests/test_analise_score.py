"""
Test Suite for Análise e Score de Clientes Feature
Tests the /api/analise/* endpoints for score calculation and client analysis
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@sgej.com"
ADMIN_PASSWORD = "admin123"


class TestAuthAndAnalise:
    """Test authentication and Análise endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for admin user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "senha": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, f"No access_token in response: {data}"
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    # ==================== AUTH TESTS ====================
    
    def test_login_success(self):
        """Test login with valid admin credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "senha": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "usuario" in data  # API returns 'usuario' not 'user'
        print(f"SUCCESS: Login successful, user: {data['usuario'].get('nome', 'N/A')}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "wrong@email.com", "senha": "wrongpassword"}
        )
        assert response.status_code in [401, 400, 404]
        print(f"SUCCESS: Invalid login rejected with status {response.status_code}")
    
    def test_refresh_token(self):
        """Test refresh token functionality"""
        # First login to get tokens
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "senha": ADMIN_PASSWORD}
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        
        # Check if refresh_token exists
        assert "refresh_token" in tokens, "No refresh_token in login response"
        print(f"SUCCESS: Refresh token received: {tokens['refresh_token'][:20]}...")
    
    # ==================== ANÁLISE DASHBOARD TESTS ====================
    
    def test_analise_dashboard_unauthorized(self):
        """Test dashboard without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/analise/dashboard")
        assert response.status_code in [401, 403]
        print(f"SUCCESS: Dashboard unauthorized access rejected with {response.status_code}")
    
    def test_analise_dashboard_success(self, auth_headers):
        """Test dashboard with valid auth"""
        response = requests.get(
            f"{BASE_URL}/api/analise/dashboard",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "resumo" in data
        assert "distribuicao_classificacao" in data
        assert "score_medio" in data
        assert "tendencias" in data
        assert "evolucao_mensal" in data
        
        # Validate resumo structure
        resumo = data["resumo"]
        assert "total_clientes" in resumo
        assert "bons_pagadores" in resumo
        assert "pagadores_irregulares" in resumo
        assert "inadimplentes" in resumo
        
        # Validate distribuicao structure
        dist = data["distribuicao_classificacao"]
        assert all(k in dist for k in ["A", "B", "C", "D", "E"])
        
        print(f"SUCCESS: Dashboard loaded - {resumo['total_clientes']} clientes, score médio: {data['score_medio']}")
    
    def test_analise_dashboard_with_period(self, auth_headers):
        """Test dashboard with different periods"""
        periods = ["30d", "90d", "1y", "all"]
        
        for period in periods:
            response = requests.get(
                f"{BASE_URL}/api/analise/dashboard",
                headers=auth_headers,
                params={"periodo": period}
            )
            assert response.status_code == 200, f"Failed for period {period}"
            print(f"SUCCESS: Dashboard loaded for period {period}")
    
    # ==================== ANÁLISE CLIENTES TESTS ====================
    
    def test_analise_clientes_unauthorized(self):
        """Test clientes list without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/analise/clientes")
        assert response.status_code in [401, 403]
        print(f"SUCCESS: Clientes list unauthorized access rejected")
    
    def test_analise_clientes_success(self, auth_headers):
        """Test clientes list with valid auth"""
        response = requests.get(
            f"{BASE_URL}/api/analise/clientes",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert "clientes" in data
        
        # If there are clients, validate structure
        if data["clientes"]:
            cliente = data["clientes"][0]
            assert "id" in cliente
            assert "nome" in cliente
            assert "score" in cliente
            assert "classificacao" in cliente
            print(f"SUCCESS: Clientes list loaded - {data['total']} clientes, first: {cliente['nome']}")
        else:
            print(f"SUCCESS: Clientes list loaded - 0 clientes (empty)")
    
    def test_analise_clientes_filter_classificacao(self, auth_headers):
        """Test clientes list with classification filter"""
        for classificacao in ["A", "B", "C", "D", "E"]:
            response = requests.get(
                f"{BASE_URL}/api/analise/clientes",
                headers=auth_headers,
                params={"classificacao": classificacao}
            )
            assert response.status_code == 200
            data = response.json()
            
            # All returned clients should have the filtered classification
            for cliente in data["clientes"]:
                assert cliente["classificacao"] == classificacao, f"Expected {classificacao}, got {cliente['classificacao']}"
            
            print(f"SUCCESS: Filter by classificacao {classificacao} - {len(data['clientes'])} clientes")
    
    def test_analise_clientes_filter_score_range(self, auth_headers):
        """Test clientes list with score range filter"""
        response = requests.get(
            f"{BASE_URL}/api/analise/clientes",
            headers=auth_headers,
            params={"score_min": 50, "score_max": 80}
        )
        assert response.status_code == 200
        data = response.json()
        
        # All returned clients should be within score range
        for cliente in data["clientes"]:
            assert 50 <= cliente["score"] <= 80, f"Score {cliente['score']} out of range"
        
        print(f"SUCCESS: Filter by score range 50-80 - {len(data['clientes'])} clientes")
    
    def test_analise_clientes_ordering(self, auth_headers):
        """Test clientes list ordering"""
        # Test score descending
        response = requests.get(
            f"{BASE_URL}/api/analise/clientes",
            headers=auth_headers,
            params={"ordenar": "score_desc"}
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data["clientes"]) > 1:
            scores = [c["score"] for c in data["clientes"]]
            assert scores == sorted(scores, reverse=True), "Scores not in descending order"
            print(f"SUCCESS: Ordering score_desc works correctly")
        
        # Test score ascending
        response = requests.get(
            f"{BASE_URL}/api/analise/clientes",
            headers=auth_headers,
            params={"ordenar": "score_asc"}
        )
        assert response.status_code == 200
        data = response.json()
        
        if len(data["clientes"]) > 1:
            scores = [c["score"] for c in data["clientes"]]
            assert scores == sorted(scores), "Scores not in ascending order"
            print(f"SUCCESS: Ordering score_asc works correctly")
    
    # ==================== SCORE DETAILS TESTS ====================
    
    def test_score_details_unauthorized(self):
        """Test score details without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/analise/score/fake-id")
        assert response.status_code in [401, 403]
        print(f"SUCCESS: Score details unauthorized access rejected")
    
    def test_score_details_not_found(self, auth_headers):
        """Test score details for non-existent client"""
        response = requests.get(
            f"{BASE_URL}/api/analise/score/non-existent-id",
            headers=auth_headers
        )
        assert response.status_code == 404
        print(f"SUCCESS: Score details for non-existent client returns 404")
    
    def test_score_details_success(self, auth_headers):
        """Test score details for existing client"""
        # First get a client ID
        clientes_response = requests.get(
            f"{BASE_URL}/api/analise/clientes",
            headers=auth_headers
        )
        assert clientes_response.status_code == 200
        clientes = clientes_response.json()["clientes"]
        
        if not clientes:
            pytest.skip("No clients available for score details test")
        
        cliente_id = clientes[0]["id"]
        
        # Get score details
        response = requests.get(
            f"{BASE_URL}/api/analise/score/{cliente_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "cliente" in data
        assert "score" in data
        assert "classificacao" in data
        assert "componentes" in data
        assert "metricas" in data
        assert "recomendacao" in data
        
        # Validate componentes structure
        componentes = data["componentes"]
        expected_components = ["pontualidade", "atrasos", "valor_pago", "tempo_relacionamento", "historico_recente"]
        for comp in expected_components:
            assert comp in componentes, f"Missing component: {comp}"
            assert "pontos" in componentes[comp]
            assert "maximo" in componentes[comp]
            assert "percentual" in componentes[comp]
        
        # Validate metricas structure
        metricas = data["metricas"]
        assert "total_emprestimos" in metricas
        assert "emprestimos_quitados" in metricas
        assert "taxa_pontualidade" in metricas
        
        print(f"SUCCESS: Score details loaded for {data['cliente']['nome']} - Score: {data['score']}, Class: {data['classificacao']}")
    
    # ==================== RECALCULAR SCORE TESTS ====================
    
    def test_recalcular_score_unauthorized(self):
        """Test recalcular without auth returns 401"""
        response = requests.post(f"{BASE_URL}/api/analise/recalcular/fake-id")
        assert response.status_code in [401, 403]
        print(f"SUCCESS: Recalcular unauthorized access rejected")
    
    def test_recalcular_score_not_found(self, auth_headers):
        """Test recalcular for non-existent client"""
        response = requests.post(
            f"{BASE_URL}/api/analise/recalcular/non-existent-id",
            headers=auth_headers
        )
        assert response.status_code == 404
        print(f"SUCCESS: Recalcular for non-existent client returns 404")
    
    def test_recalcular_score_success(self, auth_headers):
        """Test recalcular for existing client"""
        # First get a client ID
        clientes_response = requests.get(
            f"{BASE_URL}/api/analise/clientes",
            headers=auth_headers
        )
        assert clientes_response.status_code == 200
        clientes = clientes_response.json()["clientes"]
        
        if not clientes:
            pytest.skip("No clients available for recalcular test")
        
        cliente_id = clientes[0]["id"]
        
        # Recalcular score
        response = requests.post(
            f"{BASE_URL}/api/analise/recalcular/{cliente_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "message" in data
        assert "score_anterior" in data
        assert "score_novo" in data
        assert "classificacao" in data
        assert "variacao" in data
        
        print(f"SUCCESS: Score recalculado - Anterior: {data['score_anterior']}, Novo: {data['score_novo']}, Variação: {data['variacao']}")


class TestClientesPage:
    """Test /api/clientes endpoints for modal functionality"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for admin user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "senha": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_clientes_list(self, auth_headers):
        """Test clientes list endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/clientes",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"SUCCESS: Clientes list loaded - {len(data)} clientes")
    
    def test_cliente_details(self, auth_headers):
        """Test cliente details endpoint"""
        # First get a client ID
        clientes_response = requests.get(
            f"{BASE_URL}/api/clientes",
            headers=auth_headers
        )
        assert clientes_response.status_code == 200
        clientes = clientes_response.json()
        
        if not clientes:
            pytest.skip("No clients available for details test")
        
        cliente_id = clientes[0]["id"]
        
        # Get client details
        response = requests.get(
            f"{BASE_URL}/api/clientes/{cliente_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Validate structure
        assert "id" in data
        assert "nome" in data
        assert "cpf_cnpj" in data
        assert "email" in data
        
        print(f"SUCCESS: Cliente details loaded - {data['nome']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
