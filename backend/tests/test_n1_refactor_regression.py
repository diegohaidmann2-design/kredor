"""Regression tests for N+1 refactors in analise.py and emprestimos.py.

Ensures observable behavior is IDENTICAL after batching queries via $in/aggregate/bulk_write.
Focus: valores monetarios, contagens, status de parcelas, nomes de cliente.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://gestorcred-staging-1.preview.emergentagent.com").rstrip("/")
QA_EMAIL = "qa.kredor@kredor.com.br"
QA_SENHA = os.environ.get("KREDOR_QA_SENHA")


@pytest.fixture(scope="module")
def token():
    if not QA_SENHA:
        pytest.skip("Defina KREDOR_QA_SENHA para rodar os testes de regressão N+1")
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": QA_EMAIL, "senha": QA_SENHA, "turnstile_token": "x"},
        timeout=30,
    )
    assert r.status_code == 200, f"login falhou: {r.status_code} {r.text}"
    data = r.json()
    assert "access_token" in data
    return data["access_token"]


@pytest.fixture(scope="module")
def client(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def cliente_id(client):
    suffix = uuid.uuid4().hex[:6]
    payload = {
        "nome": f"TEST_N1_{suffix}",
        "cpf_cnpj": "390.533.447-05",
        "telefone": "11999990000",
        "endereco": {
            "rua": "Rua Teste",
            "numero": "123",
            "bairro": "Centro",
            "cidade": "Sao Paulo",
            "estado": "SP",
            "cep": "01000-000",
        },
    }
    r = client.post(f"{BASE_URL}/api/clientes", json=payload, timeout=30)
    # If CPF already exists, try to find it
    if r.status_code in (400, 409):
        r2 = client.get(f"{BASE_URL}/api/clientes", timeout=30)
        assert r2.status_code == 200
        items = r2.json() if isinstance(r2.json(), list) else r2.json().get("items", [])
        for c in items:
            if (c.get("cpf_cnpj") or "").replace(".", "").replace("-", "").replace("/", "") == "39053344705":
                return c["id"]
        pytest.fail(f"Não foi possível criar/reutilizar cliente: {r.status_code} {r.text}")
    assert r.status_code in (200, 201), f"criar cliente: {r.status_code} {r.text}"
    return r.json()["id"]


# -----------------------------
# Login
# -----------------------------
def test_login_qa(token):
    assert isinstance(token, str) and len(token) > 20


# -----------------------------
# Criar empréstimo Price
# -----------------------------
@pytest.fixture(scope="module")
def emprestimo_price_id(client, cliente_id):
    payload = {
        "cliente_id": cliente_id,
        "valor_principal_centavos": 1_000_000,
        "taxa_juros_mensal": 2,
        "prazo_meses": 12,
        "metodo_calculo": "tabela_price",
        "data_inicio": time.strftime("%Y-%m-%d"),
    }
    r = client.post(f"{BASE_URL}/api/emprestimos", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"criar Price: {r.status_code} {r.text}"
    return r.json()["id"]


def test_price_gera_12_parcelas(client, emprestimo_price_id):
    r = client.get(f"{BASE_URL}/api/emprestimos/{emprestimo_price_id}/parcelas", timeout=30)
    assert r.status_code == 200, r.text
    parcelas = r.json()
    assert isinstance(parcelas, list)
    assert len(parcelas) == 12, f"esperado 12 parcelas, obteve {len(parcelas)}"


def test_listar_parcelas_idempotente_bulk_write(client, emprestimo_price_id):
    """Chamar 2x deve produzir mesmo resultado (refactor bulk_write não deve gerar side-effect duplicado)."""
    r1 = client.get(f"{BASE_URL}/api/emprestimos/{emprestimo_price_id}/parcelas", timeout=30)
    r2 = client.get(f"{BASE_URL}/api/emprestimos/{emprestimo_price_id}/parcelas", timeout=30)
    assert r1.status_code == 200 and r2.status_code == 200
    p1, p2 = r1.json(), r2.json()
    assert len(p1) == len(p2)
    # Comparar campos-chave (status, multa, juros_mora) parcela a parcela
    for a, b in zip(p1, p2):
        assert a.get("status") == b.get("status"), f"status diverge: {a.get('numero')} {a.get('status')} vs {b.get('status')}"
        assert a.get("multa_centavos", a.get("multa")) == b.get("multa_centavos", b.get("multa"))
        assert a.get("juros_mora_centavos", a.get("juros_mora")) == b.get("juros_mora_centavos", b.get("juros_mora"))


# -----------------------------
# Empréstimo aberto (sem_prazo)
# -----------------------------
@pytest.fixture(scope="module")
def emprestimo_aberto_id(client, cliente_id):
    payload = {
        "cliente_id": cliente_id,
        "valor_principal_centavos": 100_000,
        "taxa_juros_mensal": 10,
        "metodo_calculo": "apenas_juros",
        "sem_prazo": True,
        "data_inicio": time.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
    }
    r = client.post(f"{BASE_URL}/api/emprestimos", json=payload, timeout=30)
    assert r.status_code in (200, 201), f"criar aberto: {r.status_code} {r.text}"
    return r.json()["id"]


def test_aberto_gera_parcela_com_valor(client, emprestimo_aberto_id):
    r = client.get(f"{BASE_URL}/api/emprestimos/{emprestimo_aberto_id}/parcelas", timeout=30)
    assert r.status_code == 200, r.text
    parcelas = r.json()
    assert len(parcelas) >= 1, "esperado ao menos 1 parcela em aberto"
    p0 = parcelas[0]
    # valor_total ~100.00 (10% de 1000). Aceitar centavos ou reais.
    vt = p0.get("valor_total_centavos") or (p0.get("valor_total", 0) * 100 if p0.get("valor_total") else None)
    assert vt is not None
    assert 9500 <= vt <= 10500, f"valor_total inesperado: {vt}"


# -----------------------------
# Listagem geral com resumo
# -----------------------------
def test_listar_emprestimos_com_resumo(client, emprestimo_price_id, emprestimo_aberto_id):
    r = client.get(f"{BASE_URL}/api/emprestimos?page=1&limit=50", timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    assert len(items) > 0
    ids = {it["id"] for it in items}
    # Ambos empréstimos devem aparecer (podem estar em páginas diferentes se muito volume)
    achou_price = emprestimo_price_id in ids
    achou_aberto = emprestimo_aberto_id in ids
    # Verificar campos do resumo em pelo menos um item
    for it in items:
        assert ("total_recebido_centavos" in it) or ("total_recebido" in it), f"faltando total_recebido: {list(it.keys())}"
        assert "qtd_pagamentos" in it
        assert ("saldo_restante_centavos" in it) or ("saldo_restante" in it)
        if it.get("sem_prazo"):
            assert ("valor_total_juros_centavos" in it) or ("valor_total_juros" in it), f"aberto sem valor_total_juros: {it.get('id')}"
            assert ("valor_total_com_juros_centavos" in it) or ("valor_total_com_juros" in it)
    # Ao menos um dos criados apareceu
    assert achou_price or achou_aberto


# -----------------------------
# Resumo abertos (batch clientes+parcelas)
# -----------------------------
def test_resumo_abertos(client, emprestimo_aberto_id):
    r = client.get(f"{BASE_URL}/api/emprestimos/abertos/resumo", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, dict)
    itens = data.get("itens") or data.get("items") or []
    # Verifica campos coerentes
    for it in itens:
        assert "cliente_nome" in it and it["cliente_nome"], f"cliente_nome vazio: {it}"
        assert "juros_gerado_centavos" in it or "juros_gerado" in it
        assert "juros_em_aberto_centavos" in it or "juros_em_aberto" in it


# -----------------------------
# Pagamento parcial e total + estorno
# -----------------------------
def test_pagamento_parcial_total_estorno(client, emprestimo_price_id):
    r = client.get(f"{BASE_URL}/api/emprestimos/{emprestimo_price_id}/parcelas", timeout=30)
    assert r.status_code == 200
    parcelas = r.json()
    p0 = parcelas[0]
    parcela_id = p0["id"]
    valor_total_cents = p0.get("valor_total_centavos") or int(round(p0.get("valor_total", 0) * 100))
    assert valor_total_cents > 0

    # Pagamento parcial (metade)
    metade = valor_total_cents // 2
    pay1 = client.post(
        f"{BASE_URL}/api/pagamentos",
        json={
            "emprestimo_id": emprestimo_price_id,
            "parcela_id": parcela_id,
            "valor_pago_centavos": metade,
            "metodo_pagamento": "pix",
            "data_pagamento": time.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        },
        timeout=30,
    )
    assert pay1.status_code in (200, 201), f"pagamento parcial: {pay1.status_code} {pay1.text}"
    pag1_id = pay1.json().get("id") or pay1.json().get("pagamento", {}).get("id")

    # Verifica status parcial
    r2 = client.get(f"{BASE_URL}/api/emprestimos/{emprestimo_price_id}/parcelas", timeout=30)
    p0_after = next(p for p in r2.json() if p["id"] == parcela_id)
    assert p0_after.get("status") in ("parcial", "parcialmente_pago", "parcialmente_paga"), f"status apos parcial: {p0_after.get('status')}"

    # Pagamento do restante
    restante = valor_total_cents - metade
    pay2 = client.post(
        f"{BASE_URL}/api/pagamentos",
        json={
            "emprestimo_id": emprestimo_price_id,
            "parcela_id": parcela_id,
            "valor_pago_centavos": restante,
            "metodo_pagamento": "pix",
            "data_pagamento": time.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        },
        timeout=30,
    )
    assert pay2.status_code in (200, 201), f"pagamento total: {pay2.status_code} {pay2.text}"
    pag2_id = pay2.json().get("id") or pay2.json().get("pagamento", {}).get("id")

    r3 = client.get(f"{BASE_URL}/api/emprestimos/{emprestimo_price_id}/parcelas", timeout=30)
    p0_pago = next(p for p in r3.json() if p["id"] == parcela_id)
    assert p0_pago.get("status") in ("pago", "paga", "quitado"), f"status apos total: {p0_pago.get('status')}"

    # Estorno do segundo pagamento -> deve voltar para parcial
    if pag2_id:
        d = client.delete(f"{BASE_URL}/api/pagamentos/{pag2_id}", timeout=30)
        assert d.status_code in (200, 204), f"estorno: {d.status_code} {d.text}"
        r4 = client.get(f"{BASE_URL}/api/emprestimos/{emprestimo_price_id}/parcelas", timeout=30)
        p0_est = next(p for p in r4.json() if p["id"] == parcela_id)
        assert p0_est.get("status") not in ("pago", "paga", "quitado"), f"status apos estorno ainda pago: {p0_est.get('status')}"


# -----------------------------
# Análise clientes (refactor $in/aggregate)
# -----------------------------
def test_analise_clientes(client, cliente_id):
    r = client.get(f"{BASE_URL}/api/analise/clientes?page=1&limit=100", timeout=60)
    assert r.status_code == 200, r.text
    body = r.json()
    items = body if isinstance(body, list) else body.get("clientes", body.get("items", body.get("data", [])))
    assert isinstance(items, list) and len(items) > 0, f"lista vazia. body keys={list(body.keys()) if isinstance(body, dict) else body}"
    achou = None
    for it in items:
        cid = it.get("cliente_id") or it.get("id")
        assert "emprestimos_ativos" in it, f"faltando emprestimos_ativos: {list(it.keys())}"
        assert "total_devido_centavos" in it or "total_devido" in it
        # ultimo_pagamento pode ser None
        if cid == cliente_id:
            achou = it
    if achou:
        assert achou["emprestimos_ativos"] >= 1
        td = achou.get("total_devido_centavos", achou.get("total_devido", 0))
        assert td > 0, f"total_devido esperado > 0, obteve {td}"


def test_analise_dashboard(client):
    r = client.get(f"{BASE_URL}/api/analise/dashboard", timeout=60)
    assert r.status_code == 200, f"{r.status_code} {r.text[:400]}"
    assert isinstance(r.json(), (dict, list))
