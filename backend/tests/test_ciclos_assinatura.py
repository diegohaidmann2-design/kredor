"""Ciclos de cobrança: preço do ciclo, dias concedidos e separação nível/ciclo.

O risco que estes testes guardam é de dinheiro. Antes, os três caminhos de ativação fixavam
`dias_validade=30`: um cliente do plano anual pagaria 8 meses e receberia 30 dias de acesso.
E gravar o id composto ("profissional:anual") em `usuario.plano` faria a conta perder os
limites do plano que pagou, porque PLANOS_PADRAO indexa pelo nível.
"""
import pytest

from models.plano import PLANOS_PADRAO
from services.ciclos_assinatura import (
    ANUAL,
    CICLOS,
    MENSAL,
    ORDEM,
    SEMESTRAL,
    ciclo_valido,
    descrever_ciclos,
    desconto_percentual,
    dias_do_ciclo,
    economia_do_ciclo,
    meses_gratis,
    montar_id,
    preco_do_ciclo,
    separar_id,
)


# --- dias concedidos (o ponto do dinheiro) ---------------------------------------------

def test_dias_por_ciclo():
    assert dias_do_ciclo(MENSAL) == 30
    assert dias_do_ciclo(SEMESTRAL) == 180
    assert dias_do_ciclo(ANUAL) == 365, "ano tem 365 dias, não 12 x 30"


def test_ciclo_desconhecido_cai_em_mensal():
    """Nunca conceder mais do que o contratado por causa de um valor inesperado."""
    for entrada in (None, "", "vitalicio", "ANUALX", "30", "trimestral"):
        assert ciclo_valido(entrada) == MENSAL
        assert dias_do_ciclo(entrada) == 30


def test_dias_crescem_com_o_ciclo():
    dias = [dias_do_ciclo(c) for c in ORDEM]
    assert dias == sorted(dias) and len(set(dias)) == 3


# --- preço -----------------------------------------------------------------------------

@pytest.mark.parametrize("mensal,semestral,anual", [
    (100.0, 500.0, 800.0),      # Profissional
    (200.0, 1000.0, 1600.0),    # Enterprise
    (49.99, 249.95, 399.92),    # Básico
])
def test_preco_do_ciclo(mensal, semestral, anual):
    assert preco_do_ciclo(mensal, MENSAL) == mensal
    assert preco_do_ciclo(mensal, SEMESTRAL) == semestral
    assert preco_do_ciclo(mensal, ANUAL) == anual


def test_ciclo_longo_nunca_custa_mais_que_pagar_mes_a_mes():
    """A propaganda promete economia: o total do ciclo tem de ser menor que meses x mensal."""
    for mensal in (19.9, 49.99, 100.0, 200.0, 497.0):
        for ciclo in (SEMESTRAL, ANUAL):
            total = preco_do_ciclo(mensal, ciclo)
            cheio = round(mensal * CICLOS[ciclo]["meses_uso"], 2)
            assert total < cheio, f"{ciclo} de {mensal} custaria {total}, mais que {cheio}"
            assert economia_do_ciclo(mensal, ciclo) > 0


def test_preco_por_mes_cai_conforme_o_ciclo_aumenta():
    ciclos = {c["ciclo"]: c for c in descrever_ciclos(100.0)}
    assert ciclos[MENSAL]["preco_por_mes"] > ciclos[SEMESTRAL]["preco_por_mes"]
    assert ciclos[SEMESTRAL]["preco_por_mes"] > ciclos[ANUAL]["preco_por_mes"]


def test_desconto_e_meses_gratis_batem_com_o_preco():
    assert desconto_percentual(SEMESTRAL) == 17 and meses_gratis(SEMESTRAL) == 1
    assert desconto_percentual(ANUAL) == 33 and meses_gratis(ANUAL) == 4
    # O desconto exibido não pode ser maior que o real, senão a oferta é falsa.
    for ciclo in (SEMESTRAL, ANUAL):
        c = CICLOS[ciclo]
        real = (1 - c["meses_cobrados"] / c["meses_uso"]) * 100
        assert desconto_percentual(ciclo) <= round(real) + 1


def test_trial_nao_tem_ciclo_pago():
    assert descrever_ciclos(0) == []
    assert descrever_ciclos(None) == []


# --- separação nível / ciclo -----------------------------------------------------------

def test_separar_id():
    assert separar_id("profissional:anual") == ("profissional", ANUAL)
    assert separar_id("enterprise:semestral") == ("enterprise", SEMESTRAL)
    assert separar_id("basico") == ("basico", MENSAL)
    assert separar_id("") == ("", MENSAL)
    # sufixo inválido não deve virar um ciclo mais longo
    assert separar_id("profissional:vitalicio") == ("profissional", MENSAL)


def test_montar_id_nao_suja_o_mensal():
    """Mensal mantém o id puro: é o que a tela já consome e o que vai para usuario.plano."""
    assert montar_id("profissional", MENSAL) == "profissional"
    assert montar_id("profissional", ANUAL) == "profissional:anual"


def test_ida_e_volta():
    for nivel in ("basico", "profissional", "enterprise"):
        for ciclo in ORDEM:
            assert separar_id(montar_id(nivel, ciclo)) == (nivel, ciclo)


def test_nivel_separado_continua_existindo_em_PLANOS_PADRAO():
    """É a razão de o ciclo não entrar em usuario.plano: os limites indexam pelo nível."""
    for nivel in ("basico", "profissional", "enterprise"):
        composto = montar_id(nivel, ANUAL)
        assert composto not in PLANOS_PADRAO, "id composto não é um plano"
        assert separar_id(composto)[0] in PLANOS_PADRAO, (
            "o nível extraído tem de existir em PLANOS_PADRAO, senão a conta perde os limites"
        )
