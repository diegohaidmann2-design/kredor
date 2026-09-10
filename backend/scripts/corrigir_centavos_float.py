"""Arredonda para int qualquer campo *_centavos armazenado como float (dado legado anômalo).

Dinheiro é sempre int de centavos (regra R1). Idempotente. Uso:
    python scripts/corrigir_centavos_float.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import db  # noqa: E402

COLECOES = ["parcelas", "emprestimos", "pagamentos", "carteira_movimentos", "transacoes_checkout"]


async def main():
    total = 0
    for coll in COLECOES:
        amostra = await db[coll].find_one()
        if not amostra:
            continue
        campos = [k for k in amostra.keys() if k.endswith("_centavos")]
        corrigidos = 0
        for campo in campos:
            cursor = db[coll].find({campo: {"$type": "double"}}, {"_id": 1, campo: 1})
            async for doc in cursor:
                valor = doc[campo]
                await db[coll].update_one({"_id": doc["_id"]}, {"$set": {campo: int(round(valor))}})
                corrigidos += 1
        total += corrigidos
        print(f"{coll}: {corrigidos} campo(s) corrigido(s)")
    print(f"TOTAL: {total}")


if __name__ == "__main__":
    asyncio.run(main())
