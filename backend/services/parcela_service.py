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
    elif periodicidade == "quinzenal":
        taxa = emprestimo.get("taxa_juros_quinzenal", 0) or 0
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


def perdao_da_parcela(parcela: dict) -> dict[str, int]:
    """O que o credor abriu mão de receber nesta parcela, por natureza.

    Quitar com desconto não é dinheiro que entrou: o valor perdoado sai do "a receber" sem
    nunca entrar em "recebido". Por isso ele fica gravado separado do valor pago.
    """
    juros = parcela.get("perdao_juros_centavos") or 0
    capital = parcela.get("perdao_capital_centavos") or 0
    encargos = parcela.get("perdao_encargos_centavos") or 0
    return {"juros": juros, "capital": capital, "encargos": encargos,
            "total": juros + capital + encargos}


def saldo_devedor_parcela(parcela: dict) -> int:
    """Quanto ainda falta pagar na parcela: total + multa + juros de mora - já pago - perdoado."""
    devido = (
        (parcela.get("valor_total_centavos") or 0)
        + (parcela.get("valor_multa_centavos") or 0)
        + (parcela.get("valor_juros_mora_centavos") or 0)
    )
    pago = (parcela.get("valor_pago_centavos") or 0) + perdao_da_parcela(parcela)["total"]
    return max(devido - pago, 0)


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


def juros_da_parcela(parcela: dict) -> int:
    """Juros que a parcela cobra: o total menos o capital, menos o que foi perdoado.

    Na Tabela Price a prestação é arredondada inteira e capital e juros são arredondados cada um,
    então às vezes capital + juros fica 1 centavo abaixo do total cobrado. Esse centavo é juros:
    ignorá-lo faria o "a receber" não bater com o que o cliente paga. Sem total (dado antigo),
    vale o campo de juros.

    Juros perdoados na quitação saem daqui: não são juros a receber nem juros recebidos — o credor
    deixou de cobrá-los. Se ficassem, a imputação (juros primeiro) os lançaria como ganho.
    """
    total = parcela.get("valor_total_centavos")
    capital = parcela.get("valor_principal_centavos") or 0
    if not total or total < capital:
        juros = parcela.get("valor_juros_centavos") or 0
    else:
        juros = total - capital
    return max(juros - (parcela.get("perdao_juros_centavos") or 0), 0)


def capital_cobrado_parcela(parcela: dict) -> int:
    """Capital que a parcela cobra, já sem o que foi perdoado na quitação."""
    capital = parcela.get("valor_principal_centavos") or 0
    return max(capital - (parcela.get("perdao_capital_centavos") or 0), 0)


def encargos_cobrados_parcela(parcela: dict) -> int:
    """Multa + juros de mora que a parcela cobra, já sem o que foi perdoado na quitação."""
    encargos = (parcela.get("valor_multa_centavos") or 0) + (parcela.get("valor_juros_mora_centavos") or 0)
    return max(encargos - (parcela.get("perdao_encargos_centavos") or 0), 0)


def resumo_parcelas(parcelas: list) -> dict[str, int]:
    """Quantas parcelas estão quitadas, quantas seguem em aberto, quanto já foi pago e quanto falta.

    O saldo sai do mesmo cálculo do resto do sistema (total + multa + mora − pago), para o cliente
    ver no portal o mesmo número que o credor vê. Conta as duas grafias de status ("pago"/"paga")
    e ignora parcela excluída.
    """
    ativas = [p for p in parcelas if not p.get("deleted")]
    em_aberto = [p for p in ativas if p.get("status") not in STATUS_PARCELA_QUITADA]
    return {
        "total": len(ativas),
        "quitadas": len(ativas) - len(em_aberto),
        "em_aberto": len(em_aberto),
        "pago_centavos": sum(p.get("valor_pago_centavos") or 0 for p in ativas),
        "saldo_centavos": sum(saldo_devedor_parcela(p) for p in em_aberto),
    }


def imputar_pagamento_parcela(parcela: dict, valor_pago: Optional[int] = None) -> dict[str, int]:
    """Divide o que foi pago na parcela entre juros, capital e encargos, nessa ordem.

    Código Civil, art. 354: havendo capital e juros, o pagamento imputa-se primeiro nos juros e
    depois no capital. Multa e juros de mora ficam por último porque o sistema os recalcula todo
    dia enquanto a parcela está em atraso: se viessem antes, um pagamento antigo passaria a
    "devolver menos capital" a cada dia. O que passar de juros + capital é encargo.
    Sem valor_pago, divide o total já pago na parcela.
    """
    pago = (parcela.get("valor_pago_centavos") or 0) if valor_pago is None else valor_pago
    juros = min(pago, juros_da_parcela(parcela))
    capital = min(pago - juros, capital_cobrado_parcela(parcela))
    return {"juros": juros, "capital": capital, "encargos": pago - juros - capital}


def juros_em_aberto_parcela(parcela: dict) -> int:
    """Juros da parcela que ainda não foram pagos (o perdoado já saiu do que ela cobra)."""
    return max(juros_da_parcela(parcela) - imputar_pagamento_parcela(parcela)["juros"], 0)


def encargos_em_aberto_parcela(parcela: dict) -> int:
    """Multa + juros de mora da parcela ainda não pagos (na imputação eles vêm por último)."""
    return max(encargos_cobrados_parcela(parcela) - imputar_pagamento_parcela(parcela)["encargos"], 0)


def capital_em_aberto_parcela(parcela: dict) -> int:
    """Capital desta parcela que ainda não voltou para o credor."""
    return max(capital_cobrado_parcela(parcela) - imputar_pagamento_parcela(parcela)["capital"], 0)


def distribuir_perdao(parcela: dict, valor: int) -> dict[str, int]:
    """Divide o valor perdoado na quitação entre encargos, juros e capital, nessa ordem.

    Ordem inversa da imputação do pagamento (art. 354): quem perdoa abre mão primeiro da multa e
    da mora, depois dos juros e só por último do capital, que é o dinheiro que saiu do bolso do
    credor. Assim, quem recebeu o valor redondo sem cobrar a mora fica com os juros inteiros, e
    quem não cobrou parte dos juros não vê esses juros como ganho.

    A divisão é sobre o que a parcela cobra (não sobre o que falta), porque é a cobrança que está
    sendo reduzida: com isso o que sobrar de juros a receber, capital a devolver e encargos fecha
    em zero. A parcela precisa vir com a multa e a mora da data do pagamento.
    """
    restante = max(valor, 0)
    perdao = {"encargos": 0, "juros": 0, "capital": 0}
    for chave, disponivel in (
        ("encargos", encargos_cobrados_parcela(parcela)),
        ("juros", juros_da_parcela(parcela)),
        ("capital", capital_cobrado_parcela(parcela)),
    ):
        parte = min(restante, disponivel)
        perdao[chave] = parte
        restante -= parte
    perdao["total"] = perdao["encargos"] + perdao["juros"] + perdao["capital"]
    return perdao


def juros_por_pagamento(parcela: dict, valores_pagos: list[int]) -> list[int]:
    """Parte de juros de cada pagamento da parcela, na ordem em que foram feitos.

    Os pagamentos cobrem a parcela em sequência, juros primeiro (art. 354): o primeiro leva os
    juros e os seguintes, o capital. Serve para lançar os juros no mês em que o dinheiro entrou.
    """
    juros_restante = juros_da_parcela(parcela)
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
        capital_pago = sum(
            imputar_pagamento_parcela(p)["capital"] + perdao_da_parcela(p)["capital"] for p in ativas
        )  # perdoado também não volta mais: sai do capital em aberto
        return max((emprestimo.get("valor_principal_centavos") or 0) - capital_pago, 0)
    return sum(
        capital_em_aberto_parcela(p)
        for p in ativas
        if p.get("status") not in STATUS_PARCELA_QUITADA
    )
