"""
Job de Inadimplência

Regra de negócio (padrão de mercado para empréstimo mensal a juros):
  - Empréstimo com parcela vencida há 30+ dias  -> status "inadimplente"
  - Empréstimo "inadimplente" que regularizou (sem parcela 30+ dias) -> volta a "ativo"

Apenas empréstimos com status "ativo" ou "inadimplente" (não deletados) são afetados.
Empréstimos "quitado"/"cancelado" são ignorados.

Executa diariamente. Também pode ser rodado manualmente:
    python -m jobs.inadimplencia_job
"""
import os
from datetime import datetime, timezone

from config import db

# Dias de atraso para considerar inadimplente (padrão de mercado: 30 dias)
DIAS_INADIMPLENCIA = int(os.environ.get("DIAS_INADIMPLENCIA", "30"))

STATUS_ABERTO = ["pendente", "parcial", "atrasado"]


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


async def atualizar_status_inadimplencia(dias: int = DIAS_INADIMPLENCIA) -> dict:
    """
    Recalcula o status de inadimplência de todos os empréstimos.
    Retorna um resumo com quantos foram marcados/revertidos.
    """
    hoje_inicio = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. Descobrir quais empréstimos têm parcela em aberto com 'dias'+ de atraso
    parcelas_abertas = await db.parcelas.find(
        {"deleted": {"$ne": True}, "status": {"$in": STATUS_ABERTO}},
        {"_id": 0, "emprestimo_id": 1, "data_vencimento": 1, "valor_total": 1, "valor_pago": 1}
    ).to_list(200000)

    emp_inadimplentes = set()
    for p in parcelas_abertas:
        venc = _parse_date(p.get("data_vencimento"))
        if not venc:
            continue
        # Ignorar parcelas sem saldo devido
        devido = (p.get("valor_total", 0) or 0) - (p.get("valor_pago", 0) or 0)
        if devido <= 0:
            continue
        dias_atraso = (hoje_inicio - venc).days
        if dias_atraso >= dias:
            emp_inadimplentes.add(p["emprestimo_id"])

    # 2. Empréstimos ativos que devem virar inadimplentes
    marcados = 0
    if emp_inadimplentes:
        res_marcar = await db.emprestimos.update_many(
            {
                "id": {"$in": list(emp_inadimplentes)},
                "status": "ativo",
                "deleted": {"$ne": True},
            },
            {"$set": {"status": "inadimplente", "updated_at": hoje_inicio.isoformat()}}
        )
        marcados = res_marcar.modified_count

    # 3. Empréstimos inadimplentes que regularizaram -> voltam a ativo
    res_reverter = await db.emprestimos.update_many(
        {
            "status": "inadimplente",
            "deleted": {"$ne": True},
            "id": {"$nin": list(emp_inadimplentes)},
        },
        {"$set": {"status": "ativo", "updated_at": hoje_inicio.isoformat()}}
    )
    revertidos = res_reverter.modified_count

    return {
        "dias_corte": dias,
        "emprestimos_inadimplentes_detectados": len(emp_inadimplentes),
        "marcados_inadimplente": marcados,
        "revertidos_ativo": revertidos,
    }


async def job_inadimplencia():
    """Job agendado: recalcula inadimplência (30+ dias de atraso)."""
    print("=" * 70)
    print(f"⏰ [Job] Recalcular inadimplência ({DIAS_INADIMPLENCIA}+ dias) - {datetime.now(timezone.utc).isoformat()}")
    print("=" * 70)
    try:
        resumo = await atualizar_status_inadimplencia()
        print(f"✅ Inadimplência atualizada: {resumo}")
        return resumo
    except Exception as e:
        print(f"❌ Erro ao atualizar inadimplência: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import asyncio
    print("🧪 Testando job de inadimplência...")
    print(asyncio.run(atualizar_status_inadimplencia()))
