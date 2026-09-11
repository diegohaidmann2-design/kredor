"""
Serviço compartilhado de geração de parcelas de empréstimos ABERTOS (sem_prazo).

Centraliza a lógica de criar UMA parcela de juros para empréstimos abertos,
usada tanto pelo job diário (jobs/emprestimos_abertos_job.py) quanto pelo
fluxo de pagamento (routes/pagamentos.py). Evita divergências que já causaram
bug de geração parada (status filtrado incorretamente em dois lugares).
"""
from datetime import datetime, timezone
from typing import Optional

from config import db
from utils.dinheiro import arredondar_centavos
from models.emprestimo import Parcela
from services.calculos import calcular_data_vencimento

# Empréstimos nesses status continuam gerando parcelas de juros.
# 'quitado'/'cancelado' param.
STATUS_GERA_PARCELA = ("ativo", "inadimplente")


def calcular_juros_periodo(emprestimo: dict) -> tuple[float, str]:
    """Retorna (juros_do_periodo, periodicidade) para um empréstimo aberto."""
    periodicidade = emprestimo.get("periodicidade", "mensal")
    if periodicidade == "semanal":
        taxa = emprestimo.get("taxa_juros_semanal", 0) or 0
    else:
        taxa = emprestimo.get("taxa_juros_mensal", 0) or 0
    juros = arredondar_centavos((emprestimo.get("valor_principal_centavos", 0) or 0) * (taxa / 100))
    return juros, periodicidade


async def inserir_parcela_juros_aberto(emprestimo: dict, numero_parcela: int, session=None) -> dict:
    """
    Cria e insere UMA parcela de juros para um empréstimo aberto (sem_prazo).

    Protegido contra race condition pelo índice único parcial
    (emprestimo_id, numero_parcela) com deleted != True.

    Retorna dict com:
      inserida (bool), data_vencimento (datetime), status (str),
      valor_juros_centavos (int, centavos), numero_parcela (int)
    """
    juros_periodo, periodicidade = calcular_juros_periodo(emprestimo)
    data_inicio = datetime.fromisoformat(emprestimo["data_inicio"])
    hoje = datetime.now(timezone.utc)

    data_vencimento = calcular_data_vencimento(
        data_inicio,
        numero_parcela,
        emprestimo.get("dia_vencimento"),
        periodicidade,
    )

    status_parcela = "atrasado" if data_vencimento < hoje else "pendente"

    nova_parcela = Parcela(
        emprestimo_id=emprestimo["id"],
        numero_parcela=numero_parcela,
        data_vencimento=data_vencimento,
        valor_principal_centavos=0,
        valor_juros_centavos=juros_periodo,
        valor_total_centavos=juros_periodo,
        saldo_devedor_centavos=emprestimo.get("valor_principal_centavos") or 0,
        total_parcelas=None,
    )

    parcela_doc = nova_parcela.model_dump()
    parcela_doc["status"] = status_parcela
    parcela_doc["data_vencimento"] = parcela_doc["data_vencimento"].isoformat()
    parcela_doc["created_at"] = parcela_doc["created_at"].isoformat()
    parcela_doc["usuario_id"] = emprestimo["usuario_id"]
    parcela_doc["deleted"] = False  # match do índice único parcial

    inserida = False
    try:
        await db.parcelas.insert_one(parcela_doc, session=session)
        inserida = True
    except Exception as dup_err:
        if "duplicate key" in str(dup_err).lower() or "E11000" in str(dup_err):
            inserida = False  # outra execução venceu a corrida
        else:
            raise

    return {
        "inserida": inserida,
        "data_vencimento": data_vencimento,
        "status": status_parcela,
        "valor_juros_centavos": juros_periodo,
        "numero_parcela": numero_parcela,
    }


STATUS_PARCELA_QUITADA = ("pago", "paga")


def saldo_devedor_parcela(parcela: dict) -> int:
    """Quanto ainda falta pagar na parcela: total + multa + juros de mora - já pago."""
    devido = (
        (parcela.get("valor_total_centavos") or 0)
        + (parcela.get("valor_multa_centavos") or 0)
        + (parcela.get("valor_juros_mora_centavos") or 0)
    )
    return max(devido - (parcela.get("valor_pago_centavos") or 0), 0)


def saldo_devedor_emprestimo(emprestimo: dict, parcelas: list) -> int:
    """Saldo devedor total do empréstimo, a partir das suas parcelas.

    Em empréstimo aberto (sem_prazo) as parcelas são só de juros e o capital só volta por
    amortização, então o capital atual entra somado ao juros em aberto.
    """
    if emprestimo.get("status") in ("quitado", "cancelado"):
        return 0
    em_aberto = sum(
        saldo_devedor_parcela(p) for p in parcelas
        if not p.get("deleted") and p.get("status") not in STATUS_PARCELA_QUITADA
    )
    if emprestimo.get("sem_prazo"):
        em_aberto += emprestimo.get("valor_principal_centavos") or 0
    return em_aberto


def imputar_pagamento_parcela(parcela: dict, valor_pago: Optional[int] = None) -> dict[str, int]:
    """Divide o que foi pago na parcela entre juros, capital e encargos, nessa ordem.

    Código Civil, art. 354: havendo capital e juros, o pagamento imputa-se primeiro nos juros e
    depois no capital. Multa e juros de mora ficam por último porque o sistema os recalcula todo
    dia enquanto a parcela está em atraso: se viessem antes, um pagamento antigo passaria a
    "devolver menos capital" a cada dia. O que passar de juros + capital é encargo.
    Sem valor_pago, divide o total já pago na parcela.
    """
    pago = (parcela.get("valor_pago_centavos") or 0) if valor_pago is None else valor_pago
    juros = min(pago, parcela.get("valor_juros_centavos") or 0)
    capital = min(pago - juros, parcela.get("valor_principal_centavos") or 0)
    return {"juros": juros, "capital": capital, "encargos": pago - juros - capital}


def juros_por_pagamento(parcela: dict, valores_pagos: list[int]) -> list[int]:
    """Parte de juros de cada pagamento da parcela, na ordem em que foram feitos.

    Os pagamentos cobrem a parcela em sequência, juros primeiro (art. 354): o primeiro leva os
    juros e os seguintes, o capital. Serve para lançar os juros no mês em que o dinheiro entrou.
    """
    juros_restante = parcela.get("valor_juros_centavos") or 0
    partes = []
    for valor in valores_pagos:
        parte = min(max(valor, 0), juros_restante)
        partes.append(parte)
        juros_restante -= parte
    return partes


def capital_em_aberto_emprestimo(emprestimo: dict, parcelas: list) -> int:
    """Capital emprestado que ainda não voltou para o credor.

    Com prazo: soma, parcela a parcela, do capital ainda não pago. Parcela quitada não tem mais nada
    a receber, e parcela excluída deixa de ser cobrada — as duas saem da conta.
    Aberto (sem_prazo): as parcelas são só de juros e o capital volta por amortização, que já reduz
    valor_principal_centavos. Sem parcelas (dado incompleto), vale o capital do empréstimo.
    """
    if emprestimo.get("status") in ("quitado", "cancelado"):
        return 0
    ativas = [p for p in parcelas if not p.get("deleted")]
    if emprestimo.get("sem_prazo") or not ativas:
        capital_pago = sum(imputar_pagamento_parcela(p)["capital"] for p in ativas)
        return max((emprestimo.get("valor_principal_centavos") or 0) - capital_pago, 0)
    return sum(
        max((p.get("valor_principal_centavos") or 0) - imputar_pagamento_parcela(p)["capital"], 0)
        for p in ativas
        if p.get("status") not in STATUS_PARCELA_QUITADA
    )
