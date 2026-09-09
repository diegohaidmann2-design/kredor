"""Precisão monetária: centavos inteiros, sem resíduo em nenhum método de amortização."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.dinheiro import (  # noqa: E402
    reais_para_centavos, centavos_para_reais, dividir_centavos, arredondar_centavos,
    formatar_reais, para_api, EntradaEmReais,
)
from models.emprestimo import SimulacaoRequest  # noqa: E402
from models.pagamento import PagamentoCreate  # noqa: E402
from services import calculos  # noqa: E402

METODOS = ["juros_simples", "juros_compostos", "tabela_price", "sac", "apenas_juros"]


def test_reais_para_centavos_string():
    assert reais_para_centavos("100.50") == 10050


def test_soma_de_floats_fecha():
    assert reais_para_centavos(0.1) + reais_para_centavos(0.2) == reais_para_centavos(0.3)


@pytest.mark.parametrize("valor,esperado", [(0.29, 29), (1.15, 115), (2.01, 201), (999.99, 99999), (10000, 1000000)])
def test_reais_para_centavos_nao_perde_centavo(valor, esperado):
    assert reais_para_centavos(valor) == esperado


def test_ida_e_volta_todos_os_valores_ate_999_99():
    for c in range(1, 100000):
        assert reais_para_centavos(centavos_para_reais(c)) == c


def test_dividir_centavos_soma_exata():
    partes = dividir_centavos(10000_00, 12)
    assert sum(partes) == 10000_00
    assert len(partes) == 12
    assert max(partes) - min(partes) <= 12


def test_dividir_centavos_partes_invalidas():
    with pytest.raises(ValueError):
        dividir_centavos(100, 0)


def test_arredondar_centavos_half_up():
    assert arredondar_centavos(10.5) == 11
    assert arredondar_centavos(10.49) == 10


def test_formatar_reais_pt_br():
    assert formatar_reais(123456) == "1.234,56"
    assert formatar_reais(None) == "0,00"


def _simulacao(metodo, principal=10000.0, taxa=2.0, meses=12):
    return SimulacaoRequest(valor_principal=principal, taxa_juros_mensal=taxa, prazo_meses=meses, metodo_calculo=metodo)


@pytest.mark.parametrize("metodo", METODOS)
def test_amortizacao_fecha_com_principal(metodo):
    sim = _simulacao(metodo)
    parcelas = calculos.gerar_parcelas_simulacao(sim, __import__("datetime").datetime(2026, 1, 10))
    assert sum(p.valor_principal_centavos for p in parcelas) == sim.valor_principal_centavos == 1000000
    for p in parcelas:
        assert isinstance(p.valor_total_centavos, int)
        assert p.valor_total_centavos == p.valor_principal_centavos + p.valor_juros_centavos


@pytest.mark.parametrize("metodo", METODOS)
@pytest.mark.parametrize("principal,taxa,meses", [(1234.56, 3.33, 7), (0.99, 15, 3), (50000, 1.5, 60), (777.77, 0, 5)])
def test_amortizacao_fecha_em_casos_irregulares(metodo, principal, taxa, meses):
    sim = _simulacao(metodo, principal, taxa, meses)
    parcelas = calculos.gerar_parcelas_simulacao(sim, __import__("datetime").datetime(2026, 1, 10))
    assert len(parcelas) == meses
    assert sum(p.valor_principal_centavos for p in parcelas) == sim.valor_principal_centavos


def test_price_10k_12x_2pct_sem_residuo():
    parcelas = calculos.calcular_tabela_price(1000000, 2.0, 12, 0)
    assert sum(p["valor_principal_centavos"] for p in parcelas) == 1000000
    assert parcelas[-1]["saldo_devedor_centavos"] == 0
    assert parcelas[0]["valor_total_centavos"] == 94560  # PMT de R$ 945,60


def test_juros_simples_totais():
    total, juros = calculos.calcular_juros_simples(1000000, 2.0, 12)
    assert (total, juros) == (1240000, 240000)


def test_entrada_em_reais_converte_na_fronteira():
    req = PagamentoCreate(parcela_id="x", valor_pago=100.50, metodo_pagamento="pix")
    assert req.valor_pago_centavos == 10050
    req2 = PagamentoCreate(parcela_id="x", valor_pago_centavos=777, metodo_pagamento="pix")
    assert req2.valor_pago_centavos == 777


def test_para_api_converte_apenas_sufixo_centavos():
    saida = para_api({"valor_total_centavos": 10050, "taxa": 2.0, "itens": [{"saldo_devedor_centavos": 1}], "valor_pago": {"pontos": 1}})
    assert saida == {"valor_total": 100.5, "taxa": 2.0, "itens": [{"saldo_devedor": 0.01}], "valor_pago": {"pontos": 1}}
