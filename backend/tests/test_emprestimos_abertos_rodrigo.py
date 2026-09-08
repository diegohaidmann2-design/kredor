"""
Testes: geração de parcelas de empréstimos abertos + idempotência
Foco: empréstimo do RODRIGO FERREIRA DA LUZ (id 01068c2e-d9ef-4a6a-a63a-077ad6d95f54)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://financial-portal-26.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "diego.haidmann@gmail.com"
ADMIN_SENHA = "Admin@2026"
EMP_ID = "01068c2e-d9ef-4a6a-a63a-077ad6d95f54"
CLIENTE_ID = "7f56aecd-b2db-424f-9c6f-280e796b4e60"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "senha": ADMIN_SENHA}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    tk = data.get("access_token") or data.get("token")
    assert tk, f"No token in response: {data}"
    return tk


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# Feature: detalhe do empréstimo deve retornar parcelas até #24
def test_emprestimo_detalhe_tem_parcela_24(auth_headers):
    r = requests.get(f"{BASE_URL}/api/emprestimos/{EMP_ID}/parcelas", headers=auth_headers, timeout=30)
    assert r.status_code == 200, r.text
    parcelas = r.json()
    assert isinstance(parcelas, list)
    numeros = sorted([p.get("numero_parcela") for p in parcelas if p.get("numero_parcela")])
    assert numeros, f"Sem parcelas retornadas ({len(parcelas)})"
    assert 22 in numeros and 23 in numeros and 24 in numeros, f"Faltando #22/#23/#24. numeros={numeros}"
    p24 = next(p for p in parcelas if p.get("numero_parcela") == 24)
    assert p24["status"] == "pendente", f"Parcela #24 status={p24['status']}"
    assert "2026-09-09" in p24["data_vencimento"], f"venc #24={p24['data_vencimento']}"


# Feature: endpoint /abertos/resumo
def test_abertos_resumo_contem_rodrigo(auth_headers):
    r = requests.get(f"{BASE_URL}/api/emprestimos/abertos/resumo", headers=auth_headers, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    itens = data if isinstance(data, list) else (data.get("itens") or data.get("emprestimos") or data.get("data") or [])
    rodrigo = next((i for i in itens if i.get("id") == EMP_ID or i.get("emprestimo_id") == EMP_ID), None)
    assert rodrigo is not None, f"Emprestimo Rodrigo nao encontrado. keys sample: {itens[:1]}"
    prox = rodrigo.get("proxima_parcela") or rodrigo.get("proximaParcela")
    assert prox is not None, f"proxima_parcela ausente: {rodrigo}"
    # proxima deve estar em aberto (pendente ou atrasado)
    status = prox.get("status")
    assert status in ("pendente", "atrasado"), f"proxima status invalido: {status}"


# Feature: idempotência do job - segunda execução não deve gerar parcelas
def test_job_idempotente():
    import asyncio
    from jobs.emprestimos_abertos_job import job_gerar_parcelas_emprestimos_abertos
    from pymongo import MongoClient
    db = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "gestorcred")]
    before = db.parcelas.count_documents({"emprestimo_id": EMP_ID, "deleted": {"$ne": True}})
    asyncio.run(job_gerar_parcelas_emprestimos_abertos())
    after = db.parcelas.count_documents({"emprestimo_id": EMP_ID, "deleted": {"$ne": True}})
    assert after == before, f"Job nao idempotente: before={before} after={after}"
    assert before == 24, f"Esperava 24 parcelas, tem {before}"


# Regra empréstimo aberto: sempre 1 parcela futura pendente
def test_sempre_uma_parcela_futura_pendente():
    from pymongo import MongoClient
    from datetime import datetime, timezone
    db = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))[os.environ.get("DB_NAME", "gestorcred")]
    hoje = datetime.now(timezone.utc)
    parcelas = list(db.parcelas.find({"emprestimo_id": EMP_ID, "deleted": {"$ne": True}, "status": "pendente"}))
    futuras = []
    for p in parcelas:
        dv = p.get("data_vencimento")
        if isinstance(dv, str):
            dv = datetime.fromisoformat(dv.replace("Z", "+00:00"))
        if dv >= hoje:
            futuras.append(p)
    assert len(futuras) >= 1, f"Nao existe parcela futura pendente. pendentes={len(parcelas)}"
