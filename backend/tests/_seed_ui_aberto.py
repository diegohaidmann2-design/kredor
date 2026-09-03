"""Seed/limpeza de empréstimo aberto sintético para o teste de UI do painel.
Uso: python _seed_ui_aberto.py seed|clean
"""
import sys
import uuid
from datetime import datetime, timedelta, timezone

from dotenv import dotenv_values
from pymongo import MongoClient

env = dotenv_values("/app/backend/.env")
db = MongoClient(env["MONGO_URL"])[env["DB_NAME"]]
MARK = "TEST_UI_PAINEL"
EMAIL = "diego.haidmann@gmail.com"


def seed():
    usuario_id = db.usuarios.find_one({"email": EMAIL}, {"_id": 0, "id": 1})["id"]
    cliente_id = str(uuid.uuid4())
    db.clientes.insert_one({
        "id": cliente_id, "nome": "TEST_UI Painel Cliente", "cpf": "00000000191",
        "telefone": "11999990000", "usuario_id": usuario_id, "deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(), "observacoes": MARK,
    })
    emp_id = str(uuid.uuid4())
    db.emprestimos.insert_one({
        "id": emp_id, "cliente_id": cliente_id, "cliente_nome": "TEST_UI Painel Cliente",
        "valor_principal": 1000, "taxa_juros_semanal": 5, "taxa_juros_mensal": None,
        "periodicidade": "semanal", "metodo_calculo": "apenas_juros", "sem_prazo": True,
        "status": "ativo", "usuario_id": usuario_id, "deleted": False,
        "data_inicio": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
        "dia_vencimento": None, "valor_total_juros": 0,
        "created_at": datetime.now(timezone.utc).isoformat(), "observacoes": MARK,
    })
    pid = str(uuid.uuid4())
    db.parcelas.insert_one({
        "id": pid, "emprestimo_id": emp_id, "numero_parcela": 1,
        "data_vencimento": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
        "valor_principal": 0, "valor_juros": 50, "valor_total": 50, "valor_pago": 0,
        "valor_multa": 0, "valor_juros_mora": 0, "saldo_devedor": 1000,
        "total_parcelas": None, "status": "atrasado", "usuario_id": usuario_id,
        "deleted": False, "created_at": datetime.now(timezone.utc).isoformat(),
    })
    print(f"EMP_ID={emp_id}")
    print(f"CLI_ID={cliente_id}")


def clean():
    emps = list(db.emprestimos.find({"observacoes": MARK}, {"_id": 0, "id": 1, "cliente_id": 1}))
    for e in emps:
        db.parcelas.delete_many({"emprestimo_id": e["id"]})
        db.pagamentos.delete_many({"emprestimo_id": e["id"]})
        db.notificacoes.delete_many({"emprestimo_id": e["id"]})
        db.emprestimos.delete_many({"id": e["id"]})
        db.clientes.delete_many({"id": e["cliente_id"]})
    print(f"limpos={len(emps)}")


if __name__ == "__main__":
    (seed if sys.argv[1] == "seed" else clean)()
