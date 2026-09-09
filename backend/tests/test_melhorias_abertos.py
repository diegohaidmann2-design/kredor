"""
Testes das 4 melhorias de Empréstimos Abertos (Kredor):
 1. Serviço compartilhado de geração de parcela (services/parcela_service.py)
 2. Alerta automático de inadimplência (jobs/inadimplencia_job.py)
 3. Painel de Empréstimos Abertos (GET /api/emprestimos/abertos/resumo)
 4. Reversão automática inadimplente -> ativo ao quitar atrasadas (routes/pagamentos.py)

Usa dados sintéticos prefixados com TEST_ para não corromper os dados reais importados.
"""
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL ausente")
BASE_URL = base_url.rstrip("/")

backend_env = dotenv_values("/app/backend/.env")
MONGO_URL = os.environ.get("MONGO_URL") or backend_env.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME") or backend_env.get("DB_NAME")

BACKEND_DIR = "/app/backend"


# ---------------------------------------------------------------- fixtures
@pytest.fixture(scope="session")
def mongo_db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="session")
def test_credentials():
    path = Path("/app/memory/test_credentials.md")
    if not path.exists():
        pytest.skip("Missing /app/memory/test_credentials.md")
    content = path.read_text(encoding="utf-8")
    email = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?email(?:\*\*)?\s*:\s*`?([^`\s]+)', content)
    senha = re.search(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?senha(?:\*\*)?\s*:\s*`?([^`\s]+)', content)
    if not email or not senha:
        pytest.skip("credenciais não encontradas")
    return {"email": email.group(1), "senha": senha.group(1)}


@pytest.fixture(scope="session")
def auth(test_credentials):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=test_credentials, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"Login falhou {r.status_code}: {r.text[:300]}")
    token = r.json().get("access_token")
    assert token, f"sem access_token: {r.json().keys()}"
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="session")
def usuario_id(mongo_db, test_credentials):
    u = mongo_db.usuarios.find_one({"email": test_credentials["email"]}, {"_id": 0, "id": 1})
    assert u, "usuário admin não encontrado no banco"
    return u["id"]


def _run_job(module: str) -> str:
    proc = subprocess.run(
        [sys.executable if Path(sys.executable).exists() else "/root/.venv/bin/python", "-m", module],
        cwd=BACKEND_DIR, capture_output=True, text=True, timeout=280,
    )
    assert proc.returncode == 0, f"job {module} falhou: {proc.stdout[-2000:]} {proc.stderr[-2000:]}"
    return proc.stdout


# ---------------------------------------------------- 3. Painel de abertos (API)
class TestResumoAbertos:
    def test_requer_autenticacao(self):
        r = requests.get(f"{BASE_URL}/api/emprestimos/abertos/resumo", timeout=60)
        assert r.status_code in (401, 403), r.status_code

    def test_estrutura_e_consistencia(self, auth, mongo_db, usuario_id):
        r = auth.get(f"{BASE_URL}/api/emprestimos/abertos/resumo", timeout=120)
        assert r.status_code == 200, r.text[:400]
        data = r.json()
        assert set(["total_emprestimos", "totais", "itens"]).issubset(data.keys())
        assert set(["principal", "juros_gerado", "juros_recebido", "juros_em_aberto"]) == set(data["totais"].keys())
        assert data["total_emprestimos"] == len(data["itens"])

        # deve casar com a contagem no banco (sem_prazo + ativo/inadimplente do usuário)
        esperado = mongo_db.emprestimos.count_documents({
            "usuario_id": usuario_id, "sem_prazo": True,
            "status": {"$in": ["ativo", "inadimplente"]}, "deleted": {"$ne": True},
        })
        assert data["total_emprestimos"] == esperado, f"API {data['total_emprestimos']} != DB {esperado}"
        assert data["total_emprestimos"] > 0, "sem dados para validar"

        campos = {"cliente_nome", "status", "valor_principal", "taxa_juros", "periodicidade",
                  "juros_gerado", "juros_recebido", "juros_em_aberto", "parcelas_atrasadas",
                  "proxima_parcela"}
        soma_gerado = 0.0
        for it in data["itens"]:
            assert campos.issubset(it.keys()), f"campos faltando: {campos - set(it.keys())}"
            assert "_id" not in it
            assert it["status"] in ("ativo", "inadimplente")
            soma_gerado += it["juros_gerado"]
            if it["proxima_parcela"] is not None:
                p = it["proxima_parcela"]
                assert {"parcela_id", "numero_parcela", "data_vencimento", "valor",
                        "status", "dias_atraso"} == set(p.keys())
                assert isinstance(p["parcela_id"], str) and p["parcela_id"]
                assert p["status"] in ("pendente", "atrasado", "parcial")
                assert p["dias_atraso"] >= 0
        assert abs(soma_gerado - data["totais"]["juros_gerado"]) < 1.0

    def test_ordenacao_mais_atrasados_primeiro(self, auth):
        data = auth.get(f"{BASE_URL}/api/emprestimos/abertos/resumo", timeout=120).json()
        atrasos = [it["parcelas_atrasadas"] for it in data["itens"]]
        assert atrasos == sorted(atrasos, reverse=True), atrasos

    def test_apenas_sem_prazo_do_usuario(self, auth, mongo_db, usuario_id):
        data = auth.get(f"{BASE_URL}/api/emprestimos/abertos/resumo", timeout=120).json()
        for it in data["itens"][:10]:
            emp = mongo_db.emprestimos.find_one({"id": it["emprestimo_id"]}, {"_id": 0})
            assert emp["sem_prazo"] is True
            assert emp["usuario_id"] == usuario_id


# ------------------------------------- 1. Serviço compartilhado / job idempotente
class TestJobAbertosIdempotente:
    def test_job_nao_duplica_parcelas(self, mongo_db):
        # roda uma vez para estabilizar, depois valida que a 2a execução não muda nada
        _run_job("jobs.emprestimos_abertos_job")
        antes = mongo_db.parcelas.count_documents({})
        out = _run_job("jobs.emprestimos_abertos_job")
        depois = mongo_db.parcelas.count_documents({})
        assert depois == antes, f"job duplicou parcelas: {antes} -> {depois}\n{out[-1500:]}"
        assert "0 parcela(s) gerada(s)" in out, out[-1500:]

    def test_sem_duplicidade_numero_parcela(self, mongo_db):
        dup = list(mongo_db.parcelas.aggregate([
            {"$match": {"deleted": {"$ne": True}}},
            {"$group": {"_id": {"e": "$emprestimo_id", "n": "$numero_parcela"}, "c": {"$sum": 1}}},
            {"$match": {"c": {"$gt": 1}}},
            {"$limit": 5},
        ]))
        assert dup == [], f"parcelas duplicadas: {dup}"

    def test_job_cobre_inadimplentes(self, mongo_db, usuario_id):
        """Empréstimos abertos inadimplentes devem ter parcela futura pendente gerada."""
        inad = list(mongo_db.emprestimos.find(
            {"sem_prazo": True, "status": "inadimplente", "deleted": {"$ne": True}}, {"_id": 0, "id": 1}
        ).limit(20))
        assert inad, "sem empréstimo inadimplente aberto para validar"
        sem_aberta = []
        for e in inad:
            abertas = mongo_db.parcelas.count_documents({
                "emprestimo_id": e["id"], "deleted": {"$ne": True},
                "status": {"$in": ["pendente", "atrasado", "parcial"]},
            })
            if abertas == 0:
                sem_aberta.append(e["id"])
        assert sem_aberta == [], f"inadimplentes abertos sem parcela em aberto: {sem_aberta}"

    def test_valor_juros_calculado_corretamente(self, mongo_db):
        """valor_juros = valor_principal * taxa/100 (semanal ou mensal)."""
        erros = []
        for e in mongo_db.emprestimos.find(
            {"sem_prazo": True, "status": {"$in": ["ativo", "inadimplente"]}, "deleted": {"$ne": True}},
            {"_id": 0}
        ).limit(30):
            taxa = e.get("taxa_juros_semanal") if e.get("periodicidade") == "semanal" else e.get("taxa_juros_mensal")
            esperado = round((e.get("valor_principal") or 0) * ((taxa or 0) / 100), 2)
            ultima = mongo_db.parcelas.find_one(
                {"emprestimo_id": e["id"], "deleted": {"$ne": True}}, {"_id": 0},
                sort=[("numero_parcela", -1)]
            )
            if ultima and abs((ultima.get("valor_juros") or 0) - esperado) > 0.02:
                erros.append((e["id"], ultima.get("valor_juros"), esperado))
        assert erros == [], f"juros divergentes: {erros}"

    def test_servico_compartilhado_usado_nos_dois_fluxos(self):
        job = Path(f"{BACKEND_DIR}/jobs/emprestimos_abertos_job.py").read_text()
        pag = Path(f"{BACKEND_DIR}/routes/pagamentos.py").read_text()
        assert "inserir_parcela_juros_aberto" in job
        assert "inserir_parcela_juros_aberto" in pag


# ------------------------------------------ 2 & 4. Dados sintéticos (alerta + reversão)
def _criar_emprestimo_sintetico(mongo_db, usuario_id, status, vencimentos, dias_inicio=90):
    """Cria cliente + empréstimo aberto + parcelas atrasadas sintéticos (TEST_)."""
    cliente_id = str(uuid.uuid4())
    mongo_db.clientes.insert_one({
        "id": cliente_id, "nome": "TEST_Cliente Melhorias", "cpf": "00000000191",
        "telefone": "11999990000", "usuario_id": usuario_id, "deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    emp_id = str(uuid.uuid4())
    mongo_db.emprestimos.insert_one({
        "id": emp_id, "cliente_id": cliente_id, "cliente_nome": "TEST_Cliente Melhorias",
        "valor_principal": 1000, "taxa_juros_semanal": 5, "taxa_juros_mensal": None,
        "periodicidade": "semanal", "metodo_calculo": "apenas_juros", "sem_prazo": True,
        "status": status, "usuario_id": usuario_id, "deleted": False,
        "data_inicio": (datetime.now(timezone.utc) - timedelta(days=dias_inicio)).isoformat(),
        "dia_vencimento": None, "valor_total_juros": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "observacoes": "TEST_melhorias",
    })
    parcelas = []
    for i, dias in enumerate(vencimentos, start=1):
        pid = str(uuid.uuid4())
        mongo_db.parcelas.insert_one({
            "id": pid, "emprestimo_id": emp_id, "numero_parcela": i,
            "data_vencimento": (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat(),
            "valor_principal": 0, "valor_juros": 50, "valor_total": 50, "valor_pago": 0,
            "valor_multa": 0, "valor_juros_mora": 0, "saldo_devedor": 1000,
            "total_parcelas": None, "status": "atrasado", "usuario_id": usuario_id,
            "deleted": False, "created_at": datetime.now(timezone.utc).isoformat(),
        })
        parcelas.append(pid)
    return cliente_id, emp_id, parcelas


def _limpar(mongo_db, cliente_id, emp_id):
    mongo_db.parcelas.delete_many({"emprestimo_id": emp_id})
    mongo_db.pagamentos.delete_many({"emprestimo_id": emp_id})
    mongo_db.notificacoes.delete_many({"emprestimo_id": emp_id})
    mongo_db.emprestimos.delete_many({"id": emp_id})
    mongo_db.clientes.delete_many({"id": cliente_id})


class TestAlertaInadimplencia:
    def test_notificacao_criada_e_nao_recriada(self, mongo_db, usuario_id):
        cliente_id, emp_id, _ = _criar_emprestimo_sintetico(mongo_db, usuario_id, "ativo", [45])
        try:
            _run_job("jobs.inadimplencia_job")
            emp = mongo_db.emprestimos.find_one({"id": emp_id}, {"_id": 0, "status": 1})
            assert emp["status"] == "inadimplente", f"status não virou inadimplente: {emp}"

            notifs = list(mongo_db.notificacoes.find({"emprestimo_id": emp_id}, {"_id": 0}))
            assert len(notifs) == 1, f"esperava 1 notificação, obteve {len(notifs)}"
            n = notifs[0]
            assert n["tipo"] == "atraso", n
            assert n.get("prioridade") == "alta", n
            assert n.get("link") == f"/emprestimos/{emp_id}", n
            assert n.get("usuario_id") == usuario_id
            assert "TEST_Cliente Melhorias" in (n.get("mensagem") or "")

            # 2a execução: já inadimplente -> não deve recriar
            _run_job("jobs.inadimplencia_job")
            notifs2 = list(mongo_db.notificacoes.find({"emprestimo_id": emp_id}))
            assert len(notifs2) == 1, f"notificação duplicada: {len(notifs2)}"
        finally:
            _limpar(mongo_db, cliente_id, emp_id)

    def test_notificacao_visivel_na_api(self, auth, mongo_db, usuario_id):
        cliente_id, emp_id, _ = _criar_emprestimo_sintetico(mongo_db, usuario_id, "ativo", [60])
        try:
            _run_job("jobs.inadimplencia_job")
            r = auth.get(f"{BASE_URL}/api/notificacoes", timeout=120)
            assert r.status_code == 200, r.text[:300]
            payload = r.json()
            lista = payload if isinstance(payload, list) else payload.get("notificacoes", [])
            achou = [n for n in lista if n.get("emprestimo_id") == emp_id]
            assert achou, "notificação de inadimplência não retornada pela API /api/notificacoes"
            assert achou[0]["tipo"] == "atraso"
        finally:
            _limpar(mongo_db, cliente_id, emp_id)


class TestReversaoAutomatica:
    def test_volta_para_ativo_somente_quando_zera_atrasadas(self, auth, mongo_db, usuario_id):
        # REGRA UNIFICADA (30 dias): parcelas #1 (-45d) e #2 (-38d) — ambas 30+.
        # Pagar a #1 mantém inadimplente (a #2 segue 38d vencida); pagar a #2 reverte.
        cliente_id, emp_id, parcelas = _criar_emprestimo_sintetico(
            mongo_db, usuario_id, "inadimplente", [45, 38], dias_inicio=45
        )
        try:
            # paga a 1a parcela atrasada -> ainda deve ficar inadimplente
            r1 = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": parcelas[0], "valor_pago": 50, "metodo_pagamento": "pix",
                "observacoes": "TEST_reversao 1"
            }, timeout=120)
            assert r1.status_code == 200, r1.text[:400]
            p1 = mongo_db.parcelas.find_one({"id": parcelas[0]}, {"_id": 0, "status": 1})
            assert p1["status"] == "pago", p1
            emp = mongo_db.emprestimos.find_one({"id": emp_id}, {"_id": 0, "status": 1})
            assert emp["status"] == "inadimplente", f"reverteu cedo demais: {emp}"

            # paga a 2a (última atrasada) -> deve voltar para ativo
            r2 = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": parcelas[1], "valor_pago": 50, "metodo_pagamento": "pix",
                "observacoes": "TEST_reversao 2"
            }, timeout=120)
            assert r2.status_code == 200, r2.text[:400]
            emp = mongo_db.emprestimos.find_one({"id": emp_id}, {"_id": 0, "status": 1})
            assert emp["status"] == "ativo", f"não reverteu para ativo: {emp}"

            # e deve ter gerado a próxima parcela de juros (serviço compartilhado)
            nova = mongo_db.parcelas.find_one(
                {"emprestimo_id": emp_id, "deleted": {"$ne": True}}, {"_id": 0},
                sort=[("numero_parcela", -1)]
            )
            assert nova["numero_parcela"] == 3, f"próxima parcela não gerada: {nova}"
            assert abs(nova["valor_juros"] - 50.0) < 0.01, nova
            # #3 vence em data_inicio+21d (-24d) -> atrasado, mas < 30 dias
            assert nova["status"] in ("pendente", "atrasado"), nova

            # detalhe do empréstimo pela API reflete 'ativo'
            det = auth.get(f"{BASE_URL}/api/emprestimos/{emp_id}", timeout=120)
            assert det.status_code == 200, det.text[:300]
            assert det.json()["status"] == "ativo"
        finally:
            _limpar(mongo_db, cliente_id, emp_id)

    def test_pagamento_parcial_nao_reverte(self, auth, mongo_db, usuario_id):
        # regra unificada: parcela 40d vencida, pagamento parcial mantém inadimplente
        cliente_id, emp_id, parcelas = _criar_emprestimo_sintetico(
            mongo_db, usuario_id, "inadimplente", [40], dias_inicio=40
        )
        try:
            r = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": parcelas[0], "valor_pago": 10, "metodo_pagamento": "dinheiro",
                "observacoes": "TEST_parcial"
            }, timeout=120)
            assert r.status_code == 200, r.text[:400]
            p = mongo_db.parcelas.find_one({"id": parcelas[0]}, {"_id": 0, "status": 1, "valor_pago": 1})
            assert p["status"] == "parcial", p
            emp = mongo_db.emprestimos.find_one({"id": emp_id}, {"_id": 0, "status": 1})
            assert emp["status"] == "inadimplente", f"reverteu com pagamento parcial: {emp}"
        finally:
            _limpar(mongo_db, cliente_id, emp_id)

    def test_pagamento_de_metade_nao_deve_marcar_pago(self, auth, mongo_db, usuario_id):
        """Bug suspeito: recálculo de status usa saldo restante, então pagar exatamente
        50% do valor total marca a parcela como 'pago'."""
        cliente_id, emp_id, parcelas = _criar_emprestimo_sintetico(
            mongo_db, usuario_id, "inadimplente", [10], dias_inicio=15
        )
        try:
            r = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": parcelas[0], "valor_pago": 25, "metodo_pagamento": "pix",
                "observacoes": "TEST_metade"
            }, timeout=120)
            assert r.status_code == 200, r.text[:400]
            p = mongo_db.parcelas.find_one({"id": parcelas[0]}, {"_id": 0, "status": 1, "valor_pago": 1})
            assert p["status"] == "parcial", f"pagou 25 de 50 e ficou {p}"
        finally:
            _limpar(mongo_db, cliente_id, emp_id)


# ------------------------------------------ Re-validação dos 2 fixes (iteration_23)
class TestFixesPagamento:
    def test_metade_depois_restante_vira_pago(self, auth, mongo_db, usuario_id):
        """FIX1: 25 de 50 -> 'parcial'; +25 -> 'pago' e gera próxima parcela."""
        cliente_id, emp_id, parcelas = _criar_emprestimo_sintetico(
            mongo_db, usuario_id, "ativo", [6], dias_inicio=10
        )
        try:
            r1 = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": parcelas[0], "valor_pago": 25, "metodo_pagamento": "pix",
                "observacoes": "TEST_fix1 a"}, timeout=120)
            assert r1.status_code == 200, r1.text[:400]
            p = mongo_db.parcelas.find_one({"id": parcelas[0]}, {"_id": 0})
            assert p["status"] == "parcial", p
            assert abs(p["valor_pago"] - 25) < 0.01, p
            assert p.get("data_pagamento") in (None, ""), f"data_pagamento setada em parcial: {p.get('data_pagamento')}"
            # não deve gerar parcela nova ainda
            assert mongo_db.parcelas.count_documents({"emprestimo_id": emp_id}) == 1

            r2 = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": parcelas[0], "valor_pago": 25, "metodo_pagamento": "pix",
                "observacoes": "TEST_fix1 b"}, timeout=120)
            assert r2.status_code == 200, r2.text[:400]
            p2 = mongo_db.parcelas.find_one({"id": parcelas[0]}, {"_id": 0})
            assert p2["status"] == "pago", p2
            assert abs(p2["valor_pago"] - 50) < 0.01, p2
            assert p2.get("data_pagamento"), "data_pagamento não registrada ao quitar"

            nova = mongo_db.parcelas.find_one(
                {"emprestimo_id": emp_id, "deleted": {"$ne": True}}, {"_id": 0},
                sort=[("numero_parcela", -1)])
            assert nova["numero_parcela"] == 2, f"próxima parcela não gerada: {nova}"
            assert abs(nova["valor_juros"] - 50.0) < 0.01, nova
        finally:
            _limpar(mongo_db, cliente_id, emp_id)

    def test_multa_e_mora_contam_no_total_devido(self, auth, mongo_db, usuario_id):
        """FIX1: com multa+mora, pagar valor_total não deve marcar 'pago'."""
        cliente_id, emp_id, parcelas = _criar_emprestimo_sintetico(
            mongo_db, usuario_id, "ativo", [8], dias_inicio=12
        )
        try:
            mongo_db.parcelas.update_one({"id": parcelas[0]},
                                         {"$set": {"valor_multa": 5, "valor_juros_mora": 3}})
            r = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": parcelas[0], "valor_pago": 50, "metodo_pagamento": "pix",
                "observacoes": "TEST_fix1 multa"}, timeout=120)
            assert r.status_code == 200, r.text[:400]
            p = mongo_db.parcelas.find_one({"id": parcelas[0]}, {"_id": 0, "status": 1})
            assert p["status"] == "parcial", f"total devido é 58, pagou 50 e ficou {p}"

            r2 = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": parcelas[0], "valor_pago": 8, "metodo_pagamento": "pix",
                "observacoes": "TEST_fix1 multa b"}, timeout=120)
            assert r2.status_code == 200, r2.text[:400]
            p2 = mongo_db.parcelas.find_one({"id": parcelas[0]}, {"_id": 0, "status": 1})
            assert p2["status"] == "pago", p2
        finally:
            _limpar(mongo_db, cliente_id, emp_id)

    def test_parcial_depois_quitacao_reverte_para_ativo(self, auth, mongo_db, usuario_id):
        """FIX2: parcial mantém inadimplente; ao quitar a vencida (40d) volta a 'ativo'.
        dias_inicio=35 => próxima parcela (#2) vence a -28d (atrasada, mas < 30d)."""
        cliente_id, emp_id, parcelas = _criar_emprestimo_sintetico(
            mongo_db, usuario_id, "inadimplente", [40], dias_inicio=35
        )
        try:
            r1 = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": parcelas[0], "valor_pago": 10, "metodo_pagamento": "dinheiro",
                "observacoes": "TEST_fix2 a"}, timeout=120)
            assert r1.status_code == 200, r1.text[:400]
            assert mongo_db.parcelas.find_one({"id": parcelas[0]})["status"] == "parcial"
            assert mongo_db.emprestimos.find_one({"id": emp_id})["status"] == "inadimplente"

            r2 = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": parcelas[0], "valor_pago": 40, "metodo_pagamento": "dinheiro",
                "observacoes": "TEST_fix2 b"}, timeout=120)
            assert r2.status_code == 200, r2.text[:400]
            assert mongo_db.parcelas.find_one({"id": parcelas[0]})["status"] == "pago"
            emp = mongo_db.emprestimos.find_one({"id": emp_id}, {"_id": 0, "status": 1})
            assert emp["status"] == "ativo", f"não reverteu após quitar a vencida: {emp}"

            nova = mongo_db.parcelas.find_one(
                {"emprestimo_id": emp_id, "deleted": {"$ne": True}}, {"_id": 0},
                sort=[("numero_parcela", -1)])
            assert nova["numero_parcela"] == 2 and nova["status"] in ("pendente", "atrasado"), nova
            det = auth.get(f"{BASE_URL}/api/emprestimos/{emp_id}", timeout=120)
            assert det.status_code == 200 and det.json()["status"] == "ativo"
        finally:
            _limpar(mongo_db, cliente_id, emp_id)

    def test_quitar_uma_vencida_com_outra_vencida_mantem_inadimplente(self, auth, mongo_db, usuario_id):
        """FIX2 + regra 30d: quitar 1 de 2 vencidas 30+ não deve reverter."""
        cliente_id, emp_id, parcelas = _criar_emprestimo_sintetico(
            mongo_db, usuario_id, "inadimplente", [45, 38], dias_inicio=45
        )
        try:
            r = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": parcelas[0], "valor_pago": 50, "metodo_pagamento": "pix",
                "observacoes": "TEST_fix2 c"}, timeout=120)
            assert r.status_code == 200, r.text[:400]
            emp = mongo_db.emprestimos.find_one({"id": emp_id}, {"_id": 0, "status": 1})
            assert emp["status"] == "inadimplente", f"reverteu com outra vencida em aberto: {emp}"
        finally:
            _limpar(mongo_db, cliente_id, emp_id)

    def test_pagamento_acima_do_devido_marca_pago(self, auth, mongo_db, usuario_id):
        """Excesso de pagamento continua marcando 'pago' (não vira 'parcial')."""
        cliente_id, emp_id, parcelas = _criar_emprestimo_sintetico(
            mongo_db, usuario_id, "ativo", [4], dias_inicio=8
        )
        try:
            r = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": parcelas[0], "valor_pago": 70, "metodo_pagamento": "pix",
                "observacoes": "TEST_excesso"}, timeout=120)
            assert r.status_code == 200, r.text[:400]
            p = mongo_db.parcelas.find_one({"id": parcelas[0]}, {"_id": 0, "status": 1})
            assert p["status"] == "pago", p
        finally:
            _limpar(mongo_db, cliente_id, emp_id)
