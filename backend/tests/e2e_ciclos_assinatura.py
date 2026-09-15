"""E2E: planos semestral e anual — preço cobrado e dias de acesso concedidos.

Pedido de 15/09/2026 ("crie planos semestral e anual com desconto top"). O que este roteiro
guarda é dinheiro: antes, os três caminhos de ativação fixavam `dias_validade=30`, então um
cliente do anual pagaria 8 meses e receberia 30 dias de acesso.

NÃO cria cobrança no gateway — PIX de verdade é dinheiro de verdade. Verifica a resolução do
plano, o que a API pública oferece, e a ATIVAÇÃO (que é onde a conta de dias acontece),
chamando ativar_plano_pago direto contra o banco de teste.

Rodar da raiz do repositório:

    docker run --rm --network kredor_network --env-file backend/.env \\
      -e MONGO_URL='mongodb://kredor_mongodb:27017/kredor_test?replicaSet=rs0' \\
      -e DB_NAME=kredor_test -e PYTHONPATH=/app -e TURNSTILE_SECRET_KEY= \\
      --tmpfs /app/static:mode=1777 \\
      -v "$PWD/backend:/app" -w /app --entrypoint python kredor-backend \\
      tests/e2e_ciclos_assinatura.py

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
from models.plano import PLANOS_PADRAO
from routes.assinaturas import get_plano_by_id
from services.auth import hash_senha
from services.ciclos_assinatura import ANUAL, MENSAL, SEMESTRAL, dias_do_ciclo
from services.plano_service import ativar_plano_pago

FALHAS = []
PREFIXO = f"e2e-ciclo-{uuid.uuid4().hex[:6]}"
SENHA = uuid.uuid4().hex[:10] + "aA1x"

# Preços configurados na conta (mensal). Os do ciclo são derivados.
MENSAL_ESPERADO = {"basico": 49.99, "profissional": 100.0, "enterprise": 200.0}


def conferir(condicao, mensagem):
    print(("  OK    " if condicao else "  FALHA ") + mensagem)
    if not condicao:
        FALHAS.append(mensagem)


def titulo(t):
    print(f"\n=== {t} ===")


async def _ip_aleatorio(request):
    request.headers["X-Forwarded-For"] = ".".join(str(random.randint(11, 250)) for _ in range(4))


_CONFIG_ORIGINAL = {}


async def plantar_precos():
    """Grava os preços que este roteiro espera, em vez de depender do que estiver no banco.

    Sem isto o teste cai nos defaults do LandingConfig (97/197/497) e as asserções de preço
    passariam ou falhariam por causa do ambiente, não do código.
    """
    atual = await db.configuracoes.find_one({"tipo": "landing"})
    _CONFIG_ORIGINAL["doc"] = atual  # None se não existia
    await db.configuracoes.update_one(
        {"tipo": "landing"},
        {"$set": {"dados.plano_basico_preco": MENSAL_ESPERADO["basico"],
                  "dados.plano_profissional_preco": MENSAL_ESPERADO["profissional"],
                  "dados.plano_enterprise_preco": MENSAL_ESPERADO["enterprise"]}},
        upsert=True,
    )


async def restaurar_precos():
    original = _CONFIG_ORIGINAL.get("doc")
    if original is None:
        await db.configuracoes.delete_one({"tipo": "landing"})
    else:
        await db.configuracoes.replace_one({"tipo": "landing"}, original)


async def limpar():
    await db.usuarios.delete_many({"id": {"$regex": f"^{PREFIXO}"}})
    await db.auditoria.delete_many({"usuario_id": {"$regex": f"^{PREFIXO}"}})
    await db.rate_limits.delete_many({})


async def criar_comprador(sufixo, ciclo):
    """Usuário como o checkout o deixa: plano pendente e o ciclo contratado gravado."""
    agora = datetime.now(timezone.utc)
    uid = f"{PREFIXO}-{sufixo}"
    await db.usuarios.insert_one({
        "id": uid, "nome": f"Comprador {sufixo}", "email": f"{uid}@kredor-e2e.com.br",
        "perfil": "usuario", "ativo": True, "email_verificado": True,
        "plano": "profissional", "plano_ativo": False, "payment_status": "pending",
        "ciclo_assinatura": ciclo, "dias_validade_contratada": dias_do_ciclo(ciclo),
        "owner_id": None, "permissoes": [],
        "data_inicio_trial": agora.isoformat(), "data_fim_trial": agora.isoformat(),
        "senha_hash": hash_senha(SENHA), "created_at": agora.isoformat(),
        "two_factor_enabled": False,
    })
    return uid


async def main():
    await limpar()
    await plantar_precos()

    # ---------------------------------------------------------------------------
    titulo("resolução do plano com ciclo no id")

    for nivel, mensal in MENSAL_ESPERADO.items():
        base = await get_plano_by_id(nivel)
        conferir(base is not None and abs(base.preco - mensal) < 0.01,
                 f"{nivel} mensal custa {getattr(base, 'preco', None)} (esperado {mensal})")
        conferir(base.dias_validade == 30, f"{nivel} mensal concede 30 dias")
        conferir(base.id == nivel, f"{nivel} mantém o id puro na listagem")

        for ciclo, meses_cobrados in ((SEMESTRAL, 5), (ANUAL, 8)):
            p = await get_plano_by_id(f"{nivel}:{ciclo}")
            esperado = round(mensal * meses_cobrados, 2)
            conferir(p is not None and abs(p.preco - esperado) < 0.01,
                     f"{nivel} {ciclo} custa {getattr(p, 'preco', None)} (esperado {esperado})")
            conferir(p.dias_validade == dias_do_ciclo(ciclo),
                     f"{nivel} {ciclo} concede {p.dias_validade} dias")
            conferir(p.nivel == nivel,
                     f"{nivel} {ciclo} preserva o nível ({p.nivel}) — é o que vai para o usuário")
            conferir(p.nivel in PLANOS_PADRAO,
                     f"o nível de {nivel}:{ciclo} existe em PLANOS_PADRAO (limites preservados)")

    p = await get_plano_by_id("profissional:vitalicio")
    conferir(p is not None and p.dias_validade == 30 and abs(p.preco - 100.0) < 0.01,
             f"ciclo inventado cai em mensal, não em algo mais barato ({p.preco}/{p.dias_validade}d)")

    conferir(await get_plano_by_id("inexistente:anual") is None,
             "nível inexistente não resolve")

    # ---------------------------------------------------------------------------
    titulo("a API pública oferece os três ciclos")

    transporte = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transporte, base_url="http://teste",
                                 event_hooks={"request": [_ip_aleatorio]}) as c:
        r = await c.get("/api/assinaturas/planos")
        conferir(r.status_code == 200, f"GET /assinaturas/planos (got {r.status_code})")
        planos = {p["id"]: p for p in r.json()}

        conferir(set(planos) == {"trial", "basico", "profissional", "enterprise"},
                 f"a listagem segue com 4 planos, sem quebrar a tela: {sorted(planos)}")

        prof = planos["profissional"]
        conferir(len(prof.get("ciclos") or []) == 3,
                 f"profissional traz 3 ciclos: {[x['ciclo'] for x in prof.get('ciclos', [])]}")
        por_ciclo = {x["ciclo"]: x for x in prof["ciclos"]}
        conferir(por_ciclo[ANUAL]["preco_total"] == 800.0,
                 f"anual do profissional: R$ {por_ciclo[ANUAL]['preco_total']}")
        conferir(por_ciclo[ANUAL]["economia"] == 400.0,
                 f"economia anunciada: R$ {por_ciclo[ANUAL]['economia']}")
        conferir(por_ciclo[ANUAL]["meses_gratis"] == 4, "4 meses grátis no anual")
        conferir(planos["trial"].get("ciclos") == [], "trial não oferece ciclo pago")

    # ---------------------------------------------------------------------------
    titulo("ativação concede os dias do ciclo contratado (era 30 fixo)")

    for ciclo, dias_esperados in ((MENSAL, 30), (SEMESTRAL, 180), (ANUAL, 365)):
        uid = await criar_comprador(ciclo, ciclo)
        antes = datetime.now(timezone.utc)

        res = await ativar_plano_pago(
            usuario_id=uid, plano_id="profissional",
            payment_id=f"teste-{ciclo}", gateway="syncpay",
            dias_validade=dias_do_ciclo(ciclo),
            valor=1.0, origem="e2e",
        )
        conferir(res.get("success") is True, f"{ciclo}: ativação concluída")

        doc = await db.usuarios.find_one({"id": uid})
        expira = datetime.fromisoformat(doc["data_expiracao_plano"])
        dias = (expira - antes).total_seconds() / 86400
        conferir(abs(dias - dias_esperados) < 0.05,
                 f"{ciclo}: concedeu {dias:.2f} dias (esperado {dias_esperados})")
        conferir(doc["plano"] == "profissional",
                 f"{ciclo}: usuario.plano segue o nível ({doc['plano']}), não o id composto")
        conferir(doc.get("plano_ativo") is True, f"{ciclo}: plano ficou ativo")

    # ---------------------------------------------------------------------------
    titulo("o anual entrega 12x mais acesso que o mensal pagando 8x")

    mensal = await get_plano_by_id("profissional")
    anual = await get_plano_by_id("profissional:anual")
    razao_preco = anual.preco / mensal.preco
    razao_dias = anual.dias_validade / mensal.dias_validade
    conferir(abs(razao_preco - 8) < 0.01, f"preço = {razao_preco:.2f}x o mensal")
    conferir(razao_dias > razao_preco,
             f"acesso = {razao_dias:.2f}x, maior que o preço ({razao_preco:.2f}x) — há desconto real")

    await restaurar_precos()
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
