import asyncio, sys
sys.path.insert(0, '.')
from config import db

async def fix():
    # Fix #9: Normalizar 'paga' -> 'pago' em todas as parcelas
    result = await db.parcelas.update_many(
        {"status": "paga"},
        {"$set": {"status": "pago"}}
    )
    print(f"Parcelas normalizadas paga->pago: {result.modified_count}")

    # Remover debug tokens nos logs de verificacao (campo sensivel)
    # Não há nada a migrar no banco para isso

    total_parcelas = await db.parcelas.count_documents({})
    print(f"Total parcelas no banco: {total_parcelas}")

asyncio.run(fix())
