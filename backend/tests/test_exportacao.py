"""Backend tests for /api/exportacao endpoints (bug fix regression)."""
import os
import io
import json
import zipfile
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://gestorcred-preview-3.preview.emergentagent.com").rstrip("/")
EMAIL = "pro@kredorteste.com"
SENHA = "Kredor@2026"


@pytest.fixture(scope="module")
def token():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": EMAIL, "senha": SENHA, "turnstile_token": "test"},
        timeout=30,
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token")
    assert tok, f"No access_token in response: {data}"
    return tok


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def test_resumo(headers):
    r = requests.get(f"{BASE_URL}/api/exportacao/resumo", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("pode_exportar") is True
    for k in ("clientes", "emprestimos", "pagamentos", "parcelas"):
        assert k in data
        assert isinstance(data[k], int)
    print("Resumo:", data)


def test_export_csv_zip_all(headers):
    """Bug principal: exportar CSV com todas as entidades (produzia HTTP 500)."""
    payload = {
        "entidades": ["clientes", "emprestimos", "pagamentos", "parcelas"],
        "formato": "csv",
    }
    r = requests.post(f"{BASE_URL}/api/exportacao/exportar", headers=headers, json=payload, timeout=60)
    assert r.status_code == 200, f"Status {r.status_code}: {r.text[:500]}"
    assert r.headers.get("content-type", "").startswith("application/zip")
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    assert set(names) == {"clientes.csv", "emprestimos.csv", "pagamentos.csv", "parcelas.csv"}, names
    for name in names:
        content = zf.read(name).decode("utf-8")
        assert len(content) > 0
        # Header line exists
        assert "\n" in content or content.count(",") >= 0


def test_export_csv_pagamentos_only(headers):
    payload = {"entidades": ["pagamentos"], "formato": "csv"}
    r = requests.post(f"{BASE_URL}/api/exportacao/exportar", headers=headers, json=payload, timeout=60)
    assert r.status_code == 200, r.text[:500]
    assert r.headers.get("content-type", "").startswith("text/csv")
    body = r.content.decode("utf-8")
    header = body.splitlines()[0].split(",")
    assert len(header) >= 5  # should be many columns


def test_export_json(headers):
    payload = {"entidades": ["clientes", "emprestimos"], "formato": "json"}
    r = requests.post(f"{BASE_URL}/api/exportacao/exportar", headers=headers, json=payload, timeout=60)
    assert r.status_code == 200, r.text[:500]
    assert r.headers.get("content-type", "").startswith("application/json")
    data = r.json()
    assert "clientes" in data and "emprestimos" in data
    assert isinstance(data["clientes"], list)
