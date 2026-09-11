"""Recibo de pagamento parcial: cálculo do saldo e geração do PDF (sem banco)."""
import pytest

from routes.pagamentos import _formatar_data_sp, _montar_pdf_recibo
from services.parcela_service import saldo_devedor_emprestimo, saldo_devedor_parcela


def _parcela(total, pago=0, multa=0, mora=0, status="pendente", deleted=False):
    return {
        "valor_total_centavos": total,
        "valor_pago_centavos": pago,
        "valor_multa_centavos": multa,
        "valor_juros_mora_centavos": mora,
        "status": status,
        "deleted": deleted,
    }


def test_saldo_da_parcela_desconta_o_pago_e_soma_multa_e_mora():
    assert saldo_devedor_parcela(_parcela(10_000, pago=4_000, multa=200, mora=33)) == 6_233


def test_saldo_da_parcela_nunca_fica_negativo():
    assert saldo_devedor_parcela(_parcela(10_000, pago=12_000)) == 0


def test_saldo_do_emprestimo_ignora_parcelas_pagas_e_deletadas():
    parcelas = [
        _parcela(10_000, pago=10_000, status="pago"),
        _parcela(10_000, pago=3_000, status="parcial"),
        _parcela(10_000, status="pendente"),
        _parcela(10_000, status="pendente", deleted=True),
    ]
    assert saldo_devedor_emprestimo({"status": "ativo"}, parcelas) == 17_000


def test_saldo_do_emprestimo_aberto_inclui_o_capital():
    # Em empréstimo aberto as parcelas são só de juros; o capital volta por amortização.
    emprestimo = {"status": "ativo", "sem_prazo": True, "valor_principal_centavos": 10_000}
    assert saldo_devedor_emprestimo(emprestimo, [_parcela(500, pago=200, status="parcial")]) == 10_300


@pytest.mark.parametrize("status", ["quitado", "cancelado"])
def test_saldo_do_emprestimo_encerrado_e_zero(status):
    assert saldo_devedor_emprestimo({"status": status}, [_parcela(10_000)]) == 0


def test_data_do_recibo_usa_o_fuso_de_sao_paulo():
    # 01:30 UTC do dia 11 ainda é dia 10 em São Paulo.
    assert _formatar_data_sp("2026-09-11T01:30:00+00:00") == "10/09/2026"


def _dados(saldo_parcela, posicao_atual=False):
    return {
        "pagamento": {
            "id": "pag-1", "valor_pago_centavos": 4_000, "data_pagamento": "2026-09-11T01:30:00+00:00",
            "metodo_pagamento": "pix", "numero_parcela": 2, "total_parcelas": 12,
        },
        "emprestimo": {"id": "abcdef1234567890"},
        "parcela": {},
        # "&" e "<" no nome testam o escape da marcação do reportlab.
        "cliente": {"nome": "Maria & Filhos <Ltda>", "cpf_cnpj": "000.000.000-00", "telefone": "11999999999"},
        "saldo_parcela": saldo_parcela,
        "saldo_emprestimo": 50_000,
        "posicao_atual": posicao_atual,
    }


@pytest.mark.parametrize("saldo_parcela,posicao_atual", [
    (6_000, False),  # pagamento parcial
    (0, False),      # pagamento que quitou a parcela
    (6_000, True),   # pagamento antigo, sem o retrato do saldo gravado
])
def test_pdf_do_recibo_e_gerado(saldo_parcela, posicao_atual):
    pdf = _montar_pdf_recibo(_dados(saldo_parcela, posicao_atual), "Credor Teste").getvalue()
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1_000
