"""
Testes de isolamento e edição dos WhatsApp templates (escopo por get_user_context).

Cenários:
1. Login em Conta A e Conta B
2. Listar templates iniciais (cada conta ~6 padrão)
3. Conta A cria 'ISOLTEST_A'; Conta B NÃO deve enxergar
4. Conta B cria 'ISOLTEST_B'; Conta A NÃO deve enxergar
5. Edição de template não-padrão em Conta A (mensagem persiste)
6. Edição de template padrão bloqueada com 400
7. Regressão: duplicar, preview, excluir
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
TURNSTILE = "test-token"

CONTA_A = {"email": "diego.haidmann@gmail.com", "senha": "Teste@2026"}
CONTA_B = {"email": "adilsonsoares203@gmail.com", "senha": "Teste@2026"}


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": creds["email"], "senha": creds["senha"], "turnstile_token": TURNSTILE
    }, timeout=30)
    assert r.status_code == 200, f"Login {creds['email']} falhou: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def token_a():
    return _login(CONTA_A)


@pytest.fixture(scope="module")
def token_b():
    return _login(CONTA_B)


def _hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


def _list(tok):
    r = requests.get(f"{BASE_URL}/api/whatsapp/templates", headers=_hdr(tok), timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["templates"]


def _create(tok, nome, msg="Ola {cliente_nome}"):
    r = requests.post(
        f"{BASE_URL}/api/whatsapp/templates",
        headers=_hdr(tok),
        params={"nome": nome, "tipo": "cobranca", "mensagem": msg},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    return r.json()["template"]["id"]


def _delete(tok, tid):
    return requests.delete(f"{BASE_URL}/api/whatsapp/templates/{tid}", headers=_hdr(tok), timeout=30)


def test_login_ambas_contas(token_a, token_b):
    assert token_a and token_b and token_a != token_b


def test_isolamento_A_cria_B_nao_ve(token_a, token_b):
    unique = f"ISOLTEST_A_{uuid.uuid4().hex[:6]}"
    tid = _create(token_a, unique)
    try:
        tpls_a = _list(token_a)
        tpls_b = _list(token_b)
        nomes_a = [t["nome"] for t in tpls_a]
        nomes_b = [t["nome"] for t in tpls_b]
        assert unique in nomes_a, f"Conta A deveria ver seu template: {nomes_a}"
        assert unique not in nomes_b, f"Conta B NÃO deveria ver template da A: {nomes_b}"
        # Conta B não deve poder acessar pelo ID
        r = requests.get(f"{BASE_URL}/api/whatsapp/templates/{tid}", headers=_hdr(token_b), timeout=30)
        assert r.status_code == 404
    finally:
        _delete(token_a, tid)


def test_isolamento_B_cria_A_nao_ve(token_a, token_b):
    unique = f"ISOLTEST_B_{uuid.uuid4().hex[:6]}"
    tid = _create(token_b, unique)
    try:
        nomes_a = [t["nome"] for t in _list(token_a)]
        nomes_b = [t["nome"] for t in _list(token_b)]
        assert unique in nomes_b
        assert unique not in nomes_a
    finally:
        _delete(token_b, tid)


def test_edit_template_nao_padrao_persiste(token_a):
    unique = f"EDITTEST_{uuid.uuid4().hex[:6]}"
    tid = _create(token_a, unique, msg="Original {cliente_nome}")
    try:
        nova_msg = "Editada {cliente_nome} valor {valor}"
        r = requests.put(
            f"{BASE_URL}/api/whatsapp/templates/{tid}",
            headers=_hdr(token_a),
            params={"mensagem": nova_msg},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        got = requests.get(f"{BASE_URL}/api/whatsapp/templates/{tid}", headers=_hdr(token_a)).json()
        assert got["mensagem"] == nova_msg
    finally:
        _delete(token_a, tid)


def test_edit_template_padrao_bloqueado(token_a):
    templates = _list(token_a)
    padrao = next((t for t in templates if t.get("padrao")), None)
    assert padrao, "Nenhum template padrão encontrado"
    r = requests.put(
        f"{BASE_URL}/api/whatsapp/templates/{padrao['id']}",
        headers=_hdr(token_a),
        params={"mensagem": "tentativa hack"},
        timeout=30,
    )
    assert r.status_code == 400, f"Esperado 400, veio {r.status_code}: {r.text}"

    # Mas ativar/desativar deve funcionar
    r2 = requests.put(
        f"{BASE_URL}/api/whatsapp/templates/{padrao['id']}",
        headers=_hdr(token_a),
        params={"ativo": not padrao.get("ativo", True)},
        timeout=30,
    )
    assert r2.status_code == 200, r2.text
    # Restaurar
    requests.put(
        f"{BASE_URL}/api/whatsapp/templates/{padrao['id']}",
        headers=_hdr(token_a),
        params={"ativo": padrao.get("ativo", True)},
        timeout=30,
    )


def test_duplicar_preview_excluir(token_a):
    unique = f"REGRESS_{uuid.uuid4().hex[:6]}"
    tid = _create(token_a, unique, msg="Ola {cliente_nome}")
    dup_id = None
    try:
        # Duplicar
        r = requests.post(
            f"{BASE_URL}/api/whatsapp/templates/{tid}/duplicar",
            headers=_hdr(token_a), timeout=30
        )
        assert r.status_code == 200, r.text
        dup_id = r.json()["template"]["id"]
        assert r.json()["template"]["nome"].endswith("(Cópia)")

        # Preview
        r2 = requests.post(
            f"{BASE_URL}/api/whatsapp/templates/preview",
            headers=_hdr(token_a),
            params={"mensagem": "Ola {cliente_nome}"},
            timeout=30,
        )
        assert r2.status_code == 200
        assert "João Silva" in r2.json()["preview"]
    finally:
        if dup_id:
            _delete(token_a, dup_id)
        _delete(token_a, tid)
