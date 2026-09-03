"""
Testes das melhorias (iteration_24):
 1. REGRA UNIFICADA de inadimplência (30 dias) — services/inadimplencia_service.py
    usada tanto por jobs/inadimplencia_job.py como por routes/pagamentos.py
 2. COBRANÇA NO PAINEL — GET /api/emprestimos/abertos/resumo com proxima_parcela.parcela_id
    e POST /api/pagamentos usando esse parcela_id
 4. RESUMO NO WHATSAPP — jobs/resumo_whatsapp_job.py

Dados sintéticos TEST_ com limpeza no teardown (não toca dados reais).
"""
import asyncio
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
PYBIN = "/root/.venv/bin/python"


# ------------------------------------------------------------------ fixtures
@pytest.fixture(scope="session")
def mongo_db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="session")
def creds():
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
def auth(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"Login falhou {r.status_code}: {r.text[:300]}")
    token = r.json().get("access_token")
    assert token
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="session")
def usuario_id(mongo_db, creds):
    u = mongo_db.usuarios.find_one({"email": creds["email"]}, {"_id": 0, "id": 1})
    assert u, "usuário admin não encontrado"
    return u["id"]


def _run_job(module: str) -> str:
    proc = subprocess.run([PYBIN, "-m", module], cwd=BACKEND_DIR,
                          capture_output=True, text=True, timeout=280)
    assert proc.returncode == 0, f"job {module} falhou:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
    return proc.stdout


def _criar(mongo_db, usuario_id, status, vencimentos, dias_inicio=45, valor_juros=50):
    cliente_id = str(uuid.uuid4())
    mongo_db.clientes.insert_one({
        "id": cliente_id, "nome": "TEST_Regra Unificada", "cpf": "00000000191",
        "telefone": "11999990000", "usuario_id": usuario_id, "deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    emp_id = str(uuid.uuid4())
    mongo_db.emprestimos.insert_one({
        "id": emp_id, "cliente_id": cliente_id, "cliente_nome": "TEST_Regra Unificada",
        "valor_principal": 1000, "taxa_juros_semanal": 5, "taxa_juros_mensal": None,
        "periodicidade": "semanal", "metodo_calculo": "apenas_juros", "sem_prazo": True,
        "status": status, "usuario_id": usuario_id, "deleted": False,
        "data_inicio": (datetime.now(timezone.utc) - timedelta(days=dias_inicio)).isoformat(),
        "dia_vencimento": None, "valor_total_juros": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "observacoes": "TEST_regra_unificada",
    })
    parcelas = []
    for i, dias in enumerate(vencimentos, start=1):
        pid = str(uuid.uuid4())
        mongo_db.parcelas.insert_one({
            "id": pid, "emprestimo_id": emp_id, "numero_parcela": i,
            "data_vencimento": (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat(),
            "valor_principal": 0, "valor_juros": valor_juros, "valor_total": valor_juros,
            "valor_pago": 0, "valor_multa": 0, "valor_juros_mora": 0, "saldo_devedor": 1000,
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


def _status(mongo_db, emp_id):
    return mongo_db.emprestimos.find_one({"id": emp_id}, {"_id": 0, "status": 1})["status"]


# =============================== 1. REGRA UNIFICADA (30 dias) ================
class TestRegraUnificada:
    def test_fonte_unica_do_limiar(self):
        svc = Path(f"{BACKEND_DIR}/services/inadimplencia_service.py").read_text()
        job = Path(f"{BACKEND_DIR}/jobs/inadimplencia_job.py").read_text()
        pag = Path(f"{BACKEND_DIR}/routes/pagamentos.py").read_text()
        assert "DIAS_INADIMPLENCIA" in svc
        assert "from services.inadimplencia_service import DIAS_INADIMPLENCIA" in job
        assert "recalcular_status_emprestimo" in pag
        # job não deve redefinir o limiar localmente
        assert not re.search(r'^DIAS_INADIMPLENCIA\s*=', job, re.M), "job redefine o limiar"
        sys.path.insert(0, BACKEND_DIR)
        from services.inadimplencia_service import DIAS_INADIMPLENCIA
        assert DIAS_INADIMPLENCIA == 30

    def test_a_pagar_parcela_40d_reverte_para_ativo(self, auth, mongo_db, usuario_id):
        """(a) 40d + 20d vencidas; quitar a de 40d => volta a 'ativo' (restante <30d)."""
        cliente_id, emp_id, parcelas = _criar(
            mongo_db, usuario_id, "inadimplente", [40, 20], dias_inicio=47)
        try:
            r = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": parcelas[0], "valor_pago": 50,
                "metodo_pagamento": "pix", "observacoes": "TEST_ru a"}, timeout=120)
            assert r.status_code == 200, r.text[:400]
            assert mongo_db.parcelas.find_one({"id": parcelas[0]})["status"] == "pago"
            assert _status(mongo_db, emp_id) == "ativo", "não reverteu com a regra de 30 dias"
            det = auth.get(f"{BASE_URL}/api/emprestimos/{emp_id}", timeout=120)
            assert det.status_code == 200 and det.json()["status"] == "ativo"
        finally:
            _limpar(mongo_db, cliente_id, emp_id)

    def test_b_permanece_inadimplente_com_outra_30_mais(self, auth, mongo_db, usuario_id):
        """(b) 45d + 35d; quitar a de 45d => permanece 'inadimplente'."""
        cliente_id, emp_id, parcelas = _criar(
            mongo_db, usuario_id, "inadimplente", [45, 35], dias_inicio=45)
        try:
            r = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": parcelas[0], "valor_pago": 50,
                "metodo_pagamento": "pix", "observacoes": "TEST_ru b"}, timeout=120)
            assert r.status_code == 200, r.text[:400]
            assert _status(mongo_db, emp_id) == "inadimplente"
        finally:
            _limpar(mongo_db, cliente_id, emp_id)

    def test_c_pagamento_parcial_nao_reverte(self, auth, mongo_db, usuario_id):
        """(c) parcial em parcela 40d vencida => segue 'inadimplente'."""
        cliente_id, emp_id, parcelas = _criar(
            mongo_db, usuario_id, "inadimplente", [40], dias_inicio=40)
        try:
            r = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": parcelas[0], "valor_pago": 10,
                "metodo_pagamento": "dinheiro", "observacoes": "TEST_ru c"}, timeout=120)
            assert r.status_code == 200, r.text[:400]
            assert mongo_db.parcelas.find_one({"id": parcelas[0]})["status"] == "parcial"
            assert _status(mongo_db, emp_id) == "inadimplente"
        finally:
            _limpar(mongo_db, cliente_id, emp_id)

    def test_d_job_nao_oscila_apos_pagamento(self, auth, mongo_db, usuario_id):
        """(d) consistência job x pagamento: rodar o job não deve reverter/re-marcar."""
        # caso revertido (a)
        c1, e1, p1 = _criar(mongo_db, usuario_id, "inadimplente", [40, 20], dias_inicio=47)
        # caso mantido inadimplente (b)
        c2, e2, p2 = _criar(mongo_db, usuario_id, "inadimplente", [45, 35], dias_inicio=45)
        try:
            for pid in (p1[0], p2[0]):
                r = auth.post(f"{BASE_URL}/api/pagamentos", json={
                    "parcela_id": pid, "valor_pago": 50,
                    "metodo_pagamento": "pix", "observacoes": "TEST_ru d"}, timeout=120)
                assert r.status_code == 200, r.text[:400]
            s1_pag, s2_pag = _status(mongo_db, e1), _status(mongo_db, e2)
            assert (s1_pag, s2_pag) == ("ativo", "inadimplente"), (s1_pag, s2_pag)

            _run_job("jobs.inadimplencia_job")
            assert _status(mongo_db, e1) == s1_pag, "job oscilou o status revertido"
            assert _status(mongo_db, e2) == s2_pag, "job oscilou o status mantido"

            # 2a execução do job também estável
            _run_job("jobs.inadimplencia_job")
            assert _status(mongo_db, e1) == s1_pag
            assert _status(mongo_db, e2) == s2_pag
        finally:
            _limpar(mongo_db, c1, e1)
            _limpar(mongo_db, c2, e2)

    def test_job_marca_apenas_30_mais(self, mongo_db, usuario_id):
        """Empréstimo ativo com atraso de 20d NÃO deve virar inadimplente."""
        c1, e1, _ = _criar(mongo_db, usuario_id, "ativo", [20], dias_inicio=20)
        c2, e2, _ = _criar(mongo_db, usuario_id, "ativo", [31], dias_inicio=31)
        try:
            _run_job("jobs.inadimplencia_job")
            assert _status(mongo_db, e1) == "ativo", "marcou inadimplente com 20 dias"
            assert _status(mongo_db, e2) == "inadimplente", "não marcou com 31 dias"
        finally:
            _limpar(mongo_db, c1, e1)
            _limpar(mongo_db, c2, e2)

    def test_divergencia_multa_mora_job_vs_pagamento(self, auth, mongo_db, usuario_id):
        """EDGE: parcela 40d com multa/mora — o serviço conta multa+mora no saldo,
        mas o job usa apenas valor_total - valor_pago. Se divergirem, o status oscila."""
        cliente_id, emp_id, parcelas = _criar(
            mongo_db, usuario_id, "inadimplente", [40], dias_inicio=40)
        try:
            mongo_db.parcelas.update_one({"id": parcelas[0]},
                                         {"$set": {"valor_multa": 10, "valor_juros_mora": 5}})
            r = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": parcelas[0], "valor_pago": 50,
                "metodo_pagamento": "pix", "observacoes": "TEST_ru multa"}, timeout=120)
            assert r.status_code == 200, r.text[:400]
            p = mongo_db.parcelas.find_one({"id": parcelas[0]}, {"_id": 0})
            assert p["status"] == "parcial", p  # ainda deve 15 (multa+mora)
            status_pagamento = _status(mongo_db, emp_id)
            _run_job("jobs.inadimplencia_job")
            status_job = _status(mongo_db, emp_id)
            assert status_job == status_pagamento, (
                f"OSCILAÇÃO: pagamento deixou '{status_pagamento}', job mudou p/ '{status_job}' "
                "(job ignora multa/juros_mora no cálculo do saldo devido)"
            )
        finally:
            _limpar(mongo_db, cliente_id, emp_id)


# ============================ 2. COBRANÇA NO PAINEL (API) ====================
class TestCobrancaPainel:
    def test_resumo_expoe_parcela_id_valido(self, auth, mongo_db):
        r = auth.get(f"{BASE_URL}/api/emprestimos/abertos/resumo", timeout=120)
        assert r.status_code == 200, r.text[:300]
        itens = r.json()["itens"]
        assert itens, "sem itens no painel"
        com_proxima = [i for i in itens if i.get("proxima_parcela")]
        assert com_proxima, "nenhum item com proxima_parcela"
        for it in com_proxima[:10]:
            pid = it["proxima_parcela"].get("parcela_id")
            assert pid, f"parcela_id ausente em {it['emprestimo_id']}"
            parcela = mongo_db.parcelas.find_one({"id": pid}, {"_id": 0})
            assert parcela, f"parcela_id inexistente no banco: {pid}"
            assert parcela["emprestimo_id"] == it["emprestimo_id"]
            assert parcela["status"] in ("pendente", "atrasado", "parcial")
            esperado = round(max((parcela.get("valor_total") or 0) - (parcela.get("valor_pago") or 0), 0), 2)
            assert abs(it["proxima_parcela"]["valor"] - esperado) < 0.01

    def test_pagar_pelo_painel_atualiza_totais(self, auth, mongo_db, usuario_id):
        """Fluxo do painel: ler parcela_id do resumo -> POST /api/pagamentos -> totais mudam."""
        cliente_id, emp_id, parcelas = _criar(
            mongo_db, usuario_id, "ativo", [5], dias_inicio=5)
        try:
            data = auth.get(f"{BASE_URL}/api/emprestimos/abertos/resumo", timeout=120).json()
            item = next((i for i in data["itens"] if i["emprestimo_id"] == emp_id), None)
            assert item, "empréstimo sintético não apareceu no painel"
            pid = item["proxima_parcela"]["parcela_id"]
            assert pid == parcelas[0]
            valor = item["proxima_parcela"]["valor"]
            assert abs(valor - 50.0) < 0.01, valor
            juros_recebido_antes = item["juros_recebido"]
            aberto_antes = item["juros_em_aberto"]

            r = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": pid, "valor_pago": valor,
                "metodo_pagamento": "pix"}, timeout=120)
            assert r.status_code == 200, r.text[:400]

            data2 = auth.get(f"{BASE_URL}/api/emprestimos/abertos/resumo", timeout=120).json()
            item2 = next(i for i in data2["itens"] if i["emprestimo_id"] == emp_id)
            assert abs(item2["juros_recebido"] - (juros_recebido_antes + valor)) < 0.01, item2
            assert item2["juros_em_aberto"] <= aberto_antes + 0.01
            # nova parcela de juros gerada e virou a próxima do painel
            assert item2["proxima_parcela"] is not None
            assert item2["proxima_parcela"]["parcela_id"] != pid
        finally:
            _limpar(mongo_db, cliente_id, emp_id)

    def test_pagamento_valor_invalido_rejeitado(self, auth, mongo_db, usuario_id):
        cliente_id, emp_id, parcelas = _criar(
            mongo_db, usuario_id, "ativo", [5], dias_inicio=5)
        try:
            r = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": parcelas[0], "valor_pago": 0,
                "metodo_pagamento": "pix"}, timeout=60)
            assert r.status_code == 422, r.status_code
            r2 = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": "inexistente-000", "valor_pago": 10,
                "metodo_pagamento": "pix"}, timeout=60)
            assert r2.status_code == 404, r2.status_code
        finally:
            _limpar(mongo_db, cliente_id, emp_id)


# ============================ 4. RESUMO NO WHATSAPP ==========================
class TestResumoWhatsapp:
    def test_job_executa_sem_erro(self, mongo_db):
        out = _run_job("jobs.resumo_whatsapp_job")
        assert "conexoes" in out and "enviados" in out, out[-800:]
        reg = mongo_db.jobs_execucoes.find_one({"job": "resumo_semanal_whatsapp"},
                                               sort=[("executado_em", -1)])
        assert reg, "execução do job não registrada em jobs_execucoes"
        for k in ("conexoes", "enviados", "falhas", "sem_numero"):
            assert k in reg["resultado"], reg["resultado"]

    def test_registrado_no_scheduler(self):
        sched = Path(f"{BACKEND_DIR}/scheduler.py").read_text()
        assert "job_resumo_semanal_whatsapp" in sched
        assert "id='resumo_semanal_whatsapp'" in sched
        assert "day_of_week='mon'" in sched and "hour=8" in sched and "minute=30" in sched

    def test_resumo_do_gestor_coerente(self, mongo_db, usuario_id):
        sys.path.insert(0, BACKEND_DIR)
        from jobs.resumo_whatsapp_job import _resumo_do_gestor, _montar_mensagem
        r = asyncio.get_event_loop().run_until_complete(_resumo_do_gestor(usuario_id)) \
            if False else asyncio.run(_resumo_do_gestor(usuario_id))

        esperado_emp = mongo_db.emprestimos.count_documents({
            "usuario_id": usuario_id, "status": {"$in": ["ativo", "inadimplente"]},
            "deleted": {"$ne": True}})
        assert r["emprestimos_ativos"] == esperado_emp, (r, esperado_emp)
        assert r["emprestimos_ativos"] > 0, "gestor sem carteira para validar"

        # FIX iteration_25: quantidades devem ser int (antes a_vencer_qtd vinha float)
        for k in ("emprestimos_ativos", "vencidas_qtd", "a_vencer_qtd"):
            assert isinstance(r[k], int) and not isinstance(r[k], bool), (k, r[k], type(r[k]))
            assert r[k] >= 0, (k, r[k])
        for k in ("vencidas_total", "a_vencer_total", "juros_aberto_total"):
            assert r[k] >= 0, (k, r[k])

        # recálculo independente a partir do banco
        emps = list(mongo_db.emprestimos.find(
            {"usuario_id": usuario_id, "status": {"$in": ["ativo", "inadimplente"]},
             "deleted": {"$ne": True}}, {"_id": 0, "id": 1, "sem_prazo": 1}))
        ids = [e["id"] for e in emps]
        abertos = {e["id"] for e in emps if e.get("sem_prazo")}
        hoje = datetime.now(timezone.utc)
        limite = hoje + timedelta(days=7)
        venc_qtd = venc_tot = av_qtd = av_tot = juros_ab = 0
        for p in mongo_db.parcelas.find(
                {"emprestimo_id": {"$in": ids}, "deleted": {"$ne": True},
                 "status": {"$in": ["pendente", "parcial", "atrasado"]}}, {"_id": 0}):
            saldo = ((p.get("valor_total") or 0) + (p.get("valor_multa") or 0)
                     + (p.get("valor_juros_mora") or 0) - (p.get("valor_pago") or 0))
            if saldo <= 0.005:
                continue
            v = p.get("data_vencimento")
            v = datetime.fromisoformat(str(v).replace("Z", "+00:00")) if v else None
            if v and not v.tzinfo:
                v = v.replace(tzinfo=timezone.utc)
            if p.get("emprestimo_id") in abertos:
                juros_ab += saldo
            if v and v < hoje:
                venc_qtd += 1
                venc_tot += saldo
            elif v and hoje <= v <= limite:
                av_qtd += 1
                av_tot += saldo
        assert r["vencidas_qtd"] == venc_qtd, (r["vencidas_qtd"], venc_qtd)
        assert abs(r["vencidas_total"] - round(venc_tot, 2)) < 0.05
        assert r["a_vencer_qtd"] == av_qtd
        assert abs(r["a_vencer_total"] - round(av_tot, 2)) < 0.05
        assert abs(r["juros_aberto_total"] - round(juros_ab, 2)) < 0.05

        msg = _montar_mensagem("TEST_Gestor", r)
        assert "Resumo semanal" in msg and "TEST_Gestor" in msg
        assert "R$" in msg


# ================= iteration_25: hardening do FIX crítico (multa/mora) =======
class TestFixMultaMoraJobVsServico:
    """Re-validação do fix: jobs/inadimplencia_job usa a MESMA fórmula de saldo
    devido (valor_total + multa + mora - pago, limiar > 0.005) que
    services/inadimplencia_service.esta_inadimplente."""

    def test_job_marca_quando_resta_apenas_multa_mora(self, mongo_db, usuario_id):
        """Empréstimo ATIVO, parcela 40d com valor_total totalmente pago mas
        restando multa+mora => serviço considera inadimplente; o job também deve."""
        sys.path.insert(0, BACKEND_DIR)
        from services.inadimplencia_service import esta_inadimplente, DIAS_INADIMPLENCIA

        cliente_id, emp_id, parcelas = _criar(
            mongo_db, usuario_id, "ativo", [40], dias_inicio=40)
        try:
            mongo_db.parcelas.update_one(
                {"id": parcelas[0]},
                {"$set": {"valor_pago": 50, "valor_multa": 10,
                          "valor_juros_mora": 5, "status": "parcial"}})
            docs = list(mongo_db.parcelas.find({"emprestimo_id": emp_id}, {"_id": 0}))
            hoje = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0)
            assert esta_inadimplente(docs, DIAS_INADIMPLENCIA, hoje) is True

            _run_job("jobs.inadimplencia_job")
            assert _status(mongo_db, emp_id) == "inadimplente", (
                "job NÃO marcou inadimplente com saldo só de multa/mora "
                "=> divergência com esta_inadimplente()")
            # idempotente
            _run_job("jobs.inadimplencia_job")
            assert _status(mongo_db, emp_id) == "inadimplente"
        finally:
            _limpar(mongo_db, cliente_id, emp_id)

    def test_job_reverte_quando_saldo_residual_menor_que_limiar(self, mongo_db, usuario_id):
        """Saldo residual 0.004 (<= 0.005) => não é inadimplente no serviço nem no job."""
        sys.path.insert(0, BACKEND_DIR)
        from services.inadimplencia_service import esta_inadimplente, DIAS_INADIMPLENCIA

        cliente_id, emp_id, parcelas = _criar(
            mongo_db, usuario_id, "inadimplente", [40], dias_inicio=40)
        try:
            mongo_db.parcelas.update_one(
                {"id": parcelas[0]},
                {"$set": {"valor_multa": 10, "valor_juros_mora": 5,
                          "valor_pago": 64.996, "status": "parcial"}})
            docs = list(mongo_db.parcelas.find({"emprestimo_id": emp_id}, {"_id": 0}))
            hoje = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0)
            assert esta_inadimplente(docs, DIAS_INADIMPLENCIA, hoje) is False

            _run_job("jobs.inadimplencia_job")
            assert _status(mongo_db, emp_id) == "ativo"
            _run_job("jobs.inadimplencia_job")
            assert _status(mongo_db, emp_id) == "ativo"
        finally:
            _limpar(mongo_db, cliente_id, emp_id)

    def test_pagamento_e_job_convergem_em_multiplos_ciclos(self, auth, mongo_db, usuario_id):
        """Pagamento -> job -> pagamento -> job: status estável em cenário com multa/mora."""
        cliente_id, emp_id, parcelas = _criar(
            mongo_db, usuario_id, "inadimplente", [40, 35], dias_inicio=45)
        try:
            mongo_db.parcelas.update_one({"id": parcelas[0]},
                                         {"$set": {"valor_multa": 8, "valor_juros_mora": 4}})
            mongo_db.parcelas.update_one({"id": parcelas[1]},
                                         {"$set": {"valor_multa": 6, "valor_juros_mora": 3}})
            # 1o pagamento parcial na parcela 1
            r = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": parcelas[0], "valor_pago": 50,
                "metodo_pagamento": "pix", "observacoes": "TEST_ru ciclo1"}, timeout=120)
            assert r.status_code == 200, r.text[:400]
            s_pag1 = _status(mongo_db, emp_id)
            _run_job("jobs.inadimplencia_job")
            assert _status(mongo_db, emp_id) == s_pag1, f"oscilou ciclo1 ({s_pag1})"

            # quita o resíduo da parcela 1 (multa+mora = 12)
            r = auth.post(f"{BASE_URL}/api/pagamentos", json={
                "parcela_id": parcelas[0], "valor_pago": 12,
                "metodo_pagamento": "pix", "observacoes": "TEST_ru ciclo2"}, timeout=120)
            assert r.status_code == 200, r.text[:400]
            p = mongo_db.parcelas.find_one({"id": parcelas[0]}, {"_id": 0})
            assert p["status"] == "pago", p["status"]
            s_pag2 = _status(mongo_db, emp_id)
            _run_job("jobs.inadimplencia_job")
            assert _status(mongo_db, emp_id) == s_pag2, f"oscilou ciclo2 ({s_pag2})"
            # parcela 2 ainda 35d vencida com saldo => deve seguir inadimplente
            assert s_pag2 == "inadimplente", s_pag2
        finally:
            _limpar(mongo_db, cliente_id, emp_id)
