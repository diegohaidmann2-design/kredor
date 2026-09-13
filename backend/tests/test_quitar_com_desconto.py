"""Quitação com desconto: o que o credor não cobrou sai do a receber sem virar ganho."""
from services.parcela_service import (
    capital_em_aberto_emprestimo,
    capital_em_aberto_parcela,
    distribuir_perdao,
    encargos_em_aberto_parcela,
    imputar_pagamento_parcela,
    juros_da_parcela,
    juros_em_aberto_parcela,
    perdao_da_parcela,
    saldo_devedor_parcela,
)


def parcela(principal, juros, pago=0, status="pendente", **extra):
    return {"valor_principal_centavos": principal, "valor_juros_centavos": juros,
            "valor_total_centavos": principal + juros, "valor_pago_centavos": pago,
            "status": status, **extra}


def quitar_com_desconto(p):
    """Aplica na parcela o perdão do que faltava, como faz registrar_pagamento."""
    perdao = distribuir_perdao(p, saldo_devedor_parcela(p))
    return {**p, "status": "pago", "valor_perdoado_centavos": perdao["total"],
            "perdao_juros_centavos": perdao["juros"],
            "perdao_capital_centavos": perdao["capital"],
            "perdao_encargos_centavos": perdao["encargos"]}, perdao


def test_valor_redondo_perdoa_a_mora_e_os_centavos_de_juros():
    # Parcela de R$ 500,13 (R$ 400 de capital) com R$ 20 de mora; o cliente pagou R$ 500,00.
    p = parcela(40_000, 10_013, 50_000, "atrasado", valor_juros_mora_centavos=2_000)
    quitada, perdao = quitar_com_desconto(p)

    assert perdao == {"encargos": 2_000, "juros": 13, "capital": 0, "total": 2_013}
    # Recebeu os R$ 400 de capital e R$ 100 de juros: nada de mora entra como ganho.
    assert imputar_pagamento_parcela(quitada) == {"juros": 10_000, "capital": 40_000, "encargos": 0}


def test_juros_que_o_credor_nao_cobrou_nao_entram_como_recebidos():
    # Parcela de R$ 1.200 (R$ 1.000 + R$ 200 de juros); recebeu R$ 1.150 e não cobrou os R$ 50.
    p = parcela(100_000, 20_000, 115_000, "parcial")
    quitada, perdao = quitar_com_desconto(p)

    assert perdao == {"encargos": 0, "juros": 5_000, "capital": 0, "total": 5_000}
    assert juros_da_parcela(quitada) == 15_000
    assert imputar_pagamento_parcela(quitada) == {"juros": 15_000, "capital": 100_000, "encargos": 0}


def test_parcela_quitada_com_desconto_nao_tem_mais_nada_a_receber():
    p = parcela(40_000, 10_013, 50_000, "atrasado", valor_multa_centavos=1_000,
                valor_juros_mora_centavos=1_000)
    quitada, _ = quitar_com_desconto(p)

    assert saldo_devedor_parcela(quitada) == 0
    assert juros_em_aberto_parcela(quitada) == 0
    assert capital_em_aberto_parcela(quitada) == 0
    assert encargos_em_aberto_parcela(quitada) == 0
    assert capital_em_aberto_emprestimo(
        {"status": "ativo", "valor_principal_centavos": 40_000}, [quitada]) == 0


def test_sem_perdao_o_restante_continua_a_receber():
    # Mesmo caso, sem quitar com desconto: a parcela segue parcial devendo a mora e os centavos.
    p = parcela(40_000, 10_013, 50_000, "parcial", valor_juros_mora_centavos=2_000)

    assert perdao_da_parcela(p)["total"] == 0
    assert saldo_devedor_parcela(p) == 2_013
    # Os juros vêm primeiro na imputação, então o que falta é mora e o centavo de capital.
    assert juros_em_aberto_parcela(p) == 0
    assert (capital_em_aberto_parcela(p), encargos_em_aberto_parcela(p)) == (13, 2_000)


def test_perdao_de_juros_de_emprestimo_aberto_que_pagou_sem_a_mora():
    # Parcela só de juros (R$ 100,50) com R$ 3,40 de mora: recebeu R$ 100,50 em dinheiro.
    p = parcela(0, 10_050, 10_050, "atrasado", valor_juros_mora_centavos=340)
    quitada, perdao = quitar_com_desconto(p)

    assert perdao == {"encargos": 340, "juros": 0, "capital": 0, "total": 340}
    assert imputar_pagamento_parcela(quitada)["juros"] == 10_050
    emprestimo = {"status": "ativo", "sem_prazo": True, "valor_principal_centavos": 300_000}
    assert capital_em_aberto_emprestimo(emprestimo, [quitada]) == 300_000


def test_desconto_grande_chega_a_perdoar_capital():
    # Parcela de R$ 1.100 com R$ 50 de multa; recebeu só R$ 200.
    p = parcela(100_000, 10_000, 20_000, "atrasado", valor_multa_centavos=5_000)
    quitada, perdao = quitar_com_desconto(p)

    assert perdao == {"encargos": 5_000, "juros": 10_000, "capital": 80_000, "total": 95_000}
    # Nada de juros entra como ganho: os R$ 200 são devolução de capital.
    assert imputar_pagamento_parcela(quitada) == {"juros": 0, "capital": 20_000, "encargos": 0}
    assert saldo_devedor_parcela(quitada) == 0


def test_perdao_nunca_passa_do_que_a_parcela_cobra():
    p = parcela(10_000, 1_000)
    perdao = distribuir_perdao(p, 999_999)
    assert perdao == {"encargos": 0, "juros": 1_000, "capital": 10_000, "total": 11_000}


def test_perdao_de_valor_zero_ou_negativo_nao_perdoa_nada():
    p = parcela(10_000, 1_000, 11_000, "pago")
    assert distribuir_perdao(p, 0)["total"] == 0
    assert distribuir_perdao(p, -500)["total"] == 0
