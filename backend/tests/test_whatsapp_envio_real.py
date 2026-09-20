"""Test WhatsApp real message sending to authorized test numbers.

Confirms the fixes:
- deleted instance no longer used (no '404 instance does not exist')
- numero_telefone persists
- messages are sent successfully with message_id
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://credmanager-preview.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

EMAIL = "diego.haidmann@gmail.com"
SENHA = "GestorTest@2026"
EXPECTED_INSTANCE = "user_fabf3ca4_f2bfdb96"
EXPECTED_NUMERO = "5527999507920"

NUM_1 = "5527988292633"
NUM_2 = "5515953748288"
MSG_1 = "Teste automatizado Kredor via API #1"
MSG_2 = "Teste automatizado Kredor via API #2"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={
        "email": EMAIL,
        "senha": SENHA,
        "turnstile_token": "dummy",
    }, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"no token in response: {data}"
    return tok


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


# --- Login ---
def test_login_returns_token(token):
    assert isinstance(token, str) and len(token) > 20


# --- Regressão: conexão ativa correta ---
def test_conexao_ativa_correta(headers):
    r = requests.get(f"{API}/whatsapp/conexoes", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    payload = r.json()
    conexoes = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
    assert isinstance(conexoes, list) and len(conexoes) > 0
    target = next((c for c in conexoes if c.get("instance_name") == EXPECTED_INSTANCE), None)
    assert target is not None, f"instance {EXPECTED_INSTANCE} not found"
    assert target.get("status") == "conectado"
    assert target.get("numero_telefone") == EXPECTED_NUMERO


def _enviar(headers, numero, mensagem):
    # NOTE: request payload from problem statement used tipo='texto' but
    # backend Literal accepts only 'cobranca'|'lembrete'|'confirmacao'|'manual'.
    # 'manual' is the correct free-form type.
    body = {"numero_destino": numero, "mensagem": mensagem, "tipo": "manual"}
    r = requests.post(f"{API}/whatsapp/mensagens/enviar", headers=headers, json=body, timeout=60)
    return r


# --- Envio real #1 ---
def test_envio_real_numero_1(headers):
    r = _enviar(headers, NUM_1, MSG_1)
    assert r.status_code == 200, f"send failed: {r.status_code} {r.text}"
    data = r.json()
    # ensure no 404 instance error
    body_txt = str(data).lower()
    assert "does not exist" not in body_txt, f"deleted-instance regression: {data}"
    assert "404" not in body_txt or data.get("status") == "enviado", f"unexpected 404: {data}"
    assert data.get("status") == "enviado", f"status != enviado: {data}"
    assert data.get("message_id"), f"missing message_id: {data}"
    pytest.msg_id_1 = data.get("message_id")


# --- Envio real #2 ---
def test_envio_real_numero_2(headers):
    r = _enviar(headers, NUM_2, MSG_2)
    assert r.status_code == 200, f"send failed: {r.status_code} {r.text}"
    data = r.json()
    body_txt = str(data).lower()
    assert "does not exist" not in body_txt, f"deleted-instance regression: {data}"
    assert data.get("status") == "enviado", f"status != enviado: {data}"
    assert data.get("message_id"), f"missing message_id: {data}"
    pytest.msg_id_2 = data.get("message_id")


# --- Histórico ---
def test_historico_lista_envios(headers):
    time.sleep(2)  # allow DB write
    r = requests.get(f"{API}/whatsapp/mensagens", headers=headers, timeout=30)
    assert r.status_code == 200, r.text
    payload = r.json()
    mensagens = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
    assert isinstance(mensagens, list) and len(mensagens) > 0

    # normalize numbers for matching
    def norm(n):
        return "".join(ch for ch in str(n or "") if ch.isdigit())

    def find_recent(numero, texto):
        for m in mensagens:
            n = norm(m.get("numero_destino") or m.get("numero"))
            if n.endswith(numero[-8:]) and texto in (m.get("mensagem") or m.get("conteudo") or ""):
                return m
        return None

    m1 = find_recent(NUM_1, MSG_1)
    m2 = find_recent(NUM_2, MSG_2)
    assert m1 is not None, f"mensagem #1 not found in histórico"
    assert m2 is not None, f"mensagem #2 not found in histórico"
    assert m1.get("status") in ("enviado", "entregue", "lido"), f"status #1={m1.get('status')}"
    assert m2.get("status") in ("enviado", "entregue", "lido"), f"status #2={m2.get('status')}"
