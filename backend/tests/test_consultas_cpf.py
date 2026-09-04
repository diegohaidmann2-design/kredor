"""Tests for /api/consultas endpoints (LosDados CPF)."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    # frontend .env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip()
                    break
    except Exception:
        pass
BASE_URL = (BASE_URL or "").rstrip("/")

API = f"{BASE_URL}/api"

TEST_EMAIL = "qa.consultas@teste.com"
TEST_PASS = "Teste@123"
CPF_VALIDO = "11144477735"
CPF_INVALIDO = "12345678900"
LOSDADOS_API_KEY = os.environ.get("LOSDADOS_API_KEY", "")
if not LOSDADOS_API_KEY:
    try:
        with open("/app/backend/.env") as f:
            for line in f:
                if line.startswith("LOSDADOS_API_KEY="):
                    LOSDADOS_API_KEY = line.split("=", 1)[1].strip()
                    break
    except Exception:
        pass


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": TEST_EMAIL, "senha": TEST_PASS}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("token") or data.get("access_token")
    assert tok, f"no token in login response: {data}"
    return tok


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def cpf_consulta(headers):
    """Faz uma consulta CPF válida e retorna a resposta completa (reusa para outros testes)."""
    r = requests.post(f"{API}/consultas/cpf", json={"cpf": CPF_VALIDO}, headers=headers, timeout=60)
    assert r.status_code == 200, f"consulta cpf failed: {r.status_code} {r.text[:400]}"
    return r


# -------- POST /consultas/cpf --------
def test_cpf_valido_retorna_200(cpf_consulta):
    body = cpf_consulta.json()
    assert "id" in body
    assert body.get("tipo") == "cpf"
    assert "data" in body and isinstance(body["data"], dict)
    assert "dadosBasicos" in body["data"] or "err" in body["data"]
    assert "quota" in body


def test_cpf_valido_nao_vaza_chave_api(cpf_consulta):
    raw = cpf_consulta.text
    assert LOSDADOS_API_KEY, "LOSDADOS_API_KEY not loaded for test verification"
    assert LOSDADOS_API_KEY not in raw, "API key leaked in response!"
    # sanitized fields
    body = cpf_consulta.json()
    assert "signature" not in body
    assert "issuer" not in body
    if isinstance(body.get("data"), dict):
        assert "signature" not in body["data"]


def test_cpf_invalido_retorna_400(headers):
    r = requests.post(f"{API}/consultas/cpf", json={"cpf": CPF_INVALIDO}, headers=headers, timeout=30)
    assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text[:300]}"


def test_cpf_sem_auth_retorna_401_ou_403():
    r = requests.post(f"{API}/consultas/cpf", json={"cpf": CPF_VALIDO}, timeout=15)
    assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code}"


# -------- GET /consultas/historico --------
def test_historico_lista_recentes(headers, cpf_consulta):
    r = requests.get(f"{API}/consultas/historico", headers=headers, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert "itens" in body
    itens = body["itens"]
    assert isinstance(itens, list)
    assert len(itens) >= 1
    # Historico deve ser resumo apenas (sem payload data completo)
    for it in itens:
        assert "data" not in it, "historico item leaks full payload"
        assert "id" in it
        assert "resumo" in it
    # chave não vaza
    assert LOSDADOS_API_KEY not in r.text


# -------- GET /consultas/{id} --------
def test_obter_consulta_por_id(headers, cpf_consulta):
    consulta_id = cpf_consulta.json()["id"]
    r = requests.get(f"{API}/consultas/{consulta_id}", headers=headers, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == consulta_id
    assert "data" in body and isinstance(body["data"], dict)
    assert LOSDADOS_API_KEY not in r.text


def test_obter_consulta_id_inexistente_404(headers):
    r = requests.get(f"{API}/consultas/id-que-nao-existe-xyz", headers=headers, timeout=15)
    assert r.status_code == 404


# -------- DELETE /consultas/{id} --------
def test_delete_soft_remove(headers):
    # cria nova consulta para poder deletar sem impactar outros testes
    r = requests.post(f"{API}/consultas/cpf", json={"cpf": CPF_VALIDO}, headers=headers, timeout=60)
    assert r.status_code == 200
    cid = r.json()["id"]
    d = requests.delete(f"{API}/consultas/{cid}", headers=headers, timeout=15)
    assert d.status_code == 200
    assert d.json().get("success") is True
    # depois de deletado, GET deve retornar 404
    g = requests.get(f"{API}/consultas/{cid}", headers=headers, timeout=15)
    assert g.status_code == 404
    # e não aparece mais no histórico
    h = requests.get(f"{API}/consultas/historico", headers=headers, timeout=15)
    assert h.status_code == 200
    ids = [x["id"] for x in h.json().get("itens", [])]
    assert cid not in ids


def test_delete_id_inexistente_404(headers):
    r = requests.delete(f"{API}/consultas/id-que-nao-existe-abc", headers=headers, timeout=15)
    assert r.status_code == 404
