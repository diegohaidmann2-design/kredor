"""
Teste de regressão do job de inadimplência (30+ dias de atraso).

Valida:
  - Empréstimo ativo com parcela vencida há 35 dias -> vira 'inadimplente'.
  - Empréstimo ativo com parcela vencida há 10 dias -> permanece 'ativo'.
  - Empréstimo inadimplente que regularizou (parcela paga) -> volta a 'ativo'.

Usa dados sintéticos próprios e limpa ao final.

Uso:
    python -m tests.test_inadimplencia_job
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta

from config import db
from jobs.inadimplencia_job import atualizar_status_inadimplencia

OWNER = "teste-inadimplencia-owner"


async def _criar_emp(status, dias_atraso_parcela, paga=False):
    emp_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    venc = (now - timedelta(days=dias_atraso_parcela)).isoformat()
    await db.emprestimos.insert_one({
        "id": emp_id, "usuario_id": OWNER, "cliente_id": "c1",
        "valor_principal_centavos": 1000.0, "status": status, "deleted": False,
        "created_at": now.isoformat(),
    })
    await db.parcelas.insert_one({
        "id": str(uuid.uuid4()), "usuario_id": OWNER, "emprestimo_id": emp_id,
        "numero_parcela": 1, "data_vencimento": venc,
        "valor_total_centavos": 200.0, "valor_pago_centavos": 200.0 if paga else 0.0,
        "status": "pago" if paga else "atrasado", "deleted": False,
        "created_at": now.isoformat(),
    })
    return emp_id


async def run():
    # Limpa eventual lixo de execuções anteriores
    await db.emprestimos.delete_many({"usuario_id": OWNER})
    await db.parcelas.delete_many({"usuario_id": OWNER})

    emp_35 = await _criar_emp("ativo", 35)              # deve virar inadimplente
    emp_10 = await _criar_emp("ativo", 10)              # deve permanecer ativo
    emp_reg = await _criar_emp("inadimplente", 40, paga=True)  # regularizou -> ativo

    try:
        resumo = await atualizar_status_inadimplencia(dias=30)
        print("resumo:", resumo)

        s35 = (await db.emprestimos.find_one({"id": emp_35}))["status"]
        s10 = (await db.emprestimos.find_one({"id": emp_10}))["status"]
        sreg = (await db.emprestimos.find_one({"id": emp_reg}))["status"]
        print(f"emp_35dias={s35} | emp_10dias={s10} | emp_regularizado={sreg}")

        assert s35 == "inadimplente", f"Esperava inadimplente, veio {s35}"
        assert s10 == "ativo", f"Esperava ativo, veio {s10}"
        assert sreg == "ativo", f"Esperava ativo (regularizado), veio {sreg}"
        print("✅ TESTE PASSOU: 30+ dias vira inadimplente; <30 dias fica ativo; regularizado volta a ativo.")
    finally:
        await db.emprestimos.delete_many({"usuario_id": OWNER})
        await db.parcelas.delete_many({"usuario_id": OWNER})
        print("🧹 Dados sintéticos removidos.")


if __name__ == "__main__":
    asyncio.run(run())
