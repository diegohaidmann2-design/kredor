"""
Test Suite for SGEJ New Features:
1. Dashboard with interactive charts (evolucao_mensal, distribuicao_status, top_clientes, metodos_calculo)
2. Export page (/exportacao) with CSV/JSON export
3. Super Admin panel (/superadmin) with tenant management
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@sgej.com"
ADMIN_SENHA = "admin123"
USER_EMAIL = "usuario@teste.com"
USER_SENHA = "senha123"


class TestAuth:
    """Authentication tests"""
    
    def test_admin_login(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_SENHA
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "token" in data, "Token not in response"
        assert "usuario" in data, "Usuario not in response"
        print(f"✓ Admin login successful - User: {data['usuario'].get('email')}")
        return data["token"]
    
    def test_user_login(self):
        """Test regular user login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": USER_EMAIL,
            "senha": USER_SENHA
        })
        # User may not exist, so we accept 401 as well
        if response.status_code == 200:
            data = response.json()
            assert "token" in data
            print(f"✓ User login successful")
            return data["token"]
        else:
            print(f"⚠ User login failed (user may not exist): {response.status_code}")
            pytest.skip("User does not exist")


class TestDashboardWithCharts:
    """Dashboard API tests - verifying chart data fields"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_SENHA
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_dashboard_returns_basic_stats(self):
        """Test dashboard returns basic statistics"""
        response = requests.get(f"{BASE_URL}/api/dashboard", headers=self.headers)
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = response.json()
        
        # Basic stats
        assert "total_capital_emprestado" in data
        assert "total_juros_a_receber" in data
        assert "total_juros_recebidos" in data
        assert "taxa_inadimplencia" in data
        assert "total_clientes_ativos" in data
        assert "total_emprestimos_ativos" in data
        assert "proximos_vencimentos" in data
        
        print(f"✓ Dashboard basic stats: capital={data['total_capital_emprestado']}, clientes={data['total_clientes_ativos']}")
    
    def test_dashboard_returns_evolucao_mensal(self):
        """Test dashboard returns monthly evolution data for charts"""
        response = requests.get(f"{BASE_URL}/api/dashboard", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "evolucao_mensal" in data, "evolucao_mensal not in dashboard response"
        assert isinstance(data["evolucao_mensal"], list), "evolucao_mensal should be a list"
        
        # Should have 12 months of data
        assert len(data["evolucao_mensal"]) == 12, f"Expected 12 months, got {len(data['evolucao_mensal'])}"
        
        # Each entry should have mes and valor
        for entry in data["evolucao_mensal"]:
            assert "mes" in entry, "Each entry should have 'mes'"
            assert "valor" in entry, "Each entry should have 'valor'"
        
        print(f"✓ Dashboard evolucao_mensal: {len(data['evolucao_mensal'])} months of data")
    
    def test_dashboard_returns_distribuicao_status(self):
        """Test dashboard returns status distribution for pie chart"""
        response = requests.get(f"{BASE_URL}/api/dashboard", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "distribuicao_status" in data, "distribuicao_status not in dashboard response"
        assert isinstance(data["distribuicao_status"], list)
        
        # Should have status entries (ativo, quitado, inadimplente, cancelado)
        status_names = [s["name"] for s in data["distribuicao_status"]]
        expected_statuses = ["Ativo", "Quitado", "Inadimplente", "Cancelado"]
        for status in expected_statuses:
            assert status in status_names, f"Status '{status}' not found in distribuicao_status"
        
        # Each entry should have name, value, color
        for entry in data["distribuicao_status"]:
            assert "name" in entry
            assert "value" in entry
            assert "color" in entry
        
        print(f"✓ Dashboard distribuicao_status: {len(data['distribuicao_status'])} status types")
    
    def test_dashboard_returns_top_clientes(self):
        """Test dashboard returns top clients for bar chart"""
        response = requests.get(f"{BASE_URL}/api/dashboard", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "top_clientes" in data, "top_clientes not in dashboard response"
        assert isinstance(data["top_clientes"], list)
        
        # Each entry should have nome and valor
        for entry in data["top_clientes"]:
            assert "nome" in entry, "Each top_cliente should have 'nome'"
            assert "valor" in entry, "Each top_cliente should have 'valor'"
        
        print(f"✓ Dashboard top_clientes: {len(data['top_clientes'])} clients")
    
    def test_dashboard_returns_metodos_calculo(self):
        """Test dashboard returns calculation methods distribution"""
        response = requests.get(f"{BASE_URL}/api/dashboard", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "metodos_calculo" in data, "metodos_calculo not in dashboard response"
        assert isinstance(data["metodos_calculo"], list)
        
        # Should have method entries
        method_names = [m["name"] for m in data["metodos_calculo"]]
        expected_methods = ["Juros Simples", "Juros Compostos", "Tabela Price", "SAC"]
        for method in expected_methods:
            assert method in method_names, f"Method '{method}' not found in metodos_calculo"
        
        # Each entry should have name and value
        for entry in data["metodos_calculo"]:
            assert "name" in entry
            assert "value" in entry
        
        print(f"✓ Dashboard metodos_calculo: {len(data['metodos_calculo'])} methods")
    
    def test_dashboard_unauthorized(self):
        """Test dashboard requires authentication"""
        response = requests.get(f"{BASE_URL}/api/dashboard")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Dashboard requires authentication")


class TestExportacao:
    """Export API tests - CSV/JSON export functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_SENHA
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_exportacao_resumo(self):
        """Test export summary endpoint returns counts"""
        response = requests.get(f"{BASE_URL}/api/exportacao/resumo", headers=self.headers)
        assert response.status_code == 200, f"Resumo failed: {response.text}"
        data = response.json()
        
        # Should have counts for all entities
        assert "clientes" in data
        assert "emprestimos" in data
        assert "pagamentos" in data
        assert "parcelas" in data
        
        # All should be integers
        assert isinstance(data["clientes"], int)
        assert isinstance(data["emprestimos"], int)
        assert isinstance(data["pagamentos"], int)
        assert isinstance(data["parcelas"], int)
        
        print(f"✓ Export resumo: clientes={data['clientes']}, emprestimos={data['emprestimos']}, pagamentos={data['pagamentos']}, parcelas={data['parcelas']}")
    
    def test_exportacao_resumo_unauthorized(self):
        """Test export resumo requires authentication"""
        response = requests.get(f"{BASE_URL}/api/exportacao/resumo")
        assert response.status_code in [401, 403]
        print("✓ Export resumo requires authentication")
    
    def test_exportacao_json_single_entity(self):
        """Test JSON export for single entity"""
        response = requests.post(
            f"{BASE_URL}/api/exportacao/exportar",
            headers=self.headers,
            json={
                "entidades": ["clientes"],
                "formato": "json"
            }
        )
        assert response.status_code == 200, f"JSON export failed: {response.text}"
        
        # Should return JSON content
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type, f"Expected JSON, got {content_type}"
        
        # Should have content-disposition header
        content_disp = response.headers.get("content-disposition", "")
        assert "attachment" in content_disp
        assert ".json" in content_disp
        
        # Should be valid JSON
        data = response.json()
        assert "clientes" in data
        
        print(f"✓ JSON export single entity: {len(data.get('clientes', []))} clientes")
    
    def test_exportacao_json_multiple_entities(self):
        """Test JSON export for multiple entities"""
        response = requests.post(
            f"{BASE_URL}/api/exportacao/exportar",
            headers=self.headers,
            json={
                "entidades": ["clientes", "emprestimos", "pagamentos"],
                "formato": "json"
            }
        )
        assert response.status_code == 200, f"JSON export failed: {response.text}"
        
        data = response.json()
        assert "clientes" in data
        assert "emprestimos" in data
        assert "pagamentos" in data
        
        print(f"✓ JSON export multiple entities: clientes={len(data.get('clientes', []))}, emprestimos={len(data.get('emprestimos', []))}")
    
    def test_exportacao_csv_single_entity(self):
        """Test CSV export for single entity"""
        response = requests.post(
            f"{BASE_URL}/api/exportacao/exportar",
            headers=self.headers,
            json={
                "entidades": ["clientes"],
                "formato": "csv"
            }
        )
        assert response.status_code == 200, f"CSV export failed: {response.text}"
        
        # Should return CSV content
        content_type = response.headers.get("content-type", "")
        assert "text/csv" in content_type, f"Expected CSV, got {content_type}"
        
        # Should have content-disposition header
        content_disp = response.headers.get("content-disposition", "")
        assert "attachment" in content_disp
        assert ".csv" in content_disp
        
        print("✓ CSV export single entity successful")
    
    def test_exportacao_csv_multiple_entities_returns_zip(self):
        """Test CSV export for multiple entities returns ZIP"""
        response = requests.post(
            f"{BASE_URL}/api/exportacao/exportar",
            headers=self.headers,
            json={
                "entidades": ["clientes", "emprestimos"],
                "formato": "csv"
            }
        )
        assert response.status_code == 200, f"CSV export failed: {response.text}"
        
        # Should return ZIP content
        content_type = response.headers.get("content-type", "")
        assert "application/zip" in content_type, f"Expected ZIP, got {content_type}"
        
        # Should have content-disposition header
        content_disp = response.headers.get("content-disposition", "")
        assert "attachment" in content_disp
        assert ".zip" in content_disp
        
        print("✓ CSV export multiple entities returns ZIP")
    
    def test_exportacao_unauthorized(self):
        """Test export requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/exportacao/exportar",
            json={
                "entidades": ["clientes"],
                "formato": "json"
            }
        )
        assert response.status_code in [401, 403]
        print("✓ Export requires authentication")


class TestSuperAdmin:
    """Super Admin API tests - tenant management"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get admin token for authenticated requests"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_SENHA
        })
        if response.status_code != 200:
            pytest.skip("Admin login failed")
        self.token = response.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_superadmin_dashboard(self):
        """Test super admin dashboard returns stats"""
        response = requests.get(f"{BASE_URL}/api/superadmin/dashboard", headers=self.headers)
        assert response.status_code == 200, f"SuperAdmin dashboard failed: {response.text}"
        data = response.json()
        
        # Should have stats
        assert "stats" in data
        stats = data["stats"]
        assert "total_tenants" in stats
        assert "tenants_ativos" in stats
        assert "tenants_trial" in stats
        assert "tenants_pagantes" in stats
        assert "receita_mensal" in stats
        assert "distribuicao_planos" in stats
        
        # Should have tenants_recentes
        assert "tenants_recentes" in data
        assert isinstance(data["tenants_recentes"], list)
        
        # Should have alertas
        assert "alertas" in data
        assert isinstance(data["alertas"], list)
        
        print(f"✓ SuperAdmin dashboard: total_tenants={stats['total_tenants']}, ativos={stats['tenants_ativos']}, receita={stats['receita_mensal']}")
    
    def test_superadmin_listar_tenants(self):
        """Test listing tenants"""
        response = requests.get(f"{BASE_URL}/api/superadmin/tenants", headers=self.headers)
        assert response.status_code == 200, f"List tenants failed: {response.text}"
        data = response.json()
        
        assert "total" in data
        assert "tenants" in data
        assert isinstance(data["tenants"], list)
        
        print(f"✓ SuperAdmin list tenants: {data['total']} total tenants")
    
    def test_superadmin_listar_tenants_with_filters(self):
        """Test listing tenants with filters"""
        # Filter by status
        response = requests.get(
            f"{BASE_URL}/api/superadmin/tenants",
            headers=self.headers,
            params={"status": "ativo"}
        )
        assert response.status_code == 200
        
        # Filter by plano
        response = requests.get(
            f"{BASE_URL}/api/superadmin/tenants",
            headers=self.headers,
            params={"plano": "trial"}
        )
        assert response.status_code == 200
        
        # Filter by busca
        response = requests.get(
            f"{BASE_URL}/api/superadmin/tenants",
            headers=self.headers,
            params={"busca": "test"}
        )
        assert response.status_code == 200
        
        print("✓ SuperAdmin list tenants with filters works")
    
    def test_superadmin_criar_tenant(self):
        """Test creating a new tenant"""
        import uuid
        unique_slug = f"test-tenant-{uuid.uuid4().hex[:8]}"
        
        response = requests.post(
            f"{BASE_URL}/api/superadmin/tenants",
            headers=self.headers,
            json={
                "nome": "Test Tenant",
                "slug": unique_slug,
                "email_admin": f"{unique_slug}@test.com",
                "plano": "trial"
            }
        )
        assert response.status_code == 200, f"Create tenant failed: {response.text}"
        data = response.json()
        
        assert "id" in data
        assert data["nome"] == "Test Tenant"
        assert data["slug"] == unique_slug
        assert data["plano"] == "trial"
        assert data["status"] == "ativo"
        assert "limites" in data
        
        # Store tenant_id for cleanup
        self.created_tenant_id = data["id"]
        
        print(f"✓ SuperAdmin create tenant: id={data['id']}, slug={data['slug']}")
        return data["id"]
    
    def test_superadmin_obter_tenant(self):
        """Test getting tenant details"""
        # First create a tenant
        import uuid
        unique_slug = f"test-get-{uuid.uuid4().hex[:8]}"
        
        create_response = requests.post(
            f"{BASE_URL}/api/superadmin/tenants",
            headers=self.headers,
            json={
                "nome": "Test Get Tenant",
                "slug": unique_slug,
                "email_admin": f"{unique_slug}@test.com",
                "plano": "basico"
            }
        )
        assert create_response.status_code == 200
        tenant_id = create_response.json()["id"]
        
        # Get tenant details
        response = requests.get(
            f"{BASE_URL}/api/superadmin/tenants/{tenant_id}",
            headers=self.headers
        )
        assert response.status_code == 200, f"Get tenant failed: {response.text}"
        data = response.json()
        
        assert data["id"] == tenant_id
        assert data["nome"] == "Test Get Tenant"
        assert "stats" in data  # Should include usage stats
        
        print(f"✓ SuperAdmin get tenant: {data['nome']}")
    
    def test_superadmin_atualizar_tenant(self):
        """Test updating a tenant"""
        # First create a tenant
        import uuid
        unique_slug = f"test-update-{uuid.uuid4().hex[:8]}"
        
        create_response = requests.post(
            f"{BASE_URL}/api/superadmin/tenants",
            headers=self.headers,
            json={
                "nome": "Test Update Tenant",
                "slug": unique_slug,
                "email_admin": f"{unique_slug}@test.com",
                "plano": "trial"
            }
        )
        assert create_response.status_code == 200
        tenant_id = create_response.json()["id"]
        
        # Update tenant
        response = requests.put(
            f"{BASE_URL}/api/superadmin/tenants/{tenant_id}",
            headers=self.headers,
            json={
                "plano": "profissional"
            }
        )
        assert response.status_code == 200, f"Update tenant failed: {response.text}"
        
        # Verify update
        get_response = requests.get(
            f"{BASE_URL}/api/superadmin/tenants/{tenant_id}",
            headers=self.headers
        )
        assert get_response.status_code == 200
        assert get_response.json()["plano"] == "profissional"
        
        print("✓ SuperAdmin update tenant successful")
    
    def test_superadmin_suspender_reativar_tenant(self):
        """Test suspending and reactivating a tenant"""
        # First create a tenant
        import uuid
        unique_slug = f"test-suspend-{uuid.uuid4().hex[:8]}"
        
        create_response = requests.post(
            f"{BASE_URL}/api/superadmin/tenants",
            headers=self.headers,
            json={
                "nome": "Test Suspend Tenant",
                "slug": unique_slug,
                "email_admin": f"{unique_slug}@test.com",
                "plano": "basico"
            }
        )
        assert create_response.status_code == 200
        tenant_id = create_response.json()["id"]
        
        # Suspend tenant
        response = requests.post(
            f"{BASE_URL}/api/superadmin/tenants/{tenant_id}/suspender",
            headers=self.headers
        )
        assert response.status_code == 200, f"Suspend tenant failed: {response.text}"
        
        # Verify suspended
        get_response = requests.get(
            f"{BASE_URL}/api/superadmin/tenants/{tenant_id}",
            headers=self.headers
        )
        assert get_response.json()["status"] == "suspenso"
        
        # Reactivate tenant
        response = requests.post(
            f"{BASE_URL}/api/superadmin/tenants/{tenant_id}/reativar",
            headers=self.headers
        )
        assert response.status_code == 200, f"Reactivate tenant failed: {response.text}"
        
        # Verify reactivated
        get_response = requests.get(
            f"{BASE_URL}/api/superadmin/tenants/{tenant_id}",
            headers=self.headers
        )
        assert get_response.json()["status"] == "ativo"
        
        print("✓ SuperAdmin suspend/reactivate tenant successful")
    
    def test_superadmin_deletar_tenant(self):
        """Test deleting (soft delete) a tenant"""
        # First create a tenant
        import uuid
        unique_slug = f"test-delete-{uuid.uuid4().hex[:8]}"
        
        create_response = requests.post(
            f"{BASE_URL}/api/superadmin/tenants",
            headers=self.headers,
            json={
                "nome": "Test Delete Tenant",
                "slug": unique_slug,
                "email_admin": f"{unique_slug}@test.com",
                "plano": "trial"
            }
        )
        assert create_response.status_code == 200
        tenant_id = create_response.json()["id"]
        
        # Delete tenant
        response = requests.delete(
            f"{BASE_URL}/api/superadmin/tenants/{tenant_id}",
            headers=self.headers
        )
        assert response.status_code == 200, f"Delete tenant failed: {response.text}"
        
        # Verify deleted (soft delete - status should be cancelado)
        get_response = requests.get(
            f"{BASE_URL}/api/superadmin/tenants/{tenant_id}",
            headers=self.headers
        )
        assert get_response.json()["status"] == "cancelado"
        
        print("✓ SuperAdmin delete tenant (soft delete) successful")
    
    def test_superadmin_unauthorized_non_admin(self):
        """Test super admin requires super admin privileges"""
        # Try to access without token
        response = requests.get(f"{BASE_URL}/api/superadmin/dashboard")
        assert response.status_code in [401, 403]
        
        print("✓ SuperAdmin requires authentication")
    
    def test_superadmin_duplicate_slug_rejected(self):
        """Test that duplicate slugs are rejected"""
        import uuid
        unique_slug = f"test-dup-{uuid.uuid4().hex[:8]}"
        
        # Create first tenant
        response1 = requests.post(
            f"{BASE_URL}/api/superadmin/tenants",
            headers=self.headers,
            json={
                "nome": "First Tenant",
                "slug": unique_slug,
                "email_admin": f"{unique_slug}@test.com",
                "plano": "trial"
            }
        )
        assert response1.status_code == 200
        
        # Try to create second tenant with same slug
        response2 = requests.post(
            f"{BASE_URL}/api/superadmin/tenants",
            headers=self.headers,
            json={
                "nome": "Second Tenant",
                "slug": unique_slug,
                "email_admin": f"second-{unique_slug}@test.com",
                "plano": "trial"
            }
        )
        assert response2.status_code == 400, f"Expected 400 for duplicate slug, got {response2.status_code}"
        
        print("✓ SuperAdmin rejects duplicate slugs")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
