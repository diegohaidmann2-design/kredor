"""
Teste de regressão do endpoint POST /api/emprestimos/{id}/quitar (empréstimo aberto).

Regra validada:
  - Quitar cobra CAPITAL + JUROS DO PERÍODO ATUAL (1 período).
  - A parcela do período atual vira a parcela final, marcada como PAGA.
  - Parcelas futuras em aberto são CANCELADAS (soft-delete).
  - Empréstimo fica 'quitado' e NÃO sobra nenhuma parcela pendente.
  - Um pagamento de quitação é registrado no histórico.

Executa contra o servidor backend rodando (usa REACT_APP_BACKEND_URL) e cria/limpa
dados sintéticos próprios.

Uso:
    python -m tests.test_quitar_emprestimo_aberto
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta

import httpx

from config import db, DB_NAME
from services.auth import criar_tokens


async def _get_owner_id():
    u = await db.usuarios.find_one(
        {"perfil": {"$in": ["admin", "superadmin"]}, "deleted": {"$ne": True}},
        {"_id": 0, "id": 1}
    )
    assert u, "Nenhum usuário admin encontrado para o teste"
    return u["id"]


async def _backend_url():
    import os
    # frontend/.env tem a URL pública; backend chama via localhost internamente
    return "http://localhost:8001"


async def run():
    print(f"DB em uso: {DB_NAME}")
    owner = await _get_owner_id()
    token, _ = criar_tokens(owner)
    base = await _backend_url()

    cliente_id = str(uuid.uuid4())
    emp_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    capital = 1000.0
    juros = 200.0

    # Setup sintético
    await db.clientes.insert_one({
        "id": cliente_id, "usuario_id": owner, "nome": "TESTE QUITAR AUTO",
        "telefone": "0000", "deleted": False,
        "created_at": now.isoformat(),
    })
    await db.emprestimos.insert_one({
        "id": emp_id, "usuario_id": owner, "cliente_id": cliente_id,
        "valor_principal": capital, "taxa_juros_mensal": 20.0,
        "metodo_calculo": "apenas_juros", "periodicidade": "mensal",
        "sem_prazo": True, "status": "ativo", "deleted": False,
        "dia_vencimento": 1,
        "data_inicio": (now - timedelta(days=30)).isoformat(),
        "created_at": now.isoformat(),
        "valor_total_com_juros": 0.0, "valor_total_juros": 0.0,
    })
    # Parcela atual (pendente) + parcela futura (pendente) que deve ser cancelada
    p1 = {
        "id": str(uuid.uuid4()), "usuario_id": owner, "emprestimo_id": emp_id,
        "numero_parcela": 1, "data_vencimento": now.isoformat(),
        "valor_principal": 0.0, "valor_juros": juros, "valor_total": juros,
        "valor_pago": 0.0, "saldo_devedor": capital, "status": "pendente",
        "deleted": False, "created_at": now.isoformat(), "total_parcelas": None,
    }
    p2 = {
        "id": str(uuid.uuid4()), "usuario_id": owner, "emprestimo_id": emp_id,
        "numero_parcela": 2, "data_vencimento": (now + timedelta(days=30)).isoformat(),
        "valor_principal": 0.0, "valor_juros": juros, "valor_total": juros,
        "valor_pago": 0.0, "saldo_devedor": capital, "status": "pendente",
        "deleted": False, "created_at": now.isoformat(), "total_parcelas": None,
    }
    await db.parcelas.insert_many([p1, p2])

    try:
        async with httpx.AsyncClient(base_url=base, timeout=30) as client:
            r = await client.post(
                f"/api/emprestimos/{emp_id}/quitar",
                headers={"Authorization": f"Bearer {token}"},
            )
            print("quitar status:", r.status_code, r.json())
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["valor_total"] == round(capital + juros, 2), data
            assert data["parcelas_canceladas"] == 1, data

        # Validações no banco
        emp = await db.emprestimos.find_one({"id": emp_id}, {"_id": 0})
        assert emp["status"] == "quitado", emp["status"]

        pendentes = await db.parcelas.count_documents({
            "emprestimo_id": emp_id, "deleted": {"$ne": True},
            "status": {"$in": ["pendente", "atrasado", "parcial"]},
        })
        assert pendentes == 0, f"Ainda há {pendentes} parcela(s) pendente(s)!"

        ativas = await db.parcelas.find(
            {"emprestimo_id": emp_id, "deleted": {"$ne": True}}, {"_id": 0}
        ).to_list(100)
        assert len(ativas) == 1, f"Esperava 1 parcela ativa, achei {len(ativas)}"
        final = ativas[0]
        assert final["status"] == "pago"
        assert final["valor_principal"] == capital
        assert final["valor_total"] == round(capital + juros, 2)
        assert final["valor_pago"] == round(capital + juros, 2)

        pag = await db.pagamentos.find_one(
            {"emprestimo_id": emp_id, "tipo": "quitacao", "deleted": {"$ne": True}}, {"_id": 0}
        )
        assert pag and pag["valor_pago"] == round(capital + juros, 2), pag

        print("✅ TESTE PASSOU: quitação cobra capital+juros, cancela parcela futura, encerra sem pendências.")
    finally:
        # Cleanup
        await db.parcelas.delete_many({"emprestimo_id": emp_id})
        await db.pagamentos.delete_many({"emprestimo_id": emp_id})
        await db.emprestimos.delete_one({"id": emp_id})
        await db.clientes.delete_one({"id": cliente_id})
        print("🧹 Dados sintéticos removidos.")


if __name__ == "__main__":
    asyncio.run(run())
