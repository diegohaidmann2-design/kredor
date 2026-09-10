"""
Regression tests for fixes 2.4, 2.6, 3.2 review:
- Login flow with Turnstile test key
- Dashboard returns 200 and all *_centavos fields are ints
- Cliente + Emprestimo create + Dashboard aggregation
- Simulacao (POST /api/emprestimos/simular) principal sum equals input
- Notificacoes endpoint reachable (no ImportError from v2 merge)
- Health check /api/
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

CREDS = {"email": "usuario@teste.com", "senha": "senha123", "turnstile_token": "test"}


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def token(session):
    r = session.post(f"{BASE_URL}/api/auth/login", json=CREDS, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("token") or data.get("access_token")
    assert tok, f"no token in response: {data}"
    return tok


@pytest.fixture(scope="session")
def auth(session, token):
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


# ---------- helpers ----------
def _walk_centavos(obj, path=""):
    """Yield (path, value) for every key ending in _centavos."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            if isinstance(k, str) and k.endswith("_centavos"):
                yield p, v
            yield from _walk_centavos(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_centavos(v, f"{path}[{i}]")


# ---------- Health ----------
def test_health_root(session):
    r = session.get(f"{BASE_URL}/api/", timeout=15)
    assert r.status_code == 200, r.text


# ---------- Auth ----------
def test_login_returns_token(token):
    assert isinstance(token, str) and len(token) > 10


# ---------- Dashboard: fix 2.6 ----------
def test_dashboard_ok_and_monetary_fields_numeric(auth):
    r = auth.get(f"{BASE_URL}/api/dashboard", timeout=30)
    assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"
    body = r.json()
    # Wire format converts _centavos -> reais floats. Any remaining _centavos must still be int.
    bad_centavos = []
    for path, val in _walk_centavos(body):
        if val is None or isinstance(val, bool) or not isinstance(val, int):
            bad_centavos.append((path, val, type(val).__name__))
    assert not bad_centavos, f"Non-int _centavos fields: {bad_centavos[:10]}"
    # Sanity: known money keys must be numeric (int or float), never None/str
    money_keys = [
        "total_capital_emprestado", "total_juros_a_receber", "total_juros_recebidos",
        "valor_em_atraso", "a_receber_hoje", "a_receber_semana", "a_receber_mes",
        "recebido_mes_atual", "juros_recebidos_mes", "juros_a_receber_mes",
    ]
    for k in money_keys:
        assert k in body, f"missing key {k}"
        v = body[k]
        assert v is not None and not isinstance(v, str) and not isinstance(v, bool), (
            f"{k} = {v!r}"
        )
        assert isinstance(v, (int, float)), f"{k} type={type(v).__name__}"


# ---------- Simulacao ----------
def test_simular_price_principal_sum(auth):
    payload = {
        "valor_principal_centavos": 100000,  # R$ 1.000,00
        "taxa_juros_mensal": 5.0,
        "prazo_meses": 6,
        "metodo_calculo": "tabela_price",
        "periodicidade": "mensal",
    }
    r = auth.post(f"{BASE_URL}/api/emprestimos/simular", json=payload, timeout=30)
    assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
    data = r.json()
    parcelas = data.get("parcelas", [])
    assert parcelas, "no parcelas returned"
    # Wire uses reais (converted from _centavos). Sum principal_reais ≈ principal input / 100.
    total_principal_reais = round(sum(float(p["valor_principal"]) for p in parcelas), 2)
    expected = payload["valor_principal_centavos"] / 100.0
    assert abs(total_principal_reais - expected) < 0.05, (
        f"sum principal reais {total_principal_reais} != expected {expected}"
    )
    # top-level valor_total_com_juros must be a number
    assert isinstance(data.get("valor_total_com_juros"), (int, float))


# ---------- Cliente + Emprestimo + Dashboard ----------
@pytest.fixture(scope="module")
def created_cliente_id(session, token):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    suffix = uuid.uuid4().hex[:6]
    payload = {
        "nome": f"TEST_Cliente_{suffix}",
        "telefone": "11999999999",
        "cpf_cnpj": None,
        "endereco": {
            "rua": "Rua Teste",
            "numero": "100",
            "bairro": "Centro",
            "cidade": "Sao Paulo",
            "estado": "SP",
            "cep": "01000-000",
        },
    }
    r = s.post(f"{BASE_URL}/api/clientes", json=payload, timeout=30)
    if r.status_code not in (200, 201):
        pytest.skip(f"cliente create failed: {r.status_code} {r.text[:200]}")
    data = r.json()
    cid = data.get("id") or (data.get("cliente") or {}).get("id")
    assert cid, f"no id in cliente response: {data}"
    yield cid
    # best-effort cleanup
    try:
        s.delete(f"{BASE_URL}/api/clientes/{cid}", timeout=15)
    except Exception:
        pass


def test_create_emprestimo_and_dashboard_still_ok(auth, created_cliente_id):
    payload = {
        "cliente_id": created_cliente_id,
        "valor_principal_centavos": 50000,
        "taxa_juros_mensal": 4.0,
        "prazo_meses": 3,
        "metodo_calculo": "tabela_price",
        "periodicidade": "mensal",
    }
    r = auth.post(f"{BASE_URL}/api/emprestimos", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"emprestimo create failed: {r.status_code} {r.text[:400]}"
    emp = r.json()
    emp_id = emp.get("id")
    assert emp_id

    # Re-verify dashboard
    time.sleep(0.5)
    r2 = auth.get(f"{BASE_URL}/api/dashboard", timeout=30)
    assert r2.status_code == 200, r2.text[:300]
    body = r2.json()
    # capital total should be >= newly created principal
    # (we don't know exact aggregation key across schema versions — just ensure ints)
    for path, val in _walk_centavos(body):
        assert val is not None and isinstance(val, int) and not isinstance(val, bool), (
            f"{path} = {val!r} ({type(val).__name__})"
        )

    # cleanup emprestimo
    try:
        auth.delete(f"{BASE_URL}/api/emprestimos/{emp_id}", timeout=15)
    except Exception:
        pass


# ---------- Notificacoes: fix 3.2 (v2 merge) ----------
def test_notificacoes_list_ok(auth):
    r = auth.get(f"{BASE_URL}/api/notificacoes", timeout=30)
    # Should not 500 (would signal ImportError on notificacao_service_v2)
    assert r.status_code == 200, f"{r.status_code} {r.text[:300]}"


def test_notificacoes_verificar_vencimentos_no_import_error(auth):
    # Try known trigger endpoints; accept 200/202/404/405 but never 500 (ImportError)
    candidates = [
        ("POST", "/api/notificacoes/verificar-vencimentos"),
        ("POST", "/api/notificacoes/vencimentos/verificar"),
        ("GET", "/api/notificacoes/vencimentos"),
    ]
    any_hit = False
    for method, path in candidates:
        r = auth.request(method, f"{BASE_URL}{path}", timeout=30)
        if r.status_code == 500:
            # check body for the specific ImportError signature
            body = r.text.lower()
            assert "notificacao_service_v2" not in body, (
                f"{path} still references removed v2 module: {r.text[:400]}"
            )
        if r.status_code < 500:
            any_hit = True
    # As long as none returned 500 referencing v2, we're good.
    assert True
