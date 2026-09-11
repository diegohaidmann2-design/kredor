"""
Regressão FASE 1 — dinheiro em centavos internos, fronteira em reais.
Cobre: simulação (5 métodos), CRUD cliente+empréstimo, pagamento parcial/total/estorno,
empréstimo aberto (amortizar/incorporar/quitar), dashboard e verificação de que
NENHUMA chave *_centavos aparece em JSON de resposta.
"""
import os
import re
import time
import uuid
import pytest
import requests

def _base_url():
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        url = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
    assert url, "REACT_APP_BACKEND_URL not set"
    return url.rstrip("/")


BASE_URL = _base_url()
API = f"{BASE_URL}/api"

EMAIL = "qa.kredor@kredor.com.br"
SENHA = os.environ.get("KREDOR_QA_SENHA")

CENTAVOS_KEY_RE = re.compile(r"_centavos\b")


def _find_centavos_keys(obj, path="$"):
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if CENTAVOS_KEY_RE.search(k):
                hits.append(f"{path}.{k}")
            hits.extend(_find_centavos_keys(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(_find_centavos_keys(v, f"{path}[{i}]"))
    return hits


@pytest.fixture(scope="session")
def token():
    if not SENHA:
        pytest.skip("Defina KREDOR_QA_SENHA para rodar os testes de regressão da Fase 1")
    r = requests.post(
        f"{API}/auth/login",
        json={"email": EMAIL, "senha": SENHA, "turnstile_token": "x"},
        timeout=30,
    )
    assert r.status_code == 200, f"Login falhou: {r.status_code} {r.text[:400]}"
    tok = r.json().get("access_token")
    assert tok, r.json()
    return tok


@pytest.fixture(scope="session")
def client(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


# --------------------- Simulação ---------------------
@pytest.mark.parametrize("metodo,expect_total,check_total", [
    ("tabela_price", 11347.15, True),
    ("sac", None, False),
    ("juros_simples", None, False),
    ("juros_compostos", None, False),
    ("apenas_juros", None, False),
])
def test_simular(client, metodo, expect_total, check_total):
    body = {
        "valor_principal": 10000,
        "taxa_juros_mensal": 2,
        "prazo_meses": 12,
        "metodo_calculo": metodo,
    }
    r = client.post(f"{API}/emprestimos/simular", json=body, timeout=30)
    assert r.status_code == 200, f"{metodo}: {r.status_code} {r.text[:400]}"
    data = r.json()
    hits = _find_centavos_keys(data)
    assert not hits, f"chaves _centavos vazaram em simular({metodo}): {hits}"
    parcelas = data.get("parcelas") or data.get("cronograma") or []
    assert len(parcelas) == 12, f"{metodo}: esperava 12 parcelas, veio {len(parcelas)}"
    soma_principal = round(sum(p.get("valor_principal", 0) for p in parcelas), 2)
    # apenas_juros: só paga juros até vencimento; soma principal pode ser 0 até a última parcela
    if metodo == "apenas_juros":
        # última parcela deve conter o principal
        assert soma_principal == 10000.00, f"apenas_juros: soma principal={soma_principal}"
    else:
        assert soma_principal == 10000.00, f"{metodo}: soma principal={soma_principal}"
    if check_total:
        vt = data.get("valor_total_com_juros") or data.get("valor_total")
        assert abs(vt - expect_total) < 0.02, f"price total={vt} esperado {expect_total}"
    # nenhum valor deve estar em centavos absurdos (>1e6 quando entrada é 10k)
    assert data.get("valor_principal") in (10000, 10000.0)


# --------------------- Cliente + Empréstimo Price ---------------------
@pytest.fixture(scope="session")
def cliente_id(client):
    suf = uuid.uuid4().hex[:6]
    body = {
        "nome": f"TEST Regressao {suf}",
        "cpf": f"000000000{suf[:2]}",  # cpf fake
        "telefone": "11999990000",
        "email": f"test_{suf}@test.com",
        "endereco": {
            "rua": "Rua Teste",
            "numero": "123",
            "bairro": "Centro",
            "cidade": "SP",
            "estado": "SP",
            "cep": "01000000",
        },
    }
    r = client.post(f"{API}/clientes", json=body, timeout=30)
    assert r.status_code in (200, 201), f"criar cliente: {r.status_code} {r.text[:400]}"
    j = r.json()
    hits = _find_centavos_keys(j)
    assert not hits, f"_centavos em cliente: {hits}"
    cid = j.get("id") or j.get("_id") or j.get("cliente_id")
    assert cid
    return cid


@pytest.fixture(scope="session")
def emprestimo_price(client, cliente_id):
    body = {
        "cliente_id": cliente_id,
        "valor_principal": 2500.75,
        "taxa_juros_mensal": 3,
        "prazo_meses": 6,
        "metodo_calculo": "tabela_price",
    }
    r = client.post(f"{API}/emprestimos", json=body, timeout=30)
    assert r.status_code in (200, 201), f"criar emp: {r.status_code} {r.text[:400]}"
    j = r.json()
    hits = _find_centavos_keys(j)
    assert not hits, f"_centavos em emp: {hits}"
    return j["id"]


def test_emprestimo_price_parcelas_em_reais(client, emprestimo_price):
    r = client.get(f"{API}/emprestimos/{emprestimo_price}/parcelas", timeout=30)
    assert r.status_code == 200, r.text[:400]
    data = r.json()
    hits = _find_centavos_keys(data)
    assert not hits, f"_centavos em parcelas: {hits}"
    parcelas = data if isinstance(data, list) else data.get("parcelas", [])
    assert len(parcelas) == 6
    v = parcelas[0]["valor_total"]
    assert 400 < v < 520, f"parcela fora de faixa esperada (~461): {v}"


def test_lista_emprestimos_em_reais(client, emprestimo_price):
    r = client.get(f"{API}/emprestimos", timeout=30)
    assert r.status_code == 200, r.text[:400]
    data = r.json()
    hits = _find_centavos_keys(data)
    assert not hits, f"_centavos em lista: {hits}"
    itens = data if isinstance(data, list) else data.get("items") or data.get("emprestimos") or []
    encontrado = next((e for e in itens if e.get("id") == emprestimo_price), None)
    assert encontrado, "emprestimo criado nao apareceu na lista"
    assert abs(encontrado["valor_principal"] - 2500.75) < 0.01


# --------------------- Pagamento parcial/total/estorno ---------------------
def test_pagamento_parcial_total_erros_estorno(client, emprestimo_price):
    r = client.get(f"{API}/emprestimos/{emprestimo_price}/parcelas", timeout=30)
    parcelas = r.json() if isinstance(r.json(), list) else r.json().get("parcelas", [])
    p1 = parcelas[0]
    parcela_id = p1["id"]
    valor_total = round(p1["valor_total"], 2)

    # 1) parcial
    r = client.post(f"{API}/pagamentos", json={
        "parcela_id": parcela_id, "valor_pago": 100.10, "metodo_pagamento": "pix"
    }, timeout=30)
    assert r.status_code in (200, 201), f"parcial: {r.status_code} {r.text[:400]}"
    j = r.json()
    hits = _find_centavos_keys(j)
    assert not hits, f"_centavos pagamento parcial: {hits}"

    # confere parcela = parcial
    rp = client.get(f"{API}/emprestimos/{emprestimo_price}/parcelas", timeout=30)
    par = next(p for p in (rp.json() if isinstance(rp.json(), list) else rp.json().get("parcelas", [])) if p["id"] == parcela_id)
    assert par["status"] in ("parcial", "parcialmente_pago", "parcial_pago"), f"status={par['status']}"
    assert abs(par["valor_pago"] - 100.10) < 0.01, par

    # 2) valor absurdo -> 422
    r_bad = client.post(f"{API}/pagamentos", json={
        "parcela_id": parcela_id, "valor_pago": valor_total * 3, "metodo_pagamento": "pix"
    }, timeout=30)
    assert r_bad.status_code in (400, 422), f"esperado 400/422 para valor absurdo, veio {r_bad.status_code}"

    # 3) pagar restante exato -> pago
    restante = round(valor_total - 100.10, 2)
    r = client.post(f"{API}/pagamentos", json={
        "parcela_id": parcela_id, "valor_pago": restante, "metodo_pagamento": "pix"
    }, timeout=30)
    assert r.status_code in (200, 201), f"restante: {r.status_code} {r.text[:400]}"
    pagamento_id = r.json().get("id") or r.json().get("pagamento_id")

    rp = client.get(f"{API}/emprestimos/{emprestimo_price}/parcelas", timeout=30)
    par = next(p for p in (rp.json() if isinstance(rp.json(), list) else rp.json().get("parcelas", [])) if p["id"] == parcela_id)
    assert par["status"] in ("pago", "quitada", "quitado"), f"status={par['status']}"

    # 4) pagar parcela paga -> 400
    r_dup = client.post(f"{API}/pagamentos", json={
        "parcela_id": parcela_id, "valor_pago": 1.0, "metodo_pagamento": "pix"
    }, timeout=30)
    assert r_dup.status_code in (400, 409, 422), f"esperado erro em pagar parcela paga, veio {r_dup.status_code}"

    # 5) estorno do último pagamento
    if pagamento_id:
        r_est = client.delete(f"{API}/pagamentos/{pagamento_id}", timeout=30)
        assert r_est.status_code in (200, 204), f"estorno: {r_est.status_code} {r_est.text[:300]}"
        if r_est.status_code == 200:
            j = r_est.json()
            hits = _find_centavos_keys(j)
            assert not hits, f"_centavos estorno: {hits}"
            # valor_estornado em reais (~restante)
            ve = j.get("valor_estornado")
            if ve is not None:
                assert abs(ve - restante) < 0.02, f"valor_estornado={ve}"


# --------------------- Empréstimo Aberto ---------------------
@pytest.fixture(scope="session")
def emprestimo_aberto(client, cliente_id):
    body = {
        "cliente_id": cliente_id,
        "valor_principal": 1000,
        "taxa_juros_mensal": 10,
        "metodo_calculo": "apenas_juros",
        "sem_prazo": True,
    }
    r = client.post(f"{API}/emprestimos", json=body, timeout=30)
    assert r.status_code in (200, 201), f"aberto: {r.status_code} {r.text[:400]}"
    return r.json()["id"]


def test_aberto_fluxo_completo(client, emprestimo_aberto):
    eid = emprestimo_aberto
    # 1 parcela de 100
    r = client.get(f"{API}/emprestimos/{eid}/parcelas", timeout=30)
    parcelas = r.json() if isinstance(r.json(), list) else r.json().get("parcelas", [])
    assert len(parcelas) >= 1
    p0 = parcelas[0]
    assert abs(p0["valor_total"] - 100.00) < 0.02, f"parcela juros={p0['valor_total']}"

    # pagar 100 -> gera parcela 2
    r = client.post(f"{API}/pagamentos", json={
        "parcela_id": p0["id"], "valor_pago": 100.00, "metodo_pagamento": "pix"
    }, timeout=30)
    assert r.status_code in (200, 201), r.text[:300]

    r = client.get(f"{API}/emprestimos/{eid}/parcelas", timeout=30)
    parcelas = r.json() if isinstance(r.json(), list) else r.json().get("parcelas", [])
    assert len(parcelas) >= 2, f"esperado 2+ parcelas apos pgto, veio {len(parcelas)}"

    # amortizar 300.33
    r = client.post(f"{API}/emprestimos/{eid}/amortizar", json={
        "valor_amortizacao": 300.33, "metodo_pagamento": "pix", "recalcular_juros": True
    }, timeout=30)
    assert r.status_code in (200, 201), f"amortizar: {r.status_code} {r.text[:400]}"
    j = r.json()
    hits = _find_centavos_keys(j)
    assert not hits, f"_centavos amortizar: {hits}"
    principal = j.get("principal_atual") or j.get("valor_principal_atual")
    if principal is not None:
        assert abs(principal - 699.67) < 0.02, f"principal_atual={principal}"

    # incorporar juros 50.5
    r = client.post(f"{API}/emprestimos/{eid}/incorporar-juros", json={
        "valor_juros": 50.5, "baixar_parcelas": True, "recalcular_juros": True
    }, timeout=30)
    assert r.status_code in (200, 201), f"incorporar: {r.status_code} {r.text[:400]}"
    j = r.json()
    hits = _find_centavos_keys(j)
    assert not hits, f"_centavos incorporar: {hits}"
    principal = j.get("principal_atual") or j.get("valor_principal_atual")
    if principal is not None:
        assert abs(principal - 750.17) < 0.05, f"principal apos incorporar={principal}"

    # ajustes
    r = client.get(f"{API}/emprestimos/{eid}/ajustes", timeout=30)
    assert r.status_code == 200, r.text[:300]
    assert not _find_centavos_keys(r.json())

    # abertos resumo
    r = client.get(f"{API}/emprestimos/abertos/resumo", timeout=30)
    assert r.status_code == 200, r.text[:300]
    assert not _find_centavos_keys(r.json())

    # quitar
    r = client.post(f"{API}/emprestimos/{eid}/quitar", json={"metodo_pagamento": "pix"}, timeout=30)
    assert r.status_code in (200, 201), f"quitar: {r.status_code} {r.text[:400]}"
    assert not _find_centavos_keys(r.json())


# --------------------- Dashboard e listagens gerais ---------------------
def test_dashboard_em_reais(client):
    r = client.get(f"{API}/dashboard", timeout=30)
    assert r.status_code == 200, r.text[:400]
    j = r.json()
    hits = _find_centavos_keys(j)
    assert not hits, f"_centavos dashboard: {hits}"
    # sanity: capital emprestado > 0 e < 1e8 (não 100x)
    cap = j.get("total_capital_emprestado")
    assert cap is None or 0 <= cap < 1e8, f"capital fora de faixa: {cap}"


def test_pagamentos_lista(client):
    r = client.get(f"{API}/pagamentos", timeout=30)
    assert r.status_code == 200, r.text[:300]
    assert not _find_centavos_keys(r.json())


def test_parcelas_lista(client):
    # /api/parcelas nao e um endpoint listado. Aceitar 404 (nao existe) ou 200.
    r = client.get(f"{API}/parcelas", timeout=30)
    assert r.status_code in (200, 404), r.text[:300]
    if r.status_code == 200:
        assert not _find_centavos_keys(r.json())


def test_analise_clientes(client):
    r = client.get(f"{API}/analise/clientes", timeout=30)
    assert r.status_code == 200, r.text[:300]
    assert not _find_centavos_keys(r.json())


def test_analise_dashboard(client):
    r = client.get(f"{API}/analise/dashboard", timeout=30)
    assert r.status_code == 200, r.text[:300]
    assert not _find_centavos_keys(r.json())
