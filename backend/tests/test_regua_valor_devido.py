"""Régua de cobrança: quanto ela cobra e quando decide não cobrar.

Dois defeitos corrigidos em 14/09/2026: o valor devido ignorava multa e juros de mora (a mensagem
pedia menos do que o cliente devia) e não havia piso, então a sobra de centavos de uma parcela já
paga disparava cobrança por R$ 0,13 no WhatsApp.
"""
from services.parcela_service import saldo_devedor_parcela
from services.regua_cobranca_service import DEFAULT_CONFIG


def parcela(principal, juros, pago=0, status="pendente", **extra):
    return {"valor_principal_centavos": principal, "valor_juros_centavos": juros,
            "valor_total_centavos": principal + juros, "valor_pago_centavos": pago,
            "status": status, **extra}


def entra_na_cobranca(parc, config=None):
    """Reproduz a decisão da régua: quanto cobrar e se cobra.

    Espelha as duas linhas de processar_regua (valor devido + piso), que não podem ser chamadas
    isoladas porque a função varre o banco.
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    devido = saldo_devedor_parcela(parc)
    if devido <= 0:
        return False, devido
    minimo = cfg.get("valor_minimo_centavos") or 0
    if (parc.get("valor_pago_centavos") or 0) > 0 and devido < minimo:
        return False, devido
    return True, devido


def test_cobra_o_valor_com_multa_e_mora_nao_so_a_parcela():
    # Parcela de R$ 1.000 em atraso, com R$ 20 de multa e R$ 13,40 de mora.
    p = parcela(90_000, 10_000, 0, "atrasado",
                valor_multa_centavos=2_000, valor_juros_mora_centavos=1_340)
    cobra, devido = entra_na_cobranca(p)
    assert cobra is True
    assert devido == 103_340          # antes era 100_000: pedia R$ 33,40 a menos


def test_sobra_de_centavos_de_quem_ja_pagou_nao_vira_mensagem():
    # Parcela de R$ 500,13 paga com R$ 500,00: faltam 13 centavos.
    p = parcela(40_000, 10_013, 50_000, "parcial")
    cobra, devido = entra_na_cobranca(p)
    assert devido == 13
    assert cobra is False


def test_parcela_pequena_nunca_paga_continua_sendo_cobrada():
    # Juros de um empréstimo aberto de R$ 100 a 3%: R$ 3,00, abaixo do piso de R$ 5,00.
    # Não é sobra de pagamento, é a parcela inteira — tem de ser cobrada.
    p = parcela(0, 300, 0, "pendente")
    cobra, devido = entra_na_cobranca(p)
    assert (cobra, devido) == (True, 300)


def test_sobra_acima_do_piso_e_cobrada():
    p = parcela(40_000, 10_000, 40_000, "parcial")   # faltam R$ 100
    assert entra_na_cobranca(p) == (True, 10_000)


def test_piso_zero_volta_ao_comportamento_antigo():
    p = parcela(40_000, 10_013, 50_000, "parcial")
    assert entra_na_cobranca(p, {"valor_minimo_centavos": 0}) == (True, 13)


def test_parcela_quitada_com_desconto_nao_entra():
    # Quitada ignorando a mora: o perdão zera o saldo, então não há o que cobrar.
    p = parcela(40_000, 10_000, 50_000, "pago", valor_juros_mora_centavos=2_000,
                perdao_encargos_centavos=2_000, valor_perdoado_centavos=2_000)
    cobra, devido = entra_na_cobranca(p)
    assert (cobra, devido) == (False, 0)


def test_parcela_paga_integralmente_nao_entra():
    assert entra_na_cobranca(parcela(40_000, 10_000, 50_000, "pago")) == (False, 0)


def test_piso_padrao_e_cinco_reais():
    assert DEFAULT_CONFIG["valor_minimo_centavos"] == 500
