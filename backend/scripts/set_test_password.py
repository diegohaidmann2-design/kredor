import asyncio
from config import db
from services.auth import hash_senha

EMAIL = "diego.haidmann@gmail.com"
NOVA_SENHA = "Teste@2026"

async def main():
    h = hash_senha(NOVA_SENHA)
    res = await db.usuarios.update_one({"email": EMAIL}, {"$set": {"senha_hash": h}})
    print("matched:", res.matched_count, "modified:", res.modified_count)

if __name__ == "__main__":
    asyncio.run(main())
