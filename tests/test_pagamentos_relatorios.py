"""
Backend API Tests for SGEJ - Pagamentos and Relatórios Features
Tests for:
- POST /api/relatorios/gerar - Report generation (PDF/Excel)
- GET /api/parcelas/pendentes - Pending installments
- POST /api/pagamentos - Payment registration
- GET /api/pagamentos - Payment listing
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests to get token for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@sgej.com",
            "senha": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        return data["token"]
    
    def test_login_success(self):
        """Test successful login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@sgej.com",
            "senha": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "usuario" in data
        assert data["usuario"]["email"] == "admin@sgej.com"


class TestParcelasPendentes:
    """Tests for GET /api/parcelas/pendentes endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@sgej.com",
            "senha": "admin123"
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_listar_parcelas_pendentes_success(self, auth_headers):
        """Test listing pending installments"""
        response = requests.get(f"{BASE_URL}/api/parcelas/pendentes", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # If there are pending installments, verify structure
        if len(data) > 0:
            parcela = data[0]
            assert "id" in parcela
            assert "emprestimo_id" in parcela
            assert "numero_parcela" in parcela
            assert "data_vencimento" in parcela
            assert "valor_total" in parcela
            assert "status" in parcela
            # Enriched fields
            assert "cliente_nome" in parcela
            assert "valor_emprestimo" in parcela
            print(f"Found {len(data)} pending installments")
    
    def test_parcelas_pendentes_unauthorized(self):
        """Test that endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/parcelas/pendentes")
        assert response.status_code in [401, 403]


class TestRelatorios:
    """Tests for POST /api/relatorios/gerar endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@sgej.com",
            "senha": "admin123"
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    # PDF Report Tests
    def test_relatorio_emprestimos_pdf(self, auth_headers):
        """Test generating loans report in PDF format"""
        response = requests.post(
            f"{BASE_URL}/api/relatorios/gerar",
            headers=auth_headers,
            json={
                "tipo": "emprestimos",
                "formato": "pdf",
                "periodo": "mes_atual"
            }
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        assert len(response.content) > 0
        print(f"PDF emprestimos size: {len(response.content)} bytes")
    
    def test_relatorio_pagamentos_pdf(self, auth_headers):
        """Test generating payments report in PDF format"""
        response = requests.post(
            f"{BASE_URL}/api/relatorios/gerar",
            headers=auth_headers,
            json={
                "tipo": "pagamentos",
                "formato": "pdf",
                "periodo": "mes_atual"
            }
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        assert len(response.content) > 0
        print(f"PDF pagamentos size: {len(response.content)} bytes")
    
    def test_relatorio_clientes_pdf(self, auth_headers):
        """Test generating clients report in PDF format"""
        response = requests.post(
            f"{BASE_URL}/api/relatorios/gerar",
            headers=auth_headers,
            json={
                "tipo": "clientes",
                "formato": "pdf",
                "periodo": "mes_atual"
            }
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        assert len(response.content) > 0
        print(f"PDF clientes size: {len(response.content)} bytes")
    
    def test_relatorio_inadimplencia_pdf(self, auth_headers):
        """Test generating delinquency report in PDF format"""
        response = requests.post(
            f"{BASE_URL}/api/relatorios/gerar",
            headers=auth_headers,
            json={
                "tipo": "inadimplencia",
                "formato": "pdf",
                "periodo": "mes_atual"
            }
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        assert len(response.content) > 0
        print(f"PDF inadimplencia size: {len(response.content)} bytes")
    
    def test_relatorio_fluxo_caixa_pdf(self, auth_headers):
        """Test generating cash flow report in PDF format"""
        response = requests.post(
            f"{BASE_URL}/api/relatorios/gerar",
            headers=auth_headers,
            json={
                "tipo": "fluxo_caixa",
                "formato": "pdf",
                "periodo": "mes_atual"
            }
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        assert len(response.content) > 0
        print(f"PDF fluxo_caixa size: {len(response.content)} bytes")
    
    # Excel Report Tests
    def test_relatorio_emprestimos_excel(self, auth_headers):
        """Test generating loans report in Excel format"""
        response = requests.post(
            f"{BASE_URL}/api/relatorios/gerar",
            headers=auth_headers,
            json={
                "tipo": "emprestimos",
                "formato": "excel",
                "periodo": "mes_atual"
            }
        )
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers.get("content-type", "")
        assert len(response.content) > 0
        print(f"Excel emprestimos size: {len(response.content)} bytes")
    
    def test_relatorio_pagamentos_excel(self, auth_headers):
        """Test generating payments report in Excel format"""
        response = requests.post(
            f"{BASE_URL}/api/relatorios/gerar",
            headers=auth_headers,
            json={
                "tipo": "pagamentos",
                "formato": "excel",
                "periodo": "mes_atual"
            }
        )
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers.get("content-type", "")
        assert len(response.content) > 0
        print(f"Excel pagamentos size: {len(response.content)} bytes")
    
    def test_relatorio_clientes_excel(self, auth_headers):
        """Test generating clients report in Excel format"""
        response = requests.post(
            f"{BASE_URL}/api/relatorios/gerar",
            headers=auth_headers,
            json={
                "tipo": "clientes",
                "formato": "excel",
                "periodo": "mes_atual"
            }
        )
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers.get("content-type", "")
        assert len(response.content) > 0
        print(f"Excel clientes size: {len(response.content)} bytes")
    
    def test_relatorio_inadimplencia_excel(self, auth_headers):
        """Test generating delinquency report in Excel format"""
        response = requests.post(
            f"{BASE_URL}/api/relatorios/gerar",
            headers=auth_headers,
            json={
                "tipo": "inadimplencia",
                "formato": "excel",
                "periodo": "mes_atual"
            }
        )
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers.get("content-type", "")
        assert len(response.content) > 0
        print(f"Excel inadimplencia size: {len(response.content)} bytes")
    
    def test_relatorio_fluxo_caixa_excel(self, auth_headers):
        """Test generating cash flow report in Excel format"""
        response = requests.post(
            f"{BASE_URL}/api/relatorios/gerar",
            headers=auth_headers,
            json={
                "tipo": "fluxo_caixa",
                "formato": "excel",
                "periodo": "mes_atual"
            }
        )
        assert response.status_code == 200
        assert "spreadsheetml" in response.headers.get("content-type", "")
        assert len(response.content) > 0
        print(f"Excel fluxo_caixa size: {len(response.content)} bytes")
    
    # Period Tests
    def test_relatorio_periodo_trimestre(self, auth_headers):
        """Test report with trimester period"""
        response = requests.post(
            f"{BASE_URL}/api/relatorios/gerar",
            headers=auth_headers,
            json={
                "tipo": "emprestimos",
                "formato": "pdf",
                "periodo": "trimestre"
            }
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
    
    def test_relatorio_periodo_customizado(self, auth_headers):
        """Test report with custom period"""
        response = requests.post(
            f"{BASE_URL}/api/relatorios/gerar",
            headers=auth_headers,
            json={
                "tipo": "emprestimos",
                "formato": "pdf",
                "periodo": "customizado",
                "data_inicio": "2025-01-01",
                "data_fim": "2025-12-31"
            }
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
    
    def test_relatorio_unauthorized(self):
        """Test that endpoint requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/relatorios/gerar",
            json={
                "tipo": "emprestimos",
                "formato": "pdf",
                "periodo": "mes_atual"
            }
        )
        assert response.status_code in [401, 403]


class TestPagamentos:
    """Tests for pagamentos endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@sgej.com",
            "senha": "admin123"
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_listar_pagamentos(self, auth_headers):
        """Test listing payments"""
        response = requests.get(f"{BASE_URL}/api/pagamentos", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            pagamento = data[0]
            assert "id" in pagamento
            assert "parcela_id" in pagamento
            assert "emprestimo_id" in pagamento
            assert "data_pagamento" in pagamento
            assert "valor_pago" in pagamento
            assert "metodo_pagamento" in pagamento
            print(f"Found {len(data)} payments")
    
    def test_pagamentos_unauthorized(self):
        """Test that endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/pagamentos")
        assert response.status_code in [401, 403]


class TestDashboard:
    """Tests for dashboard endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@sgej.com",
            "senha": "admin123"
        })
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_dashboard_stats(self, auth_headers):
        """Test dashboard statistics"""
        response = requests.get(f"{BASE_URL}/api/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify all expected fields
        assert "total_capital_emprestado" in data
        assert "total_juros_a_receber" in data
        assert "total_juros_recebidos" in data
        assert "taxa_inadimplencia" in data
        assert "total_clientes_ativos" in data
        assert "total_emprestimos_ativos" in data
        assert "proximos_vencimentos" in data
        
        print(f"Dashboard: Capital={data['total_capital_emprestado']}, Clientes={data['total_clientes_ativos']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
