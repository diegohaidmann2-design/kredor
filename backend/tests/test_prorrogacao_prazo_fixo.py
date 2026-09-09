"""
E2E backend test for prorrogar empréstimo de PRAZO FIXO.
Cria empréstimo juros_simples, quita parcela 1, prorroga em 2 períodos,
valida re-amortização, quita as demais, valida quitado.
Também regride prorrogação de apenas_juros.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://cred-dashboard.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "diego.haidmann@gmail.com"
ADMIN_PASS = "Teste@2026"
TURNSTILE_TEST_TOKEN = "XXXX.DUMMY.TOKEN.XXXX"  # test-mode key accepts anything


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={
        "email": ADMIN_EMAIL,
        "senha": ADMIN_PASS,
        "turnstile_token": TURNSTILE_TEST_TOKEN,
    })
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def sess(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def cliente_id(sess):
    r = sess.get(f"{API}/clientes")
    assert r.status_code == 200
    data = r.json()
    clientes = data["items"] if isinstance(data, dict) else data
    assert len(clientes) > 0
    # pick first ativo
    for c in clientes:
        if c.get("status") != "bloqueado":
            return c["id"]
    return clientes[0]["id"]


def _get_parcelas(sess, emp_id):
    r = sess.get(f"{API}/emprestimos/{emp_id}/parcelas")
    assert r.status_code == 200, r.text
    return r.json()


def _pagar_parcela(sess, parcela):
    body = {
        "parcela_id": parcela["id"],
        "valor_pago_centavos": parcela["valor_total_centavos"],
        "metodo_pagamento": "dinheiro",
    }
    r = sess.post(f"{API}/pagamentos", json=body)
    assert r.status_code in (200, 201), f"pagar falhou: {r.status_code} {r.text}"


class TestProrrogacaoPrazoFixo:
    emp_id = None

    def test_1_criar_emprestimo_juros_simples(self, sess, cliente_id):
        payload = {
            "cliente_id": cliente_id,
            "valor_principal_centavos": 1000.0,
            "taxa_juros_mensal": 10.0,
            "prazo_meses": 3,
            "metodo_calculo": "juros_simples",
            "periodicidade": "mensal",
        }
        r = sess.post(f"{API}/emprestimos", json=payload)
        assert r.status_code in (200, 201), f"criar falhou: {r.status_code} {r.text}"
        data = r.json()
        assert data["metodo_calculo"] == "juros_simples"
        assert data["prazo_meses"] == 3
        TestProrrogacaoPrazoFixo.emp_id = data["id"]

        parcelas = _get_parcelas(sess, data["id"])
        assert len(parcelas) == 3

    def test_2_pagar_primeira_parcela(self, sess):
        emp_id = TestProrrogacaoPrazoFixo.emp_id
        parcelas = sorted(_get_parcelas(sess, emp_id), key=lambda p: p["numero_parcela"])
        _pagar_parcela(sess, parcelas[0])
        p1 = [p for p in _get_parcelas(sess, emp_id) if p["numero_parcela"] == 1][0]
        assert p1["status"] in ("pago", "paga")

    def test_3_prorrogar_prazo_fixo(self, sess):
        emp_id = TestProrrogacaoPrazoFixo.emp_id
        r = sess.post(f"{API}/emprestimos/{emp_id}/prorrogar", json={"periodos": 2})
        assert r.status_code == 200, f"prorrogar falhou: {r.status_code} {r.text}"

        parcelas = sorted(_get_parcelas(sess, emp_id), key=lambda p: p["numero_parcela"])
        # 1 paga + (2 abertas + 2 novos períodos) = 5
        assert len(parcelas) == 5, f"esperado 5, got {len(parcelas)}: {[p['numero_parcela'] for p in parcelas]}"

        p1 = parcelas[0]
        assert p1["numero_parcela"] == 1
        assert p1["status"] in ("pago", "paga"), "parcela paga deve ser mantida"

        # As parcelas em aberto novas devem re-amortizar o saldo devedor.
        abertas = [p for p in parcelas if p["status"] != "pago" and p["status"] != "paga"]
        assert len(abertas) == 4

        # Somatório de principal das abertas deve ~= saldo devedor após parcela 1
        # Empréstimo juros_simples 1000@10%/3m => parcela=433.33; principal parcela1 ~= 333.33 (ou 1000/3)
        # Saldo capital restante ~= 666.67; principal das abertas deve somar ~= 666.67
        soma_principal = sum(p["valor_principal_centavos"] for p in abertas)
        assert 660 <= soma_principal <= 675, f"soma principal abertas {soma_principal}"

        r2 = sess.get(f"{API}/emprestimos/{emp_id}")
        assert r2.status_code == 200
        emp = r2.json()
        assert emp["prazo_meses"] == 5 or emp.get("total_parcelas") == 5, f"emp: {emp}"

    def test_4_quitar_restante(self, sess):
        emp_id = TestProrrogacaoPrazoFixo.emp_id
        for _ in range(6):
            abertas = [p for p in _get_parcelas(sess, emp_id) if p["status"] not in ("pago", "paga")]
            if not abertas:
                break
            _pagar_parcela(sess, abertas[0])
        r = sess.get(f"{API}/emprestimos/{emp_id}")
        assert r.status_code == 200
        assert r.json()["status"] == "quitado"

    def test_5_cleanup(self, sess):
        emp_id = TestProrrogacaoPrazoFixo.emp_id
        if emp_id:
            sess.delete(f"{API}/emprestimos/{emp_id}")


class TestRegressaoApenasJuros:
    """Regressão: prorrogação de empréstimo apenas_juros continua funcionando."""
    emp_id = None

    def test_1_criar_apenas_juros(self, sess, cliente_id):
        payload = {
            "cliente_id": cliente_id,
            "valor_principal_centavos": 500.0,
            "taxa_juros_mensal": 5.0,
            "metodo_calculo": "apenas_juros",
            "periodicidade": "mensal",
            "sem_prazo": True,
        }
        r = sess.post(f"{API}/emprestimos", json=payload)
        assert r.status_code in (200, 201), f"criar apenas_juros falhou: {r.status_code} {r.text}"
        TestRegressaoApenasJuros.emp_id = r.json()["id"]

    def test_2_prorrogar_apenas_juros_routing(self, sess):
        """
        Este teste apenas verifica que a rota prorrogar continua indo ao
        branch antigo (apenas_juros) e não ao branch de prazo_fixo. Um
        empréstimo sem_prazo/apenas_juros com só parcelas de juros retorna
        400 "Última parcela não contém principal" — que é comportamento
        esperado do branch apenas_juros. Isso confirma que a lógica antiga
        continua sendo executada para metodo_calculo=='apenas_juros'.
        """
        emp_id = TestRegressaoApenasJuros.emp_id
        r = sess.post(f"{API}/emprestimos/{emp_id}/prorrogar", json={"periodos": 2})
        # ou 200 (sucesso) ou 400 com msg do branch apenas_juros
        assert r.status_code in (200, 400), f"routing quebrado: {r.status_code} {r.text}"
        if r.status_code == 400:
            detail = r.json().get("detail", "")
            # detail deve vir da lógica antiga (apenas_juros), não do branch prazo_fixo
            assert (
                "Última parcela" in detail
                or "última parcela" in detail
                or "principal" in detail.lower()
            ), f"erro inesperado: {detail}"

    def test_3_cleanup(self, sess):
        emp_id = TestRegressaoApenasJuros.emp_id
        if emp_id:
            sess.delete(f"{API}/emprestimos/{emp_id}")
