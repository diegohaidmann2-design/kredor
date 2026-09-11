"""
Converte campos monetários de reais (float) para centavos inteiros (`*_centavos`).

Roda em dois lugares: `scripts/migrar_para_centavos.py` (manual) e, automaticamente, ao fim de
toda restauração de backup (`services/backup_service.py`). Backup gerado antes da Fase 1 traz o
dinheiro em reais, e o código atual só lê os campos em centavos — sem converter, o painel mostra
R$ 0,00 em tudo.

Idempotente: documentos que já possuem o campo novo são ignorados. Escreve em
lotes de 1000 com bulk_write.

Valores legados não convertíveis (None, string vazia, booleano, objeto) NÃO são
gravados no campo `_centavos` — são apenas logados como erro e o campo legado é
preservado. Nunca grava lixo num campo que deve ser inteiro.

Carteiras, consultas, assinaturas e checkout não entram: o código dessas coleções lê os valores
em reais (`saldo`, `valor`).
"""
from decimal import InvalidOperation
from typing import Dict

from pymongo import UpdateOne

from config import db
from services.logging_service import get_logger
from utils.dinheiro import reais_para_centavos

logger = get_logger("gestorcred.migracao_centavos")

CAMPOS = {
    "emprestimos": ["valor_principal", "valor_total_com_juros", "valor_total_juros"],
    "parcelas": ["valor_principal", "valor_juros", "valor_total", "valor_pago",
                 "valor_multa", "valor_juros_mora", "saldo_devedor"],
    "pagamentos": ["valor_pago", "valor_emprestimo", "valor_incorporado",
                   "principal_anterior", "principal_apos"],
    "carteira_movimentos": [],
    "transacoes_checkout": [],
}
CAMPOS_HISTORICO_PRORROGACAO = ["saldo_reamortizado", "novo_valor_total", "valor_parcela", "juros_periodo"]
LEGADO_REMOVER = {"parcelas": ["valor_parcela"]}
LOTE = 1000


def _converter(valor):
    """Converte um valor legado (reais) em centavos inteiros.

    Aceita int, float e string numérica (via Decimal, para não perder centavo).
    Retorna None para qualquer coisa não convertível (bool, None, '', objeto);
    o chamador decide o que fazer — nunca grava o valor cru.
    """
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return reais_para_centavos(valor)
    if isinstance(valor, str):
        try:
            return reais_para_centavos(valor)
        except (InvalidOperation, ValueError, ArithmeticError):
            return None
    return None


def _montar_update(doc: dict, campos: list, colecao: str):
    set_, unset = {}, {}
    for campo in campos:
        if f"{campo}_centavos" in doc:
            continue
        if campo in doc:
            convertido = _converter(doc[campo])
            if convertido is None:
                logger.error(
                    "Valor legado não convertível em centavos",
                    data={"colecao": colecao, "_id": str(doc["_id"]), "campo": campo,
                          "valor": repr(doc[campo]), "tipo": type(doc[campo]).__name__},
                )
                continue
            set_[f"{campo}_centavos"] = convertido
            unset[campo] = ""
    for campo in LEGADO_REMOVER.get(colecao, []):
        if campo in doc:
            unset[campo] = ""
    if colecao == "emprestimos" and isinstance(doc.get("historico_prorrogacoes"), list):
        historico = []
        alterado = False
        for item in doc["historico_prorrogacoes"]:
            item = dict(item)
            for campo in CAMPOS_HISTORICO_PRORROGACAO:
                if campo in item and f"{campo}_centavos" not in item:
                    convertido = _converter(item.get(campo))
                    if convertido is None:
                        logger.error(
                            "Valor legado não convertível em centavos (histórico)",
                            data={"colecao": colecao, "_id": str(doc["_id"]),
                                  "campo": campo, "valor": repr(item.get(campo))},
                        )
                        continue
                    item.pop(campo, None)
                    item[f"{campo}_centavos"] = convertido
                    alterado = True
            historico.append(item)
        if alterado:
            set_["historico_prorrogacoes"] = historico
    if not set_ and not unset:
        return None
    update = {}
    if set_:
        update["$set"] = set_
    if unset:
        update["$unset"] = unset
    return UpdateOne({"_id": doc["_id"]}, update)


async def migrar_colecao(colecao: str, campos: list) -> int:
    migrados = 0
    lote = []
    async for doc in db[colecao].find({}):
        op = _montar_update(doc, campos, colecao)
        if op is None:
            continue
        lote.append(op)
        if len(lote) >= LOTE:
            resultado = await db[colecao].bulk_write(lote, ordered=False)
            migrados += resultado.modified_count
            lote = []
    if lote:
        resultado = await db[colecao].bulk_write(lote, ordered=False)
        migrados += resultado.modified_count
    return migrados


async def migrar_dados_em_reais() -> Dict[str, int]:
    """Converte todas as coleções de CAMPOS. Retorna {coleção: documentos alterados}."""
    return {colecao: await migrar_colecao(colecao, campos) for colecao, campos in CAMPOS.items()}
