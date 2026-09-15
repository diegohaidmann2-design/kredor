"""Ciclos de cobrança da assinatura: mensal, semestral e anual.

Por que o ciclo NÃO entra no campo `plano` do usuário
-----------------------------------------------------
`usuario.plano` é o NÍVEL (basico/profissional/enterprise) e é a chave de tudo que limita a
conta: PLANOS_PADRAO, os limites de clientes e empréstimos, multi_usuarios, max_membros.
Gravar "profissional_anual" ali quebraria essas buscas em silêncio — a conta perderia os
limites do plano que pagou. Então o ciclo viaja apenas na COMPRA: decide quanto se cobra e
quantos dias de acesso o pagamento concede. Depois de ativado, o que fica no usuário é o
nível e a data de expiração.

Por que "meses cobrados" e não percentual de desconto
-----------------------------------------------------
"Pague 8, use 12" é o que o cliente entende, e os preços saem redondos (12 x 100 x 0,67
daria R$ 804). O desconto é consequência do número de meses, não um percentual solto que
pode acabar desalinhado do preço exibido.
"""
from typing import Optional, Tuple

MENSAL = "mensal"
SEMESTRAL = "semestral"
ANUAL = "anual"

# meses_uso: quanto tempo de acesso o pagamento concede
# meses_cobrados: quantos meses o cliente paga (a diferença é o desconto)
# dias: o que de fato vira data de expiração — 30/mês, e 365 no anual (não 360)
CICLOS = {
    MENSAL: {"meses_uso": 1, "meses_cobrados": 1, "dias": 30,
             "rotulo": "mês", "rotulo_longo": "Mensal"},
    SEMESTRAL: {"meses_uso": 6, "meses_cobrados": 5, "dias": 180,
                "rotulo": "6 meses", "rotulo_longo": "Semestral"},
    ANUAL: {"meses_uso": 12, "meses_cobrados": 8, "dias": 365,
            "rotulo": "ano", "rotulo_longo": "Anual"},
}

ORDEM = [MENSAL, SEMESTRAL, ANUAL]

# Separador do id composto usado só no checkout: "profissional:anual".
SEPARADOR = ":"


def ciclo_valido(ciclo: Optional[str]) -> str:
    """Normaliza o ciclo. Desconhecido cai em mensal — nunca em algo mais barato."""
    c = (ciclo or MENSAL).strip().lower()
    return c if c in CICLOS else MENSAL


def separar_id(plano_id: str) -> Tuple[str, str]:
    """"profissional:anual" -> ("profissional", "anual"). Sem sufixo, é mensal."""
    if not plano_id:
        return "", MENSAL
    if SEPARADOR in plano_id:
        nivel, _, ciclo = plano_id.partition(SEPARADOR)
        return nivel.strip(), ciclo_valido(ciclo)
    return plano_id.strip(), MENSAL


def montar_id(nivel: str, ciclo: str) -> str:
    ciclo = ciclo_valido(ciclo)
    return nivel if ciclo == MENSAL else f"{nivel}{SEPARADOR}{ciclo}"


def dias_do_ciclo(ciclo: Optional[str]) -> int:
    """Dias de acesso que o pagamento concede.

    É o número que vai para `ativar_plano_pago(dias_validade=...)`. Os três caminhos de
    ativação fixavam 30: um cliente do anual pagaria 8 meses e receberia 30 dias.
    """
    return CICLOS[ciclo_valido(ciclo)]["dias"]


def preco_do_ciclo(preco_mensal: float, ciclo: Optional[str]) -> float:
    """Preço total do ciclo, em reais, com 2 casas."""
    c = CICLOS[ciclo_valido(ciclo)]
    return round(float(preco_mensal) * c["meses_cobrados"], 2)


def economia_do_ciclo(preco_mensal: float, ciclo: Optional[str]) -> float:
    """Quanto o cliente deixa de pagar em relação a assinar mês a mês."""
    c = CICLOS[ciclo_valido(ciclo)]
    cheio = round(float(preco_mensal) * c["meses_uso"], 2)
    return round(cheio - preco_do_ciclo(preco_mensal, ciclo), 2)


def desconto_percentual(ciclo: Optional[str]) -> int:
    """Desconto arredondado, para exibir ("33% off"). Consequência dos meses cobrados."""
    c = CICLOS[ciclo_valido(ciclo)]
    if c["meses_uso"] == 0:
        return 0
    return round((1 - c["meses_cobrados"] / c["meses_uso"]) * 100)


def meses_gratis(ciclo: Optional[str]) -> int:
    c = CICLOS[ciclo_valido(ciclo)]
    return c["meses_uso"] - c["meses_cobrados"]


def descrever_ciclos(preco_mensal: float) -> list:
    """Os três ciclos de um nível, já com preço, economia e rótulos para a tela."""
    if not preco_mensal or float(preco_mensal) <= 0:
        return []
    saida = []
    for ciclo in ORDEM:
        c = CICLOS[ciclo]
        total = preco_do_ciclo(preco_mensal, ciclo)
        saida.append({
            "ciclo": ciclo,
            "rotulo": c["rotulo_longo"],
            "meses": c["meses_uso"],
            "dias": c["dias"],
            "preco_total": total,
            # O que o cliente compara: quanto sai por mês neste ciclo.
            "preco_por_mes": round(total / c["meses_uso"], 2),
            "economia": economia_do_ciclo(preco_mensal, ciclo),
            "desconto_percentual": desconto_percentual(ciclo),
            "meses_gratis": meses_gratis(ciclo),
        })
    return saida
