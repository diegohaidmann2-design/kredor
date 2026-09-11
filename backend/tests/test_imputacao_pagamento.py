"""Imputação do pagamento na parcela (juros antes do capital, CC art. 354) e capital em aberto."""
from services.parcela_service import (
    capital_em_aberto_emprestimo,
    encargos_em_aberto_parcela,
    imputar_pagamento_parcela,
    juros_da_parcela,
    juros_em_aberto_parcela,
    juros_por_pagamento,
    saldo_devedor_parcela,
)


def parcela(principal, juros, pago=0, status="pendente", **extra):
    return {"valor_principal_centavos": principal, "valor_juros_centavos": juros,
            "valor_total_centavos": principal + juros, "valor_pago_centavos": pago, "status": status, **extra}


def test_pagamento_parcial_abate_primeiro_os_juros():
    # R$ 15.000 a 13,4% em 1x (R$ 2.010 de juros), pagos R$ 10.010: faltam R$ 7.000 de capital.
    assert imputar_pagamento_parcela(parcela(1_500_000, 201_000, 1_001_000, "parcial")) == {
        "juros": 201_000, "capital": 800_000, "encargos": 0}


def test_pagamento_menor_que_os_juros_nao_devolve_capital():
    assert imputar_pagamento_parcela(parcela(100_000, 20_000, 5_000, "parcial")) == {
        "juros": 5_000, "capital": 0, "encargos": 0}


def test_o_que_passa_de_juros_e_capital_e_encargo():
    # Parcela de juros de empréstimo aberto paga com atraso: R$ 100 de juros + R$ 3,40 de mora.
    assert imputar_pagamento_parcela(parcela(0, 10_000, 10_340, "pago")) == {
        "juros": 10_000, "capital": 0, "encargos": 340}


def test_valor_pago_informado_substitui_o_da_parcela():
    assert imputar_pagamento_parcela(parcela(100_000, 20_000, 0), valor_pago=50_000) == {
        "juros": 20_000, "capital": 30_000, "encargos": 0}


def test_juros_de_cada_pagamento_em_sequencia():
    assert juros_por_pagamento(parcela(100_000, 70_000), [50_000, 30_000, 100_000]) == [50_000, 20_000, 0]


def test_capital_em_aberto_desconta_o_capital_ja_pago():
    emprestimo = {"status": "ativo", "valor_principal_centavos": 200_000}
    parcelas = [parcela(100_000, 10_000, 110_000, "pago"), parcela(100_000, 10_000, 60_000, "parcial")]
    assert capital_em_aberto_emprestimo(emprestimo, parcelas) == 50_000


def test_parcela_quitada_e_parcela_excluida_saem_da_conta():
    emprestimo = {"status": "ativo", "valor_principal_centavos": 300_000}
    parcelas = [
        parcela(100_000, 0, 90_000, "pago"),  # quitada com desconto: não há mais nada a receber
        parcela(100_000, 0, 0, "pendente", deleted=True),
        parcela(100_000, 0, 0, "pendente"),
    ]
    assert capital_em_aberto_emprestimo(emprestimo, parcelas) == 100_000


def test_emprestimo_aberto_usa_o_capital_atual():
    emprestimo = {"status": "ativo", "sem_prazo": True, "valor_principal_centavos": 30_000}
    parcelas = [parcela(0, 10_050, 10_050, "pago"), parcela(0, 10_050)]
    assert capital_em_aberto_emprestimo(emprestimo, parcelas) == 30_000


def test_quitado_nao_tem_capital_em_aberto():
    assert capital_em_aberto_emprestimo({"status": "quitado", "valor_principal_centavos": 100_000}, []) == 0


def test_sem_parcelas_vale_o_capital_do_emprestimo():
    assert capital_em_aberto_emprestimo({"status": "ativo", "valor_principal_centavos": 100_000}, []) == 100_000


def test_centavo_de_arredondamento_da_price_e_juros():
    # Prestação R$ 157,69; capital R$ 30,56 e juros R$ 127,12 arredondados em separado (soma 157,68).
    p = {"valor_total_centavos": 15_769, "valor_principal_centavos": 3_056, "valor_juros_centavos": 12_712,
         "valor_pago_centavos": 0, "status": "pendente"}
    assert juros_da_parcela(p) == 12_713
    emprestimo = {"status": "ativo", "valor_principal_centavos": 3_056}
    assert capital_em_aberto_emprestimo(emprestimo, [p]) + juros_em_aberto_parcela(p) == saldo_devedor_parcela(p)


def test_capital_juros_e_encargos_em_aberto_fecham_com_o_saldo():
    # Parcela em atraso, paga em parte: R$ 800 de capital, R$ 200 de juros, R$ 50 de multa/mora.
    p = parcela(80_000, 20_000, 60_000, "atrasado", valor_multa_centavos=30_00, valor_juros_mora_centavos=20_00)
    emprestimo = {"status": "ativo", "valor_principal_centavos": 80_000}
    total = capital_em_aberto_emprestimo(emprestimo, [p]) + juros_em_aberto_parcela(p) + encargos_em_aberto_parcela(p)
    assert (juros_em_aberto_parcela(p), encargos_em_aberto_parcela(p)) == (0, 5_000)
    assert total == saldo_devedor_parcela(p) == 45_000


def test_sem_total_usa_o_campo_de_juros():
    assert juros_da_parcela({"valor_principal_centavos": 0, "valor_juros_centavos": 500}) == 500
