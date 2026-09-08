"""
Test WhatsApp cobrança de parcela — fix para empréstimo SEM PRAZO
- Verifica que a mensagem contém 'Parcela X/∞ (somente juros)', 'Capital em aberto', sem 'None'
- Verifica regressão para empréstimo COM PRAZO (Parcela X/N sem ∞)
- Verifica ultima_cobranca_em gravado
- Verifica status_envio no retorno
"""
import os
import time
import asyncio
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

ADMIN_EMAIL = "diego.haidmann@gmail.com"
ADMIN_PASS = "GestorTest@2026"

DIEGO_UID = "fabf3ca4-0d42-4f32-a583-ad346916a27a"
PARCELA_SEM_PRAZO = "dd22b8a9-d41b-4714-86d0-4cce391efeaf"   # Andressa, valor_principal 1000
PARCELA_COM_PRAZO = "63ad6b68-bded-4bbc-b774-cbacb943a8d3"   # DIEGO ALEXANDRE, prazo 3, n=2


@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL, "senha": ADMIN_PASS,
        "turnstile_token": "XXXX.DUMMY.TOKEN.XXXX"
    }, timeout=20)
    if r.status_code != 200:
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "senha": ADMIN_PASS
        }, timeout=20)
    assert r.status_code == 200, f"Login falhou: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"sem token na resposta: {data}"
    return tok


def _headers(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _latest_log(parcela_id):
    from pymongo import MongoClient
    c = MongoClient(MONGO_URL)
    db = c[DB_NAME]
    return db.whatsapp_mensagens_log.find_one({"parcela_id": parcela_id}, sort=[("created_at", -1)])


def _get_parcela(parcela_id):
    from pymongo import MongoClient
    c = MongoClient(MONGO_URL)
    db = c[DB_NAME]
    return db.parcelas.find_one({"id": parcela_id})


def test_sem_prazo_message_content(token):
    before = _latest_log(PARCELA_SEM_PRAZO)
    before_ts = before.get("created_at") if before else None

    r = requests.post(
        f"{BASE_URL}/api/whatsapp/enviar-cobranca-parcela/{PARCELA_SEM_PRAZO}?usar_fila=false",
        headers=_headers(token), timeout=45
    )
    print("STATUS", r.status_code, "BODY", r.text[:400])
    assert r.status_code == 200, r.text
    data = r.json()

    # Se anti-spam bloqueou, cai para fila. Ambos devem gravar ultima_cobranca_em e log
    if data.get("success") is False:
        # anti-spam - envia por fila
        r2 = requests.post(
            f"{BASE_URL}/api/whatsapp/enviar-cobranca-parcela/{PARCELA_SEM_PRAZO}?usar_fila=true",
            headers=_headers(token), timeout=45
        )
        print("FALLBACK FILA", r2.status_code, r2.text[:400])
        assert r2.status_code == 200
        # espera processar
        time.sleep(20)
    else:
        assert data.get("modo") == "imediato"
        # status_envio presente
        assert "status_envio" in data, f"status_envio ausente no retorno: {data}"

    # buscar novo log
    time.sleep(3)
    after = _latest_log(PARCELA_SEM_PRAZO)
    assert after is not None, "Sem log de mensagem após envio"
    assert (before_ts is None) or (after.get("created_at") != before_ts), "Nenhum novo log foi criado"

    msg = after.get("mensagem", "")
    print("MSG SEM PRAZO:\n", msg)
    assert "None" not in msg, f"Mensagem contém 'None': {msg}"
    assert "∞" in msg, "Mensagem sem prazo deve conter símbolo ∞"
    assert "Parcela 1/∞" in msg, "Deve conter 'Parcela 1/∞'"
    assert "somente juros" in msg.lower(), "Deve indicar 'somente juros'"
    assert "Capital em aberto" in msg, "Deve exibir 'Capital em aberto'"
    assert "1.000,00" in msg, f"Deve exibir capital formatado 1.000,00 no texto: {msg}"

    # ultima_cobranca_em foi gravado
    p = _get_parcela(PARCELA_SEM_PRAZO)
    assert p.get("ultima_cobranca_em"), "ultima_cobranca_em não gravado"
    print("ultima_cobranca_em:", p.get("ultima_cobranca_em"))


def test_com_prazo_message_regression(token):
    time.sleep(30)  # respeitar anti-spam
    before = _latest_log(PARCELA_COM_PRAZO)
    before_ts = before.get("created_at") if before else None

    r = requests.post(
        f"{BASE_URL}/api/whatsapp/enviar-cobranca-parcela/{PARCELA_COM_PRAZO}?usar_fila=false",
        headers=_headers(token), timeout=45
    )
    print("STATUS", r.status_code, "BODY", r.text[:400])
    assert r.status_code == 200, r.text
    data = r.json()

    if data.get("success") is False:
        r2 = requests.post(
            f"{BASE_URL}/api/whatsapp/enviar-cobranca-parcela/{PARCELA_COM_PRAZO}?usar_fila=true",
            headers=_headers(token), timeout=45
        )
        print("FALLBACK FILA", r2.status_code, r2.text[:400])
        assert r2.status_code == 200
        time.sleep(20)

    time.sleep(3)
    after = _latest_log(PARCELA_COM_PRAZO)
    assert after is not None
    assert (before_ts is None) or (after.get("created_at") != before_ts)
    msg = after.get("mensagem", "")
    print("MSG COM PRAZO:\n", msg)
    assert "None" not in msg
    assert "∞" not in msg, "Mensagem com prazo NÃO deve conter ∞"
    assert "Parcela 2/3" in msg, f"Deve conter 'Parcela 2/3': {msg}"
