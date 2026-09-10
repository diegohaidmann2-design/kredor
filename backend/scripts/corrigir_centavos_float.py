"""Normaliza para int qualquer campo *_centavos com tipo errado (float, string,
etc.) — dado legado anômalo. Dinheiro é sempre int de centavos (regra R1).

A lista de campos vem da união real de todos os documentos da coleção (não de
uma amostra), e a busca cobre todos os tipos != int/long, não só double.
Valores não convertíveis (None, booleano, objeto) são logados e preservados.
Idempotente.

Uso: python scripts/corrigir_centavos_float.py
"""
import asyncio
import os
import sys
from decimal import Decimal, InvalidOperation

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import db  # noqa: E402
from services.logging_service import get_logger  # noqa: E402

logger = get_logger("gestorcred.corrigir_centavos")

COLECOES = ["parcelas", "emprestimos", "pagamentos", "carteira_movimentos", "transacoes_checkout"]


def _para_int_centavos(valor):
    """Converte um valor de centavos anômalo para int. None se não convertível."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float):
        return int(round(valor))
    if isinstance(valor, str):
        try:
            return int(round(float(Decimal(valor))))
        except (InvalidOperation, ValueError, ArithmeticError):
            return None
    return None


async def _campos_centavos(coll: str) -> set:
    """União real de todos os campos *_centavos presentes na coleção."""
    campos = set()
    async for doc in db[coll].find({}, {"_id": 0}):
        campos.update(k for k in doc if k.endswith("_centavos"))
    return campos


async def main():
    total = 0
    for coll in COLECOES:
        campos = await _campos_centavos(coll)
        corrigidos = 0
        for campo in campos:
            cursor = db[coll].find(
                {campo: {"$exists": True, "$not": {"$type": ["int", "long"]}}},
                {"_id": 1, campo: 1},
            )
            async for doc in cursor:
                novo = _para_int_centavos(doc[campo])
                if novo is None:
                    logger.error(
                        "Campo _centavos com valor não convertível",
                        data={"colecao": coll, "_id": str(doc["_id"]),
                              "campo": campo, "valor": repr(doc[campo])},
                    )
                    continue
                await db[coll].update_one({"_id": doc["_id"]}, {"$set": {campo: novo}})
                corrigidos += 1
        total += corrigidos
        print(f"{coll}: {corrigidos} campo(s) corrigido(s)")
    print(f"TOTAL: {total}")


if __name__ == "__main__":
    asyncio.run(main())
