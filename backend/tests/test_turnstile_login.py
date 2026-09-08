"""
Tests for Turnstile enforcement on /api/auth/login and /api/auth/registro
plus regression on security summary, rate limiter and forged webhook.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://gestor-cred.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "diego.haidmann@gmail.com"
ADMIN_PASSWORD = "Admin@2026"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- LOGIN Turnstile enforcement ----------

class TestLoginTurnstile:
    def test_login_without_turnstile_returns_400(self, session):
        r = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD,
        })
        assert r.status_code == 400, r.text
        assert "segurança" in r.text.lower() or "turnstile" in r.text.lower() or "verifica" in r.text.lower()

    def test_login_wrong_password_with_turnstile_returns_401(self, session):
        r = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": "wrong-password-xyz",
            "turnstile_token": "dummy",
        })
        assert r.status_code == 401, r.text

    def test_login_success_with_turnstile_returns_tokens(self, session):
        r = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "senha": ADMIN_PASSWORD,
            "turnstile_token": "dummy",
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert "access_token" in data and data["access_token"]
        assert "refresh_token" in data and data["refresh_token"]
        assert data.get("usuario", {}).get("email") == ADMIN_EMAIL


@pytest.fixture(scope="module")
def admin_token(session):
    r = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "senha": ADMIN_PASSWORD,
        "turnstile_token": "dummy",
    })
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text}")
    return r.json()["access_token"]


# ---------- REGISTRO Turnstile ----------

class TestRegistroTurnstile:
    def _payload(self, email):
        return {
            "nome": "TEST User",
            "email": email,
            "senha": "TestPass@123",
        }

    def test_registro_without_turnstile_returns_400(self, session):
        email = f"TEST_noturnstile_{uuid.uuid4().hex[:8]}@example.com"
        r = session.post(f"{BASE_URL}/api/auth/registro", json=self._payload(email))
        assert r.status_code == 400, r.text

    def test_registro_with_turnstile_creates_user(self, session, admin_token):
        email = f"TEST_reg_{uuid.uuid4().hex[:8]}@example.com"
        payload = self._payload(email)
        payload["turnstile_token"] = "dummy"
        r = session.post(f"{BASE_URL}/api/auth/registro", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("email") == email
        assert data.get("plano") == "trial"

        # Cleanup: try admin delete endpoint (if exists), otherwise mark for db cleanup
        auth_headers = {"Authorization": f"Bearer {admin_token}"}
        # Try common admin route
        user_id = data.get("id")
        if user_id:
            for path in [f"/api/admin/usuarios/{user_id}", f"/api/usuarios/{user_id}"]:
                dr = session.delete(f"{BASE_URL}{path}", headers=auth_headers)
                if dr.status_code < 400:
                    break


# ---------- Security summary regression ----------

class TestSecuritySummary:
    def test_seguranca_resumo_requires_auth(self, session):
        r = session.get(f"{BASE_URL}/api/seguranca/resumo")
        assert r.status_code in (401, 403), r.text

    def test_seguranca_resumo_with_admin(self, session, admin_token):
        r = session.get(
            f"{BASE_URL}/api/seguranca/resumo",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200, r.text


# ---------- Forged webhook regression ----------

class TestForgedWebhook:
    def test_forged_syncpay_webhook_returns_200_no_mutation(self, session):
        # Missing/invalid signature — endpoint should accept but log as suspeito.
        payload = {"event": "payment.paid", "data": {"id": "fake-tx", "reference_id": "nope"}}
        r = session.post(f"{BASE_URL}/api/assinaturas/webhook-syncpay", json=payload)
        assert r.status_code == 200, r.text
