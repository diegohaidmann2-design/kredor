"""
Serviço de cálculos financeiros.

Todos os valores monetários entram e saem em CENTAVOS inteiros. As taxas são
percentuais (float). O único arredondamento acontece ao converter o resultado de
(centavos x taxa) para centavos inteiros; o resto de divisões vai para a última
parcela, de modo que a soma das amortizações fecha exatamente com o principal.
"""
import math
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Optional
from calendar import monthrange
from models.emprestimo import ParcelaSimulacao, SimulacaoRequest
from utils.dinheiro import arredondar_centavos, dividir_centavos


def calcular_juros_simples(principal_centavos: int, taxa_mensal: float, meses: int) -> tuple:
    """Retorna (valor_total_centavos, valor_juros_centavos)"""
    juros_total = arredondar_centavos(principal_centavos * (taxa_mensal / 100) * meses)
    return principal_centavos + juros_total, juros_total


def calcular_juros_compostos(principal_centavos: int, taxa_mensal: float, meses: int) -> tuple:
    """Retorna (valor_total_centavos, valor_juros_centavos)"""
    valor_total = arredondar_centavos(principal_centavos * math.pow(1 + taxa_mensal / 100, meses))
    return valor_total, valor_total - principal_centavos


def _parcela(numero: int, principal: int, juros: int, saldo: int) -> dict:
    return {
        "numero": numero,
        "valor_principal_centavos": principal,
        "valor_juros_centavos": juros,
        "valor_total_centavos": principal + juros,
        "saldo_devedor_centavos": max(saldo, 0),
    }


def calcular_tabela_price(principal_centavos: int, taxa_mensal: float, meses: int, carencia: int) -> List[dict]:
    """Parcela fixa (PMT); a última absorve o resíduo para que a amortização feche com o principal."""
    taxa = taxa_mensal / 100
    if taxa == 0:
        amortizacoes = dividir_centavos(principal_centavos, meses)
        return [
            _parcela(i + 1 + carencia, amort, 0, principal_centavos - sum(amortizacoes[: i + 1]))
            for i, amort in enumerate(amortizacoes)
        ]

    fator = math.pow(1 + taxa, meses)
    pmt = arredondar_centavos(principal_centavos * (taxa * fator) / (fator - 1))

    parcelas = []
    saldo = principal_centavos
    for i in range(meses):
        juros = arredondar_centavos(saldo * taxa)
        amortizacao = saldo if i == meses - 1 else pmt - juros
        saldo -= amortizacao
        parcelas.append(_parcela(i + 1 + carencia, amortizacao, juros, saldo))
    return parcelas


def calcular_sac(principal_centavos: int, taxa_mensal: float, meses: int, carencia: int) -> List[dict]:
    """Amortização constante; juros sobre o saldo devedor de cada período."""
    taxa = taxa_mensal / 100
    amortizacoes = dividir_centavos(principal_centavos, meses)
    parcelas = []
    saldo = principal_centavos
    for i, amortizacao in enumerate(amortizacoes):
        juros = arredondar_centavos(saldo * taxa)
        saldo -= amortizacao
        parcelas.append(_parcela(i + 1 + carencia, amortizacao, juros, saldo))
    return parcelas


def calcular_data_vencimento(data_inicio: datetime, mes_index: int, dia_vencimento: Optional[int] = None, periodicidade: str = "mensal") -> datetime:
    """
    Calcula data de vencimento para periodicidade mensal, semanal ou diária.

    Exemplos:
        periodicidade="mensal", mes_index=1 -> +1 mês
        periodicidade="semanal", mes_index=1 -> +1 semana (7 dias, mesmo dia da semana)
    """
    if periodicidade == "semanal":
        return data_inicio + timedelta(weeks=mes_index)

    if periodicidade == "diario":
        return data_inicio + timedelta(days=mes_index)

    data_venc = data_inicio + relativedelta(months=mes_index)

    if dia_vencimento:
        ultimo_dia = monthrange(data_venc.year, data_venc.month)[1]
        data_venc = data_venc.replace(day=min(dia_vencimento, ultimo_dia))

    return data_venc


def _plano_parcelas_fixas(principal: int, valor_total: int, periodos: int) -> List[dict]:
    """Parcelas iguais (juros simples/compostos): totais e principais divididos, resto na última."""
    totais = dividir_centavos(valor_total, periodos)
    principais = dividir_centavos(principal, periodos)
    saldo = valor_total
    plano = []
    for i in range(periodos):
        saldo -= totais[i]
        plano.append(_parcela(i + 1, principais[i], totais[i] - principais[i], saldo))
    return plano


def gerar_parcelas_simulacao(
    simulacao: SimulacaoRequest,
    data_inicio: datetime,
    dia_vencimento: Optional[int] = None
) -> List[ParcelaSimulacao]:
    """Gera lista de parcelas para simulação (mensal, semanal ou diária), em centavos."""
    principal = simulacao.valor_principal_centavos
    periodicidade = simulacao.periodicidade

    if periodicidade == "semanal":
        taxa = simulacao.taxa_juros_semanal or 0
        periodos = simulacao.prazo_semanas or 0
        carencia = simulacao.periodo_carencia_meses * 4
    elif periodicidade == "diario":
        taxa = simulacao.taxa_juros_diaria or 0
        periodos = simulacao.prazo_dias or 0
        carencia = simulacao.periodo_carencia_meses * 30
    else:
        taxa = simulacao.taxa_juros_mensal
        periodos = simulacao.prazo_meses
        carencia = simulacao.periodo_carencia_meses

    metodo = simulacao.metodo_calculo

    if metodo == "juros_simples":
        valor_total, _ = calcular_juros_simples(principal, taxa, periodos)
        plano = _plano_parcelas_fixas(principal, valor_total, periodos)
        plano = [dict(p, numero=p["numero"] + carencia) for p in plano]

    elif metodo == "juros_compostos":
        valor_total, _ = calcular_juros_compostos(principal, taxa, periodos)
        plano = _plano_parcelas_fixas(principal, valor_total, periodos)
        plano = [dict(p, numero=p["numero"] + carencia) for p in plano]

    elif metodo == "tabela_price":
        plano = calcular_tabela_price(principal, taxa, periodos, carencia)

    elif metodo == "sac":
        plano = calcular_sac(principal, taxa, periodos, carencia)

    elif metodo == "apenas_juros":
        # Paga só juros durante o período; o principal inteiro vai na última parcela.
        juros_periodo = arredondar_centavos(principal * (taxa / 100))
        plano = [_parcela(i + 1 + carencia, 0, juros_periodo, principal) for i in range(periodos - 1)]
        plano.append(_parcela(periodos + carencia, principal, juros_periodo, 0))

    else:
        plano = []

    return [
        ParcelaSimulacao(
            numero_parcela=p["numero"] - carencia,
            data_vencimento=calcular_data_vencimento(data_inicio, p["numero"], dia_vencimento, periodicidade).isoformat(),
            valor_principal_centavos=p["valor_principal_centavos"],
            valor_juros_centavos=p["valor_juros_centavos"],
            valor_total_centavos=p["valor_total_centavos"],
            saldo_devedor_centavos=p["saldo_devedor_centavos"],
        )
        for p in plano
    ]
