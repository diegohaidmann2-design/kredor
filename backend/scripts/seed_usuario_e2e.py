"""Cria/atualiza um usuário de teste E2E (idempotente) reutilizando o hash da app.

Uso: python scripts/seed_usuario_e2e.py
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import db  # noqa: E402
from services.auth import hash_senha  # noqa: E402

EMAIL = "e2e@gestorcred.com.br"
SENHA = "E2eTest@2026"


async def main():
    agora = datetime.now(timezone.utc)
    doc = {
        "nome": "E2E Tester",
        "email": EMAIL,
        "perfil": "admin",
        "ativo": True,
        "plano": "enterprise",
        "plano_ativo": True,
        "email_verificado": True,
        "onboarding_completed": True,
        "onboarding_tour_finished": True,
        "senha_hash": hash_senha(SENHA),
        "data_inicio_trial": agora.isoformat(),
        "data_fim_trial": (agora + timedelta(days=3650)).isoformat(),
    }
    existente = await db.usuarios.find_one({"email": EMAIL})
    if existente:
        await db.usuarios.update_one({"email": EMAIL}, {"$set": doc})
        print(f"Usuário E2E atualizado: {EMAIL} (id={existente.get('id')})")
    else:
        doc["id"] = str(uuid.uuid4())
        doc["created_at"] = agora.isoformat()
        await db.usuarios.insert_one(doc)
        print(f"Usuário E2E criado: {EMAIL} (id={doc['id']})")
    print(f"Senha: {SENHA}")


if __name__ == "__main__":
    asyncio.run(main())
