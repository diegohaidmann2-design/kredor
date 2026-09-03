"""
Testes do fix: geração de parcelas para empréstimos ABERTOS (sem_prazo) que
estão com status 'inadimplente'.

Cobre:
 - jobs/emprestimos_abertos_job.py -> job_gerar_parcelas_emprestimos_abertos
   (query agora usa status {$in: ['ativo','inadimplente']})
 - routes/pagamentos.py -> registrar_pagamento gera próxima parcela para
   empréstimo aberto 'ativo' OU 'inadimplente'
 - Estado do empréstimo real do cliente Rodrigo (id 01068c2e-...)
"""
import asyncio
import os
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, "/app/backend")

BACKEND_ENV = dotenv_values("/app/backend/.env")
FRONTEND_ENV = dotenv_values("/app/frontend/.env")

BASE_URL = (
    os.environ.get("REACT_APP_BACKEND_URL") or FRONTEND_ENV.get("REACT_APP_BACKEND_URL")
)
if not BASE_URL:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = BASE_URL.rstrip("/")

MONGO_URL = BACKEND_ENV.get("MONGO_URL")
DB_NAME = BACKEND_ENV.get("DB_NAME")
if not MONGO_URL or not DB_NAME:
    raise RuntimeError("MONGO_URL/DB_NAME missing in /app/backend/.env")

RODRIGO_EMPRESTIMO_ID = "01068c2e-d9ef-4a6a-a63a-077ad6d95f54"
ADMIN_USER_ID = "fabf3ca4-0d42-4f32-a583-ad346916a27a"
TEST_PREFIX = "TESTJOB-"


# ---------------------------------------------------------------- fixtures
@pytest.fixture(scope="session")
def credentials():
    path = Path("/app/memory/test_credentials.md")
    if not path.exists():
        pytest.skip("missing /app/memory/test_credentials.md")
    content = path.read_text(encoding="utf-8")
    email = re.search(r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?Email(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    senha = re.search(r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?Senha(?:\*\*)?\s*:\s*`?([^`\s]+)", content)
    if not email or not senha:
        pytest.skip("credentials not parseable")
    return {"email": email.group(1), "senha": senha.group(1)}


@pytest.fixture(scope="session")
def api(credentials):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json=credentials, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"login failed {r.status_code}: {r.text[:300]}")
    token = r.json().get("access_token")
    assert token, f"no access_token in login response: {r.json()}"
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.get_event_loop_policy()


def run_async(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def get_db():
    client = AsyncIOMotorClient(MONGO_URL)
    return client, client[DB_NAME]


async def _seed_loan(db, status, weeks_back=5, first_parcela_status="pago"):
    """Cria empréstimo aberto semanal apenas_juros + parcela #1."""
    emp_id = TEST_PREFIX + str(uuid.uuid4())
    data_inicio = datetime.now(timezone.utc) - timedelta(weeks=weeks_back)
    emp = {
        "id": emp_id,
        "usuario_id": ADMIN_USER_ID,
        "cliente_id": None,
        "cliente_nome": "TEST_Cliente Aberto",
        "valor_principal": 2000.0,
        "taxa_juros_semanal": 5.0,
        "taxa_juros_mensal": 0.0,
        "periodicidade": "semanal",
        "metodo_calculo": "apenas_juros",
        "sem_prazo": True,
        "status": status,
        "deleted": False,
        "data_inicio": data_inicio.isoformat(),
        "dia_vencimento": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.emprestimos.insert_one(emp)
    p = {
        "id": TEST_PREFIX + str(uuid.uuid4()),
        "emprestimo_id": emp_id,
        "usuario_id": ADMIN_USER_ID,
        "numero_parcela": 1,
        "data_vencimento": (data_inicio + timedelta(weeks=1)).isoformat(),
        "valor_principal": 0.0,
        "valor_juros": 100.0,
        "valor_total": 100.0,
        "valor_pago": 100.0 if first_parcela_status == "pago" else 0.0,
        "valor_multa": 0.0,
        "valor_juros_mora": 0.0,
        "saldo_devedor": 2000.0,
        "status": first_parcela_status,
        "total_parcelas": None,
        "deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.parcelas.insert_one(p)
    return emp_id, data_inicio


async def _cleanup(db):
    await db.parcelas.delete_many({"emprestimo_id": {"$regex": f"^{TEST_PREFIX}"}})
    await db.emprestimos.delete_many({"id": {"$regex": f"^{TEST_PREFIX}"}})
    await db.pagamentos.delete_many({"emprestimo_id": {"$regex": f"^{TEST_PREFIX}"}})


# ---------------------------------------------------------------- health/auth
class TestHealthAndAuth:
    def test_backend_reachable(self):
        r = requests.get(f"{BASE_URL}/api/", timeout=60)
        assert r.status_code in (200, 404), f"unexpected {r.status_code}: {r.text[:200]}"

    def test_login(self, api):
        r = api.get(f"{BASE_URL}/api/auth/me", timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.json().get("perfil") == "admin"


# ---------------------------------------------------------------- Rodrigo loan
class TestRodrigoEmprestimo:
    """Empréstimo real reportado no bug"""

    def test_status_inadimplente_and_open(self, api):
        r = api.get(f"{BASE_URL}/api/emprestimos/{RODRIGO_EMPRESTIMO_ID}", timeout=60)
        assert r.status_code == 200, r.text[:300]
        emp = r.json()
        assert emp["sem_prazo"] is True
        assert emp["periodicidade"] == "semanal"
        assert emp["metodo_calculo"] == "apenas_juros"
        assert emp["status"] == "inadimplente", f"status={emp['status']}"
        assert emp["valor_principal"] == 2000.0

    def test_parcelas_continuas_sem_gaps_e_parcela_futura(self, api):
        r = api.get(
            f"{BASE_URL}/api/emprestimos/{RODRIGO_EMPRESTIMO_ID}/parcelas", timeout=60
        )
        assert r.status_code == 200, r.text[:300]
        parcelas = [p for p in r.json() if not p.get("deleted")]
        assert parcelas, "nenhuma parcela retornada"
        numeros = sorted(p["numero_parcela"] for p in parcelas)
        # sem duplicatas ativas
        assert len(numeros) == len(set(numeros)), f"numeros duplicados: {numeros}"
        # sem gaps
        assert numeros == list(range(numeros[0], numeros[-1] + 1)), f"gaps: {numeros}"
        assert numeros[-1] >= 24, f"ultima parcela {numeros[-1]} < 24"
        # juros semanal = 2000 * 5% = 100
        for p in parcelas:
            if p["numero_parcela"] >= 16:
                assert round(p["valor_total"], 2) == 100.0, p

        hoje = datetime.now(timezone.utc)
        futuras_pendentes = [
            p
            for p in parcelas
            if p["status"] == "pendente"
            and datetime.fromisoformat(str(p["data_vencimento"]).replace("Z", "+00:00")) > hoje
        ]
        assert len(futuras_pendentes) >= 1, "nenhuma parcela futura pendente"


# ---------------------------------------------------------------- job
class TestJobGeracaoParcelas:
    def test_job_gera_para_ativo_e_inadimplente_nao_para_quitado_cancelado(self):
        async def scenario():
            client, db = get_db()
            try:
                await _cleanup(db)
                ativo, di_a = await _seed_loan(db, "ativo")
                inad, di_i = await _seed_loan(db, "inadimplente")
                quit_, _ = await _seed_loan(db, "quitado")
                canc, _ = await _seed_loan(db, "cancelado")

                from jobs.emprestimos_abertos_job import job_gerar_parcelas_emprestimos_abertos

                await job_gerar_parcelas_emprestimos_abertos()

                res = {}
                for eid in (ativo, inad, quit_, canc):
                    ps = await db.parcelas.find(
                        {"emprestimo_id": eid, "deleted": {"$ne": True}}, {"_id": 0}
                    ).sort("numero_parcela", 1).to_list(200)
                    res[eid] = ps

                # segunda execução -> idempotente
                await job_gerar_parcelas_emprestimos_abertos()
                res2 = {}
                for eid in (ativo, inad, quit_, canc):
                    res2[eid] = await db.parcelas.count_documents(
                        {"emprestimo_id": eid, "deleted": {"$ne": True}}
                    )
                return (ativo, inad, quit_, canc), res, res2
            finally:
                await _cleanup(db)
                client.close()

        (ativo, inad, quit_, canc), res, res2 = run_async(scenario())
        hoje = datetime.now(timezone.utc)

        for label, eid in (("ativo", ativo), ("inadimplente", inad)):
            ps = res[eid]
            nums = [p["numero_parcela"] for p in ps]
            assert nums == list(range(1, len(nums) + 1)), f"{label}: gaps {nums}"
            assert len(nums) >= 6, f"{label}: só {len(nums)} parcelas geradas ({nums})"
            # valor juros semanal correto
            for p in ps[1:]:
                assert round(p["valor_total"], 2) == 100.0, f"{label}: {p}"
                assert round(p["valor_juros"], 2) == 100.0, f"{label}: {p}"
                assert p["valor_principal"] == 0.0
                assert p["saldo_devedor"] == 2000.0
            # exatamente 1 parcela futura pendente
            futuras = [
                p
                for p in ps
                if p["status"] == "pendente"
                and datetime.fromisoformat(p["data_vencimento"]) > hoje
            ]
            assert len(futuras) == 1, f"{label}: futuras pendentes={len(futuras)}"
            # as passadas geradas ficam atrasadas
            passadas = [
                p for p in ps[1:] if datetime.fromisoformat(p["data_vencimento"]) <= hoje
            ]
            assert all(p["status"] == "atrasado" for p in passadas), f"{label}: {passadas}"

        for label, eid in (("quitado", quit_), ("cancelado", canc)):
            assert len(res[eid]) == 1, f"{label}: gerou parcelas indevidamente {res[eid]}"

        # idempotência
        assert res2[ativo] == len(res[ativo]), "job duplicou parcelas (ativo)"
        assert res2[inad] == len(res[inad]), "job duplicou parcelas (inadimplente)"
        assert res2[quit_] == 1 and res2[canc] == 1

    def test_job_nao_duplica_parcelas_do_emprestimo_rodrigo(self):
        async def scenario():
            client, db = get_db()
            try:
                q = {"emprestimo_id": RODRIGO_EMPRESTIMO_ID, "deleted": {"$ne": True}}
                antes = await db.parcelas.count_documents(q)
                from jobs.emprestimos_abertos_job import job_gerar_parcelas_emprestimos_abertos

                await job_gerar_parcelas_emprestimos_abertos()
                depois = await db.parcelas.count_documents(q)
                nums = await db.parcelas.distinct("numero_parcela", q)
                return antes, depois, sorted(nums)
            finally:
                client.close()

        antes, depois, nums = run_async(scenario())
        assert depois == antes, f"job gerou parcela extra (antes={antes}, depois={depois})"
        assert nums == list(range(nums[0], nums[-1] + 1)), f"gaps: {nums}"


# ---------------------------------------------------------------- payment flow
class TestPagamentoGeraProximaParcela:
    def test_pagar_ultima_parcela_de_emprestimo_inadimplente_gera_proxima(self, api):
        async def setup():
            client, db = get_db()
            try:
                await _cleanup(db)
                emp_id = TEST_PREFIX + str(uuid.uuid4())
                data_inicio = datetime.now(timezone.utc) - timedelta(weeks=4)
                await db.emprestimos.insert_one({
                    "id": emp_id,
                    "usuario_id": ADMIN_USER_ID,
                    "cliente_id": None,
                    "cliente_nome": "TEST_Cliente Pagto",
                    "valor_principal": 2000.0,
                    "taxa_juros_semanal": 5.0,
                    "taxa_juros_mensal": 0.0,
                    "periodicidade": "semanal",
                    "metodo_calculo": "apenas_juros",
                    "sem_prazo": True,
                    "status": "inadimplente",
                    "deleted": False,
                    "data_inicio": data_inicio.isoformat(),
                    "dia_vencimento": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                parcela_ids = {}
                for n, st in ((1, "pago"), (2, "pago"), (3, "atrasado")):
                    pid = TEST_PREFIX + str(uuid.uuid4())
                    parcela_ids[n] = pid
                    await db.parcelas.insert_one({
                        "id": pid,
                        "emprestimo_id": emp_id,
                        "usuario_id": ADMIN_USER_ID,
                        "numero_parcela": n,
                        "data_vencimento": (data_inicio + timedelta(weeks=n)).isoformat(),
                        "valor_principal": 0.0,
                        "valor_juros": 100.0,
                        "valor_total": 100.0,
                        "valor_pago": 100.0 if st == "pago" else 0.0,
                        "valor_multa": 0.0,
                        "valor_juros_mora": 0.0,
                        "saldo_devedor": 2000.0,
                        "status": st,
                        "total_parcelas": None,
                        "deleted": False,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
                return emp_id, parcela_ids[3]
            finally:
                client.close()

        async def verify(emp_id):
            client, db = get_db()
            try:
                ps = await db.parcelas.find(
                    {"emprestimo_id": emp_id, "deleted": {"$ne": True}}, {"_id": 0}
                ).sort("numero_parcela", 1).to_list(50)
                emp = await db.emprestimos.find_one({"id": emp_id}, {"_id": 0})
                return ps, emp
            finally:
                client.close()

        async def cleanup():
            client, db = get_db()
            try:
                await _cleanup(db)
            finally:
                client.close()

        emp_id, parcela_id = run_async(setup())
        try:
            r = api.post(
                f"{BASE_URL}/api/pagamentos",
                json={
                    "parcela_id": parcela_id,
                    "valor_pago": 100.0,
                    "metodo_pagamento": "pix",
                    "observacoes": "TEST_pagamento",
                },
                timeout=60,
            )
            assert r.status_code == 200, f"pagamento falhou {r.status_code}: {r.text[:400]}"

            ps, emp = run_async(verify(emp_id))
            nums = [p["numero_parcela"] for p in ps]
            assert nums == [1, 2, 3, 4], f"nova parcela não gerada: {nums}"
            nova = ps[-1]
            assert round(nova["valor_total"], 2) == 100.0, nova
            assert round(nova["valor_juros"], 2) == 100.0, nova
            assert nova["status"] in ("pendente", "atrasado"), nova
            assert nova["saldo_devedor"] == 2000.0
            paga = next(p for p in ps if p["numero_parcela"] == 3)
            assert paga["status"] == "pago", paga
            assert emp["status"] != "quitado", "empréstimo aberto não deve ser quitado"
        finally:
            run_async(cleanup())

    def test_pagar_com_outra_parcela_pendente_nao_gera_nova(self, api):
        """Regra: só gera nova quando não restam pendentes."""
        async def setup():
            client, db = get_db()
            try:
                await _cleanup(db)
                emp_id = TEST_PREFIX + str(uuid.uuid4())
                data_inicio = datetime.now(timezone.utc) - timedelta(weeks=4)
                await db.emprestimos.insert_one({
                    "id": emp_id,
                    "usuario_id": ADMIN_USER_ID,
                    "cliente_id": None,
                    "cliente_nome": "TEST_Cliente Pagto2",
                    "valor_principal": 2000.0,
                    "taxa_juros_semanal": 5.0,
                    "taxa_juros_mensal": 0.0,
                    "periodicidade": "semanal",
                    "metodo_calculo": "apenas_juros",
                    "sem_prazo": True,
                    "status": "inadimplente",
                    "deleted": False,
                    "data_inicio": data_inicio.isoformat(),
                    "dia_vencimento": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })
                ids = {}
                for n, st in ((1, "atrasado"), (2, "pendente")):
                    pid = TEST_PREFIX + str(uuid.uuid4())
                    ids[n] = pid
                    await db.parcelas.insert_one({
                        "id": pid,
                        "emprestimo_id": emp_id,
                        "usuario_id": ADMIN_USER_ID,
                        "numero_parcela": n,
                        "data_vencimento": (data_inicio + timedelta(weeks=n * 6)).isoformat(),
                        "valor_principal": 0.0,
                        "valor_juros": 100.0,
                        "valor_total": 100.0,
                        "valor_pago": 0.0,
                        "valor_multa": 0.0,
                        "valor_juros_mora": 0.0,
                        "saldo_devedor": 2000.0,
                        "status": st,
                        "total_parcelas": None,
                        "deleted": False,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })
                return emp_id, ids[1]
            finally:
                client.close()

        async def count(emp_id):
            client, db = get_db()
            try:
                return await db.parcelas.count_documents(
                    {"emprestimo_id": emp_id, "deleted": {"$ne": True}}
                )
            finally:
                client.close()

        async def cleanup():
            client, db = get_db()
            try:
                await _cleanup(db)
            finally:
                client.close()

        emp_id, parcela_id = run_async(setup())
        try:
            r = api.post(
                f"{BASE_URL}/api/pagamentos",
                json={
                    "parcela_id": parcela_id,
                    "valor_pago": 100.0,
                    "metodo_pagamento": "pix",
                },
                timeout=60,
            )
            assert r.status_code == 200, f"{r.status_code}: {r.text[:300]}"
            assert run_async(count(emp_id)) == 2, "gerou parcela extra havendo pendente"
        finally:
            run_async(cleanup())
