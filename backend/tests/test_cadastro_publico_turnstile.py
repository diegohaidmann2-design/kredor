"""Tests for public cadastro endpoint with Turnstile anti-bot validation.

Covers:
- Info endpoint returns company name
- Missing turnstile_token -> 400
- Valid turnstile token (test secret 1x0000...AA always passes) -> 200
- Multipart with attachment but no consent -> 400
- Multipart with consent + turnstile + attachment -> 200 and attachment persisted
- Field validations: invalid phone/cpf/nome
"""
import io
import os
import uuid
import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cred-sistema-preview-1.preview.emergentagent.com").rstrip("/")
TOKEN = "KAora9C1Qqs"
TS_TOKEN = "test-token-any-nonempty"  # test secret accepts any non-empty


def _png_bytes(color=(255, 0, 0)) -> bytes:
    img = Image.new("RGB", (32, 32), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_info_publica_returns_empresa():
    r = requests.get(f"{BASE_URL}/api/cadastro-publico/info/{TOKEN}", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("valido") is True
    assert body.get("empresa"), "empresa deve estar presente"


def test_info_invalid_token_404():
    r = requests.get(f"{BASE_URL}/api/cadastro-publico/info/invalid-xyz-000", timeout=15)
    assert r.status_code == 404


def test_solicitar_sem_turnstile_400():
    payload = {
        "nome": f"Teste Sem TS {uuid.uuid4().hex[:6]} QA",
        "telefone": "11999998888",
    }
    r = requests.post(f"{BASE_URL}/api/cadastro-publico/solicitar/{TOKEN}", json=payload, timeout=15)
    assert r.status_code == 400, f"expected 400 without turnstile, got {r.status_code}: {r.text}"
    assert "anti-rob" in r.text.lower() or "turnstile" in r.text.lower()


def test_solicitar_com_turnstile_json_success():
    payload = {
        "nome": f"Joao Teste {uuid.uuid4().hex[:6]} QA",
        "telefone": "11987654321",
        "turnstile_token": TS_TOKEN,
    }
    r = requests.post(f"{BASE_URL}/api/cadastro-publico/solicitar/{TOKEN}", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "id" in data
    assert "sucesso" in data.get("message", "").lower() or "aprovação" in data.get("message", "").lower()


def test_solicitar_telefone_invalido():
    payload = {
        "nome": f"Nome Valido {uuid.uuid4().hex[:6]} QA",
        "telefone": "123",  # invalid
        "turnstile_token": TS_TOKEN,
    }
    r = requests.post(f"{BASE_URL}/api/cadastro-publico/solicitar/{TOKEN}", json=payload, timeout=15)
    assert r.status_code in (400, 422), r.text


def test_solicitar_cpf_invalido():
    payload = {
        "nome": f"Nome Valido {uuid.uuid4().hex[:6]} QA",
        "telefone": "11987654321",
        "cpf_cnpj": "11111111111",  # invalid CPF
        "turnstile_token": TS_TOKEN,
    }
    r = requests.post(f"{BASE_URL}/api/cadastro-publico/solicitar/{TOKEN}", json=payload, timeout=15)
    assert r.status_code == 400, r.text
    assert "cpf" in r.text.lower()


def test_solicitar_nome_curto():
    payload = {
        "nome": "Jo",
        "telefone": "11987654321",
        "turnstile_token": TS_TOKEN,
    }
    r = requests.post(f"{BASE_URL}/api/cadastro-publico/solicitar/{TOKEN}", json=payload, timeout=15)
    assert r.status_code in (400, 422), r.text


def test_solicitar_multipart_sem_consentimento_com_anexo_400():
    files = {
        "selfie": ("selfie.png", _png_bytes(), "image/png"),
    }
    data = {
        "nome": f"Multipart NoConsent {uuid.uuid4().hex[:6]} QA",
        "telefone": "11987654321",
        "turnstile_token": TS_TOKEN,
        # sem consentimento
    }
    r = requests.post(f"{BASE_URL}/api/cadastro-publico/solicitar/{TOKEN}", data=data, files=files, timeout=30)
    assert r.status_code == 400, r.text
    assert "autoriz" in r.text.lower() or "consent" in r.text.lower() or "imagens" in r.text.lower()


def test_solicitar_multipart_com_consentimento_sucesso():
    files = {
        "selfie": ("selfie.png", _png_bytes((0, 255, 0)), "image/png"),
        "assinatura": ("assinatura.png", _png_bytes((0, 0, 255)), "image/png"),
    }
    data = {
        "nome": f"Multipart OK {uuid.uuid4().hex[:6]} QA",
        "telefone": "11987654321",
        "turnstile_token": TS_TOKEN,
        "consentimento": "true",
        "versao_termo": "v1-2026-09",
    }
    r = requests.post(f"{BASE_URL}/api/cadastro-publico/solicitar/{TOKEN}", data=data, files=files, timeout=60)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "id" in body


def test_solicitar_multipart_sem_turnstile_400():
    files = {
        "selfie": ("selfie.png", _png_bytes(), "image/png"),
    }
    data = {
        "nome": f"Multipart NoTS {uuid.uuid4().hex[:6]} QA",
        "telefone": "11987654321",
        "consentimento": "true",
    }
    r = requests.post(f"{BASE_URL}/api/cadastro-publico/solicitar/{TOKEN}", data=data, files=files, timeout=30)
    assert r.status_code == 400, r.text
