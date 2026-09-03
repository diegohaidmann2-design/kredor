"""
Serviço de cálculos financeiros
"""
import math
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from typing import List, Optional
from models.emprestimo import ParcelaSimulacao, SimulacaoRequest


def calcular_juros_simples(principal: float, taxa_mensal: float, meses: int) -> tuple:
    """Retorna (valor_total, valor_juros)"""
    juros_total = principal * (taxa_mensal / 100) * meses
    valor_total = principal + juros_total
    return valor_total, juros_total


def calcular_juros_compostos(principal: float, taxa_mensal: float, meses: int) -> tuple:
    """Retorna (valor_total, valor_juros)"""
    valor_total = principal * math.pow(1 + taxa_mensal / 100, meses)
    juros_total = valor_total - principal
    return valor_total, juros_total


def calcular_tabela_price(principal: float, taxa_mensal: float, meses: int, carencia: int) -> List[dict]:
    """Retorna lista de parcelas com Tabela Price"""
    taxa = taxa_mensal / 100
    parcelas = []
    
    # Cálculo da parcela fixa (PMT)
    if taxa == 0:
        valor_parcela = principal / meses
    else:
        valor_parcela = principal * (taxa * math.pow(1 + taxa, meses)) / (math.pow(1 + taxa, meses) - 1)
    
    saldo = principal
    
    for i in range(meses):
        juros = saldo * taxa
        amortizacao = valor_parcela - juros
        saldo -= amortizacao
        
        parcelas.append({
            "numero": i + 1 + carencia,
            "valor_principal": round(amortizacao, 2),
            "valor_juros": round(juros, 2),
            "valor_total": round(valor_parcela, 2),
            "saldo_devedor": round(max(saldo, 0), 2)
        })
    
    return parcelas


def calcular_sac(principal: float, taxa_mensal: float, meses: int, carencia: int) -> List[dict]:
    """Retorna lista de parcelas com SAC"""
    taxa = taxa_mensal / 100
    amortizacao = principal / meses
    saldo = principal
    parcelas = []
    
    for i in range(meses):
        juros = saldo * taxa
        valor_total = amortizacao + juros
        saldo -= amortizacao
        
        parcelas.append({
            "numero": i + 1 + carencia,
            "valor_principal": round(amortizacao, 2),
            "valor_juros": round(juros, 2),
            "valor_total": round(valor_total, 2),
            "saldo_devedor": round(max(saldo, 0), 2)
        })
    
    return parcelas


def calcular_data_vencimento(data_inicio: datetime, mes_index: int, dia_vencimento: Optional[int] = None, periodicidade: str = "mensal") -> datetime:
    """
    Calcula data de vencimento para periodicidade mensal ou semanal
    
    Args:
        data_inicio: Data de início do empréstimo
        mes_index: Índice do período (mês ou semana)
        dia_vencimento: Dia do mês desejado (1-31) ou None
        periodicidade: "mensal" ou "semanal"
    
    Returns:
        Data de vencimento calculada
    
    Exemplos:
        periodicidade="mensal", mes_index=1 -> +1 mês
        periodicidade="semanal", mes_index=1 -> +1 semana (7 dias, mesmo dia da semana)
    """
    if periodicidade == "semanal":
        # Vencimento semanal: sempre no mesmo dia da semana
        return data_inicio + timedelta(weeks=mes_index)

    if periodicidade == "diario":
        # Vencimento diário: um dia após o outro
        return data_inicio + timedelta(days=mes_index)
    
    # Vencimento mensal (comportamento original)
    data_venc = data_inicio + relativedelta(months=mes_index)
    
    if dia_vencimento:
        try:
            data_venc = data_venc.replace(day=dia_vencimento)
        except ValueError:
            from calendar import monthrange
            ultimo_dia = monthrange(data_venc.year, data_venc.month)[1]
            data_venc = data_venc.replace(day=min(dia_vencimento, ultimo_dia))
    
    return data_venc


def gerar_parcelas_simulacao(
    simulacao: SimulacaoRequest, 
    data_inicio: datetime,
    dia_vencimento: Optional[int] = None
) -> List[ParcelaSimulacao]:
    """Gera lista de parcelas para simulação (mensal ou semanal)"""
    parcelas = []
    principal = simulacao.valor_principal
    periodicidade = simulacao.periodicidade
    
    # Determinar taxa e prazo baseado na periodicidade
    if periodicidade == "semanal":
        taxa = simulacao.taxa_juros_semanal or 0
        periodos = simulacao.prazo_semanas or 0
        carencia = simulacao.periodo_carencia_meses * 4  # Converter meses em semanas
    elif periodicidade == "diario":
        taxa = simulacao.taxa_juros_diaria or 0
        periodos = simulacao.prazo_dias or 0
        carencia = simulacao.periodo_carencia_meses * 30  # Converter meses em dias
    else:
        taxa = simulacao.taxa_juros_mensal
        periodos = simulacao.prazo_meses
        carencia = simulacao.periodo_carencia_meses
    
    metodo = simulacao.metodo_calculo
    
    if metodo == "juros_simples":
        valor_total, valor_juros = calcular_juros_simples(principal, taxa, periodos)
        valor_parcela = valor_total / periodos
        juros_parcela = valor_juros / periodos
        principal_parcela = principal / periodos
        saldo = valor_total
        
        for i in range(periodos):
            saldo -= valor_parcela
            data_venc = calcular_data_vencimento(data_inicio, i + 1 + carencia, dia_vencimento, periodicidade)
            parcelas.append(ParcelaSimulacao(
                numero_parcela=i + 1,
                data_vencimento=data_venc.isoformat(),
                valor_principal=round(principal_parcela, 2),
                valor_juros=round(juros_parcela, 2),
                valor_total=round(valor_parcela, 2),
                saldo_devedor=round(max(saldo, 0), 2)
            ))
    
    elif metodo == "juros_compostos":
        valor_total, valor_juros = calcular_juros_compostos(principal, taxa, periodos)
        valor_parcela = valor_total / periodos
        saldo = valor_total
        
        for i in range(periodos):
            saldo -= valor_parcela
            data_venc = calcular_data_vencimento(data_inicio, i + 1 + carencia, dia_vencimento, periodicidade)
            
            prop_juros = valor_juros / valor_total
            prop_principal = principal / valor_total
            
            parcelas.append(ParcelaSimulacao(
                numero_parcela=i + 1,
                data_vencimento=data_venc.isoformat(),
                valor_principal=round(valor_parcela * prop_principal, 2),
                valor_juros=round(valor_parcela * prop_juros, 2),
                valor_total=round(valor_parcela, 2),
                saldo_devedor=round(max(saldo, 0), 2)
            ))
    
    elif metodo == "tabela_price":
        parcelas_calc = calcular_tabela_price(principal, taxa, periodos, carencia)
        for p in parcelas_calc:
            data_venc = calcular_data_vencimento(data_inicio, p["numero"], dia_vencimento, periodicidade)
            parcelas.append(ParcelaSimulacao(
                numero_parcela=p["numero"] - carencia,
                data_vencimento=data_venc.isoformat(),
                valor_principal=p["valor_principal"],
                valor_juros=p["valor_juros"],
                valor_total=p["valor_total"],
                saldo_devedor=p["saldo_devedor"]
            ))
    
    elif metodo == "sac":
        parcelas_calc = calcular_sac(principal, taxa, periodos, carencia)
        for p in parcelas_calc:
            data_venc = calcular_data_vencimento(data_inicio, p["numero"], dia_vencimento, periodicidade)
            parcelas.append(ParcelaSimulacao(
                numero_parcela=p["numero"] - carencia,
                data_vencimento=data_venc.isoformat(),
                valor_principal=p["valor_principal"],
                valor_juros=p["valor_juros"],
                valor_total=p["valor_total"],
                saldo_devedor=p["saldo_devedor"]
            ))
    
    elif metodo == "apenas_juros":
        # Apenas juros: paga só juros durante período, principal no final
        juros_periodo = principal * (taxa / 100)
        
        for i in range(periodos - 1):
            data_venc = calcular_data_vencimento(data_inicio, i + 1 + carencia, dia_vencimento, periodicidade)
            parcelas.append(ParcelaSimulacao(
                numero_parcela=i + 1,
                data_vencimento=data_venc.isoformat(),
                valor_principal=0.0,
                valor_juros=round(juros_periodo, 2),
                valor_total=round(juros_periodo, 2),
                saldo_devedor=principal
            ))
        
        # Última parcela: principal + juros
        data_venc = calcular_data_vencimento(data_inicio, periodos + carencia, dia_vencimento, periodicidade)
        parcelas.append(ParcelaSimulacao(
            numero_parcela=periodos,
            data_vencimento=data_venc.isoformat(),
            valor_principal=principal,
            valor_juros=round(juros_periodo, 2),
            valor_total=round(principal + juros_periodo, 2),
            saldo_devedor=0.0
        ))
    
    return parcelas
