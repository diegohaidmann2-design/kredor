"""E2E: cadastro de membro, permissões aplicadas de verdade e ciclo de vida do acesso.

Pedido de 14/09/2026 ("veja se em /equipe ao cadastrar um membro está padrão, ou se tem bug
ou vulnerabilidades"). Cobre, pela API real:

  * membro criado com senha fraca é recusado, e o email duplicado em outra caixa alta também
  * a listagem não devolve senha_hash, token de convite nem sessao_jti
  * membro sem permissão nenhuma não alcança cliente, empréstimo, dashboard nem consulta
  * permissão concedida abre exatamente o que promete, e nada além
  * área do dono (pagamentos, configuração, carteira) fica fechada mesmo com tudo marcado
  * quem tem "gerir equipe" não promove ninguém acima de si nem a si mesmo
  * convite expirado é recusado, reenvio invalida o token anterior
  * desativar corta o acesso na requisição seguinte; reativar devolve
  * a assinatura que o membro vê é a do dono, não um "inativo" fantasma

Não é coletado pelo pytest (não começa com test_). Rodar da raiz do repositório:

    docker run --rm --network kredor_network --env-file backend/.env \\
      -e MONGO_URL='mongodb://kredor_mongodb:27017/kredor_test?replicaSet=rs0' \\
      -e DB_NAME=kredor_test -e PYTHONPATH=/app -e TURNSTILE_SECRET_KEY= \\
      --tmpfs /app/static:mode=1777 \\
      -v "$PWD/backend:/app" -w /app --entrypoint python kredor-backend tests/e2e_equipe.py

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
from services.permissoes_equipe import (
    GERIR_CLIENTES,
    GERIR_EQUIPE,
    USAR_CONSULTAS,
    VER_CLIENTES,
    VER_EMPRESTIMOS,
    VER_FINANCEIRO,
)

FALHAS = []
SENHA = uuid.uuid4().hex[:10] + "aA1x"      # nunca fixa no código (R7)
PREFIXO = f"e2e-equipe-{uuid.uuid4().hex[:6]}"


def conferir(condicao, mensagem):
    print(("  OK    " if condicao else "  FALHA ") + mensagem)
    if not condicao:
        FALHAS.append(mensagem)


def titulo(texto):
    print(f"\n=== {texto} ===")


async def criar_dono(plano="enterprise"):
    agora = datetime.now(timezone.utc)
    uid = f"{PREFIXO}-dono"
    email = f"{uid}@kredor-e2e.com.br"
    await db.usuarios.insert_one({
        "id": uid, "nome": "Dona da Conta", "email": email, "perfil": "usuario",
        "ativo": True, "email_verificado": True, "plano": plano, "plano_ativo": True,
        "owner_id": None, "permissoes": [],
        "data_inicio_trial": agora.isoformat(),
        "data_fim_trial": (agora + timedelta(days=30)).isoformat(),
        "data_vencimento_assinatura": (agora + timedelta(days=30)).isoformat(),
        "senha_hash": hash_senha(SENHA), "created_at": agora.isoformat(),
        "two_factor_enabled": False,
    })
    return uid, email


async def logar(c, email, senha=SENHA):
    r = await c.post("/api/auth/login", json={"email": email, "senha": senha})
    assert r.status_code == 200, f"login de {email} falhou: {r.status_code} {r.text[:300]}"
    return r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


async def _ip_aleatorio(request):
    """Um IP diferente por requisição.

    O RateLimitMiddleware conta por IP (200 req/min, 50 nas rotas de auth) e este roteiro
    faz mais de uma centena de chamadas em segundos. Sem isto, o teste esbarra no limitador
    — que não é o que ele está verificando.
    """
    request.headers["X-Forwarded-For"] = ".".join(str(random.randint(11, 250)) for _ in range(4))


async def limpar():
    await db.usuarios.delete_many({"id": {"$regex": f"^{PREFIXO}"}})
    await db.usuarios.delete_many({"owner_id": {"$regex": f"^{PREFIXO}"}})
    await db.auditoria.delete_many({"usuario_id": {"$regex": f"^{PREFIXO}"}})
    await db.clientes.delete_many({"usuario_id": {"$regex": f"^{PREFIXO}"}})
    await db.rate_limits.delete_many({})


async def main():
    await limpar()
    dono_id, dono_email = await criar_dono()

    transporte = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transporte, base_url="http://teste",
        event_hooks={"request": [_ip_aleatorio]},
    ) as c:
        tk_dono = await logar(c, dono_email)

        # ---------------------------------------------------------------------------
        titulo("cadastro do membro: as validações que não existiam")

        r = await c.post("/api/equipe/convidar", headers=auth(tk_dono), json={
            "nome": "Fraco", "email": f"{PREFIXO}-fraco@kredor-e2e.com.br", "senha": "123",
        })
        conferir(r.status_code == 422, f"senha de 3 caracteres recusada (got {r.status_code})")

        r = await c.post("/api/equipe/convidar", headers=auth(tk_dono), json={
            "nome": "Obvia", "email": f"{PREFIXO}-obvia@kredor-e2e.com.br", "senha": "senha123",
        })
        conferir(r.status_code == 422, f"senha óbvia recusada (got {r.status_code})")

        r = await c.post("/api/equipe/convidar", headers=auth(tk_dono), json={
            "nome": "Permissao Falsa", "email": f"{PREFIXO}-pf@kredor-e2e.com.br",
            "senha": SENHA, "permissoes": ["ver_clientes", "inventada", "admin"],
        })
        conferir(r.status_code == 200, f"membro criado (got {r.status_code} {r.text[:200]})")
        id_pf = r.json().get("id")
        doc_pf = await db.usuarios.find_one({"id": id_pf})
        conferir((doc_pf or {}).get("permissoes") == ["ver_clientes"],
                 f"permissão inexistente descartada: {(doc_pf or {}).get('permissoes')}")

        r = await c.post("/api/equipe/convidar", headers=auth(tk_dono), json={
            "nome": "Duplicada", "email": f"{PREFIXO}-PF@Kredor-E2E.com.BR", "senha": SENHA,
        })
        conferir(r.status_code == 400,
                 f"email duplicado em outra caixa alta recusado (got {r.status_code})")

        # ---------------------------------------------------------------------------
        titulo("listagem: nada de sensível na resposta")

        r = await c.get("/api/equipe", headers=auth(tk_dono))
        conferir(r.status_code == 200, f"GET /equipe (got {r.status_code})")
        corpo = r.json()
        bruto = r.text
        for campo in ("senha_hash", "email_verification_token", "sessao_jti", "sessao_ip"):
            conferir(campo not in bruto, f"a resposta não contém {campo}")
        conferir(corpo["limites"]["total"] == -1 and corpo["limites"]["ilimitado"],
                 f"limite real do plano enterprise: {corpo['limites']}")
        conferir(len(corpo.get("permissoes_disponiveis") or []) == 7,
                 "a lista de permissões vem do servidor (7 itens)")

        # ---------------------------------------------------------------------------
        titulo("membro SEM permissão: o furo principal")

        membro_email = f"{PREFIXO}-m0@kredor-e2e.com.br"
        r = await c.post("/api/equipe/convidar", headers=auth(tk_dono), json={
            "nome": "Sem Permissao", "email": membro_email, "senha": SENHA, "permissoes": [],
        })
        id_m0 = r.json()["id"]
        tk_m0 = await logar(c, membro_email)

        for caminho, metodo in [
            ("/api/clientes", "get"), ("/api/clientes", "post"),
            ("/api/emprestimos", "get"), ("/api/emprestimos", "post"),
            ("/api/dashboard", "get"), ("/api/relatorios/gerar", "post"),
            ("/api/consultas/historico", "get"), ("/api/analise/dashboard", "get"),
            ("/api/carteira/", "get"), ("/api/assistente/historico", "get"),
            ("/api/equipe", "get"),
        ]:
            r = await getattr(c, metodo)(caminho, headers=auth(tk_m0),
                                         **({"json": {}} if metodo == "post" else {}))
            conferir(r.status_code == 403, f"{metodo.upper()} {caminho} barrado (got {r.status_code})")

        titulo("membro SEM permissão: o que a tela precisa continua aberto")
        for caminho in ("/api/auth/me", "/api/auth/permissoes", "/api/notificacoes",
                        "/api/notificacoes/contagem", "/api/assinaturas/status",
                        "/api/onboarding/status"):
            r = await c.get(caminho, headers=auth(tk_m0))
            conferir(r.status_code == 200, f"GET {caminho} liberado (got {r.status_code})")

        r = await c.get("/api/assinaturas/status", headers=auth(tk_m0))
        status = r.json()
        conferir(status.get("status") != "inativo",
                 f"membro vê a assinatura do dono, não 'inativo': {status.get('status')}")
        conferir(status.get("membro_equipe") is True, "resposta marca que é membro de equipe")

        # ---------------------------------------------------------------------------
        titulo("permissão concedida abre exatamente o que promete")

        r = await c.put(f"/api/equipe/{id_m0}/permissoes", headers=auth(tk_dono),
                        json={"permissoes": [VER_CLIENTES]})
        conferir(r.status_code == 200, f"PUT permissões (got {r.status_code} {r.text[:200]})")

        r = await c.get("/api/clientes", headers=auth(tk_m0))
        conferir(r.status_code == 200, f"com ver_clientes, GET /clientes (got {r.status_code})")
        r = await c.post("/api/clientes", headers=auth(tk_m0), json={"nome": "X", "cpf_cnpj": "1"})
        conferir(r.status_code == 403, f"com ver_clientes, POST /clientes barrado (got {r.status_code})")

        r = await c.put(f"/api/equipe/{id_m0}/permissoes", headers=auth(tk_dono),
                        json={"permissoes": [GERIR_CLIENTES]})
        r = await c.get("/api/clientes", headers=auth(tk_m0))
        conferir(r.status_code == 200, f"gerir_clientes implica ver_clientes (got {r.status_code})")

        # ---------------------------------------------------------------------------
        titulo("área do dono continua do dono, mesmo com tudo marcado")

        todas = [VER_CLIENTES, GERIR_CLIENTES, VER_EMPRESTIMOS, "gerir_emprestimos",
                 VER_FINANCEIRO, USAR_CONSULTAS]
        await c.put(f"/api/equipe/{id_m0}/permissoes", headers=auth(tk_dono),
                    json={"permissoes": todas})

        for caminho, metodo in [
            ("/api/pagamentos", "get"), ("/api/pagamentos", "post"),
            ("/api/configuracoes/notificacoes", "get"),
            ("/api/whatsapp/regua/config", "get"),
            ("/api/whatsapp/conexoes", "get"),
            ("/api/exportacao/resumo", "get"),
            ("/api/auditoria", "get"),
            ("/api/carteira/recarga/asaas", "post"),
            ("/api/superadmin/dashboard", "get"),
            ("/api/equipe", "get"),
        ]:
            r = await getattr(c, metodo)(caminho, headers=auth(tk_m0),
                                         **({"json": {}} if metodo == "post" else {}))
            conferir(r.status_code == 403, f"{metodo.upper()} {caminho} é do dono (got {r.status_code})")

        r = await c.get("/api/dashboard", headers=auth(tk_m0))
        conferir(r.status_code == 200, f"ver_financeiro abre o dashboard (got {r.status_code})")

        # ---------------------------------------------------------------------------
        titulo("as telas que o membro abre respondem de verdade")

        # Agenda de Cobrança e Cadastros & Aprovações tinham redirect próprio mandando todo
        # membro para o dashboard, o que contradizia as permissões que o dono concedeu.
        await c.put(f"/api/equipe/{id_m0}/permissoes", headers=auth(tk_dono),
                    json={"permissoes": [VER_EMPRESTIMOS]})
        r = await c.get("/api/parcelas/pendentes", headers=auth(tk_m0))
        conferir(r.status_code == 200, f"agenda (parcelas/pendentes) com ver_emprestimos (got {r.status_code})")
        r = await c.get("/api/cadastro-publico/solicitacoes", headers=auth(tk_m0))
        conferir(r.status_code == 403, f"aprovações barradas sem gerir_clientes (got {r.status_code})")

        await c.put(f"/api/equipe/{id_m0}/permissoes", headers=auth(tk_dono),
                    json={"permissoes": [GERIR_CLIENTES]})
        r = await c.get("/api/cadastro-publico/solicitacoes", headers=auth(tk_m0))
        conferir(r.status_code == 200, f"aprovações com gerir_clientes (got {r.status_code})")

        # ---------------------------------------------------------------------------
        titulo("gerir equipe sem escalação de privilégio")

        gerente_email = f"{PREFIXO}-gerente@kredor-e2e.com.br"
        r = await c.post("/api/equipe/convidar", headers=auth(tk_dono), json={
            "nome": "Gerente", "email": gerente_email, "senha": SENHA,
            "permissoes": [GERIR_EQUIPE, VER_CLIENTES],
        })
        id_gerente = r.json()["id"]
        tk_gerente = await logar(c, gerente_email)

        r = await c.get("/api/equipe", headers=auth(tk_gerente))
        conferir(r.status_code == 200, f"gerente vê a equipe (got {r.status_code})")

        r = await c.post("/api/equipe/convidar", headers=auth(tk_gerente), json={
            "nome": "Clone", "email": f"{PREFIXO}-clone@kredor-e2e.com.br", "senha": SENHA,
            "permissoes": [GERIR_EQUIPE],
        })
        conferir(r.status_code == 403, f"gerente não delega gerir_equipe (got {r.status_code})")

        r = await c.post("/api/equipe/convidar", headers=auth(tk_gerente), json={
            "nome": "Turbo", "email": f"{PREFIXO}-turbo@kredor-e2e.com.br", "senha": SENHA,
            "permissoes": [VER_FINANCEIRO],
        })
        conferir(r.status_code == 403,
                 f"gerente não concede o que ele não tem (got {r.status_code})")

        r = await c.post("/api/equipe/convidar", headers=auth(tk_gerente), json={
            "nome": "Colega", "email": f"{PREFIXO}-colega@kredor-e2e.com.br", "senha": SENHA,
            "permissoes": [VER_CLIENTES],
        })
        conferir(r.status_code == 200,
                 f"gerente concede o que ele tem (got {r.status_code} {r.text[:200]})")

        r = await c.put(f"/api/equipe/{id_gerente}/permissoes", headers=auth(tk_gerente),
                        json={"permissoes": [GERIR_EQUIPE, VER_FINANCEIRO]})
        conferir(r.status_code == 400, f"gerente não edita as próprias permissões (got {r.status_code})")

        r = await c.delete(f"/api/equipe/{id_gerente}", headers=auth(tk_gerente))
        conferir(r.status_code == 400, f"gerente não remove o próprio acesso (got {r.status_code})")

        # ---------------------------------------------------------------------------
        titulo("convite por email: expiração e reenvio")

        convidado_email = f"{PREFIXO}-convidado@kredor-e2e.com.br"
        r = await c.post("/api/equipe/convidar", headers=auth(tk_dono), json={
            "nome": "Convidado", "email": convidado_email, "permissoes": [VER_CLIENTES],
        })
        conferir(r.status_code == 200, f"convite criado (got {r.status_code} {r.text[:200]})")
        id_conv = r.json()["id"]
        doc = await db.usuarios.find_one({"id": id_conv})
        conferir(doc.get("convite_pendente") is True, "membro fica com convite pendente")
        conferir(bool(doc.get("convite_expira_em")), "convite recebe prazo de validade")
        conferir(doc.get("senha_hash") is None, "convite pendente não tem senha")
        token_antigo = doc["email_verification_token"]

        r = await c.post("/api/equipe/aceitar-convite",
                         json={"token": token_antigo, "senha": "abc"})
        conferir(r.status_code == 422, f"aceite com senha fraca recusado (got {r.status_code})")

        # expira à força
        await db.usuarios.update_one({"id": id_conv}, {"$set": {
            "convite_expira_em": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}})
        r = await c.post("/api/equipe/aceitar-convite",
                         json={"token": token_antigo, "senha": SENHA})
        conferir(r.status_code == 400 and "expirou" in r.text,
                 f"convite expirado recusado (got {r.status_code} {r.text[:160]})")

        await c.post(f"/api/equipe/{id_conv}/reenviar-convite", headers=auth(tk_dono))
        doc = await db.usuarios.find_one({"id": id_conv})
        token_novo = doc["email_verification_token"]
        conferir(token_novo != token_antigo, "reenvio gera token novo")

        r = await c.post("/api/equipe/aceitar-convite",
                         json={"token": token_antigo, "senha": SENHA})
        conferir(r.status_code == 400, f"token antigo deixa de valer (got {r.status_code})")

        r = await c.post("/api/equipe/aceitar-convite",
                         json={"token": token_novo, "senha": SENHA, "nome": "Convidado Final"})
        conferir(r.status_code == 200, f"aceite válido (got {r.status_code} {r.text[:200]})")
        tk_conv = await logar(c, convidado_email)
        r = await c.get("/api/clientes", headers=auth(tk_conv))
        conferir(r.status_code == 200, f"convidado entra e usa a permissão dada (got {r.status_code})")

        # ---------------------------------------------------------------------------
        titulo("desativar corta o acesso, reativar devolve")

        r = await c.delete(f"/api/equipe/{id_conv}", headers=auth(tk_dono))
        conferir(r.status_code == 200, f"desativou (got {r.status_code})")
        r = await c.get("/api/clientes", headers=auth(tk_conv))
        conferir(r.status_code == 401, f"token do desativado para de valer (got {r.status_code})")

        r = await c.post(f"/api/equipe/{id_conv}/reativar", headers=auth(tk_dono))
        conferir(r.status_code == 200, f"reativou (got {r.status_code} {r.text[:200]})")
        tk_conv2 = await logar(c, convidado_email)
        r = await c.get("/api/clientes", headers=auth(tk_conv2))
        conferir(r.status_code == 200, f"reativado volta a acessar (got {r.status_code})")

        r = await c.get("/api/equipe", headers=auth(tk_dono))
        pendentes = [m for m in r.json()["membros"] if m.get("convite_pendente")]
        conferir(pendentes == [], "nenhum convite pendente sobrou")

        # ---------------------------------------------------------------------------
        titulo("limite de membros vem do plano, não de um 999 no código")

        await db.usuarios.update_one({"id": dono_id}, {"$set": {"plano": "profissional"}})
        r = await c.get("/api/equipe", headers=auth(tk_dono))
        conferir(r.json()["limites"]["total"] == 0,
                 f"plano sem equipe informa limite 0: {r.json()['limites']}")
        r = await c.post("/api/equipe/convidar", headers=auth(tk_dono), json={
            "nome": "Extra", "email": f"{PREFIXO}-extra@kredor-e2e.com.br", "senha": SENHA,
        })
        conferir(r.status_code == 403,
                 f"plano sem multi_usuarios não cadastra membro (got {r.status_code})")
        await db.usuarios.update_one({"id": dono_id}, {"$set": {"plano": "enterprise"}})

        # ---------------------------------------------------------------------------
        titulo("auditoria: conceder e cortar acesso deixa rastro")

        logs = await db.auditoria.find({"entidade": "membro_equipe"}).to_list(200)
        acoes = {(l["acao"], l["entidade_id"]) for l in logs}
        conferir(any(a == "criar" for a, _ in acoes), "criação de membro auditada")
        conferir(("atualizar", id_m0) in acoes, "mudança de permissão auditada")
        conferir(any(a in ("atualizar", "excluir") and e == id_conv for a, e in acoes),
                 "desativação auditada")

        # ---------------------------------------------------------------------------
        titulo("o dono não se restringe a si mesmo")
        for caminho in ("/api/clientes", "/api/dashboard", "/api/pagamentos", "/api/equipe"):
            r = await c.get(caminho, headers=auth(tk_dono))
            conferir(r.status_code == 200, f"dono em {caminho} (got {r.status_code})")

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
