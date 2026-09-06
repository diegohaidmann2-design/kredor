"""Test admin carteira ajuste endpoint (fix for _id serialization 500)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback to frontend .env parse
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

ADMIN_EMAIL = "admin.qa@teste.com"
ADMIN_PASSWORD = "Teste@123"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "senha": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    assert token, f"No token in response: {data}"
    return token


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_owner_id(admin_headers):
    # Get current user's own id via /api/auth/me
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=admin_headers)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_listar_carteiras_admin(admin_headers):
    r = requests.get(f"{BASE_URL}/api/admin/carteiras/", headers=admin_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "itens" in data


def test_ajuste_credito_e_reverte(admin_headers, admin_owner_id):
    # Get initial balance
    r = requests.get(f"{BASE_URL}/api/admin/carteiras/{admin_owner_id}", headers=admin_headers)
    assert r.status_code == 200, r.text
    saldo_inicial = r.json()["carteira"]["saldo"]

    # Aplicar crédito +1.00
    r = requests.post(
        f"{BASE_URL}/api/admin/carteiras/{admin_owner_id}/ajuste",
        headers=admin_headers,
        json={"valor": 1.0, "motivo": "teste ajuste credito"},
    )
    assert r.status_code == 200, f"Expected 200 got {r.status_code}: {r.text}"
    body = r.json()
    assert "carteira" in body and "movimento" in body
    # Fix validation: NO _id in movimento
    assert "_id" not in body["movimento"], f"movimento contains _id! {body['movimento']}"
    assert "_id" not in body["carteira"], f"carteira contains _id!"
    assert body["movimento"]["tipo"] == "ajuste"
    assert body["movimento"]["valor"] == 1.0
    assert round(body["carteira"]["saldo"], 2) == round(saldo_inicial + 1.0, 2)

    saldo_apos_credito = body["carteira"]["saldo"]

    # Reverter com débito -1.00
    r = requests.post(
        f"{BASE_URL}/api/admin/carteiras/{admin_owner_id}/ajuste",
        headers=admin_headers,
        json={"valor": -1.0, "motivo": "teste ajuste reversao"},
    )
    assert r.status_code == 200, f"Debit failed: {r.status_code} {r.text}"
    body2 = r.json()
    assert "_id" not in body2["movimento"]
    assert body2["movimento"]["valor"] == -1.0
    assert round(body2["carteira"]["saldo"], 2) == round(saldo_apos_credito - 1.0, 2)


def test_ajuste_debito_maior_que_saldo(admin_headers, admin_owner_id):
    # Get current saldo
    r = requests.get(f"{BASE_URL}/api/admin/carteiras/{admin_owner_id}", headers=admin_headers)
    saldo = r.json()["carteira"]["saldo"]

    # Try to debit way more than saldo
    valor_debito = -(saldo + 999999.0)
    r = requests.post(
        f"{BASE_URL}/api/admin/carteiras/{admin_owner_id}/ajuste",
        headers=admin_headers,
        json={"valor": valor_debito, "motivo": "teste saldo insuficiente"},
    )
    assert r.status_code == 400, f"Expected 400 got {r.status_code}: {r.text}"
    detail = r.json().get("detail", "").lower()
    assert "saldo" in detail or "insuficiente" in detail


def test_ajuste_valor_zero(admin_headers, admin_owner_id):
    r = requests.post(
        f"{BASE_URL}/api/admin/carteiras/{admin_owner_id}/ajuste",
        headers=admin_headers,
        json={"valor": 0, "motivo": "teste zero"},
    )
    assert r.status_code == 400, f"Expected 400 got {r.status_code}: {r.text}"
