"""
Corrige empréstimos marcados como 'quitado' que ainda possuem parcelas em aberto
(estado inconsistente causado pela versão antiga do endpoint /quitar, que marcava
o empréstimo como quitado e gerava uma parcela final SEM dar baixa nela).

Estratégia (apenas para empréstimos SEM pagamentos reais registrados):
  - O empréstimo nunca foi realmente pago -> reverter status para 'ativo'.
  - A parcela final gerada pela quitação antiga (valor_principal > 0 e não paga)
    é cancelada (soft-delete), pois não é mais necessária.

Empréstimos quitados COM pagamentos registrados são apenas REPORTADOS para
revisão manual (não alterados automaticamente).

Uso:
    python -m scripts.corrigir_quitados_inconsistentes            # dry-run (apenas mostra)
    python -m scripts.corrigir_quitados_inconsistentes --apply    # aplica correções
"""
import asyncio
import sys
from datetime import datetime, timezone

from config import db

ABERTAS = ["pendente", "atrasado", "parcial"]


async def main(apply: bool):
    print("=" * 80)
    print(f"🔍 Verificando empréstimos 'quitado' com parcelas em aberto — {'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 80)

    quitados = await db.emprestimos.find(
        {"status": "quitado", "deleted": {"$ne": True}},
        {"_id": 0, "id": 1, "cliente_id": 1, "valor_principal": 1, "sem_prazo": 1}
    ).to_list(10000)

    corrigidos = 0
    revisao_manual = 0

    for emp in quitados:
        emp_id = emp["id"]
        abertas = await db.parcelas.find(
            {"emprestimo_id": emp_id, "deleted": {"$ne": True}, "status": {"$in": ABERTAS}},
            {"_id": 0, "id": 1, "numero_parcela": 1, "status": 1, "valor_principal": 1,
             "valor_total": 1, "valor_pago": 1}
        ).sort("numero_parcela", 1).to_list(1000)

        if not abertas:
            continue  # consistente

        # Existe algum pagamento real (não amortização) neste empréstimo?
        pagamentos_reais = await db.pagamentos.count_documents({
            "emprestimo_id": emp_id,
            "deleted": {"$ne": True},
            "tipo": {"$ne": "amortizacao"},
            "valor_pago": {"$gt": 0},
        })

        print(f"\n• Empréstimo {emp_id} (cliente {emp.get('cliente_id')}) "
              f"capital={emp.get('valor_principal')} | parcelas_abertas={len(abertas)} | pagamentos_reais={pagamentos_reais}")
        for p in abertas:
            print(f"    parcela #{p['numero_parcela']} status={p['status']} "
                  f"principal={p.get('valor_principal')} total={p.get('valor_total')} pago={p.get('valor_pago')}")

        if pagamentos_reais > 0:
            print("    ⚠️  Possui pagamentos registrados — REVISÃO MANUAL (não alterado).")
            revisao_manual += 1
            continue

        # Sem pagamentos -> nunca foi pago de fato. Reverter para 'ativo'.
        # Cancelar parcela(s) final(is) de quitação geradas pela versão antiga:
        # valor_principal > 0 (carrega o capital) e ainda não paga.
        ids_cancelar = [
            p["id"] for p in abertas
            if float(p.get("valor_principal", 0) or 0) > 0 and float(p.get("valor_pago", 0) or 0) == 0
        ]

        print(f"    → AÇÃO: reverter para 'ativo' e cancelar {len(ids_cancelar)} parcela(s) final(is) de quitação.")

        if apply:
            now = datetime.now(timezone.utc).isoformat()
            if ids_cancelar:
                await db.parcelas.update_many(
                    {"id": {"$in": ids_cancelar}},
                    {"$set": {
                        "deleted": True,
                        "deleted_at": now,
                        "deleted_motivo": "Correção: parcela de quitação indevida (empréstimo nunca foi pago)",
                    }}
                )
            await db.emprestimos.update_one(
                {"id": emp_id},
                {"$set": {"status": "ativo"}}
            )
            print("    ✅ Corrigido.")
        corrigidos += 1

    print("\n" + "=" * 80)
    print(f"Resumo: {corrigidos} empréstimo(s) {'corrigido(s)' if apply else 'a corrigir'} | "
          f"{revisao_manual} para revisão manual")
    if not apply and corrigidos:
        print("Rode novamente com --apply para aplicar.")
    print("=" * 80)


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    asyncio.run(main(apply))
