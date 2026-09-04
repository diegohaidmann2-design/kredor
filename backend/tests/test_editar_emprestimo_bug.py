"""
Testa correção do bug em PUT /api/emprestimos/{id}:
- Editar SÓ status em empréstimo com parcelas pagas => 200 (era 400 falsamente)
- Editar valor financeiro (valor_principal) em empréstimo com parcelas pagas => 400
- Editar status em empréstimo SEM parcelas pagas não regenera parcelas
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://instant-launch-44.preview.emergentagent.com").rstrip("/")
EMPRESTIMO_COM_PAGAS = "f08409ea-5480-4f7c-ab28-96044e475684"
ADMIN_EMAIL = "diego.haidmann@gmail.com"
ADMIN_SENHA = "Admin@2026"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "senha": ADMIN_SENHA})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def emp_original(auth):
    r = requests.get(f"{BASE_URL}/api/emprestimos/{EMPRESTIMO_COM_PAGAS}", headers=auth)
    assert r.status_code == 200, r.text
    return r.json()


def test_editar_apenas_status_com_parcelas_pagas_deve_passar(auth, emp_original):
    """Bug principal: só alterar status quando há parcelas pagas deve retornar 200."""
    payload = {"status": "ativo"}
    r = requests.put(f"{BASE_URL}/api/emprestimos/{EMPRESTIMO_COM_PAGAS}", headers=auth, json=payload)
    assert r.status_code == 200, f"Esperado 200, veio {r.status_code}: {r.text}"
    assert r.json()["status"] == "ativo"
    # Restaurar status
    requests.put(f"{BASE_URL}/api/emprestimos/{EMPRESTIMO_COM_PAGAS}", headers=auth,
                 json={"status": emp_original.get("status", "inadimplente")})


def test_editar_valor_financeiro_com_parcelas_pagas_deve_bloquear(auth, emp_original):
    """Guarda mantida: alterar valor_principal com parcelas pagas => 400."""
    novo_valor = float(emp_original["valor_principal"]) + 100
    r = requests.put(
        f"{BASE_URL}/api/emprestimos/{EMPRESTIMO_COM_PAGAS}", headers=auth,
        json={"valor_principal": novo_valor},
    )
    assert r.status_code == 400, f"Esperado 400, veio {r.status_code}: {r.text}"
    assert "financeiros" in r.text.lower() or "parcelas" in r.text.lower()


def test_editar_data_inicio_igual_nao_deve_disparar_recalculo(auth, emp_original):
    """Bug RCA: mandar data_inicio como ISO string do frontend (mesmo dia) não deve marcar alterou_financeiro."""
    data_iso = emp_original["data_inicio"]
    # Simular payload do frontend: date + T12:00:00 ISO
    from datetime import datetime
    try:
        d = datetime.fromisoformat(str(data_iso).replace("Z", "+00:00"))
        payload_data = d.replace(hour=12, minute=0, second=0, microsecond=0).isoformat()
    except Exception:
        payload_data = data_iso
    r = requests.put(f"{BASE_URL}/api/emprestimos/{EMPRESTIMO_COM_PAGAS}", headers=auth,
                     json={"status": "inadimplente", "data_inicio": payload_data})
    assert r.status_code == 200, f"Esperado 200 (mesma data), veio {r.status_code}: {r.text}"


def test_editar_status_sem_parcelas_pagas_nao_regenera_parcelas(auth):
    """Regressão: empréstimo sem parcelas pagas, alterar só status não deve apagar/regerar parcelas."""
    # Buscar um empréstimo ATIVO sem parcelas pagas
    r = requests.get(f"{BASE_URL}/api/emprestimos?limit=100", headers=auth)
    assert r.status_code == 200
    data = r.json()
    emps = data.get("items", data) if isinstance(data, dict) else data
    alvo = None
    for e in emps:
        if e.get("status") == "quitado":
            continue
        if e["id"] == EMPRESTIMO_COM_PAGAS:
            continue
        pr = requests.get(f"{BASE_URL}/api/emprestimos/{e['id']}/parcelas", headers=auth)
        if pr.status_code != 200:
            continue
        parcelas = pr.json()
        pagas = [p for p in parcelas if p.get("status") == "pago"]
        if not pagas and parcelas:
            alvo = (e, parcelas)
            break
    if not alvo:
        pytest.skip("Nenhum empréstimo sem parcelas pagas disponível para regressão")
    emp, parcelas_antes = alvo
    ids_antes = sorted([p["id"] for p in parcelas_antes])
    status_orig = emp.get("status", "ativo")
    novo_status = "inadimplente" if status_orig == "ativo" else "ativo"
    r = requests.put(f"{BASE_URL}/api/emprestimos/{emp['id']}", headers=auth, json={"status": novo_status})
    assert r.status_code == 200, r.text
    pr = requests.get(f"{BASE_URL}/api/emprestimos/{emp['id']}/parcelas", headers=auth)
    ids_depois = sorted([p["id"] for p in pr.json()])
    # Restaurar status
    requests.put(f"{BASE_URL}/api/emprestimos/{emp['id']}", headers=auth, json={"status": status_orig})
    assert ids_antes == ids_depois, "Parcelas foram regeneradas indevidamente!"
