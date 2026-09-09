"""
Regression suite for the Kredor import + main-agent edits.
Covers: auth login, clientes/emprestimos listings, emprestimos detail/parcelas,
relatorios generation, admin_transacoes exports, suporte tickets, upload refactor.
"""
import io
import os
import re
import struct
import zlib
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL is missing from env and /app/frontend/.env")
BASE_URL = base_url.rstrip("/")


# ---------------------------------------------------------------- fixtures
@pytest.fixture(scope="session")
def test_credentials():
    credentials_path = Path("/app/memory/test_credentials.md")
    if not credentials_path.exists():
        pytest.skip("Missing /app/memory/test_credentials.md")
    content = credentials_path.read_text(encoding="utf-8")
    email = re.search(r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?email(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    senha = re.search(r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?senha(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    if not email or not senha:
        pytest.skip("No email/senha found in test_credentials.md")
    return {"email": email.group(1), "senha": senha.group(1)}


@pytest.fixture(scope="session")
def api_client():
    s = requests.Session()
    return s


@pytest.fixture(scope="session")
def auth_token(api_client, test_credentials):
    r = api_client.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": test_credentials["email"], "senha": test_credentials["senha"]},
        timeout=60,
    )
    if r.status_code != 200:
        pytest.fail(f"Login failed {r.status_code}: {r.text[:500]}")
    token = r.json().get("access_token")
    if not token:
        pytest.fail(f"No access_token in login response: {r.text[:300]}")
    return token


@pytest.fixture(scope="session")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


def _png_bytes():
    """Build a minimal valid 1x1 PNG without external deps."""
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00\xff\x00\x00"
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


# ---------------------------------------------------------------- auth
class TestAuth:
    def test_login_success(self, api_client, test_credentials):
        r = api_client.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": test_credentials["email"], "senha": test_credentials["senha"]},
            timeout=60,
        )
        assert r.status_code == 200, r.text[:500]
        data = r.json()
        assert isinstance(data.get("access_token"), str) and data["access_token"]
        assert isinstance(data.get("refresh_token"), str) and data["refresh_token"]

    def test_login_invalid_password(self, api_client, test_credentials):
        r = api_client.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": test_credentials["email"], "senha": "senha-errada-xyz"},
            timeout=60,
        )
        assert r.status_code in (400, 401), f"{r.status_code}: {r.text[:300]}"

    def test_me_endpoint(self, api_client, auth_headers, test_credentials):
        r = api_client.get(f"{BASE_URL}/api/auth/me", headers=auth_headers, timeout=60)
        assert r.status_code == 200, r.text[:500]
        body = r.json()
        blob = str(body)
        assert test_credentials["email"] in blob
        assert "_id" not in body

    def test_protected_requires_token(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/clientes", timeout=60)
        assert r.status_code in (401, 403), f"{r.status_code}: {r.text[:200]}"


# ------------------------------------------------- imported data listings
class TestImportedData:
    def test_listar_clientes(self, api_client, auth_headers):
        r = api_client.get(f"{BASE_URL}/api/clientes", headers=auth_headers, timeout=90)
        assert r.status_code == 200, r.text[:500]
        data = r.json()
        assert "items" in data and "pagination" in data, f"unexpected shape: {list(data)[:5]}"
        assert isinstance(data["items"], list)
        assert data["pagination"].get("total", 0) > 0, "no imported clientes returned"
        for item in data["items"][:5]:
            assert "_id" not in item
            assert "id" in item

    def test_listar_emprestimos(self, api_client, auth_headers):
        r = api_client.get(f"{BASE_URL}/api/emprestimos", headers=auth_headers, timeout=90)
        assert r.status_code == 200, r.text[:500]
        data = r.json()
        assert "items" in data and "pagination" in data
        assert data["pagination"].get("total", 0) > 0, "no imported emprestimos returned"
        for item in data["items"][:5]:
            assert "_id" not in item

    def test_emprestimo_detalhe_e_parcelas(self, api_client, auth_headers):
        lst = api_client.get(
            f"{BASE_URL}/api/emprestimos", headers=auth_headers, timeout=90
        )
        assert lst.status_code == 200, lst.text[:300]
        items = lst.json()["items"]
        assert items, "no emprestimos to drill into"
        checked = 0
        for emp in items[:3]:
            eid = emp["id"]
            det = api_client.get(
                f"{BASE_URL}/api/emprestimos/{eid}", headers=auth_headers, timeout=90
            )
            assert det.status_code == 200, f"GET /emprestimos/{eid} -> {det.status_code}: {det.text[:300]}"
            assert det.json()["id"] == eid
            par = api_client.get(
                f"{BASE_URL}/api/emprestimos/{eid}/parcelas", headers=auth_headers, timeout=90
            )
            assert par.status_code == 200, f"parcelas {eid} -> {par.status_code}: {par.text[:300]}"
            assert isinstance(par.json(), list)
            checked += 1
        assert checked >= 1

    def test_emprestimo_inexistente_404(self, api_client, auth_headers):
        r = api_client.get(
            f"{BASE_URL}/api/emprestimos/nao-existe-123", headers=auth_headers, timeout=60
        )
        assert r.status_code == 404, f"{r.status_code}: {r.text[:300]}"

    def test_dashboard(self, api_client, auth_headers):
        r = api_client.get(f"{BASE_URL}/api/dashboard", headers=auth_headers, timeout=90)
        assert r.status_code in (200, 404), r.text[:300]


# ---------------------------------------------------------------- relatorios
class TestRelatorios:
    @pytest.mark.parametrize("tipo", ["clientes", "emprestimos"])
    def test_gerar_relatorio_pdf(self, api_client, auth_headers, tipo):
        r = api_client.post(
            f"{BASE_URL}/api/relatorios/gerar",
            headers=auth_headers,
            json={"tipo": tipo, "formato": "pdf", "periodo": "ano"},
            timeout=180,
        )
        assert r.status_code in (200, 404), f"{r.status_code}: {r.text[:500]}"
        if r.status_code == 200:
            assert len(r.content) > 100

    def test_gerar_relatorio_excel(self, api_client, auth_headers):
        r = api_client.post(
            f"{BASE_URL}/api/relatorios/gerar",
            headers=auth_headers,
            json={"tipo": "clientes", "formato": "excel", "periodo": "ano"},
            timeout=180,
        )
        assert r.status_code in (200, 404), f"{r.status_code}: {r.text[:500]}"


# ------------------------------------------------------- admin transacoes
class TestAdminTransacoes:
    def test_listar(self, api_client, auth_headers):
        r = api_client.get(f"{BASE_URL}/api/admin/transacoes/", headers=auth_headers, timeout=90)
        assert r.status_code == 200, f"{r.status_code}: {r.text[:500]}"
        for t in r.json().get("transacoes", []):
            assert "_id" not in t, "raw mongo _id leaked in transacoes listing"

    def test_exportar_json(self, api_client, auth_headers):
        r = api_client.get(
            f"{BASE_URL}/api/admin/transacoes/exportar", headers=auth_headers, timeout=90
        )
        assert r.status_code == 200, f"{r.status_code}: {r.text[:500]}"
        data = r.json()
        assert data.get("success") is True
        assert "dados" in data and isinstance(data["dados"], list)
        for row in data["dados"]:
            assert "_id" not in row, "raw mongo _id leaked in exportar payload"

    def test_exportar_csv(self, api_client, auth_headers):
        r = api_client.get(
            f"{BASE_URL}/api/admin/transacoes/exportar/csv", headers=auth_headers, timeout=90
        )
        assert r.status_code == 200, f"{r.status_code}: {r.text[:500]}"

    def test_metricas(self, api_client, auth_headers):
        r = api_client.get(
            f"{BASE_URL}/api/admin/transacoes/metricas", headers=auth_headers, timeout=90
        )
        assert r.status_code == 200, f"{r.status_code}: {r.text[:500]}"


# ---------------------------------------------------------------- suporte
class TestSuporte:
    def test_tickets_usuario(self, api_client, auth_headers):
        r = api_client.get(f"{BASE_URL}/api/suporte/tickets", headers=auth_headers, timeout=90)
        assert r.status_code == 200, f"{r.status_code}: {r.text[:500]}"
        assert isinstance(r.json(), list)

    def test_tickets_admin(self, api_client, auth_headers):
        r = api_client.get(
            f"{BASE_URL}/api/suporte/admin/tickets", headers=auth_headers, timeout=90
        )
        assert r.status_code == 200, f"{r.status_code}: {r.text[:500]}"
        assert isinstance(r.json(), list)

    def test_estatisticas_admin(self, api_client, auth_headers):
        r = api_client.get(
            f"{BASE_URL}/api/suporte/admin/estatisticas", headers=auth_headers, timeout=90
        )
        assert r.status_code == 200, f"{r.status_code}: {r.text[:500]}"


# ------------------------------------------------------------------ upload
class TestUpload:
    def test_upload_png_and_serve(self, api_client, auth_headers):
        png = _png_bytes()
        r = api_client.post(
            f"{BASE_URL}/api/upload/upload",
            headers=auth_headers,
            files={"file": ("TEST_pixel.png", io.BytesIO(png), "image/png")},
            timeout=180,
        )
        assert r.status_code == 200, f"upload -> {r.status_code}: {r.text[:500]}"
        data = r.json()
        assert data.get("success") is True
        url = data.get("url", "")
        assert url.startswith("/api/upload/files/"), f"unexpected url: {url}"
        assert data.get("type") == "imagem"

        # Serve without auth header
        g = requests.get(f"{BASE_URL}{url}", timeout=120)
        assert g.status_code == 200, f"serve -> {g.status_code}: {g.text[:300]}"
        assert g.headers.get("content-type", "").startswith("image/png"), g.headers.get("content-type")
        assert g.content == png, "served bytes differ from uploaded bytes"

    def test_upload_rejects_bad_extension(self, api_client, auth_headers):
        r = api_client.post(
            f"{BASE_URL}/api/upload/upload",
            headers=auth_headers,
            files={"file": ("TEST_evil.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
            timeout=120,
        )
        assert r.status_code == 400, f"{r.status_code}: {r.text[:300]}"

    def test_upload_requires_auth(self, api_client):
        r = api_client.post(
            f"{BASE_URL}/api/upload/upload",
            files={"file": ("TEST_pixel.png", io.BytesIO(_png_bytes()), "image/png")},
            timeout=120,
        )
        assert r.status_code in (401, 403), f"{r.status_code}: {r.text[:300]}"

    def test_serve_unknown_path_404(self, api_client):
        r = api_client.get(
            f"{BASE_URL}/api/upload/files/gestorcred/uploads/none/does-not-exist.png", timeout=60
        )
        assert r.status_code == 404, f"{r.status_code}: {r.text[:300]}"
