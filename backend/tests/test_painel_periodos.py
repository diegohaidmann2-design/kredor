"""Limites de "hoje" e "mês" do painel no horário de Brasília, e os 12 meses dos gráficos."""
from datetime import datetime, timezone

import pytest

from routes.dashboard import _limites_do_periodo, _mes_sp, _ultimos_12_meses


def test_22h_do_ultimo_dia_do_mes_ainda_e_hoje_e_ainda_e_o_mesmo_mes():
    agora = datetime(2026, 10, 1, 1, 0, tzinfo=timezone.utc)  # 30/09 às 22:00 em Brasília
    hoje, fim_hoje, fim_semana, inicio_mes, fim_mes = _limites_do_periodo(agora)

    assert hoje == datetime(2026, 9, 30, 3, 0, tzinfo=timezone.utc)
    assert fim_hoje == datetime(2026, 10, 1, 3, 0, tzinfo=timezone.utc)
    assert fim_semana == datetime(2026, 10, 7, 3, 0, tzinfo=timezone.utc)
    assert inicio_mes == datetime(2026, 9, 1, 3, 0, tzinfo=timezone.utc)
    assert fim_mes == datetime(2026, 10, 1, 3, 0, tzinfo=timezone.utc)
    assert inicio_mes <= agora < fim_mes


def test_pagamento_as_22h_de_30_09_conta_em_setembro():
    assert _mes_sp(datetime(2026, 10, 1, 1, 0, tzinfo=timezone.utc)) == (2026, 9)


def test_dezembro_termina_em_janeiro_do_ano_seguinte():
    _, _, _, inicio_mes, fim_mes = _limites_do_periodo(datetime(2026, 12, 15, 12, 0, tzinfo=timezone.utc))
    assert inicio_mes == datetime(2026, 12, 1, 3, 0, tzinfo=timezone.utc)
    assert fim_mes == datetime(2027, 1, 1, 3, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("agora", [
    datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc),  # dia 31: a regra antiga repetia outubro
    datetime(2027, 3, 31, 12, 0, tzinfo=timezone.utc),   # e aqui repetia dezembro e março, pulando fevereiro
    datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
])
def test_grafico_tem_12_meses_distintos_e_seguidos_terminando_no_atual(agora):
    meses = _ultimos_12_meses(agora)

    assert len(meses) == 12 and len(set(meses)) == 12
    assert meses[-1] == _mes_sp(agora)
    for (ano_a, mes_a), (ano_b, mes_b) in zip(meses, meses[1:]):
        assert (ano_b * 12 + mes_b) - (ano_a * 12 + mes_a) == 1
