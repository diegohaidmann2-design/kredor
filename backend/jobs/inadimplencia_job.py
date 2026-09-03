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

# Dias de atraso para considerar inadimplente — fonte única no serviço unificado
from services.inadimplencia_service import DIAS_INADIMPLENCIA

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
        {"_id": 0, "emprestimo_id": 1, "data_vencimento": 1, "valor_total": 1,
         "valor_pago": 1, "valor_multa": 1, "valor_juros_mora": 1}
    ).to_list(200000)

    emp_inadimplentes = set()
    for p in parcelas_abertas:
        venc = _parse_date(p.get("data_vencimento"))
        if not venc:
            continue
        # Fonte única do saldo devido (igual a inadimplencia_service.esta_inadimplente):
        # inclui multa e juros de mora para não divergir do fluxo de pagamento.
        devido = (
            (p.get("valor_total", 0) or 0)
            + (p.get("valor_multa", 0) or 0)
            + (p.get("valor_juros_mora", 0) or 0)
            - (p.get("valor_pago", 0) or 0)
        )
        if devido <= 0.005:
            continue
        dias_atraso = (hoje_inicio - venc).days
        if dias_atraso >= dias:
            emp_inadimplentes.add(p["emprestimo_id"])

    # 2. Empréstimos ativos que devem virar inadimplentes
    marcados = 0
    if emp_inadimplentes:
        # Capturar quais serão NOVAMENTE marcados (estavam 'ativo') para notificar
        novos_inadimplentes_docs = await db.emprestimos.find(
            {
                "id": {"$in": list(emp_inadimplentes)},
                "status": "ativo",
                "deleted": {"$ne": True},
            },
            {"_id": 0, "id": 1, "cliente_id": 1, "usuario_id": 1, "valor_principal": 1}
        ).to_list(100000)

        res_marcar = await db.emprestimos.update_many(
            {
                "id": {"$in": list(emp_inadimplentes)},
                "status": "ativo",
                "deleted": {"$ne": True},
            },
            {"$set": {"status": "inadimplente", "updated_at": hoje_inicio.isoformat()}}
        )
        marcados = res_marcar.modified_count

        # Criar alerta de inadimplência para o dono de cada empréstimo recém-marcado
        if novos_inadimplentes_docs:
            try:
                from services.notificacao_service import criar_notificacao
                for d in novos_inadimplentes_docs:
                    cliente = await db.clientes.find_one(
                        {"id": d.get("cliente_id")}, {"_id": 0, "nome": 1}
                    )
                    nome_cliente = (cliente or {}).get("nome", "Cliente")
                    await criar_notificacao(
                        usuario_id=d.get("usuario_id"),
                        tipo="atraso",
                        titulo="⚠️ Empréstimo inadimplente",
                        mensagem=(
                            f"O empréstimo de {nome_cliente} está com {dias}+ dias de atraso "
                            f"e foi marcado como INADIMPLENTE. Faça a cobrança para não acumular semanas."
                        ),
                        link=f"/emprestimos/{d.get('id')}",
                        prioridade="alta",
                        emprestimo_id=d.get("id"),
                        cliente_id=d.get("cliente_id"),
                        dados_referencia={"dias_atraso_min": dias},
                    )
            except Exception as e:
                print(f"⚠️ Erro ao criar alertas de inadimplência: {e}")

    # 3. Empréstimos inadimplentes que regularizaram -> voltam a ativo
    reverter_docs = await db.emprestimos.find(
        {
            "status": "inadimplente",
            "deleted": {"$ne": True},
            "id": {"$nin": list(emp_inadimplentes)},
        },
        {"_id": 0, "id": 1, "cliente_id": 1, "usuario_id": 1}
    ).to_list(100000)

    res_reverter = await db.emprestimos.update_many(
        {
            "status": "inadimplente",
            "deleted": {"$ne": True},
            "id": {"$nin": list(emp_inadimplentes)},
        },
        {"$set": {"status": "ativo", "updated_at": hoje_inicio.isoformat()}}
    )
    revertidos = res_reverter.modified_count

    # 4. Recalcular score dos clientes afetados (marcados + revertidos)
    try:
        from services.score_service import ScoreService
        afetados = set()
        if emp_inadimplentes:
            marcados_docs = await db.emprestimos.find(
                {"id": {"$in": list(emp_inadimplentes)}, "deleted": {"$ne": True}},
                {"_id": 0, "cliente_id": 1, "usuario_id": 1}
            ).to_list(100000)
            for d in marcados_docs:
                if d.get("cliente_id") and d.get("usuario_id"):
                    afetados.add((d["cliente_id"], d["usuario_id"]))
        for d in reverter_docs:
            if d.get("cliente_id") and d.get("usuario_id"):
                afetados.add((d["cliente_id"], d["usuario_id"]))
        for cliente_id, usuario_id in afetados:
            await ScoreService.atualizar_score_cliente(cliente_id, usuario_id)
    except Exception as e:
        print(f"⚠️ Erro ao recalcular scores na inadimplência: {e}")

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
