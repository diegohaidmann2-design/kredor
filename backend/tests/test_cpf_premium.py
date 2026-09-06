"""
Tests for CPF Premium module (POST /api/consultas/cpf-premium).
Covers: happy path with wallet debit, insufficient balance (402), invalid CPF (400),
history retrieval, single-item retrieval, PDF generation (no base64 foto embedded),
and admin price endpoints (list + update).
"""
import os
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback for direct pytest execution
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

MONGO_URL = os.environ.get("MONGO_URL") or open("/app/backend/.env").read().split("MONGO_URL=", 1)[1].split("\n")[0].strip()
DB_NAME = os.environ.get("DB_NAME") or open("/app/backend/.env").read().split("DB_NAME=", 1)[1].split("\n")[0].strip()

TEST_CPF_VALID = "05827585564"
TEST_EMAIL = f"TEST_premium_{uuid.uuid4().hex[:8]}@teste.com"
TEST_PASSWORD = "Teste@123"


@pytest.fixture(scope="module")
def mongo():
    c = MongoClient(MONGO_URL)
    yield c[DB_NAME]
    c.close()


@pytest.fixture(scope="module")
def user_context(mongo):
    """Create user, promote to admin+enterprise, return {token, user_id, email}."""
    r = requests.post(f"{BASE_URL}/api/auth/registro", json={
        "nome": "Premium Tester",
        "email": TEST_EMAIL,
        "senha": TEST_PASSWORD,
        "telefone": "11999998888",
    })
    assert r.status_code in (200, 201), f"registro falhou: {r.status_code} {r.text}"

    # Promote in Mongo
    mongo.usuarios.update_one(
        {"email": TEST_EMAIL},
        {"$set": {
            "email_verificado": True, "perfil": "admin", "plano": "enterprise",
            "status": "ativo", "ativo": True, "plano_ativo": True,
        }},
    )
    u = mongo.usuarios.find_one({"email": TEST_EMAIL}, {"_id": 0, "id": 1})
    assert u and u.get("id"), "usuario nao encontrado apos registro"
    user_id = u["id"]

    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": TEST_EMAIL, "senha": TEST_PASSWORD})
    assert r.status_code == 200, f"login falhou: {r.status_code} {r.text}"
    token = r.json().get("access_token") or r.json().get("token")
    assert token, f"token ausente: {r.json()}"

    ctx = {"token": token, "user_id": user_id, "email": TEST_EMAIL,
           "headers": {"Authorization": f"Bearer {token}"}}

    # Give saldo via admin ajuste (own wallet, admin allowed)
    r = requests.post(f"{BASE_URL}/api/admin/carteiras/{user_id}/ajuste",
                      json={"valor": 50, "motivo": "teste cpf premium"},
                      headers=ctx["headers"])
    assert r.status_code == 200, f"ajuste falhou: {r.status_code} {r.text}"

    yield ctx

    # Cleanup
    try:
        mongo.consultas.delete_many({"usuario_id": user_id})
        mongo.carteiras.delete_many({"owner_id": user_id})
        mongo.carteira_movimentos.delete_many({"owner_id": user_id})
        mongo.usuarios.delete_many({"email": TEST_EMAIL})
    except Exception as e:
        print(f"cleanup error: {e}")


# ---- Admin: preço cpf-premium ----
class TestPrecos:
    def test_list_prices_contains_cpf_premium(self, user_context):
        r = requests.get(f"{BASE_URL}/api/admin/carteiras/precos", headers=user_context["headers"])
        assert r.status_code == 200, r.text
        itens = r.json().get("itens", [])
        premium = next((i for i in itens if i["tipo"] == "cpf-premium"), None)
        assert premium is not None, "cpf-premium não listado em precos"
        assert premium["label"] == "CPF Premium"
        assert float(premium["valor"]) == 2.50

    def test_update_price_cpf_premium(self, user_context):
        r = requests.put(
            f"{BASE_URL}/api/admin/carteiras/precos/cpf-premium",
            json={"valor": 2.50, "ativo": True},
            headers=user_context["headers"],
        )
        assert r.status_code == 200, r.text


# ---- Consulta CPF Premium ----
class TestConsultaCpfPremium:
    _shared = {}

    def test_cpf_invalido_400(self, user_context):
        r = requests.post(f"{BASE_URL}/api/consultas/cpf-premium",
                          json={"cpf": "11111111111"}, headers=user_context["headers"])
        assert r.status_code == 400, f"esperava 400, veio {r.status_code}: {r.text}"

        r2 = requests.post(f"{BASE_URL}/api/consultas/cpf-premium",
                           json={"cpf": "123"}, headers=user_context["headers"])
        assert r2.status_code == 400

    def test_consulta_premium_sucesso_e_debito(self, user_context, mongo):
        # Get saldo antes
        w_before = mongo.carteiras.find_one({"owner_id": user_context["user_id"]}) or {}
        saldo_before = float(w_before.get("saldo") or 0)

        r = requests.post(f"{BASE_URL}/api/consultas/cpf-premium",
                          json={"cpf": TEST_CPF_VALID}, headers=user_context["headers"])
        assert r.status_code == 200, f"esperava 200, veio {r.status_code}: {r.text[:500]}"
        body = r.json()
        assert body.get("tipo") == "cpf-premium"
        assert "id" in body
        assert "data" in body
        dados = (body["data"] or {}).get("dados") or {}
        assert dados.get("nome"), f"nome ausente em dados: {list(dados.keys())[:20]}"
        # documento presente
        assert dados.get("documento")
        secoes = dados.get("secoes")
        assert isinstance(secoes, list) and len(secoes) > 0, "secoes ausentes"
        # Verifica que ao menos uma secao tem estrutura {titulo, blocos}
        assert any(isinstance(s, dict) and "titulo" in s and "blocos" in s for s in secoes)
        # carteira response
        assert "carteira" in body

        # Verifica debito
        w_after = mongo.carteiras.find_one({"owner_id": user_context["user_id"]}) or {}
        saldo_after = float(w_after.get("saldo") or 0)
        assert round(saldo_before - saldo_after, 2) == 2.50, \
            f"debito esperado 2.50, saldo_before={saldo_before} saldo_after={saldo_after}"

        TestConsultaCpfPremium._shared["consulta_id"] = body["id"]

    def test_historico_contains_premium(self, user_context):
        r = requests.get(f"{BASE_URL}/api/consultas/historico?tipo=cpf-premium",
                         headers=user_context["headers"])
        assert r.status_code == 200
        itens = r.json().get("itens", [])
        assert any(i["id"] == TestConsultaCpfPremium._shared.get("consulta_id") for i in itens), \
            "consulta premium não apareceu no historico"

    def test_get_consulta_by_id(self, user_context):
        cid = TestConsultaCpfPremium._shared.get("consulta_id")
        assert cid
        r = requests.get(f"{BASE_URL}/api/consultas/{cid}", headers=user_context["headers"])
        assert r.status_code == 200
        body = r.json()
        assert body["tipo"] == "cpf-premium"
        assert (body.get("data") or {}).get("dados", {}).get("nome")

    def test_pdf_generation(self, user_context):
        cid = TestConsultaCpfPremium._shared.get("consulta_id")
        assert cid
        r = requests.get(f"{BASE_URL}/api/consultas/{cid}/pdf", headers=user_context["headers"])
        assert r.status_code == 200, r.text[:300]
        content = r.content
        assert content.startswith(b"%PDF"), "resposta não é um PDF válido"
        # Não deve conter data URL base64 gigante da foto
        assert b"data:image/" not in content, "PDF contém base64 embutido (data:image/)"

    def test_saldo_insuficiente_402(self, user_context, mongo):
        # Zera saldo
        mongo.carteiras.update_one(
            {"owner_id": user_context["user_id"]},
            {"$set": {"saldo": 0.0}},
        )
        r = requests.post(f"{BASE_URL}/api/consultas/cpf-premium",
                          json={"cpf": TEST_CPF_VALID}, headers=user_context["headers"])
        assert r.status_code == 402, f"esperava 402, veio {r.status_code}: {r.text[:300]}"
        detail = r.json().get("detail") or {}
        if isinstance(detail, dict):
            assert detail.get("code") == "SALDO_INSUFICIENTE"
