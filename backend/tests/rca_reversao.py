"""RCA: por que a reversão inadimplente->ativo não ocorreu no cenário anterior.

Hipótese: a parcela nova gerada pelo serviço compartilhado nasce 'atrasado'
(vencimento retroativo), bloqueando a reversão que checa status == 'atrasado'.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import requests
from dotenv import dotenv_values
from pymongo import MongoClient

fe = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or fe["REACT_APP_BACKEND_URL"]).rstrip("/")
be = dotenv_values("/app/backend/.env")
db = MongoClient(be["MONGO_URL"])[be["DB_NAME"]]

s = requests.Session()
r = s.post(f"{BASE_URL}/api/auth/login", json={"email": "diego.haidmann@gmail.com", "senha": "Admin@2026"}, timeout=60)
s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
usuario_id = db.usuarios.find_one({"email": "diego.haidmann@gmail.com"})["id"]

cliente_id, emp_id = str(uuid.uuid4()), str(uuid.uuid4())
db.clientes.insert_one({"id": cliente_id, "nome": "TEST_RCA", "usuario_id": usuario_id, "deleted": False})
db.emprestimos.insert_one({
    "id": emp_id, "cliente_id": cliente_id, "cliente_nome": "TEST_RCA", "valor_principal_centavos": 1000,
    "taxa_juros_semanal": 5, "taxa_juros_mensal": None, "periodicidade": "semanal",
    "metodo_calculo": "apenas_juros", "sem_prazo": True, "status": "inadimplente",
    "usuario_id": usuario_id, "deleted": False,
    "data_inicio": (datetime.now(timezone.utc) - timedelta(days=20)).isoformat(),
    "dia_vencimento": None, "created_at": datetime.now(timezone.utc).isoformat(),
})
pids = []
for i, dias in enumerate([13, 6], start=1):
    pid = str(uuid.uuid4())
    db.parcelas.insert_one({
        "id": pid, "emprestimo_id": emp_id, "numero_parcela": i,
        "data_vencimento": (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat(),
        "valor_principal_centavos": 0, "valor_juros_centavos": 50, "valor_total_centavos": 50, "valor_pago_centavos": 0,
        "valor_multa_centavos": 0, "valor_juros_mora_centavos": 0, "status": "atrasado",
        "usuario_id": usuario_id, "deleted": False, "total_parcelas": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    pids.append(pid)

try:
    for pid in pids:
        resp = s.post(f"{BASE_URL}/api/pagamentos", json={
            "parcela_id": pid, "valor_pago_centavos": 50, "metodo_pagamento": "pix", "observacoes": "TEST_RCA"
        }, timeout=120)
        print("pagamento", resp.status_code)
        print("  status emprestimo:", db.emprestimos.find_one({"id": emp_id})["status"])
    print("--- parcelas ---")
    for p in db.parcelas.find({"emprestimo_id": emp_id}, {"_id": 0}).sort("numero_parcela", 1):
        print(p["numero_parcela"], p["status"], p["data_vencimento"], p["valor_total_centavos"], p["valor_pago_centavos"])
    print("STATUS FINAL:", db.emprestimos.find_one({"id": emp_id})["status"])
finally:
    db.parcelas.delete_many({"emprestimo_id": emp_id})
    db.pagamentos.delete_many({"emprestimo_id": emp_id})
    db.notificacoes.delete_many({"emprestimo_id": emp_id})
    db.emprestimos.delete_many({"id": emp_id})
    db.clientes.delete_many({"id": cliente_id})
    print("cleanup ok")
