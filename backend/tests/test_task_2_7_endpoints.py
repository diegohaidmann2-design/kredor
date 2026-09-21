"""Task 2.7 — verify backend admin endpoints return 403 for usuario and 200 for admin."""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://gestorcred-staging-2.preview.emergentagent.com").rstrip("/")

ADMIN_ENDPOINTS = [
    "/api/superadmin/dashboard",
    "/api/assinaturas/gateway/config",
    "/api/notificacoes/admin/todas",
]


def _login(email: str, senha: str) -> str:
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "senha": senha, "turnstile_token": "test"},
        timeout=30,
    )
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("token") or data.get("access_token")
    assert token, f"No token in login response: {data}"
    return token


@pytest.fixture(scope="module")
def usuario_token():
    return _login("usuario@teste.com", "senha123")


@pytest.fixture(scope="module")
def admin_token():
    return _login("admin@gestorcerd.com", "admin123")


@pytest.mark.parametrize("endpoint", ADMIN_ENDPOINTS)
def test_usuario_blocked_403(usuario_token, endpoint):
    r = requests.get(f"{BASE_URL}{endpoint}", headers={"Authorization": f"Bearer {usuario_token}"}, timeout=30)
    assert r.status_code == 403, f"Expected 403 for usuario on {endpoint}, got {r.status_code}: {r.text[:200]}"


@pytest.mark.parametrize("endpoint", ADMIN_ENDPOINTS)
def test_admin_allowed_200(admin_token, endpoint):
    r = requests.get(f"{BASE_URL}{endpoint}", headers={"Authorization": f"Bearer {admin_token}"}, timeout=30)
    assert r.status_code == 200, f"Expected 200 for admin on {endpoint}, got {r.status_code}: {r.text[:200]}"
