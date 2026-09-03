"""
Serviço unificado de inadimplência.

Fonte ÚNICA da regra de inadimplência (padrão de mercado: 30+ dias de atraso).
Usado tanto pelo job diário (jobs/inadimplencia_job.py) quanto pelo fluxo de
pagamento (routes/pagamentos.py), para o status NUNCA oscilar entre os dois.

Regra:
  - Empréstimo com parcela em aberto e saldo > 0 vencida há DIAS_INADIMPLENCIA+ dias -> "inadimplente"
  - Empréstimo "inadimplente" que deixou de ter parcela 30+ vencida -> volta a "ativo"
  - Empréstimos "quitado"/"cancelado" são ignorados.
"""
import os
from datetime import datetime, timezone

from config import db

# Fonte única do limiar (dias). Também importado pelo job.
DIAS_INADIMPLENCIA = int(os.environ.get("DIAS_INADIMPLENCIA", "30"))

STATUS_ABERTO = ["pendente", "parcial", "atrasado"]
STATUS_AFETAVEIS = ("ativo", "inadimplente")


def parse_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def esta_inadimplente(parcelas: list, dias: int, hoje_inicio: datetime) -> bool:
    """True se houver ao menos 1 parcela em aberto, com saldo, vencida há `dias`+ dias."""
    for p in parcelas:
        if p.get("status") not in STATUS_ABERTO:
            continue
        venc = parse_date(p.get("data_vencimento"))
        if not venc:
            continue
        devido = (
            (p.get("valor_total", 0) or 0)
            + (p.get("valor_multa", 0) or 0)
            + (p.get("valor_juros_mora", 0) or 0)
            - (p.get("valor_pago", 0) or 0)
        )
        if devido <= 0.005:
            continue
        if (hoje_inicio - venc).days >= dias:
            return True
    return False


async def _criar_alerta_inadimplencia(emprestimo: dict, dias: int):
    try:
        from services.notificacao_service import criar_notificacao
        cliente = await db.clientes.find_one(
            {"id": emprestimo.get("cliente_id")}, {"_id": 0, "nome": 1}
        )
        nome_cliente = (cliente or {}).get("nome", "Cliente")
        await criar_notificacao(
            usuario_id=emprestimo.get("usuario_id"),
            tipo="atraso",
            titulo="⚠️ Empréstimo inadimplente",
            mensagem=(
                f"O empréstimo de {nome_cliente} está com {dias}+ dias de atraso "
                f"e foi marcado como INADIMPLENTE. Faça a cobrança para não acumular semanas."
            ),
            link=f"/emprestimos/{emprestimo.get('id')}",
            prioridade="alta",
            emprestimo_id=emprestimo.get("id"),
            cliente_id=emprestimo.get("cliente_id"),
            dados_referencia={"dias_atraso_min": dias},
        )
    except Exception as e:
        print(f"⚠️ Erro ao criar alerta de inadimplência: {e}")


async def recalcular_status_emprestimo(
    emprestimo_id: str,
    context_id: str = None,
    dias: int = DIAS_INADIMPLENCIA,
    criar_alerta: bool = True,
) -> dict:
    """
    Recalcula o status inadimplente/ativo de UM empréstimo, aplicando a regra dos
    30 dias. Só transiciona entre 'ativo' <-> 'inadimplente'.

    Retorna {"status": <status atual/novo>, "transicao": "marcado"|"revertido"|None}
    """
    filtro = {"id": emprestimo_id, "deleted": {"$ne": True}}
    if context_id:
        filtro["usuario_id"] = context_id

    emprestimo = await db.emprestimos.find_one(filtro, {"_id": 0})
    if not emprestimo:
        return {"status": None, "transicao": None}

    status_atual = emprestimo.get("status")
    if status_atual not in STATUS_AFETAVEIS:
        return {"status": status_atual, "transicao": None}

    parcelas = await db.parcelas.find(
        {"emprestimo_id": emprestimo_id, "deleted": {"$ne": True},
         "status": {"$in": STATUS_ABERTO}},
        {"_id": 0, "status": 1, "data_vencimento": 1, "valor_total": 1,
         "valor_pago": 1, "valor_multa": 1, "valor_juros_mora": 1}
    ).to_list(100000)

    hoje_inicio = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    inadimplente = esta_inadimplente(parcelas, dias, hoje_inicio)

    if inadimplente and status_atual == "ativo":
        await db.emprestimos.update_one(
            {"id": emprestimo_id},
            {"$set": {"status": "inadimplente", "updated_at": hoje_inicio.isoformat()}}
        )
        if criar_alerta:
            await _criar_alerta_inadimplencia(emprestimo, dias)
        return {"status": "inadimplente", "transicao": "marcado"}

    if not inadimplente and status_atual == "inadimplente":
        await db.emprestimos.update_one(
            {"id": emprestimo_id},
            {"$set": {"status": "ativo", "updated_at": hoje_inicio.isoformat()}}
        )
        return {"status": "ativo", "transicao": "revertido"}

    return {"status": status_atual, "transicao": None}
