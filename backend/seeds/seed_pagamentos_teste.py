"""
Seed de teste para validar ordenação por vencimento na página /pagamentos.
Cria 4 clientes com cenários distintos: atrasado antigo, atrasado recente,
vence hoje, vence amanhã e vence no futuro.
Uso: python -m seeds.seed_pagamentos_teste
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config import db

EMAIL_USUARIO = "usuario@teste.com"


def parcela_doc(usuario_id, emprestimo_id, numero, venc, valor, status, dias_atraso=0):
    return {
        "id": str(uuid.uuid4()),
        "usuario_id": usuario_id,
        "emprestimo_id": emprestimo_id,
        "numero_parcela": numero,
        "data_vencimento": venc.isoformat(),
        "valor_principal": valor * 0.8,
        "valor_juros": valor * 0.2,
        "valor_total": valor,
        "valor_pago": 0.0,
        "valor_multa": 0.0,
        "valor_juros_mora": 0.0,
        "dias_atraso": dias_atraso,
        "saldo_devedor": 0.0,
        "status": status,
        "data_pagamento": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def main():
    usuario = await db.usuarios.find_one({"email": EMAIL_USUARIO})
    if not usuario:
        print(f"Usuário {EMAIL_USUARIO} não encontrado. Rode seeds.seeder antes.")
        return
    uid = usuario["id"]

    hoje = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)

    cenarios = [
        # (nome, telefone, valor, lista de (offset_dias, status))
        ("Atrasado Antigo", "11999990001", 1000.0, [(-30, "atrasado"), (0, "pendente"), (30, "pendente")]),
        ("Atrasado Recente", "11999990002", 5000.0, [(-2, "atrasado"), (28, "pendente")]),
        ("Vence Hoje", "11999990003", 800.0, [(0, "pendente"), (30, "pendente")]),
        ("Vence Amanha", "11999990004", 9000.0, [(1, "pendente"), (31, "pendente")]),
        ("Vence Futuro", "11999990005", 20000.0, [(20, "pendente"), (50, "pendente")]),
    ]

    # Limpar dados anteriores deste seed
    clientes_antigos = await db.clientes.find({"usuario_id": uid, "observacoes": "SEED_PAGAMENTOS_TESTE"}).to_list(100)
    for c in clientes_antigos:
        emps = await db.emprestimos.find({"cliente_id": c["id"]}).to_list(100)
        for e in emps:
            await db.parcelas.delete_many({"emprestimo_id": e["id"]})
        await db.emprestimos.delete_many({"cliente_id": c["id"]})
        await db.clientes.delete_one({"id": c["id"]})

    for nome, telefone, valor, parcelas in cenarios:
        cliente_id = str(uuid.uuid4())
        await db.clientes.insert_one({
            "id": cliente_id,
            "usuario_id": uid,
            "nome": nome,
            "telefone": telefone,
            "cpf_cnpj": None,
            "status": "ativo",
            "score": 500,
            "observacoes": "SEED_PAGAMENTOS_TESTE",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        emprestimo_id = str(uuid.uuid4())
        await db.emprestimos.insert_one({
            "id": emprestimo_id,
            "usuario_id": uid,
            "cliente_id": cliente_id,
            "valor_principal": valor,
            "taxa_juros_mensal": 10.0,
            "prazo_meses": len(parcelas),
            "metodo_calculo": "juros_simples",
            "periodo_carencia_meses": 0,
            "taxa_multa_atraso": 2.0,
            "taxa_juros_mora_diario": 0.033,
            "periodicidade": "mensal",
            "sem_prazo": False,
            "data_inicio": (hoje - timedelta(days=60)).isoformat(),
            "valor_total_com_juros": valor * 1.2,
            "valor_total_juros": valor * 0.2,
            "status": "ativo",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        docs = []
        for i, (offset, status) in enumerate(parcelas, start=1):
            venc = hoje + timedelta(days=offset)
            dias_atraso = max(0, -offset) if status == "atrasado" else 0
            docs.append(parcela_doc(uid, emprestimo_id, i, venc, valor / len(parcelas), status, dias_atraso))
        await db.parcelas.insert_many(docs)
        print(f"✅ {nome}: {len(parcelas)} parcelas (valor total {valor})")

    print("🎉 Seed de teste de pagamentos concluído!")


if __name__ == "__main__":
    asyncio.run(main())
