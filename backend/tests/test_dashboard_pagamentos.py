"""
Testes backend para melhorias do Dashboard e tela de Pagamentos.

Cobertura:
- GET /api/dashboard - novos campos (valor_em_atraso, a_receber_*, aging, top_inadimplentes, etc)
- BUG FIX: total_juros_recebidos = soma valor_juros de parcelas pagas
- DELETE /api/pagamentos/{id} - estorno completo
- POST /api/parcelas/cobrar-em-massa - cobrança em massa
- GET /api/parcelas/pendentes - inclui campo ultima_cobranca_em
- Modelo Pagamento.tipo
"""
import os
import pytest
import requests
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback para .env do frontend
    try:
        from pathlib import Path
        env_path = Path("/app/frontend/.env")
        for line in env_path.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL"):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass

ADMIN_EMAIL = "admin@gestorcerd.com"
ADMIN_SENHA = "admin123"


@pytest.fixture(scope="session")
def auth_token():
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "senha": ADMIN_SENHA},
        timeout=30,
    )
    assert resp.status_code == 200, f"Login falhou: {resp.status_code} {resp.text}"
    data = resp.json()
    token = data.get("token") or data.get("access_token")
    assert token, f"Token nao encontrado: {data}"
    return token


@pytest.fixture(scope="session")
def headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


# ================== DASHBOARD ==================

class TestDashboard:
    def test_dashboard_returns_200(self, headers):
        r = requests.get(f"{BASE_URL}/api/dashboard", headers=headers, timeout=60)
        assert r.status_code == 200, r.text

    def test_dashboard_novos_campos_presentes(self, headers):
        r = requests.get(f"{BASE_URL}/api/dashboard", headers=headers, timeout=60)
        data = r.json()
        expected = [
            "valor_em_atraso", "a_receber_hoje", "a_receber_semana",
            "a_receber_mes", "recebido_mes_atual", "proximo_recebimento",
            "aging_atrasos", "top_inadimplentes",
        ]
        for key in expected:
            assert key in data, f"Campo {key} ausente no dashboard"

    def test_dashboard_aging_atrasos_estrutura(self, headers):
        r = requests.get(f"{BASE_URL}/api/dashboard", headers=headers, timeout=60)
        data = r.json()
        aging = data["aging_atrasos"]
        assert isinstance(aging, list)
        assert len(aging) == 4, f"Esperado 4 faixas, obtido {len(aging)}"
        faixas = [a["faixa"] for a in aging]
        assert faixas == ["1-7 dias", "8-15 dias", "16-30 dias", "30+ dias"]
        for a in aging:
            assert "valor" in a and "quantidade" in a and "color" in a
            assert isinstance(a["valor"], (int, float))
            assert isinstance(a["quantidade"], int)

    def test_dashboard_top_inadimplentes_estrutura(self, headers):
        r = requests.get(f"{BASE_URL}/api/dashboard", headers=headers, timeout=60)
        data = r.json()
        top = data["top_inadimplentes"]
        assert isinstance(top, list)
        assert len(top) <= 10
        if top:
            item = top[0]
            for k in ["cliente_id", "cliente_nome", "valor_devido",
                      "dias_max_atraso", "parcelas_atrasadas"]:
                assert k in item, f"Falta {k} em top_inadimplentes"
            # Ordem decrescente por valor_devido
            valores = [t["valor_devido"] for t in top]
            assert valores == sorted(valores, reverse=True)

    def test_juros_recebidos_nao_eh_30_porcento(self, headers):
        """Bug fix: total_juros_recebidos nao pode ser 30% chutado do total de pagamentos."""
        r = requests.get(f"{BASE_URL}/api/dashboard", headers=headers, timeout=60)
        data = r.json()
        juros_dashboard = float(data["total_juros_recebidos"])
        recebido_mes = float(data["recebido_mes_atual"])

        # Calcular a soma real direta no banco via lista pagamentos
        pag_resp = requests.get(f"{BASE_URL}/api/pagamentos", headers=headers, timeout=60)
        assert pag_resp.status_code == 200
        pagamentos = pag_resp.json()
        total_pagamentos = sum(p.get("valor_pago", 0) or 0 for p in pagamentos)

        # Se chutado seria == round(total_pagamentos * 0.3, 2)
        chutado = round(total_pagamentos * 0.3, 2)
        # Verificacao robusta: tolerancia minima
        if total_pagamentos > 0:
            assert abs(juros_dashboard - chutado) > 0.01 or juros_dashboard == 0, (
                f"juros_recebidos={juros_dashboard} parece ser 30% de {total_pagamentos} (chutado)"
            )

        assert juros_dashboard >= 0
        assert recebido_mes >= 0

    def test_dashboard_valores_nao_negativos(self, headers):
        r = requests.get(f"{BASE_URL}/api/dashboard", headers=headers, timeout=60)
        data = r.json()
        for k in ["valor_em_atraso", "a_receber_hoje", "a_receber_semana",
                  "a_receber_mes", "recebido_mes_atual", "total_juros_recebidos",
                  "total_juros_a_receber"]:
            assert data[k] >= 0, f"{k} negativo: {data[k]}"


# ================== PARCELAS PENDENTES ==================

class TestParcelasPendentes:
    def test_parcelas_pendentes_retorna_lista(self, headers):
        r = requests.get(f"{BASE_URL}/api/parcelas/pendentes", headers=headers, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list)

    def test_parcelas_pendentes_inclui_ultima_cobranca_em(self, headers):
        r = requests.get(f"{BASE_URL}/api/parcelas/pendentes", headers=headers, timeout=60)
        assert r.status_code == 200
        data = r.json()
        if data:
            # Pelo menos uma parcela deve ter a chave (pode ser null)
            assert "ultima_cobranca_em" in data[0], (
                f"Campo ultima_cobranca_em ausente. Chaves: {list(data[0].keys())}"
            )


# ================== COBRANCA EM MASSA ==================

class TestCobrancaEmMassa:
    def test_cobrar_em_massa_lista_vazia_400(self, headers):
        r = requests.post(
            f"{BASE_URL}/api/parcelas/cobrar-em-massa",
            headers=headers,
            json={"parcela_ids": []},
            timeout=30,
        )
        assert r.status_code == 400

    def test_cobrar_em_massa_limite_50(self, headers):
        ids = [str(uuid.uuid4()) for _ in range(51)]
        r = requests.post(
            f"{BASE_URL}/api/parcelas/cobrar-em-massa",
            headers=headers,
            json={"parcela_ids": ids},
            timeout=30,
        )
        assert r.status_code == 400
        assert "50" in r.text

    def test_cobrar_em_massa_estrutura_resposta(self, headers):
        # Buscar uma parcela pendente real
        pend = requests.get(f"{BASE_URL}/api/parcelas/pendentes", headers=headers, timeout=60)
        parcelas = pend.json()
        if not parcelas:
            pytest.skip("Sem parcelas pendentes para testar")

        pid = parcelas[0]["id"]
        r = requests.post(
            f"{BASE_URL}/api/parcelas/cobrar-em-massa",
            headers=headers,
            json={"parcela_ids": [pid]},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ["enviadas", "falhas", "detalhes"]:
            assert k in data
        assert isinstance(data["detalhes"], list)
        assert data["enviadas"] + data["falhas"] == 1
        # Sem whatsapp conectado, deve haver falhas com mensagem
        if data["falhas"] >= 1:
            assert data["detalhes"][0]["sucesso"] is False
            assert isinstance(data["detalhes"][0]["mensagem"], str)


# ================== ESTORNO PAGAMENTO ==================

class TestEstornoPagamento:
    def _criar_pagamento_teste(self, headers):
        """Helper: cria pagamento parcial em uma parcela pendente."""
        pend = requests.get(f"{BASE_URL}/api/parcelas/pendentes", headers=headers, timeout=60)
        parcelas = pend.json()
        if not parcelas:
            return None, None, None

        # Pega parcela com saldo > 0
        for parcela in parcelas:
            saldo = (parcela.get("valor_total", 0) - parcela.get("valor_pago", 0))
            if saldo > 1:
                valor = round(min(saldo, 10.0), 2)
                payload = {
                    "parcela_id": parcela["id"],
                    "valor_pago": valor,
                    "metodo_pagamento": "pix",
                    "observacoes": "TEST_estorno",
                }
                r = requests.post(
                    f"{BASE_URL}/api/pagamentos",
                    headers=headers,
                    json=payload,
                    timeout=30,
                )
                if r.status_code == 200:
                    return r.json(), parcela["id"], valor
        return None, None, None

    def test_estornar_pagamento_inexistente_404(self, headers):
        r = requests.delete(
            f"{BASE_URL}/api/pagamentos/{uuid.uuid4()}",
            headers=headers,
            timeout=30,
        )
        assert r.status_code == 404

    def test_estornar_pagamento_completo(self, headers):
        pag, parcela_id, valor = self._criar_pagamento_teste(headers)
        if not pag:
            pytest.skip("Nao foi possivel criar pagamento teste")

        # Estado da parcela antes
        # Estornar
        r = requests.delete(
            f"{BASE_URL}/api/pagamentos/{pag['id']}",
            headers=headers,
            timeout=30,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("success") is True
        assert data.get("valor_estornado") == valor

        # Pagamento nao deve mais aparecer na listagem (soft delete)
        lista = requests.get(f"{BASE_URL}/api/pagamentos", headers=headers, timeout=60).json()
        ids = [p["id"] for p in lista]
        assert pag["id"] not in ids, "Pagamento estornado ainda aparece na listagem"

    def test_estornar_amortizacao_bloqueado(self, headers):
        """Estorno de tipo='amortizacao' deve retornar 400."""
        # Criar pagamento e marca-lo como amortizacao via update direto seria invasivo.
        # Vamos verificar se algum pagamento existente eh amortizacao
        from pymongo import MongoClient
        # Carregar .env do backend
        try:
            from pathlib import Path
            for line in Path("/app/backend/.env").read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
        except Exception:
            pass
        mongo_url = os.environ.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME")
        if not mongo_url or not db_name:
            pytest.skip("Sem acesso direto ao mongo")

        client = MongoClient(mongo_url)
        db = client[db_name]

        # Pegar um pagamento existente, criar copia marcada como amortizacao
        pag = db.pagamentos.find_one(
            {"deleted": {"$ne": True}}, {"_id": 0}
        )
        if not pag:
            pytest.skip("Sem pagamentos para teste")

        # Inserir copia teste
        novo = dict(pag)
        novo["id"] = f"TEST_{uuid.uuid4()}"
        novo["tipo"] = "amortizacao"
        novo["observacoes"] = "TEST_amortizacao_bloqueio"
        db.pagamentos.insert_one(novo)

        try:
            r = requests.delete(
                f"{BASE_URL}/api/pagamentos/{novo['id']}",
                headers=headers,
                timeout=30,
            )
            assert r.status_code == 400, f"Esperado 400, obtido {r.status_code}: {r.text}"
            assert "amortiza" in r.text.lower()
        finally:
            db.pagamentos.delete_one({"id": novo["id"]})


# ================== MODELO PAGAMENTO ==================

class TestModeloPagamento:
    def test_listagem_pagamentos_inclui_tipo(self, headers):
        r = requests.get(f"{BASE_URL}/api/pagamentos", headers=headers, timeout=60)
        assert r.status_code == 200
        pags = r.json()
        if pags:
            assert "tipo" in pags[0], "Campo tipo ausente"
            assert pags[0]["tipo"] in ("pagamento", "amortizacao"), pags[0]["tipo"]
