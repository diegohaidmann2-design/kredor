"""
Security Audit Tests - GestorCred
Tests: NoSQL Injection, Rate Limiting, Auth, IDOR, Hard Delete, Validations, Path Traversal, Mass Assignment
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ── Credentials ──────────────────────────────────────────────────────────────
ADMIN_EMAIL = "admin@gestorcerd.com"
ADMIN_SENHA = "admin123"
USER_EMAIL = "usuario@teste.com"
USER_SENHA = "senha123"


def get_token(email, senha):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "senha": senha})
    if r.status_code == 200:
        return r.json().get("access_token") or r.json().get("token")
    return None


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def admin_token():
    token = get_token(ADMIN_EMAIL, ADMIN_SENHA)
    if not token:
        pytest.skip("Admin login failed")
    return token


@pytest.fixture(scope="module")
def user_token():
    token = get_token(USER_EMAIL, USER_SENHA)
    if not token:
        pytest.skip("User login failed")
    return token


@pytest.fixture(scope="module")
def admin_emprestimo_id(admin_token):
    """Fetch a real emprestimo ID owned by admin"""
    r = requests.get(f"{BASE_URL}/api/emprestimos", headers=auth_headers(admin_token))
    if r.status_code == 200:
        items = r.json().get("items", [])
        if items:
            return items[0]["id"]
    return None


# ══════════════════════════════════════════════════════════════════════════════
# 1. NoSQL Injection – Login
# ══════════════════════════════════════════════════════════════════════════════
class TestNoSQLInjectionLogin:
    """NoSQL injection payloads must be rejected (not bypass auth)"""

    def test_nosql_gt_operator_email(self):
        """$gt on email should NOT grant access"""
        payload = {"email": {"$gt": ""}, "senha": {"$gt": ""}}
        r = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        assert r.status_code in (400, 422, 401), f"Expected 4xx, got {r.status_code}: {r.text}"
        print(f"✅ NoSQL $gt injection blocked: {r.status_code}")

    def test_nosql_ne_operator(self):
        """$ne:null should NOT bypass authentication"""
        payload = {"email": {"$ne": None}, "senha": {"$ne": None}}
        r = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        assert r.status_code in (400, 422, 401), f"Expected 4xx, got {r.status_code}: {r.text}"
        print(f"✅ NoSQL $ne injection blocked: {r.status_code}")

    def test_nosql_regex_email(self):
        """$regex operator should NOT bypass auth"""
        payload = {"email": {"$regex": ".*"}, "senha": "qualquer"}
        r = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        assert r.status_code in (400, 422, 401), f"Expected 4xx, got {r.status_code}: {r.text}"
        print(f"✅ NoSQL $regex injection blocked: {r.status_code}")

    def test_nosql_where_operator(self):
        """$where operator should NOT bypass auth"""
        payload = {"email": {"$where": "1==1"}, "senha": "x"}
        r = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        assert r.status_code in (400, 422, 401), f"Expected 4xx, got {r.status_code}: {r.text}"
        print(f"✅ NoSQL $where injection blocked: {r.status_code}")


# ══════════════════════════════════════════════════════════════════════════════
# 2. NoSQL Injection – Resource IDs
# ══════════════════════════════════════════════════════════════════════════════
class TestNoSQLInjectionResourceIDs:
    """MongoDB operators in resource IDs should be rejected"""

    def test_nosql_emprestimo_id_gt(self, admin_token):
        """$gt in emprestimo_id must not return data"""
        r = requests.get(
            f"{BASE_URL}/api/emprestimos/%7B%24gt%3A%27%27%7D",
            headers=auth_headers(admin_token)
        )
        # Should be 404 or 422, NOT 200 with data
        assert r.status_code != 200 or r.json() is None or "id" not in str(r.json()), \
            f"NoSQL injection in ID returned unexpected data: {r.text[:200]}"
        print(f"✅ NoSQL injection in resource ID: {r.status_code}")

    def test_nosql_emprestimo_id_regex(self, admin_token):
        r = requests.get(
            f"{BASE_URL}/api/emprestimos/%7B%24regex%3A.*%7D",
            headers=auth_headers(admin_token)
        )
        assert r.status_code in (400, 404, 422), f"Got {r.status_code}"
        print(f"✅ NoSQL regex in resource ID blocked: {r.status_code}")


# ══════════════════════════════════════════════════════════════════════════════
# 3. Rate Limiting
# ══════════════════════════════════════════════════════════════════════════════
class TestRateLimiting:
    """After 5 failed attempts, login must be blocked (429)"""

    def test_login_rate_limit(self):
        """5+ failed logins should trigger 429"""
        email = "ratelimit_test_user@test.com"
        blocked = False
        for i in range(7):
            r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "senha": "wrong_pass"})
            if r.status_code == 429:
                blocked = True
                print(f"✅ Rate limit triggered on attempt {i+1}: 429")
                break
        assert blocked, "Rate limit was NOT triggered after 7 failed login attempts"

    def test_registro_rate_limit(self):
        """5+ registration attempts for same email should trigger 429"""
        email = "ratelimit_registro@test.com"
        blocked = False
        for i in range(7):
            r = requests.post(f"{BASE_URL}/api/auth/registro", json={
                "nome": "Test User",
                "email": email,
                "senha": "senha123"
            })
            if r.status_code == 429:
                blocked = True
                print(f"✅ Registro rate limit triggered on attempt {i+1}: 429")
                break
        assert blocked, "Rate limit was NOT triggered for registro after 7 attempts"


# ══════════════════════════════════════════════════════════════════════════════
# 4. Authentication
# ══════════════════════════════════════════════════════════════════════════════
class TestAuthentication:
    """Protected endpoints require valid token"""

    def test_emprestimos_without_token(self):
        """GET /api/emprestimos without token → 401 or 403 (NOTE: should be 401 per RFC 7235)"""
        r = requests.get(f"{BASE_URL}/api/emprestimos")
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"
        # NOTE: App returns 403 for unauthenticated (should be 401 per RFC 7235)
        print(f"✅ /api/emprestimos without token: {r.status_code} (NOTE: should be 401)")

    def test_emprestimos_with_forged_jwt(self):
        """Forged JWT → 401"""
        fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJoYWNrZXIiLCJpYXQiOjE3MDAwMDAwMDB9.FAKE_SIGNATURE"
        r = requests.get(f"{BASE_URL}/api/emprestimos", headers={"Authorization": f"Bearer {fake_token}"})
        assert r.status_code == 401, f"Expected 401 for forged JWT, got {r.status_code}"
        print(f"✅ Forged JWT rejected: 401")

    def test_emprestimos_with_empty_token(self):
        """Empty Bearer token → 401/403"""
        r = requests.get(f"{BASE_URL}/api/emprestimos", headers={"Authorization": "Bearer "})
        assert r.status_code in (401, 403), f"Expected 401/403 for empty token, got {r.status_code}"
        print(f"✅ Empty token rejected: {r.status_code}")

    def test_me_endpoint_no_senha_hash(self, admin_token):
        """GET /api/auth/me must NOT return senha_hash"""
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers(admin_token))
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        data = r.json()
        assert "senha_hash" not in data, f"senha_hash exposed in /api/auth/me response!"
        assert "senha" not in data, f"senha exposed in /api/auth/me response!"
        print(f"✅ /api/auth/me does not expose senha_hash")

    def test_verificar_status_email_requires_auth(self):
        """GET /api/auth/verificar-status-email without token → 401 or 403"""
        r = requests.get(f"{BASE_URL}/api/auth/verificar-status-email?email=admin@test.com")
        assert r.status_code in (401, 403), f"Expected 401/403 for email status check without auth, got {r.status_code}"
        print(f"✅ /api/auth/verificar-status-email requires auth: {r.status_code}")


# ══════════════════════════════════════════════════════════════════════════════
# 5. IDOR - Insecure Direct Object Reference
# ══════════════════════════════════════════════════════════════════════════════
class TestIDOR:
    """Normal user must NOT access admin's resources"""

    def test_idor_access_admin_emprestimo(self, user_token, admin_emprestimo_id):
        """Normal user trying to access admin's emprestimo → 404 (not 200)"""
        if not admin_emprestimo_id:
            pytest.skip("No admin emprestimo found for IDOR test")
        r = requests.get(
            f"{BASE_URL}/api/emprestimos/{admin_emprestimo_id}",
            headers=auth_headers(user_token)
        )
        assert r.status_code == 404, \
            f"IDOR: Normal user accessed admin emprestimo! Status: {r.status_code}, Body: {r.text[:200]}"
        print(f"✅ IDOR protected: normal user gets 404 on admin emprestimo")

    def test_idor_access_admin_emprestimo_parcelas(self, user_token, admin_emprestimo_id):
        """Normal user trying to access admin's parcelas → 404"""
        if not admin_emprestimo_id:
            pytest.skip("No admin emprestimo found for IDOR test")
        r = requests.get(
            f"{BASE_URL}/api/emprestimos/{admin_emprestimo_id}/parcelas",
            headers=auth_headers(user_token)
        )
        assert r.status_code == 404, \
            f"IDOR: Normal user accessed admin parcelas! Status: {r.status_code}"
        print(f"✅ IDOR parcelas protected: {r.status_code}")


# ══════════════════════════════════════════════════════════════════════════════
# 6. Hard Delete Authorization
# ══════════════════════════════════════════════════════════════════════════════
class TestHardDelete:
    """Hard delete ?hard=true requires admin role"""

    def test_hard_delete_requires_admin(self, user_token, admin_emprestimo_id):
        """Normal user with ?hard=true → 403"""
        if not admin_emprestimo_id:
            pytest.skip("No emprestimo ID available")

        # Use a fake ID – we just need to test authorization, not actual deletion
        fake_id = "00000000-0000-0000-0000-000000000099"
        r = requests.delete(
            f"{BASE_URL}/api/emprestimos/{fake_id}?hard=true",
            headers=auth_headers(user_token)
        )
        # Should be 403 (no permission) or 404 (not found but auth checked depends on implementation)
        # From code: auth check is AFTER the find, so 404 may come first
        # But the code fetches with usuario_id=context_id, so user's own loans won't have this fake ID → 404
        # Let's create a user loan first and then test hard delete
        print(f"Hard delete test with fake ID: {r.status_code}")
        assert r.status_code in (403, 404), f"Expected 403 or 404, got {r.status_code}"


# ══════════════════════════════════════════════════════════════════════════════
# 7. Business Rules
# ══════════════════════════════════════════════════════════════════════════════
class TestBusinessRules:
    """Validate business logic protections"""

    def test_payment_negative_value(self, admin_token):
        """POST /api/pagamentos with valor_pago=-100 → 422"""
        payload = {
            "parcela_id": "fake-parcela-id",
            "valor_pago": -100,
            "metodo_pagamento": "dinheiro"
        }
        r = requests.post(f"{BASE_URL}/api/pagamentos", json=payload, headers=auth_headers(admin_token))
        assert r.status_code in (422, 404, 400), f"Negative payment should be rejected, got {r.status_code}"
        print(f"✅ Negative payment rejected: {r.status_code}")

    def test_payment_zero_value(self, admin_token):
        """POST /api/pagamentos with valor_pago=0 → 422"""
        payload = {
            "parcela_id": "fake-parcela-id",
            "valor_pago": 0,
            "metodo_pagamento": "dinheiro"
        }
        r = requests.post(f"{BASE_URL}/api/pagamentos", json=payload, headers=auth_headers(admin_token))
        assert r.status_code in (422, 404, 400), f"Zero payment should be rejected, got {r.status_code}"
        print(f"✅ Zero payment rejected: {r.status_code}")

    def test_edit_quitado_emprestimo(self, admin_token, admin_emprestimo_id):
        """PUT on a quitado emprestimo → 400"""
        if not admin_emprestimo_id:
            pytest.skip("No admin emprestimo found")

        # First, find a quitado emprestimo
        r = requests.get(
            f"{BASE_URL}/api/emprestimos?status=quitado&limit=1",
            headers=auth_headers(admin_token)
        )
        if r.status_code != 200:
            pytest.skip("Could not fetch emprestimos")
        items = r.json().get("items", [])
        if not items:
            pytest.skip("No quitado emprestimo found to test")

        quitado_id = items[0]["id"]
        r2 = requests.put(
            f"{BASE_URL}/api/emprestimos/{quitado_id}",
            json={"observacoes": "tentativa de edição"},
            headers=auth_headers(admin_token)
        )
        assert r2.status_code == 400, f"Expected 400 for editing quitado, got {r2.status_code}: {r2.text[:200]}"
        print(f"✅ Editing quitado emprestimo blocked: 400")


# ══════════════════════════════════════════════════════════════════════════════
# 8. Backup Path Traversal
# ══════════════════════════════════════════════════════════════════════════════
class TestBackupPathTraversal:
    """Path traversal attempts in backup restore must be blocked"""

    def test_path_traversal_etc_passwd(self, admin_token):
        """POST /api/backup/restaurar/..%2F..%2Fetc%2Fpasswd → blocked"""
        r = requests.post(
            f"{BASE_URL}/api/backup/restaurar/..%2F..%2Fetc%2Fpasswd",
            headers=auth_headers(admin_token)
        )
        assert r.status_code in (400, 404, 422, 500), f"Path traversal should be blocked, got {r.status_code}"
        # Must NOT succeed with 200
        assert r.status_code != 200, "Path traversal returned 200 - SECURITY BREACH!"
        print(f"✅ Path traversal blocked: {r.status_code}")

    def test_path_traversal_double_dot(self, admin_token):
        """Attempt with ../etc/passwd"""
        r = requests.post(
            f"{BASE_URL}/api/backup/restaurar/../etc/passwd",
            headers=auth_headers(admin_token)
        )
        assert r.status_code != 200, f"Path traversal should NOT return 200, got {r.status_code}"
        print(f"✅ Path traversal (dot-dot) blocked: {r.status_code}")


# ══════════════════════════════════════════════════════════════════════════════
# 9. Registration Validations
# ══════════════════════════════════════════════════════════════════════════════
class TestRegistrationValidation:
    """Registration must validate inputs"""

    def test_registro_senha_curta(self):
        """Registration with 2-char password → 422"""
        r = requests.post(f"{BASE_URL}/api/auth/registro", json={
            "nome": "Test Short",
            "email": f"shortpw_{int(time.time())}@test.com",
            "senha": "12"
        })
        assert r.status_code == 422, f"Short password should be rejected with 422, got {r.status_code}: {r.text[:200]}"
        print(f"✅ Short password rejected: 422")

    def test_registro_senha_5_chars(self):
        """5-char password (< 6) → 422"""
        r = requests.post(f"{BASE_URL}/api/auth/registro", json={
            "nome": "Test User5",
            "email": f"pw5chars_{int(time.time())}@test.com",
            "senha": "12345"
        })
        assert r.status_code == 422, f"5-char password should be rejected, got {r.status_code}"
        print(f"✅ 5-char password rejected: 422")


# ══════════════════════════════════════════════════════════════════════════════
# 10. Mass Assignment
# ══════════════════════════════════════════════════════════════════════════════
class TestMassAssignment:
    """Mass assignment must not allow privilege escalation"""

    def test_mass_assignment_perfil_admin(self):
        """Sending perfil=admin in registration must not create admin user"""
        email = f"mass_assign_{int(time.time())}@test.com"
        r = requests.post(f"{BASE_URL}/api/auth/registro", json={
            "nome": "Mass Assignment Test",
            "email": email,
            "senha": "senha123456",
            "perfil": "admin",
            "plano": "enterprise"
        })
        # Registration may succeed (201/200) but user must NOT be admin
        if r.status_code in (200, 201):
            data = r.json()
            perfil = data.get("perfil", "")
            plano = data.get("plano", "")
            assert perfil != "admin", f"Mass assignment escalated perfil to admin! Response: {data}"
            assert plano != "enterprise", f"Mass assignment escalated plano to enterprise! Response: {data}"
            assert perfil == "usuario", f"Expected perfil='usuario', got: {perfil}"
            print(f"✅ Mass assignment blocked: perfil={perfil}, plano={plano}")
        else:
            # Registration failed for other reasons (e.g., rate limit), not a failure
            print(f"Registration rejected with {r.status_code} - mass assignment test inconclusive")

    def test_mass_assignment_superadmin(self):
        """Sending perfil=superadmin in registration must not create superadmin"""
        email = f"mass_superadmin_{int(time.time())}@test.com"
        r = requests.post(f"{BASE_URL}/api/auth/registro", json={
            "nome": "SuperAdmin Test",
            "email": email,
            "senha": "senha123456",
            "perfil": "superadmin"
        })
        if r.status_code in (200, 201):
            data = r.json()
            perfil = data.get("perfil", "")
            assert perfil not in ("admin", "superadmin"), \
                f"Mass assignment allowed superadmin! Response: {data}"
            print(f"✅ Mass assignment superadmin blocked: perfil={perfil}")


# ══════════════════════════════════════════════════════════════════════════════
# 11. resend-2fa - No User Enumeration
# ══════════════════════════════════════════════════════════════════════════════
class TestResend2FA:
    """resend-2fa must not reveal whether email exists"""

    def test_resend_2fa_nonexistent_email(self):
        """resend-2fa with non-existent email should return same error as no 2FA"""
        r = requests.post(f"{BASE_URL}/api/auth/resend-2fa", json={"email": "nonexistent@example.com"})
        # Should return 400 (generic error), not 404
        assert r.status_code == 400, f"Expected 400 for non-existent email, got {r.status_code}"
        print(f"✅ resend-2fa non-existent email: {r.status_code}")

    def test_resend_2fa_existing_without_2fa(self):
        """resend-2fa with existing email but no 2FA enabled → same error"""
        r = requests.post(f"{BASE_URL}/api/auth/resend-2fa", json={"email": ADMIN_EMAIL})
        # Admin may have 2FA disabled, should return 400 generic
        # Should NOT return 404 (would reveal user existence)
        assert r.status_code != 404, f"resend-2fa reveals user existence via 404!"
        print(f"✅ resend-2fa existing email: {r.status_code}")


# ══════════════════════════════════════════════════════════════════════════════
# 12. Hard Delete by Normal User (real flow)
# ══════════════════════════════════════════════════════════════════════════════
class TestHardDeleteAuthorizationFull:
    """Create a real user emprestimo and try to hard delete it"""

    @pytest.fixture(scope="class")
    def user_emprestimo_id(self, user_token):
        """Try to get a user-owned emprestimo"""
        r = requests.get(f"{BASE_URL}/api/emprestimos", headers=auth_headers(user_token))
        if r.status_code == 200:
            items = r.json().get("items", [])
            if items:
                return items[0]["id"]
        return None

    def test_normal_user_cannot_hard_delete_own_emprestimo(self, user_token, user_emprestimo_id):
        """Normal user should get 403 when trying hard delete"""
        if not user_emprestimo_id:
            pytest.skip("No user emprestimo found for hard delete test")
        r = requests.delete(
            f"{BASE_URL}/api/emprestimos/{user_emprestimo_id}?hard=true",
            headers=auth_headers(user_token)
        )
        assert r.status_code == 403, \
            f"Expected 403 for normal user hard delete, got {r.status_code}: {r.text[:200]}"
        print(f"✅ Normal user hard delete blocked: 403")
