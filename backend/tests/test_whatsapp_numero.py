"""Test WhatsApp numero_telefone sync fix (no message sending)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://gestor-cred.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

EMAIL = "diego.haidmann@gmail.com"
SENHA = "GestorTest@2026"
EXPECTED_INSTANCE = "user_fabf3ca4_f2bfdb96"
EXPECTED_NUMERO = "5527999507920"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={
        "email": EMAIL,
        "senha": SENHA,
        "turnstile_token": "dummy",
    }, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"no token in response: {data}"
    return tok


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_returns_token(token):
    assert isinstance(token, str) and len(token) > 20


def test_conexoes_lists_numero(headers):
    r = requests.get(f"{API}/whatsapp/conexoes", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    payload = r.json()
    conexoes = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
    assert isinstance(conexoes, list) and len(conexoes) > 0
    target = next((c for c in conexoes if c.get("instance_name") == EXPECTED_INSTANCE), None)
    assert target is not None, f"instance {EXPECTED_INSTANCE} not found in {conexoes}"
    assert target.get("status") == "conectado", f"status={target.get('status')}"
    assert target.get("numero_telefone") == EXPECTED_NUMERO, f"numero_telefone={target.get('numero_telefone')}"
    # cache id for next test
    pytest.conexao_id = target.get("id") or target.get("_id")


def test_status_endpoint_persists_numero(headers):
    cid = getattr(pytest, "conexao_id", None)
    assert cid, "conexao id missing"
    r = requests.get(f"{API}/whatsapp/conexoes/{cid}/status", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("status") == "conectado", f"status endpoint returned: {body}"

    # re-list to confirm numero not overwritten
    r2 = requests.get(f"{API}/whatsapp/conexoes", headers=headers, timeout=30)
    assert r2.status_code == 200
    payload2 = r2.json()
    conexoes2 = payload2["items"] if isinstance(payload2, dict) and "items" in payload2 else payload2
    target = next((c for c in conexoes2 if c.get("instance_name") == EXPECTED_INSTANCE), None)
    assert target is not None
    assert target.get("numero_telefone") == EXPECTED_NUMERO, (
        f"regression! numero_telefone after status call = {target.get('numero_telefone')}"
    )


def test_status_servico(headers):
    r = requests.get(f"{API}/whatsapp/status-servico", headers=headers, timeout=30)
    assert r.status_code == 200, r.text


def test_config_evolution(headers):
    r = requests.get(f"{API}/whatsapp/config/evolution", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
