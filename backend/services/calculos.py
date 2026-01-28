"""
Serviço de cálculos financeiros
"""
import math
from datetime import datetime, timedelta, timezone
from typing import List
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


def gerar_parcelas_simulacao(simulacao: SimulacaoRequest, data_inicio: datetime) -> List[ParcelaSimulacao]:
    """Gera lista de parcelas para simulação"""
    parcelas = []
    principal = simulacao.valor_principal
    taxa = simulacao.taxa_juros_mensal
    meses = simulacao.prazo_meses
    carencia = simulacao.periodo_carencia_meses
    metodo = simulacao.metodo_calculo
    
    if metodo == "juros_simples":
        valor_total, valor_juros = calcular_juros_simples(principal, taxa, meses)
        valor_parcela = valor_total / meses
        juros_parcela = valor_juros / meses
        principal_parcela = principal / meses
        saldo = valor_total
        
        for i in range(meses):
            saldo -= valor_parcela
            data_venc = data_inicio + timedelta(days=30 * (i + 1 + carencia))
            parcelas.append(ParcelaSimulacao(
                numero_parcela=i + 1,
                data_vencimento=data_venc.isoformat(),
                valor_principal=round(principal_parcela, 2),
                valor_juros=round(juros_parcela, 2),
                valor_total=round(valor_parcela, 2),
                saldo_devedor=round(max(saldo, 0), 2)
            ))
    
    elif metodo == "juros_compostos":
        valor_total, valor_juros = calcular_juros_compostos(principal, taxa, meses)
        valor_parcela = valor_total / meses
        saldo = valor_total
        
        for i in range(meses):
            saldo -= valor_parcela
            data_venc = data_inicio + timedelta(days=30 * (i + 1 + carencia))
            
            # Proporção de juros e principal
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
        parcelas_calc = calcular_tabela_price(principal, taxa, meses, carencia)
        for p in parcelas_calc:
            data_venc = data_inicio + timedelta(days=30 * p["numero"])
            parcelas.append(ParcelaSimulacao(
                numero_parcela=p["numero"] - carencia,
                data_vencimento=data_venc.isoformat(),
                valor_principal=p["valor_principal"],
                valor_juros=p["valor_juros"],
                valor_total=p["valor_total"],
                saldo_devedor=p["saldo_devedor"]
            ))
    
    elif metodo == "sac":
        parcelas_calc = calcular_sac(principal, taxa, meses, carencia)
        for p in parcelas_calc:
            data_venc = data_inicio + timedelta(days=30 * p["numero"])
            parcelas.append(ParcelaSimulacao(
                numero_parcela=p["numero"] - carencia,
                data_vencimento=data_venc.isoformat(),
                valor_principal=p["valor_principal"],
                valor_juros=p["valor_juros"],
                valor_total=p["valor_total"],
                saldo_devedor=p["saldo_devedor"]
            ))
    
    elif metodo == "apenas_juros":
        # Método onde cliente paga APENAS os juros mensalmente
        # Capital principal permanece constante
        # Última parcela = capital + juros do mês
        taxa_decimal = taxa / 100
        juros_mensal = principal * taxa_decimal
        saldo = principal
        
        for i in range(meses):
            data_venc = data_inicio + timedelta(days=30 * (i + 1 + carencia))
            
            # Todas as parcelas pagam apenas juros, exceto a última
            if i < meses - 1:
                # Parcelas intermediárias: apenas juros
                parcelas.append(ParcelaSimulacao(
                    numero_parcela=i + 1,
                    data_vencimento=data_venc.isoformat(),
                    valor_principal=0.0,  # Não amortiza capital
                    valor_juros=round(juros_mensal, 2),
                    valor_total=round(juros_mensal, 2),
                    saldo_devedor=round(saldo, 2)  # Saldo permanece constante
                ))
            else:
                # Última parcela: capital + juros
                parcelas.append(ParcelaSimulacao(
                    numero_parcela=i + 1,
                    data_vencimento=data_venc.isoformat(),
                    valor_principal=round(principal, 2),
                    valor_juros=round(juros_mensal, 2),
                    valor_total=round(principal + juros_mensal, 2),
                    saldo_devedor=0.0  # Quitado
                ))
    
    return parcelas
