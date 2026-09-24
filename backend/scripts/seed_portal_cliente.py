"""Seed de um cliente de teste com acesso ao Portal do Cliente (login CPF + código).

Cria: 1 cliente, portal_auth (código 123456), 1 empréstimo ativo e 6 parcelas
(1 paga, próxima a vencer pendente, demais futuras) vinculados ao usuário pro@kredorteste.com.

Uso: cd /app/backend && python scripts/seed_portal_cliente.py
"""
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "gestorcred")

CPF = "11144477735"  # somente dígitos (normalizado)
CODIGO = "123456"
NOME = "Cliente Portal Teste"
EMAIL = "cliente.portal@kredorteste.com"
TELEFONE = "11999998888"


def main():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]

    usuario = db.usuarios.find_one({"email": "pro@kredorteste.com"})
    if not usuario:
        print("ERRO: usuário pro@kredorteste.com não encontrado. Rode seed_usuarios_teste.py antes.")
        return
    usuario_id = usuario["id"]

    # Idempotência: remove cliente de teste anterior e seus dados
    antigo = db.clientes.find_one({"cpf_cnpj": CPF})
    if antigo:
        cid = antigo["id"]
        emps = list(db.emprestimos.find({"cliente_id": cid}, {"id": 1}))
        eids = [e["id"] for e in emps]
        db.parcelas.delete_many({"emprestimo_id": {"$in": eids}})
        db.emprestimos.delete_many({"cliente_id": cid})
        db.portal_auth.delete_many({"cliente_id": cid})
        db.clientes.delete_one({"id": cid})

    now = datetime.now(timezone.utc)
    cliente_id = str(uuid.uuid4())

    db.clientes.insert_one({
        "id": cliente_id,
        "usuario_id": usuario_id,
        "owner_id": usuario_id,
        "nome": NOME,
        "cpf_cnpj": CPF,
        "telefone": TELEFONE,
        "email": EMAIL,
        "status": "ativo",
        "deleted": False,
        "created_at": now,
        "updated_at": now,
    })

    db.portal_auth.insert_one({
        "id": str(uuid.uuid4()),
        "cliente_id": cliente_id,
        "usuario_id": usuario_id,
        "codigo_acesso": CODIGO,
        "tentativas_falhas": 0,
        "bloqueado_ate": None,
        "created_at": now,
    })

    emprestimo_id = str(uuid.uuid4())
    valor_principal = 300000  # R$ 3.000,00
    valor_total = 360000      # R$ 3.600,00 (6x600)
    n_parcelas = 6
    primeiro_venc = now - timedelta(days=10)  # 1ª parcela venceu (paga); 2ª a vencer em ~20 dias

    db.emprestimos.insert_one({
        "id": emprestimo_id,
        "cliente_id": cliente_id,
        "usuario_id": usuario_id,
        "owner_id": usuario_id,
        "valor_principal_centavos": valor_principal,
        "valor_total_centavos": valor_total,
        "numero_parcelas": n_parcelas,
        "taxa_juros": 3.5,
        "tipo": "price",
        "sem_prazo": False,
        "status": "ativo",
        "deleted": False,
        "created_at": now - timedelta(days=35),
        "data_primeiro_vencimento": primeiro_venc.isoformat(),
    })

    valor_parcela = valor_total // n_parcelas  # 60000
    capital_parcela = valor_principal // n_parcelas
    juros_parcela = valor_parcela - capital_parcela

    parcelas = []
    for i in range(1, n_parcelas + 1):
        venc = (primeiro_venc + timedelta(days=30 * (i - 1)))
        if i == 1:
            status = "pago"
            pago = valor_parcela
        elif i == 2:
            status = "pendente"  # próxima a vencer
            pago = 0
        else:
            status = "pendente"
            pago = 0
        parcelas.append({
            "id": str(uuid.uuid4()),
            "emprestimo_id": emprestimo_id,
            "cliente_id": cliente_id,
            "usuario_id": usuario_id,
            "numero_parcela": i,
            "valor_total_centavos": valor_parcela,
            "valor_principal_centavos": capital_parcela,
            "valor_juros_centavos": juros_parcela,
            "valor_multa_centavos": 0,
            "valor_juros_mora_centavos": 0,
            "valor_pago_centavos": pago,
            "perdao_juros_centavos": 0,
            "perdao_capital_centavos": 0,
            "perdao_encargos_centavos": 0,
            "status": status,
            "data_vencimento": venc.isoformat(),
            "deleted": False,
            "created_at": now - timedelta(days=35),
        })
    db.parcelas.insert_many(parcelas)

    print("Cliente do portal criado com sucesso:")
    print(f"  CPF (login):    {CPF}")
    print(f"  Código acesso:  {CODIGO}")
    print(f"  Nome:           {NOME}")
    print(f"  Empréstimo:     R$ {valor_total/100:.2f} em {n_parcelas}x (1 paga, 5 em aberto)")


if __name__ == "__main__":
    main()
