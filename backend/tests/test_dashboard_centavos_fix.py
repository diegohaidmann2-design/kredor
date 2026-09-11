"""Regressão pós-migração schema reais->centavos (dashboard).

Contexto: o dump antigo tinha valores em reais/float; o código atual lê
campos *_centavos (int). Após rodar backend/scripts/migrar_para_centavos.py,
o GET /api/dashboard deve somar corretamente. A resposta é convertida pelo
ReaisJSONResponse (utils/dinheiro.py) — chaves saem SEM sufixo _centavos e
com valores em REAIS (float).

Validações:
  * GET /api/dashboard 200 e valores monetários > 0 após criar 1 empréstimo
  * POST /api/pagamentos reflete em recebido_mes_atual (+juros_recebidos_mes)
  * GET /api/emprestimos e /api/analise/clientes com valores > 0 coerentes
  * Contrato: não vazam chaves *_centavos na resposta do dashboard
"""
import os
import time
import uuid

import pytest
import requests

BASE_URL = (
    os.environ.get("REACT_APP_BACKEND_URL")
    or "https://credito-app-12.preview.emergentagent.com"
).rstrip("/")
QA_EMAIL = "qa.kredor@kredor.com.br"
QA_SENHA = os.environ.get("KREDOR_QA_SENHA")


@pytest.fixture(scope="module")
def token():
    if not QA_SENHA:
        pytest.skip("Defina KREDOR_QA_SENHA para rodar os testes do dashboard")
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": QA_EMAIL, "senha": QA_SENHA, "turnstile_token": "x"},
        timeout=30,
    )
    assert r.status_code == 200, f"login falhou: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def client(token):
    s = requests.Session()
    s.headers.update(
        {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    return s


@pytest.fixture(scope="module")
def cliente_id(client):
    suffix = uuid.uuid4().hex[:6]
    payload = {
        "nome": f"TEST_DASH_{suffix}",
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
    if r.status_code in (400, 409):
        r2 = client.get(f"{BASE_URL}/api/clientes", timeout=30)
        assert r2.status_code == 200
        body = r2.json()
        items = body if isinstance(body, list) else body.get("items", [])
        for c in items:
            if (c.get("cpf_cnpj") or "").replace(".", "").replace("-", "").replace(
                "/", ""
            ) == "39053344705":
                return c["id"]
        pytest.fail(f"criar/reutilizar cliente: {r.status_code} {r.text}")
    assert r.status_code in (200, 201), f"criar cliente: {r.status_code} {r.text}"
    return r.json()["id"]


@pytest.fixture(scope="module")
def emprestimo_id(client, cliente_id):
    payload = {
        "cliente_id": cliente_id,
        "valor_principal_centavos": 1_000_000,  # R$ 10.000,00
        "taxa_juros_mensal": 2,
        "prazo_meses": 12,
        "metodo_calculo": "tabela_price",
        "data_inicio": time.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
    }
    r = client.post(f"{BASE_URL}/api/emprestimos", json=payload, timeout=60)
    assert r.status_code in (200, 201), f"criar emprestimo: {r.status_code} {r.text}"
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Dashboard: valores monetários NÃO zerados (schema centavos lido corretamente)
# ---------------------------------------------------------------------------
def test_dashboard_valores_monetarios_nao_zerados(client, emprestimo_id):
    r = client.get(f"{BASE_URL}/api/dashboard", timeout=60)
    assert r.status_code == 200, f"dashboard: {r.status_code} {r.text}"
    data = r.json()

    # ReaisJSONResponse converte *_centavos:int -> *:reais(float).
    total_capital = data.get("total_capital_emprestado")
    total_juros_receber = data.get("total_juros_a_receber")

    assert isinstance(total_capital, (int, float)), (
        f"total_capital_emprestado ausente/tipo inesperado: {type(total_capital)} / keys={list(data.keys())[:15]}"
    )
    assert isinstance(total_juros_receber, (int, float))

    # Empréstimo criado é R$ 10.000,00 => capital deve ser >= 10000.0
    assert total_capital >= 10_000.0, (
        f"total_capital_emprestado deve refletir empréstimo criado (>= 10000.0); obteve {total_capital}"
    )
    assert total_juros_receber > 0, (
        f"total_juros_a_receber deve ser > 0 após Price 2%/12m; obteve {total_juros_receber}"
    )
    assert data.get("total_emprestimos_ativos", 0) >= 1
    assert data.get("total_clientes_ativos", 0) >= 1


# ---------------------------------------------------------------------------
# Pagamento reflete no dashboard
# ---------------------------------------------------------------------------
def test_pagamento_reflete_no_dashboard(client, emprestimo_id):
    # Baseline
    r0 = client.get(f"{BASE_URL}/api/dashboard", timeout=60)
    assert r0.status_code == 200
    base = r0.json()
    base_recebido = float(base.get("recebido_mes_atual", 0) or 0)
    base_juros_rec = float(base.get("juros_recebidos_mes", 0) or 0)

    rp = client.get(f"{BASE_URL}/api/emprestimos/{emprestimo_id}/parcelas", timeout=30)
    assert rp.status_code == 200
    parcelas = rp.json()
    parcela = next(
        (p for p in parcelas if p.get("status") in ("pendente", "parcial", "atrasado")),
        None,
    )
    assert parcela is not None, "sem parcela pagável"

    valor_total_cents = parcela.get("valor_total_centavos") or int(
        round((parcela.get("valor_total") or 0) * 100)
    )
    valor_pago_cents = parcela.get("valor_pago_centavos") or int(
        round((parcela.get("valor_pago") or 0) * 100)
    )
    a_pagar = max(1, valor_total_cents - valor_pago_cents)

    pay = {
        "parcela_id": parcela["id"],
        "valor_pago_centavos": a_pagar,
        "metodo_pagamento": "pix",
        "data_pagamento": time.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
    }
    rpg = client.post(f"{BASE_URL}/api/pagamentos", json=pay, timeout=30)
    assert rpg.status_code in (200, 201), f"pagamento: {rpg.status_code} {rpg.text}"

    r1 = client.get(f"{BASE_URL}/api/dashboard", timeout=60)
    assert r1.status_code == 200
    after = r1.json()
    novo_recebido = float(after.get("recebido_mes_atual", 0) or 0)
    novo_juros_rec = float(after.get("juros_recebidos_mes", 0) or 0)

    esperado_delta_reais = a_pagar / 100.0
    assert novo_recebido > base_recebido, (
        f"recebido_mes_atual não aumentou: {base_recebido} -> {novo_recebido} (esperado +~{esperado_delta_reais})"
    )
    # Juros do mês só somam quando parcela vira 'paga'. Como pagamos o total,
    # deve subir também.
    assert novo_juros_rec > base_juros_rec, (
        f"juros_recebidos_mes não aumentou: {base_juros_rec} -> {novo_juros_rec}"
    )
    assert novo_juros_rec > 0


# ---------------------------------------------------------------------------
# /api/emprestimos: valores monetários > 0
# ---------------------------------------------------------------------------
def test_listar_emprestimos_valores_monetarios(client):
    r = client.get(f"{BASE_URL}/api/emprestimos?page=1&limit=20", timeout=30)
    assert r.status_code == 200
    body = r.json()
    items = body if isinstance(body, list) else body.get("items", body.get("data", []))
    assert items, "lista de empréstimos vazia"
    algum_com_valor = False
    for it in items:
        vp = it.get("valor_principal") or (
            (it.get("valor_principal_centavos") or 0) / 100.0
        )
        if vp and vp > 0:
            algum_com_valor = True
            break
    assert algum_com_valor, "todos empréstimos com valor_principal zero (schema não migrado?)"


# ---------------------------------------------------------------------------
# /api/analise/clientes: valores > 0
# ---------------------------------------------------------------------------
def test_analise_clientes_valores(client):
    r = client.get(f"{BASE_URL}/api/analise/clientes", timeout=60)
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    body = r.json()
    clientes = body.get("clientes") or body.get("items") or []
    assert clientes, "sem clientes na análise"
    achou = False
    for c in clientes:
        # após migração e conversão de fronteira, campos são em reais (sem _centavos)
        val = (
            c.get("total_devido")
            or c.get("total_emprestado")
            or c.get("valor_total_emprestado")
            or (c.get("total_emprestado_centavos") or 0) / 100.0
        )
        if val and val > 0:
            achou = True
            break
    assert achou, f"nenhum cliente com valor monetário > 0 (schema não migrado?). Sample keys: {list(clientes[0].keys())}"


# ---------------------------------------------------------------------------
# Contrato do dashboard: não vaza chaves *_centavos, tem chaves esperadas em reais
# ---------------------------------------------------------------------------
def test_dashboard_contrato_sem_vazar_centavos(client):
    r = client.get(f"{BASE_URL}/api/dashboard", timeout=60)
    assert r.status_code == 200
    data = r.json()
    leaked = [k for k in data.keys() if k.endswith("_centavos")]
    assert not leaked, f"chaves *_centavos vazando: {leaked}"
    # chaves esperadas (em reais/int)
    for k in (
        "total_capital_emprestado",
        "total_juros_a_receber",
        "total_juros_recebidos",
        "taxa_inadimplencia",
        "total_clientes_ativos",
        "total_emprestimos_ativos",
        "recebido_mes_atual",
        "juros_recebidos_mes",
    ):
        assert k in data, f"chave ausente: {k}. keys={list(data.keys())}"
