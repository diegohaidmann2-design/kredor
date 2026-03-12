"""
Testes de Integração - Parcelas e Relacionamentos
Previne bugs de lookup e dados nulos
"""
import pytest
from fastapi.testclient import TestClient
from motor.motor_asyncio import AsyncIOMotorClient
import sys
import os

# Adicionar path do backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from main import app
from config import MONGO_URL, DB_NAME


@pytest.fixture
def client():
    """Cliente HTTP para testar a API"""
    return TestClient(app)


@pytest.fixture
async def db():
    """Conexão com banco de dados de teste"""
    client = AsyncIOMotorClient(MONGO_URL)
    database = client[DB_NAME]
    yield database
    client.close()


@pytest.fixture
def auth_token(client):
    """Token de autenticação para testes"""
    response = client.post(
        "/api/auth/login",
        json={"email": "diego.haidmann@gmail.com", "senha": "muda2025"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


class TestParcelasPendentes:
    """Testes para prevenir bug: 'Cliente não encontrado'"""
    
    def test_parcelas_pendentes_retorna_cliente_nome(self, client, auth_token):
        """
        BUG PREVENIDO: Cliente não encontrado em /pagamentos
        
        Garante que a API de parcelas pendentes retorna nome do cliente
        através do lookup correto: Parcela → Empréstimo → Cliente
        """
        response = client.get(
            "/api/parcelas/pendentes",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        parcelas = response.json()
        
        if len(parcelas) > 0:
            primeira_parcela = parcelas[0]
            
            # ✅ VALIDAÇÕES CRÍTICAS
            assert "cliente_nome" in primeira_parcela, "Campo cliente_nome ausente"
            assert primeira_parcela["cliente_nome"] is not None, "Cliente nome é None"
            assert primeira_parcela["cliente_nome"] != "", "Cliente nome vazio"
            assert "cliente_telefone" in primeira_parcela, "Campo cliente_telefone ausente"
            
            print(f"✅ Cliente encontrado: {primeira_parcela['cliente_nome']}")
    
    def test_parcelas_pendentes_retorna_valores_corretos(self, client, auth_token):
        """
        BUG PREVENIDO: Valores R$ 0,00 em parcelas
        
        Garante que parcelas têm valores corretos (não null, não zero)
        """
        response = client.get(
            "/api/parcelas/pendentes",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        parcelas = response.json()
        
        if len(parcelas) > 0:
            for parcela in parcelas:
                # ✅ VALIDAÇÕES CRÍTICAS
                assert "valor_total" in parcela, "Campo valor_total ausente"
                assert parcela["valor_total"] is not None, f"Parcela {parcela['numero_parcela']} tem valor_total null"
                assert parcela["valor_total"] > 0, f"Parcela {parcela['numero_parcela']} tem valor_total = 0"
                
                print(f"✅ Parcela {parcela['numero_parcela']}: R$ {parcela['valor_total']}")


class TestParcelasDatabase:
    """Testes diretos no banco de dados"""
    
    @pytest.mark.asyncio
    async def test_todas_parcelas_tem_valor_parcela_preenchido(self, db):
        """
        BUG PREVENIDO: Campo valor_parcela = None
        
        Garante que todas as parcelas no banco têm valor_parcela preenchido
        """
        parcelas_invalidas = await db.parcelas.count_documents({
            "$or": [
                {"valor_parcela": None},
                {"valor_parcela": {"$exists": False}}
            ]
        })
        
        assert parcelas_invalidas == 0, f"❌ {parcelas_invalidas} parcelas com valor_parcela null/ausente"
        print("✅ Todas parcelas têm valor_parcela preenchido")
    
    @pytest.mark.asyncio
    async def test_todas_parcelas_tem_emprestimo_valido(self, db):
        """
        BUG PREVENIDO: Lookup de empréstimo falha
        
        Garante que todas parcelas referenciam empréstimos existentes
        """
        # Buscar todas parcelas
        parcelas = await db.parcelas.find({}).to_list(1000)
        
        for parcela in parcelas:
            emprestimo_id = parcela.get("emprestimo_id")
            assert emprestimo_id, f"Parcela {parcela['id']} sem emprestimo_id"
            
            # Verificar se empréstimo existe
            emprestimo = await db.emprestimos.find_one({"id": emprestimo_id})
            assert emprestimo is not None, f"Empréstimo {emprestimo_id} não encontrado"
            
            # Verificar se empréstimo tem cliente
            assert emprestimo.get("cliente_id"), f"Empréstimo {emprestimo_id} sem cliente_id"
        
        print(f"✅ Todas {len(parcelas)} parcelas têm empréstimos válidos")


class TestEmprestimosDetalhes:
    """Testes para página de detalhes do empréstimo"""
    
    @pytest.mark.asyncio
    async def test_detalhes_emprestimo_retorna_parcelas_com_valores(self, client, auth_token, db):
        """
        BUG PREVENIDO: Valores zerados na página de detalhes
        
        Garante que ao buscar detalhes do empréstimo, parcelas têm valores corretos
        """
        # Buscar um empréstimo existente
        emprestimo = await db.emprestimos.find_one({})
        
        if emprestimo:
            emprestimo_id = emprestimo["id"]
            
            response = client.get(
                f"/api/emprestimos/{emprestimo_id}/parcelas",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            
            assert response.status_code == 200
            parcelas = response.json()
            
            assert len(parcelas) > 0, "Empréstimo sem parcelas"
            
            for parcela in parcelas:
                # ✅ VALIDAÇÕES CRÍTICAS
                assert parcela["valor_total"] > 0, f"Parcela {parcela['numero_parcela']} com valor_total = 0"
                assert parcela["valor_principal"] >= 0, f"Parcela {parcela['numero_parcela']} com valor_principal negativo"
                assert parcela["valor_juros"] >= 0, f"Parcela {parcela['numero_parcela']} com valor_juros negativo"
                
                # Validar consistência
                assert parcela["valor_total"] == parcela["valor_principal"] + parcela["valor_juros"], \
                    f"Parcela {parcela['numero_parcela']}: valor_total inconsistente"
                
                print(f"✅ Parcela {parcela['numero_parcela']}: R$ {parcela['valor_total']}")


class TestCriacaoCliente:
    """Testes de validação de cliente"""
    
    def test_criar_cliente_com_cpf_invalido_retorna_422(self, client, auth_token):
        """
        BUG PREVENIDO: CPF inválido aceito
        
        Garante que backend valida CPF e retorna mensagem clara
        """
        response = client.post(
            "/api/clientes",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "nome": "Cliente Teste",
                "cpf_cnpj": "11111111111",  # CPF inválido
                "email": "teste@teste.com",
                "telefone": "11999999999",
                "endereco": {
                    "rua": "Rua Teste",
                    "numero": "123",
                    "bairro": "Centro",
                    "cidade": "São Paulo",
                    "estado": "SP",
                    "cep": "01310100"
                }
            }
        )
        
        assert response.status_code == 422, "Backend aceitou CPF inválido"
        
        error_detail = response.json()["detail"]
        assert "cpf_cnpj" in str(error_detail).lower() or "cpf" in str(error_detail).lower(), \
            "Mensagem de erro não menciona CPF"
        
        print("✅ CPF inválido rejeitado corretamente")


# Script para rodar testes manualmente
if __name__ == "__main__":
    import asyncio
    
    print("🧪 Executando testes de prevenção de bugs...\n")
    pytest.main([__file__, "-v", "--tb=short"])
