"""E2E: uma conta, um acesso por vez — e o membro da equipe como saída.

Pedido de 14/09/2026. Verifica o ciclo inteiro pela API: dois logins na mesma conta, o primeiro
token deixando de funcionar, o refresh do acesso derrubado sendo recusado, o logout encerrando a
sessão de verdade, e dois membros da equipe usando o sistema ao mesmo tempo.

Não é coletado pelo pytest (não começa com test_). Rodar da raiz do repositório:

    docker run --rm --network kredor_network --env-file backend/.env \\
      -e MONGO_URL='mongodb://kredor_mongodb:27017/kredor_test?replicaSet=rs0' \\
      -e DB_NAME=kredor_test -e PYTHONPATH=/app -e TURNSTILE_SECRET_KEY= \\
      --tmpfs /app/static:mode=1777 \\
      -v "$PWD/backend:/app" -w /app --entrypoint python kredor-backend tests/e2e_sessao_unica.py

TURNSTILE_SECRET_KEY vazio desliga o CAPTCHA da Cloudflare, que o teste não tem como resolver.

Sai com código 1 se qualquer verificação falhar.
"""
import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone

import httpx

from config import db
from main import app
from services.auth import hash_senha

FALHAS = []
SENHA = uuid.uuid4().hex + "aA1!"          # nunca fixa no código (R7)


def conferir(condicao, mensagem):
    print(("  OK    " if condicao else "  FALHA ") + mensagem)
    if not condicao:
        FALHAS.append(mensagem)


async def criar_conta(sufixo, owner_id=None):
    agora = datetime.now(timezone.utc)
    uid = f"e2e-sessao-{sufixo}"
    email = f"{uid}@kredor-e2e.com.br"
    await db.usuarios.insert_one({
        "id": uid, "nome": f"Conta {sufixo}", "email": email, "perfil": "usuario",
        "ativo": True, "email_verificado": True, "plano": "enterprise", "plano_ativo": True,
        "owner_id": owner_id,
        "data_inicio_trial": agora.isoformat(), "data_fim_trial": (agora + timedelta(days=30)).isoformat(),
        "senha_hash": hash_senha(SENHA), "created_at": agora.isoformat(), "two_factor_enabled": False,
    })
    return uid, email


async def logar(c, email):
    r = await c.post("/api/auth/login", json={"email": email, "senha": SENHA})
    assert r.status_code == 200, f"login falhou: {r.status_code} {r.text[:200]}"
    corpo = r.json()
    return corpo["access_token"], corpo.get("refresh_token")


async def quem_sou(c, token):
    return await c.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})


async def cenario(c, uid, email):
    print("\n[1] Primeiro acesso funciona")
    token1, refresh1 = await logar(c, email)
    r = await quem_sou(c, token1)
    conferir(r.status_code == 200, f"/auth/me com o 1º token -> {r.status_code}")

    print("\n[2] Segundo login na mesma conta assume e derruba o primeiro")
    token2, _ = await logar(c, email)
    r1 = await quem_sou(c, token1)
    r2 = await quem_sou(c, token2)
    conferir(r1.status_code == 401, f"1º token deixa de valer -> {r1.status_code}")
    conferir(r2.status_code == 200, f"2º token vale -> {r2.status_code}")
    detalhe = r1.json().get("detail", "") if r1.status_code == 401 else ""
    conferir("outro dispositivo" in detalhe and "Minha Equipe" in detalhe,
             f"mensagem explica e aponta a saída: {detalhe[:80]}...")

    print("\n[3] O refresh do acesso derrubado não ressuscita a sessão")
    r = await c.post("/api/auth/refresh", json={"refresh_token": refresh1})
    conferir(r.status_code == 401, f"refresh do 1º acesso -> {r.status_code}")

    print("\n[4] O refresh do acesso atual continua funcionando")
    token2b, refresh2 = await logar(c, email)
    r = await c.post("/api/auth/refresh", json={"refresh_token": refresh2})
    conferir(r.status_code == 200, f"refresh do acesso atual -> {r.status_code}")
    if r.status_code == 200:
        novo = r.json().get("access_token")
        conferir((await quem_sou(c, novo)).status_code == 200, "token renovado é aceito")

    print("\n[5] Logout encerra a sessão: o token que sobrou no navegador para de valer")
    r = await c.post("/api/auth/logout", headers={"Authorization": f"Bearer {token2b}"})
    conferir(r.status_code == 200, f"logout -> {r.status_code}")
    usuario = await db.usuarios.find_one({"id": uid}, {"_id": 0, "sessao_jti": 1})
    conferir(usuario.get("sessao_jti") is None, f"sessao_jti limpo: {usuario.get('sessao_jti')}")

    print("\n[6] A saída para duas pessoas: membro da equipe tem sessão própria")
    membro_uid, membro_email = await criar_conta(f"membro-{uuid.uuid4().hex[:6]}", owner_id=uid)
    token_dono, _ = await logar(c, email)
    token_membro, _ = await logar(c, membro_email)
    rd = await quem_sou(c, token_dono)
    rm = await quem_sou(c, token_membro)
    conferir(rd.status_code == 200 and rm.status_code == 200,
             f"dono e membro ao mesmo tempo -> dono {rd.status_code}, membro {rm.status_code}")
    return membro_uid


async def main():
    s = uuid.uuid4().hex[:8]
    uid, email = await criar_conta(s)
    membro_uid = None
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://teste") as c:
            membro_uid = await cenario(c, uid, email)
    except Exception as e:  # exceção no meio do cenário também é falha, nunca sucesso silencioso
        conferir(False, f"exceção no cenário: {type(e).__name__}: {e}")
    finally:
        await db.usuarios.delete_many({"id": {"$in": [uid, membro_uid]}})
        await db.login_attempts.delete_many({"email": {"$regex": "^e2e-sessao-"}})


asyncio.run(main())
# O veredito fica fora de main(): nenhum return antecipado pode pular o código de saída.
print(f"\n{'TUDO OK' if not FALHAS else f'{len(FALHAS)} FALHA(S)'}")
sys.exit(1 if FALHAS else 0)
