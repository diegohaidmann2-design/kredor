"""Tests for POST /api/emprestimos/simular - modo diario + regression mensal/semanal"""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": "diego.haidmann@gmail.com", "senha": "Admin@2026"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_simular_diario_juros_simples(headers):
    payload = {
        "valor_principal": 1000,
        "metodo_calculo": "juros_simples",
        "periodicidade": "diario",
        "taxa_juros_diaria": 1,
        "prazo_dias": 30,
    }
    r = requests.post(f"{API}/emprestimos/simular", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["valor_total_com_juros"] == pytest.approx(1300, abs=0.5)
    assert data["valor_total_juros"] == pytest.approx(300, abs=0.5)
    assert len(data["parcelas"]) == 30
    # Datas dia-a-dia consecutivas
    from datetime import datetime
    d1 = datetime.fromisoformat(data["parcelas"][0]["data_vencimento"])
    d2 = datetime.fromisoformat(data["parcelas"][1]["data_vencimento"])
    assert (d2 - d1).days == 1
    d_last = datetime.fromisoformat(data["parcelas"][-1]["data_vencimento"])
    assert (d_last - d1).days == 29


def test_simular_diario_sem_taxa_retorna_422(headers):
    payload = {
        "valor_principal": 1000,
        "metodo_calculo": "juros_simples",
        "periodicidade": "diario",
        "prazo_dias": 30,
    }
    r = requests.post(f"{API}/emprestimos/simular", json=payload, headers=headers)
    assert r.status_code == 422, r.text


def test_simular_diario_sem_prazo_retorna_422(headers):
    payload = {
        "valor_principal": 1000,
        "metodo_calculo": "juros_simples",
        "periodicidade": "diario",
        "taxa_juros_diaria": 1,
    }
    r = requests.post(f"{API}/emprestimos/simular", json=payload, headers=headers)
    assert r.status_code == 422, r.text


def test_simular_mensal_regressao(headers):
    payload = {
        "valor_principal": 1000,
        "metodo_calculo": "juros_simples",
        "periodicidade": "mensal",
        "taxa_juros_mensal": 5,
        "prazo_meses": 6,
    }
    r = requests.post(f"{API}/emprestimos/simular", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["parcelas"]) == 6
    assert data["valor_total_juros"] == pytest.approx(300, abs=1)


def test_simular_semanal_regressao(headers):
    payload = {
        "valor_principal": 1000,
        "metodo_calculo": "juros_simples",
        "periodicidade": "semanal",
        "taxa_juros_semanal": 2,
        "prazo_semanas": 4,
    }
    r = requests.post(f"{API}/emprestimos/simular", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["parcelas"]) == 4
    from datetime import datetime
    d1 = datetime.fromisoformat(data["parcelas"][0]["data_vencimento"])
    d2 = datetime.fromisoformat(data["parcelas"][1]["data_vencimento"])
    assert (d2 - d1).days == 7
