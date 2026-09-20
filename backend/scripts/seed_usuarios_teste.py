"""Cria usuarios de teste, um por plano (idempotente por email).

Uso:
    python scripts/seed_usuarios_teste.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime, timezone, timedelta

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from services.auth import hash_senha

SENHA = "Kredor@2026"

USERS = [
    {"nome": "Teste Trial", "email": "trial@kredorteste.com", "plano": "trial"},
    {"nome": "Teste Basico", "email": "basico@kredorteste.com", "plano": "basico"},
    {"nome": "Teste Pro", "email": "pro@kredorteste.com", "plano": "profissional"},
]


async def main():
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ.get("DB_NAME", "gestorcred")
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    fim_trial_iso = (now + timedelta(days=7)).isoformat()
    exp_plano_iso = (now + timedelta(days=30)).isoformat()
    criados = atualizados = 0
    for u in USERS:
        import uuid
        doc = {
            "nome": u["nome"],
            "email": u["email"],
            "senha_hash": hash_senha(SENHA),
            "perfil": "usuario",
            "ativo": True,
            "owner_id": None,
            "permissoes": [],
            "email_verificado": True,
            "two_factor_enabled": False,
            "plano": u["plano"],
            "plano_ativo": True,
            "plano_ilimitado": False,
            "data_inicio_trial": now_iso,
            "data_fim_trial": fim_trial_iso,
            "data_expiracao_plano": exp_plano_iso if u["plano"] != "trial" else None,
            "onboarding_completed": True,
            "onboarding_tour_finished": True,
        }
        existing = await db.usuarios.find_one({"email": u["email"]})
        if existing:
            await db.usuarios.update_one({"email": u["email"]}, {"$set": doc})
            atualizados += 1
            print(f"atualizado: {u['email']} ({u['plano']})")
        else:
            doc["id"] = str(uuid.uuid4())
            doc["created_at"] = now_iso
            await db.usuarios.insert_one(doc)
            criados += 1
            print(f"criado: {u['email']} ({u['plano']})")

    total = await db.usuarios.count_documents({})
    print(f"\nResumo: {criados} criados, {atualizados} atualizados. Total usuarios: {total}")
    print(f"Senha de todos: {SENHA}")


if __name__ == "__main__":
    asyncio.run(main())
