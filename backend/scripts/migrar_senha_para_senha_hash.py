"""
Migração idempotente: padroniza o campo de credencial em `senha_hash`.

- documento com `senha` e sem `senha_hash`  -> $rename senha -> senha_hash
- documento com os dois campos             -> mantém senha_hash, $unset senha (warning)
- documento só com senha_hash              -> nada a fazer

Uso: python -m scripts.migrar_senha_para_senha_hash
"""
import asyncio

from config import db
from services.logging_service import get_logger

logger = get_logger("gestorcred.migracao_senha")


async def migrar() -> dict:
    renomeados = 0
    duplicados = 0

    # Caso 1: só `senha` (legado) -> renomear para senha_hash
    cursor = db.usuarios.find(
        {"senha": {"$exists": True}, "senha_hash": {"$exists": False}}, {"_id": 1}
    )
    async for doc in cursor:
        await db.usuarios.update_one({"_id": doc["_id"]}, {"$rename": {"senha": "senha_hash"}})
        renomeados += 1

    # Caso 2: os dois campos coexistem -> manter senha_hash, remover senha
    cursor = db.usuarios.find(
        {"senha": {"$exists": True}, "senha_hash": {"$exists": True}}, {"_id": 1}
    )
    async for doc in cursor:
        await db.usuarios.update_one({"_id": doc["_id"]}, {"$unset": {"senha": ""}})
        duplicados += 1
        logger.warning("Usuário tinha senha e senha_hash — removido campo legado", data={"_id": str(doc["_id"])})

    resultado = {"renomeados": renomeados, "duplicados_limpos": duplicados}
    logger.info("Migração de senha concluída", data=resultado)
    print(resultado)
    return resultado


if __name__ == "__main__":
    asyncio.run(migrar())
