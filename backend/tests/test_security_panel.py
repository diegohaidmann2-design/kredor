"""
Testes de segurança - Turnstile + Painel de Segurança + Rate limit + Regressão.
Executado contra a URL pública (REACT_APP_BACKEND_URL).
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback pra rodar isoladamente
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

ADMIN_EMAIL = "diego.haidmann@gmail.com"
ADMIN_SENHA = "Admin@2026"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "senha": ADMIN_SENHA},
        timeout=30,
    )
    assert r.status_code == 200, f"Admin login falhou: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, "sem token"
    return tok


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ---------- Turnstile ----------
class TestTurnstile:
    def test_registro_sem_turnstile_400(self):
        email = f"qa_notoken_{uuid.uuid4().hex[:6]}_qa@example.com"
        r = requests.post(f"{BASE_URL}/api/auth/registro", json={
            "nome": "QA No Token",
            "email": email,
            "senha": "senha123",
        }, timeout=30)
        assert r.status_code == 400, f"esperado 400 sem token, veio {r.status_code}: {r.text}"
        # confirmar via API /auth/login que usuário não existe (login retorna 401)
        r2 = requests.post(f"{BASE_URL}/api/auth/login",
                           json={"email": email, "senha": "senha123"}, timeout=30)
        assert r2.status_code == 401

    def test_registro_com_turnstile_ok(self):
        email = f"qa_ok_{uuid.uuid4().hex[:6]}_qa@example.com"
        r = requests.post(f"{BASE_URL}/api/auth/registro", json={
            "nome": "QA With Token",
            "email": email,
            "senha": "senha123",
            "turnstile_token": "TEST-TOKEN-ACCEPTS-ANY",
        }, timeout=30)
        assert r.status_code == 200, f"esperado 200, veio {r.status_code}: {r.text}"
        body = r.json()
        assert body.get("email") == email
        # cleanup
        pytest.created_email = email


def _cleanup_created_user():
    email = getattr(pytest, "created_email", None)
    if not email:
        return
    import subprocess
    subprocess.run(
        ["mongosh", "gestorcred", "--quiet", "--eval",
         f'db.usuarios.deleteMany({{email: "{email}"}}); '
         f'db.login_attempts.deleteMany({{email: {{$regex: "{email}"}}}});'],
        capture_output=True
    )


# ---------- Painel de Segurança ----------
class TestSecurityPanel:
    def test_resumo_sem_token_401(self):
        r = requests.get(f"{BASE_URL}/api/seguranca/resumo", timeout=30)
        assert r.status_code in (401, 403), f"esperado 401/403, veio {r.status_code}"

    def test_resumo_admin_200(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/seguranca/resumo",
                         headers=admin_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        for k in ("contas_bloqueadas", "ips_bloqueados",
                  "tentativas_ativas", "webhooks_suspeitos"):
            assert k in data, f"faltando {k}"

    def test_login_bloqueios_admin(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/seguranca/login-bloqueios",
                         headers=admin_headers, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "contas" in data and "ips" in data

    def test_webhooks_suspeitos_admin(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/seguranca/webhooks-suspeitos",
                         headers=admin_headers, timeout=30)
        assert r.status_code == 200
        assert "itens" in r.json()

    def test_forjar_webhook_e_ver_no_painel(self, admin_headers):
        # Contar antes
        r1 = requests.get(f"{BASE_URL}/api/seguranca/webhooks-suspeitos",
                          headers=admin_headers, timeout=30)
        antes = r1.json().get("total", 0)

        # Enviar webhook forjado
        forged = {
            "event": "cashin.onUpdate",
            "status": "completed",
            "transaction_id": f"FORGED-QA-{uuid.uuid4().hex[:6]}",
            "external_reference": "x",
            "amount": 497,
        }
        r2 = requests.post(f"{BASE_URL}/api/assinaturas/webhook-syncpay",
                           json=forged, timeout=30)
        assert r2.status_code == 200, f"webhook status {r2.status_code}: {r2.text}"

        time.sleep(1)
        r3 = requests.get(f"{BASE_URL}/api/seguranca/webhooks-suspeitos",
                          headers=admin_headers, timeout=30)
        depois = r3.json().get("total", 0)
        assert depois >= antes + 1, f"webhook suspeito não registrado (antes={antes}, depois={depois})"


# ---------- Rate limit MongoDB shared ----------
class TestRateLimitMongo:
    def test_rate_limits_collection_populated(self):
        # Faz alguns requests
        for _ in range(3):
            requests.get(f"{BASE_URL}/api/assinaturas/planos", timeout=15)
        import subprocess
        out = subprocess.run(
            ["mongosh", "gestorcred", "--quiet", "--eval",
             "print(db.rate_limits.countDocuments({})); "
             "print(JSON.stringify(db.rate_limits.getIndexes()));"],
            capture_output=True, text=True
        )
        combined = out.stdout
        # Alguma doc deve existir
        lines = [l for l in combined.splitlines() if l.strip()]
        assert lines, f"mongosh sem saida: {combined}"
        count = int(lines[0])
        assert count >= 1, f"rate_limits vazio: {combined}"
        # Índice TTL presente
        assert "expire_at" in combined and "expireAfterSeconds" in combined, combined


# ---------- Regressão ----------
class TestRegression:
    def test_admin_login_ok(self, admin_token):
        assert admin_token

    def test_auth_me(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=admin_headers, timeout=30)
        assert r.status_code == 200

    def test_public_planos(self):
        r = requests.get(f"{BASE_URL}/api/assinaturas/planos", timeout=30)
        assert r.status_code == 200

    def test_public_landing(self):
        r = requests.get(f"{BASE_URL}/api/configuracoes/landing", timeout=30)
        assert r.status_code == 200

    def test_cupom_endpoints_require_admin(self):
        r1 = requests.get(f"{BASE_URL}/api/admin/transacoes/cupom/validar/X", timeout=30)
        assert r1.status_code in (401, 403), r1.status_code
        r2 = requests.post(f"{BASE_URL}/api/admin/transacoes/cupom/usar/X", timeout=30)
        assert r2.status_code in (401, 403), r2.status_code


def teardown_module(module):
    _cleanup_created_user()
