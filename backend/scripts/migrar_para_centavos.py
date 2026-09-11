"""
Migra campos monetários de reais (float) para centavos inteiros (`*_centavos`).

A lógica fica em `services/migracao_centavos.py` — a mesma conversão roda sozinha ao fim de toda
restauração de backup. Este script serve para rodar à mão num banco que já está no ar.

Idempotente: documentos que já possuem o campo novo são ignorados. Faça `mongodump` antes de
rodar em produção.

Uso: python scripts/migrar_para_centavos.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import db  # noqa: E402
from services.migracao_centavos import _converter, _montar_update, migrar_dados_em_reais  # noqa: E402,F401


async def main():
    print(f"Banco: {db.name}")
    for colecao, migrados in (await migrar_dados_em_reais()).items():
        print(f"{colecao:<22} documentos migrados: {migrados}")


if __name__ == "__main__":
    asyncio.run(main())
