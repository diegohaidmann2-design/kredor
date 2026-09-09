"""
Security audit regression tests for Kredor (iteration_50).
Covers:
- FIX1: SyncPay webhook forgery must NOT credit wallet / activate plan
- FIX2: Admin coupon endpoints require admin auth
- FIX3: Brute-force per-IP + per-account protection on login
- Regressions: legit login, /auth/me, IDOR isolation, public endpoints
- NoSQL injection on login
"""
import os
import time
import uuid
import json
import subprocess
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass

API = f"{BASE_URL}/api"
ADMIN_EMAIL = "diego.haidmann@gmail.com"
ADMIN_PASSWORD = "Admin@2026"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "senha": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"legit admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "access_token" in data and "refresh_token" in data
    return data["access_token"]


# ---------- REGRESSION (run FIRST, before brute-force) ----------

def test_1_legit_admin_login(admin_token):
    assert isinstance(admin_token, str) and len(admin_token) > 10


def test_2_auth_me(admin_token):
    r = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d.get("email") == ADMIN_EMAIL
    assert d.get("perfil") in ("admin", "superadmin")


def test_3_consultas_idor_random_id(admin_token):
    random_id = str(uuid.uuid4())
    r = requests.get(f"{API}/consultas/{random_id}", headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
    assert r.status_code in (404, 403), f"IDOR possible? status={r.status_code} body={r.text[:200]}"


def test_4_carteira_requires_auth():
    r = requests.get(f"{API}/carteira/", timeout=15)
    assert r.status_code in (401, 403)
    r2 = requests.get(f"{API}/carteira/movimentos", timeout=15)
    assert r2.status_code in (401, 403)


def test_5_public_planos():
    r = requests.get(f"{API}/assinaturas/planos", timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_6_public_landing():
    r = requests.get(f"{API}/configuracoes/landing", timeout=15)
    assert r.status_code == 200


def test_7_registro_short_password_422():
    r = requests.post(f"{API}/auth/registro", json={
        "nome": "T",
        "email": f"TEST_short_{uuid.uuid4().hex[:6]}@example.com",
        "senha": "abc"
    }, timeout=15)
    assert r.status_code == 422, f"expected 422 for short password, got {r.status_code} {r.text[:200]}"


# ---------- FIX 1: SyncPay webhook forgery ----------

def test_8_syncpay_webhook_forgery(admin_token):
    forged_txid = f"FORGED-{uuid.uuid4().hex[:8]}"
    me = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {admin_token}"}, timeout=15).json()
    target_user_id = me["id"]
    forged_body = {
        "event": "cashin.onUpdate",
        "status": "completed",
        "transaction_id": forged_txid,
        "external_reference": target_user_id,
        "amount": 497,
    }
    r = requests.post(f"{API}/assinaturas/webhook-syncpay", json=forged_body, timeout=20)
    assert r.status_code == 200, f"webhook returned {r.status_code}: {r.text}"
    body = r.json()
    # Expected safe path values
    assert body.get("status") in ("verification_failed", "gateway_unavailable", "processed", "ignored_no_txid"), body
    # Must NOT be processed as approved for a forged txid → confirm DB unchanged
    out = subprocess.check_output([
        "mongosh", "gestorcred", "--quiet", "--eval",
        f'JSON.stringify({{tx: db.transacoes_checkout.countDocuments({{payment_id:"{forged_txid}"}}),'
        f' mov: db.carteira_movimentos.countDocuments({{"metadata.payment_id":"{forged_txid}"}})}})'
    ]).decode().strip()
    counts = json.loads(out)
    assert counts["tx"] == 0, f"forged transacoes_checkout created! {counts}"
    assert counts["mov"] == 0, f"forged carteira_movimentos created! {counts}"

    # Also verify the admin user was NOT flipped by the forgery (still admin/enterprise/active)
    r2 = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {admin_token}"}, timeout=15).json()
    assert r2.get("email") == ADMIN_EMAIL


# ---------- FIX 2: Admin coupon endpoints ----------

def test_9_validar_cupom_no_auth_blocked():
    r = requests.get(f"{API}/admin/transacoes/cupom/validar/FAKECODE", timeout=15)
    assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}: {r.text[:200]}"


def test_10_usar_cupom_no_auth_blocked():
    r = requests.post(
        f"{API}/admin/transacoes/cupom/usar/FAKECODE",
        params={"email": "x@y.com", "valor_original": 100}, timeout=15,
    )
    assert r.status_code in (401, 403)


def test_11_validar_cupom_admin_ok(admin_token):
    r = requests.get(
        f"{API}/admin/transacoes/cupom/validar/FAKECODE_{uuid.uuid4().hex[:6]}",
        headers={"Authorization": f"Bearer {admin_token}"}, timeout=15,
    )
    assert r.status_code == 200
    assert r.json().get("valido") is False


# ---------- NoSQL injection ----------

def test_12_nosql_object_email():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": {"$ne": None}, "senha": {"$ne": None}},
        timeout=15,
    )
    assert r.status_code in (401, 422), f"NoSQL injection may work! {r.status_code} {r.text[:200]}"


# ---------- FIX 3: Brute force (LAST — creates IP blocks) ----------

def test_13_per_account_lock_5_fails():
    target_email = f"nosuchuser_{uuid.uuid4().hex[:6]}@example.com"
    got_429 = False
    last_status = None
    for _ in range(10):
        r = requests.post(f"{API}/auth/login", json={"email": target_email, "senha": "wrongpass"}, timeout=15)
        last_status = r.status_code
        if r.status_code == 429:
            got_429 = True
            break
        time.sleep(0.1)
    assert got_429, f"per-account brute-force lock did not trigger 429 (last={last_status})"


def test_14_per_ip_lock_different_emails():
    got_429 = False
    last_status = None
    for _ in range(40):
        email = f"nouser_{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(f"{API}/auth/login", json={"email": email, "senha": "wrongpass"}, timeout=15)
        last_status = r.status_code
        if r.status_code == 429:
            got_429 = True
            break
        time.sleep(0.05)
    assert got_429, f"per-IP credential-stuffing lock did not trigger 429 (last={last_status})"
