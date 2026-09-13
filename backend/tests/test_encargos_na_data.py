"""Multa e mora pela data em que o cliente pagou, não pela data em que foi lançado."""
from datetime import datetime, timedelta, timezone

from services.juros_mora_service import calcular_encargos_na_data

EMPRESTIMO = {"taxa_multa_atraso": 2.0, "taxa_juros_mora_diario": 0.1}


def parcela(dias_vencida, total=100_000, pago=0, status="atrasado"):
    venc = datetime.now(timezone.utc) - timedelta(days=dias_vencida)
    return {"data_vencimento": venc.isoformat(), "valor_total_centavos": total,
            "valor_pago_centavos": pago, "status": status}


def test_pago_no_vencimento_nao_tem_multa_nem_mora():
    # Venceu há 3 dias e o job já gravou mora, mas o cliente pagou no dia do vencimento.
    p = parcela(3)
    vencimento = datetime.fromisoformat(p["data_vencimento"])

    assert calcular_encargos_na_data(p, EMPRESTIMO, vencimento) == {
        "valor_multa_centavos": 0, "valor_juros_mora_centavos": 0, "dias_atraso": 0}


def test_lancado_depois_cobra_a_mora_do_dia_em_que_pagou():
    p = parcela(10)
    vencimento = datetime.fromisoformat(p["data_vencimento"])

    # Pagou 3 dias após o vencimento: multa de 2% (R$ 20) + 3 dias de mora de 0,1% (R$ 3)
    assert calcular_encargos_na_data(p, EMPRESTIMO, vencimento + timedelta(days=3)) == {
        "valor_multa_centavos": 2_000, "valor_juros_mora_centavos": 300, "dias_atraso": 3}


def test_multa_e_mora_incidem_sobre_o_saldo_da_parcela():
    p = parcela(10, total=100_000, pago=60_000, status="parcial")
    vencimento = datetime.fromisoformat(p["data_vencimento"])

    # Faltavam R$ 400: multa de R$ 8 e 10 dias de mora (R$ 0,40/dia)
    assert calcular_encargos_na_data(p, EMPRESTIMO, vencimento + timedelta(days=10)) == {
        "valor_multa_centavos": 800, "valor_juros_mora_centavos": 400, "dias_atraso": 10}


def test_data_no_futuro_conta_como_hoje():
    p = parcela(5)

    assert calcular_encargos_na_data(p, EMPRESTIMO, datetime.now(timezone.utc) + timedelta(days=30))["dias_atraso"] == 5


def test_data_sem_fuso_e_aceita():
    p = parcela(4)
    vencimento_sem_fuso = datetime.fromisoformat(p["data_vencimento"]).replace(tzinfo=None)

    assert calcular_encargos_na_data(p, EMPRESTIMO, vencimento_sem_fuso)["dias_atraso"] == 0


def test_parcela_ja_quitada_nao_gera_encargo():
    p = parcela(10, pago=100_000, status="pago")

    assert calcular_encargos_na_data(p, EMPRESTIMO, datetime.now(timezone.utc)) == {
        "valor_multa_centavos": 0, "valor_juros_mora_centavos": 0, "dias_atraso": 0}
