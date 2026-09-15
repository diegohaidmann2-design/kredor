"""E2E: perfil do usuário — atualização do nome e o vínculo de equipe.

Pedido de 15/09/2026 ("veja se a página de perfil está completa"). A tela tinha "Editar
Perfil" e "Salvar" desde sempre com o handler vazio e SEM rota no backend: o nome digitado
sumia na frente do usuário, sem erro nenhum.

Cobre:
  * PUT /auth/me grava o nome e o GET seguinte já responde com ele
  * nome vazio, curto demais e longo demais são recusados
  * espaço nas pontas é aparado
  * salvar o mesmo nome não gera registro de auditoria falso
  * a troca de nome fica auditada
  * email e cargo NÃO são alteráveis por aqui (campo a mais é ignorado)
  * membro de equipe também edita o próprio nome (a rota é livre)
  * /auth/permissoes entrega cargo e rótulos para o membro descobrir o que pode fazer

Não é coletado pelo pytest (não começa com test_). Rodar da raiz do repositório:

    docker run --rm --network kredor_network --env-file backend/.env \\
      -e MONGO_URL='mongodb://kredor_mongodb:27017/kredor_test?replicaSet=rs0' \\
      -e DB_NAME=kredor_test -e PYTHONPATH=/app -e TURNSTILE_SECRET_KEY= \\
      --tmpfs /app/static:mode=1777 \\
      -v "$PWD/backend:/app" -w /app --entrypoint python kredor-backend tests/e2e_perfil.py

Sai com código 1 se qualquer verificação falhar.
"""
import asyncio
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone

import httpx

from config import db
from main import app
from services.auth import hash_senha

FALHAS = []
SENHA = uuid.uuid4().hex[:10] + "aA1x"          # nunca fixa no código (R7)
PREFIXO = f"e2e-perfil-{uuid.uuid4().hex[:6]}"


def conferir(condicao, mensagem):
    print(("  OK    " if condicao else "  FALHA ") + mensagem)
    if not condicao:
        FALHAS.append(mensagem)


def titulo(texto):
    print(f"\n=== {texto} ===")


async def _ip_aleatorio(request):
    """Um IP diferente por requisição: o RateLimitMiddleware conta por IP e este roteiro faz
    muitas chamadas em segundos — o limitador não é o que está sendo verificado aqui."""
    request.headers["X-Forwarded-For"] = ".".join(str(random.randint(11, 250)) for _ in range(4))


async def criar_usuario(sufixo, owner_id=None, cargo=None, permissoes=None):
    agora = datetime.now(timezone.utc)
    uid = f"{PREFIXO}-{sufixo}"
    email = f"{uid}@kredor-e2e.com.br"
    await db.usuarios.insert_one({
        "id": uid, "nome": f"Nome Original {sufixo}", "email": email, "perfil": "usuario",
        "ativo": True, "email_verificado": True, "plano": "enterprise" if not owner_id else "equipe",
        "plano_ativo": True, "owner_id": owner_id, "cargo": cargo,
        "permissoes": permissoes or [],
        "data_inicio_trial": agora.isoformat(),
        "data_fim_trial": (agora + timedelta(days=30)).isoformat(),
        "data_vencimento_assinatura": (agora + timedelta(days=30)).isoformat(),
        "senha_hash": hash_senha(SENHA), "created_at": agora.isoformat(),
        "two_factor_enabled": False,
    })
    return uid, email


async def logar(c, email):
    r = await c.post("/api/auth/login", json={"email": email, "senha": SENHA})
    assert r.status_code == 200, f"login de {email} falhou: {r.status_code} {r.text[:300]}"
    return r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


async def limpar():
    await db.usuarios.delete_many({"id": {"$regex": f"^{PREFIXO}"}})
    await db.auditoria.delete_many({"usuario_id": {"$regex": f"^{PREFIXO}"}})
    await db.rate_limits.delete_many({})


async def main():
    await limpar()
    dono_id, dono_email = await criar_usuario("dono")
    membro_id, membro_email = await criar_usuario(
        "membro", owner_id=dono_id, cargo="Vendedor",
        permissoes=["ver_clientes", "gerir_clientes"],
    )

    transporte = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transporte, base_url="http://teste",
        event_hooks={"request": [_ip_aleatorio]},
    ) as c:
        tk = await logar(c, dono_email)

        # ---------------------------------------------------------------------------
        titulo("salvar o nome de verdade")

        r = await c.put("/api/auth/me", headers=auth(tk), json={"nome": "Diego Haidmann"})
        conferir(r.status_code == 200, f"PUT /auth/me (got {r.status_code} {r.text[:200]})")
        conferir(r.json().get("nome") == "Diego Haidmann",
                 f"resposta já traz o nome novo: {r.json().get('nome')}")

        r = await c.get("/api/auth/me", headers=auth(tk))
        conferir(r.json().get("nome") == "Diego Haidmann",
                 f"GET seguinte confirma no banco: {r.json().get('nome')}")

        doc = await db.usuarios.find_one({"id": dono_id})
        conferir(doc["nome"] == "Diego Haidmann", "gravou no documento")

        # ---------------------------------------------------------------------------
        titulo("o que não pode passar")

        for nome, rotulo in [("", "vazio"), (" ", "só espaço"), ("A", "1 caractere")]:
            r = await c.put("/api/auth/me", headers=auth(tk), json={"nome": nome})
            conferir(r.status_code == 422, f"nome {rotulo} recusado (got {r.status_code})")

        r = await c.put("/api/auth/me", headers=auth(tk), json={"nome": "x" * 121})
        conferir(r.status_code == 422, f"nome de 121 caracteres recusado (got {r.status_code})")

        r = await c.put("/api/auth/me", headers=auth(tk), json={"nome": "  Diego  Haidmann  "})
        conferir(r.status_code == 200 and r.json()["nome"] == "Diego  Haidmann",
                 f"espaço nas pontas aparado: {r.json().get('nome')!r}")

        # ---------------------------------------------------------------------------
        titulo("email e cargo não saem por esta porta")

        r = await c.put("/api/auth/me", headers=auth(tk), json={
            "nome": "Diego H", "email": "outro@dominio.com", "cargo": "CEO",
            "perfil": "admin", "plano": "enterprise", "permissoes": ["gerir_equipe"],
        })
        conferir(r.status_code == 200, f"campos a mais não quebram (got {r.status_code})")
        doc = await db.usuarios.find_one({"id": dono_id})
        conferir(doc["email"] == dono_email, f"email intacto: {doc['email']}")
        conferir(doc.get("cargo") is None, f"cargo intacto: {doc.get('cargo')}")
        conferir(doc["perfil"] == "usuario", f"perfil intacto: {doc['perfil']}")
        conferir(doc.get("permissoes") == [], f"permissões intactas: {doc.get('permissoes')}")

        # ---------------------------------------------------------------------------
        titulo("auditoria")

        logs = await db.auditoria.find({"entidade": "perfil", "entidade_id": dono_id}).to_list(50)
        conferir(len(logs) >= 1, f"troca de nome auditada ({len(logs)} registro(s))")
        conferir(any("Diego Haidmann" in (l.get("detalhes") or "") for l in logs),
                 "o registro diz o nome anterior e o novo")

        antes = len(logs)
        r = await c.put("/api/auth/me", headers=auth(tk), json={"nome": "Diego H"})
        conferir(r.status_code == 200, f"salvar o mesmo nome (got {r.status_code})")
        logs = await db.auditoria.find({"entidade": "perfil", "entidade_id": dono_id}).to_list(50)
        conferir(len(logs) == antes, "salvar sem mudar nada não gera registro falso")

        # ---------------------------------------------------------------------------
        titulo("membro de equipe também edita o próprio nome")

        tk_m = await logar(c, membro_email)
        r = await c.put("/api/auth/me", headers=auth(tk_m), json={"nome": "Kilce Ferreira"})
        conferir(r.status_code == 200, f"membro salva o nome (got {r.status_code} {r.text[:160]})")
        doc_m = await db.usuarios.find_one({"id": membro_id})
        conferir(doc_m["nome"] == "Kilce Ferreira", "nome do membro gravado")
        conferir(doc_m.get("cargo") == "Vendedor", "cargo do membro segue sendo do dono")

        # ---------------------------------------------------------------------------
        titulo("o membro descobre o que pode fazer")

        r = await c.get("/api/auth/permissoes", headers=auth(tk_m))
        conferir(r.status_code == 200, f"GET /auth/permissoes (got {r.status_code})")
        equipe = r.json().get("equipe") or {}
        conferir(equipe.get("e_membro") is True, f"marca que é membro: {equipe.get('e_membro')}")
        conferir(equipe.get("cargo") == "Vendedor", f"cargo: {equipe.get('cargo')}")
        rotulos = [p.get("label") for p in equipe.get("permissoes") or []]
        conferir(len(rotulos) == 2, f"duas permissões: {rotulos}")
        conferir(all(r_ and not r_.startswith("ver_") and not r_.startswith("gerir_")
                     for r_ in rotulos),
                 f"rótulos vêm legíveis, não o id cru: {rotulos}")

        r = await c.get("/api/auth/permissoes", headers=auth(tk))
        equipe_dono = r.json().get("equipe") or {}
        conferir(equipe_dono.get("e_membro") is False,
                 f"dono não é membro: {equipe_dono.get('e_membro')}")
        conferir(equipe_dono.get("permissoes") == [],
                 f"dono não tem lista de permissões concedidas: {equipe_dono.get('permissoes')}")

    await limpar()

    print("\n" + ("=" * 70))
    if FALHAS:
        print(f"{len(FALHAS)} FALHA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        sys.exit(1)
    print("TUDO OK")


if __name__ == "__main__":
    asyncio.run(main())
