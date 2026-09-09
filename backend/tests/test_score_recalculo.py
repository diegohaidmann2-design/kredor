"""
Testes do fix de SCORE (bug: score dos clientes não muda em /analise/clientes)
Módulos cobertos:
 - POST /api/auth/login (campo 'senha')
 - GET /api/analise/clientes (variação de scores/classificações)
 - GET /api/analise/score/{cliente_id} (detalhes + histórico)
 - POST /api/analise/recalcular/{cliente_id}
 - POST /api/pagamentos -> dispara recálculo de score
 - DELETE /api/pagamentos/{id} (estorno) -> dispara recálculo de score
"""
import os
import re
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

CRED_PATH = Path("/app/memory/test_credentials.md")


@pytest.fixture(scope="session")
def credentials():
    if not CRED_PATH.exists():
        pytest.skip("missing test_credentials.md")
    content = CRED_PATH.read_text(encoding="utf-8")
    email = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?email(?:\*\*)?\s*:\s*`?([^`\s]+)', content)
    senha = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?senha(?:\*\*)?\s*:\s*`?([^`\s]+)', content)
    if not email or not senha:
        pytest.skip("no credentials parsed")
    return {"email": email.group(1), "senha": senha.group(1)}


@pytest.fixture(scope="session")
def client(credentials):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json=credentials, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"Login failed {r.status_code}: {r.text[:400]}")
    data = r.json()
    assert "access_token" in data, f"no access_token: {data}"
    assert isinstance(data["access_token"], str) and data["access_token"]
    s.headers.update({"Authorization": f"Bearer {data['access_token']}"})
    return s


# --- GET /api/analise/clientes ---
class TestAnaliseClientes:
    def test_scores_variam(self, client):
        r = client.get(f"{BASE_URL}/api/analise/clientes?limit=100", timeout=120)
        assert r.status_code == 200, r.text[:400]
        data = r.json()
        clientes = data.get("clientes")
        assert isinstance(clientes, list) and len(clientes) > 0, "nenhum cliente retornado"
        for c in clientes:
            assert "score" in c and "classificacao" in c
            assert isinstance(c["score"], (int, float))
        scores = {c["score"] for c in clientes}
        classes = {c["classificacao"] for c in clientes}
        print(f"total={data.get('total')} scores_unicos={sorted(scores)} classes={sorted(classes)}")
        assert scores != {60} and scores != {60.0}, "TODOS os scores continuam 60 (bug não corrigido)"
        assert len(scores) > 1, "scores sem variação"
        assert len(classes) > 1, f"apenas uma classificação presente: {classes}"

    def test_no_mongo_id_leak(self, client):
        r = client.get(f"{BASE_URL}/api/analise/clientes?limit=5", timeout=120)
        assert r.status_code == 200
        for c in r.json()["clientes"]:
            assert "_id" not in c

    def test_filtro_classificacao(self, client):
        r = client.get(f"{BASE_URL}/api/analise/clientes?classificacao=A&limit=50", timeout=120)
        assert r.status_code == 200, r.text[:300]
        for c in r.json()["clientes"]:
            assert c["classificacao"] == "A"


# --- GET /api/analise/score/{id} + POST /api/analise/recalcular/{id} ---
class TestScoreDetalhe:
    @pytest.fixture(scope="class")
    def um_cliente(self, client):
        r = client.get(f"{BASE_URL}/api/analise/clientes?limit=100", timeout=120)
        assert r.status_code == 200
        clientes = r.json()["clientes"]
        assert clientes
        # preferir cliente com empréstimo ativo
        com_emp = [c for c in clientes if c.get("emprestimos_ativos", 0) > 0]
        return (com_emp or clientes)[0]

    def test_detalhes_score(self, client, um_cliente):
        cid = um_cliente["id"]
        r = client.get(f"{BASE_URL}/api/analise/score/{cid}", timeout=120)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        for k in ("score", "classificacao", "componentes", "metricas", "historico", "cliente"):
            assert k in d, f"campo {k} ausente"
        assert d["classificacao"] in list("ABCDE")
        assert 0 <= d["score"] <= 100
        assert set(d["componentes"].keys()) >= {
            "pontualidade", "atrasos", "valor_pago_centavos", "tempo_relacionamento", "historico_recente"
        }
        assert isinstance(d["historico"], list)
        print(f"cliente={d['cliente']['nome']} score={d['score']} hist={len(d['historico'])}")
        assert len(d["historico"]) >= 1, "histórico vazio (backfill não persistiu scores_historico)"

    def test_score_404_cliente_inexistente(self, client):
        r = client.get(f"{BASE_URL}/api/analise/score/TEST_inexistente_123", timeout=60)
        assert r.status_code == 404, r.status_code

    def test_recalcular_manual(self, client, um_cliente):
        cid = um_cliente["id"]
        r = client.post(f"{BASE_URL}/api/analise/recalcular/{cid}", timeout=120)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        for k in ("score_anterior", "score_novo", "variacao", "classificacao"):
            assert k in d, f"campo {k} ausente: {d}"
        assert isinstance(d["score_novo"], (int, float))
        print(f"recalculo manual: {d}")


# --- POST /api/pagamentos dispara recálculo (núcleo do fix) ---
class TestPagamentoRecalculaScore:
    def test_pagamento_recalcula_e_estorno_recalcula(self, client):
        # 1. escolher empréstimo ativo
        r = client.get(f"{BASE_URL}/api/emprestimos", timeout=120)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        emprestimos = body.get("items") if isinstance(body, dict) else body
        assert emprestimos, "nenhum empréstimo retornado"
        ativos = [e for e in emprestimos if e.get("status") in ("ativo", "inadimplente")]
        assert ativos, "nenhum empréstimo ativo"

        alvo = None
        for emp in ativos:
            rp = client.get(f"{BASE_URL}/api/emprestimos/{emp['id']}/parcelas", timeout=120)
            if rp.status_code != 200:
                continue
            pb = rp.json()
            parcelas = pb.get("items") if isinstance(pb, dict) else pb
            pend = [p for p in (parcelas or []) if p.get("status") in ("pendente", "atrasado", "parcial")]
            if pend:
                alvo = (emp, pend[0])
                break
        assert alvo, "nenhuma parcela pendente/atrasada encontrada"
        emp, parcela = alvo
        cliente_id = emp["cliente_id"]

        # 2. score antes (histórico como prova de recálculo)
        r_before = client.get(f"{BASE_URL}/api/analise/score/{cliente_id}", timeout=120)
        assert r_before.status_code == 200, r_before.text[:300]
        before = r_before.json()
        hist_before = len(before["historico"])
        score_before = before["score"]
        print(f"ANTES: cliente={cliente_id} score={score_before} hist={hist_before}")

        # 3. registrar pagamento parcial pequeno
        payload = {"parcela_id": parcela["id"], "valor_pago_centavos": 10, "metodo_pagamento": "dinheiro"}
        rpg = client.post(f"{BASE_URL}/api/pagamentos", json=payload, timeout=120)
        assert rpg.status_code in (200, 201), f"pagamento falhou {rpg.status_code}: {rpg.text[:400]}"
        pagamento = rpg.json()
        pagamento_id = pagamento.get("id")
        assert pagamento_id, pagamento

        try:
            # 4. score depois -> novo registro no histórico
            r_after = client.get(f"{BASE_URL}/api/analise/score/{cliente_id}", timeout=120)
            assert r_after.status_code == 200
            after = r_after.json()
            hist_after = len(after["historico"])
            print(f"DEPOIS: score={after['score']} hist={hist_after}")
            assert hist_after > hist_before, (
                "Registrar pagamento NÃO gerou novo registro em scores_historico "
                f"(antes={hist_before}, depois={hist_after})"
            )

            # score_atual persistido no cliente deve refletir o cálculo
            rl = client.get(f"{BASE_URL}/api/analise/clientes?limit=100", timeout=120)
            assert rl.status_code == 200
            match = [c for c in rl.json()["clientes"] if c["id"] == cliente_id]
            assert match, "cliente não encontrado na listagem"
            assert abs(match[0]["score"] - after["score"]) < 0.05, (
                f"score persistido ({match[0]['score']}) != score calculado ({after['score']})"
            )
        finally:
            # 5. estorno + recálculo
            rd = client.delete(f"{BASE_URL}/api/pagamentos/{pagamento_id}", timeout=120)
            print(f"estorno status={rd.status_code} body={rd.text[:200]}")
            assert rd.status_code in (200, 204), f"estorno falhou: {rd.text[:300]}"

        r_est = client.get(f"{BASE_URL}/api/analise/score/{cliente_id}", timeout=120)
        assert r_est.status_code == 200
        est = r_est.json()
        print(f"POS-ESTORNO: score={est['score']} hist={len(est['historico'])}")
        assert len(est["historico"]) > hist_after, (
            "Estorno NÃO gerou novo registro em scores_historico"
        )
