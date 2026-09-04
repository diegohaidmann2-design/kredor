"""Cria um usuário admin inicial (idempotente)."""
import asyncio, os, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
from services.auth import hash_senha

EMAIL = "diego.haidmann@gmail.com"
SENHA = "Admin@2026"
NOME = "Diego Haidmann"

async def main():
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    db = client[os.environ.get('DB_NAME', 'gestorcred')]
    existing = await db.usuarios.find_one({"email": EMAIL})
    now = datetime.now(timezone.utc)
    doc = {
        "id": str(uuid.uuid4()),
        "nome": NOME,
        "email": EMAIL,
        "perfil": "admin",
        "ativo": True,
        "email_verificado": True,
        "two_factor_enabled": False,
        "plano": "enterprise",
        "plano_ativo": True,
        "data_inicio_trial": now.isoformat(),
        "data_fim_trial": (now + timedelta(days=3650)).isoformat(),
        "data_expiracao_plano": (now + timedelta(days=3650)).isoformat(),
        "onboarding_completed": True,
        "onboarding_tour_finished": True,
        "senha_hash": hash_senha(SENHA),
        "created_at": now.isoformat(),
    }
    if existing:
        await db.usuarios.update_one({"email": EMAIL}, {"$set": {"senha_hash": doc["senha_hash"], "perfil": "admin", "plano": "enterprise", "plano_ativo": True, "email_verificado": True}})
        print("Admin atualizado:", EMAIL)
    else:
        await db.usuarios.insert_one(doc)
        print("Admin criado:", EMAIL)
    client.close()

if __name__ == "__main__":
    asyncio.run(main())
