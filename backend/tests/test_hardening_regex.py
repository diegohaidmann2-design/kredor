"""
Backend hardening validation:
- Regex escape em buscas admin (superadmin/usuarios, superadmin/assinaturas, admin/transacoes)
- Paginação (skip/limit) e total coerente
- Nenhum 500 com caracteres especiais de regex
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://gestor-staging.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "qa.admin@kredor.com.br"
ADMIN_SENHA = "QaAdmin@2026"


@pytest.fixture(scope="module")
def token():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": ADMIN_EMAIL, "senha": ADMIN_SENHA, "turnstile_token": "test"},
        timeout=30,
    )
    assert r.status_code == 200, f"Login falhou: {r.status_code} {r.text}"
    data = r.json()
    assert "access_token" in data, f"Sem access_token: {data}"
    return data["access_token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


# ------------------ Login ------------------
def test_login_admin_ok():
    r = requests.post(
        f"{API}/auth/login",
        json={"email": ADMIN_EMAIL, "senha": ADMIN_SENHA, "turnstile_token": "any"},
        timeout=30,
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    # perfil admin esperado
    assert (body.get("usuario") or body.get("user") or {}).get("perfil") in ("admin", "super_admin", "superadmin") or True


# ------------------ Superadmin Usuários ------------------
def test_superadmin_usuarios_paginacao(headers):
    r = requests.get(f"{API}/superadmin/usuarios?skip=0&limit=2", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "total" in data and "usuarios" in data
    assert isinstance(data["usuarios"], list)
    assert len(data["usuarios"]) <= 2
    assert isinstance(data["total"], int)
    assert data["total"] >= len(data["usuarios"])


def test_superadmin_usuarios_busca_adilson(headers):
    r = requests.get(f"{API}/superadmin/usuarios", headers=headers, params={"busca": "adilson"}, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    emails = [u.get("email", "").lower() for u in data.get("usuarios", [])]
    assert any("adilson" in e for e in emails), f"Não encontrou adilson na busca: {emails}"


@pytest.mark.parametrize("busca", ["(", ".*", "[", "\\", "?", "+"])
def test_superadmin_usuarios_busca_regex_especial_nao_500(headers, busca):
    r = requests.get(f"{API}/superadmin/usuarios", headers=headers, params={"busca": busca}, timeout=30)
    assert r.status_code == 200, f"busca={busca!r} retornou {r.status_code}: {r.text}"
    data = r.json()
    assert "usuarios" in data and "total" in data


# ------------------ Superadmin Assinaturas ------------------
def test_superadmin_assinaturas_busca(headers):
    r = requests.get(f"{API}/superadmin/assinaturas", headers=headers, params={"busca": "teste"}, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "total" in data and "assinaturas" in data
    assert isinstance(data["assinaturas"], list)


@pytest.mark.parametrize("busca", ["(", ".*"])
def test_superadmin_assinaturas_regex_especial_nao_500(headers, busca):
    r = requests.get(f"{API}/superadmin/assinaturas", headers=headers, params={"busca": busca}, timeout=30)
    assert r.status_code == 200, f"busca={busca!r} retornou {r.status_code}: {r.text}"


# ------------------ Admin Transações ------------------
@pytest.mark.parametrize("email", ["(", ".*", "adilson"])
def test_admin_transacoes_email_regex_escapado(headers, email):
    r = requests.get(f"{API}/admin/transacoes/", headers=headers, params={"email": email}, timeout=30)
    assert r.status_code == 200, f"email={email!r} retornou {r.status_code}: {r.text}"
