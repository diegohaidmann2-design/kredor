"""Tests for centavos migration bug fix - GET /api/emprestimos with sem_prazo loans.

Original bug: KeyError: 'valor_principal_centavos' in routes/emprestimos.py
when documents from backup used legacy 'valor_principal' field.
"""
import os
import pytest
import requests
from pathlib import Path

def _load_frontend_env():
    env_path = Path("/app/frontend/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return None

BASE_URL = (os.environ.get('REACT_APP_BACKEND_URL') or _load_frontend_env() or "").rstrip('/')
assert BASE_URL, "REACT_APP_BACKEND_URL not set"

QA_EMAIL = "qa.teste@gestorcred.com"
QA_SENHA = "Teste@2026"
REAL_EMAIL = "diego.haidmann@gmail.com"
REAL_SENHA = "Teste@2026"


def _login(email, senha):
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "senha": senha, "turnstile_token": "dummy"},
        timeout=30,
    )
    assert r.status_code == 200, f"Login failed {r.status_code}: {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"No token in login response: {data}"
    return token


@pytest.fixture(scope="module")
def qa_headers():
    return {"Authorization": f"Bearer {_login(QA_EMAIL, QA_SENHA)}"}


@pytest.fixture(scope="module")
def real_headers():
    return {"Authorization": f"Bearer {_login(REAL_EMAIL, REAL_SENHA)}"}


# --- Auth tests ---
class TestAuth:
    def test_login_qa(self):
        token = _login(QA_EMAIL, QA_SENHA)
        assert isinstance(token, str) and len(token) > 10

    def test_login_real(self):
        token = _login(REAL_EMAIL, REAL_SENHA)
        assert isinstance(token, str) and len(token) > 10


# --- Emprestimos endpoints (primary bug context) ---
class TestEmprestimosRealUser:
    """Diego has ~40 sem_prazo loans -> triggers the bug path."""

    def test_listar_emprestimos_default(self, real_headers):
        r = requests.get(f"{BASE_URL}/api/emprestimos", headers=real_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # Accept list or dict wrapper
        items = data if isinstance(data, list) else data.get("emprestimos") or data.get("items") or data.get("data") or []
        assert isinstance(items, list)
        assert len(items) > 0, "Expected loans for real user"
        # API returns values as 'valor_principal' (float reais) for backward compat;
        # DB stores '_centavos' (int). Just verify the value is present and numeric.
        sample = items[0]
        has_value = ("valor_principal_centavos" in sample) or ("valor_principal" in sample)
        assert has_value, f"No principal value field. Sample keys: {list(sample.keys())}"
        for e in items[:5]:
            v = e.get("valor_principal_centavos", e.get("valor_principal"))
            assert isinstance(v, (int, float)) and v >= 0, f"Bad value: {v!r}"

    def test_listar_emprestimos_excluir_quitados(self, real_headers):
        r = requests.get(
            f"{BASE_URL}/api/emprestimos?excluir_quitados=true",
            headers=real_headers, timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        items = data if isinstance(data, list) else data.get("emprestimos") or data.get("items") or data.get("data") or []
        assert isinstance(items, list)

    def test_listar_emprestimos_contem_sem_prazo(self, real_headers):
        """The critical scenario - sem_prazo loans went through the KeyError path."""
        r = requests.get(f"{BASE_URL}/api/emprestimos", headers=real_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        items = data if isinstance(data, list) else data.get("emprestimos") or data.get("items") or data.get("data") or []
        sem_prazo = [e for e in items if (e.get("tipo") == "sem_prazo" or e.get("sem_prazo") is True or e.get("modalidade") == "sem_prazo")]
        # If real user should have sem_prazo, verify count > 0
        assert len(sem_prazo) > 0, f"Expected sem_prazo loans; sample keys: {list(items[0].keys()) if items else []}"

    def test_abertos_resumo(self, real_headers):
        r = requests.get(f"{BASE_URL}/api/emprestimos/abertos/resumo", headers=real_headers, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)


class TestEmprestimosQA:
    """QA user has no data — endpoints must still return 200."""

    def test_listar_emprestimos(self, qa_headers):
        r = requests.get(f"{BASE_URL}/api/emprestimos", headers=qa_headers, timeout=30)
        assert r.status_code == 200

    def test_excluir_quitados(self, qa_headers):
        r = requests.get(f"{BASE_URL}/api/emprestimos?excluir_quitados=true", headers=qa_headers, timeout=30)
        assert r.status_code == 200

    def test_abertos_resumo(self, qa_headers):
        r = requests.get(f"{BASE_URL}/api/emprestimos/abertos/resumo", headers=qa_headers, timeout=30)
        assert r.status_code == 200


# --- Related endpoints ---
class TestRelatedEndpoints:
    def test_parcelas_pendentes_real(self, real_headers):
        r = requests.get(f"{BASE_URL}/api/parcelas/pendentes", headers=real_headers, timeout=30)
        assert r.status_code == 200, r.text

    def test_pagamentos_real(self, real_headers):
        # Try common paths
        paths = ["/api/pagamentos", "/api/pagamentos/"]
        last = None
        for p in paths:
            r = requests.get(f"{BASE_URL}{p}", headers=real_headers, timeout=30)
            last = r
            if r.status_code == 200:
                return
        pytest.fail(f"Pagamentos endpoint failed: {last.status_code} {last.text[:200]}")

    def test_dashboard_real(self, real_headers):
        r = requests.get(f"{BASE_URL}/api/dashboard", headers=real_headers, timeout=30)
        assert r.status_code == 200, r.text

    def test_dashboard_qa(self, qa_headers):
        r = requests.get(f"{BASE_URL}/api/dashboard", headers=qa_headers, timeout=30)
        assert r.status_code == 200, r.text
