"""E2E do painel com pagamento parcial: o capital em aberto e os juros refletem o que foi pago.

Reproduz o caso de 11/09/2026: empréstimo de R$ 15.000,00 a 13,4% em 1x (R$ 2.010,00 de juros),
pagamento parcial de R$ 10.010,00. Imputando primeiro nos juros (CC art. 354), o painel tem de
mostrar R$ 7.000,00 de capital em aberto, R$ 2.010,00 de juros recebidos e nada de juros a receber.
Cobre também o empréstimo aberto (card com juros pagos / em aberto).

Não é coletado pelo pytest (não começa com test_). Rodar da raiz do repositório, no banco de teste:

    docker run --rm --network kredor_network --env-file backend/.env \\
      -e MONGO_URL='mongodb://kredor_mongodb:27017/kredor_test?replicaSet=rs0' \\
      -e DB_NAME=kredor_test -e PYTHONPATH=/app --tmpfs /app/static:mode=1777 \\
      -v "$PWD/backend:/app" -w /app --entrypoint python kredor-backend tests/e2e_painel_imputacao.py

Sai com código 1 se qualquer verificação falhar.
"""
import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone

import httpx

from config import db
from main import app
from services.auth import criar_tokens, hash_senha

FALHAS = []


def conferir(condicao, mensagem):
    print(("  OK    " if condicao else "  FALHA ") + mensagem)
    if not condicao:
        FALHAS.append(mensagem)


async def criar_credor(uid):
    agora = datetime.now(timezone.utc)
    await db.usuarios.insert_one({
        "id": uid, "nome": "Credor E2E", "email": f"{uid}@kredor-e2e.com.br", "perfil": "usuario",
        "ativo": True, "email_verificado": True, "plano": "enterprise", "plano_ativo": True,
        "data_inicio_trial": agora.isoformat(), "data_fim_trial": (agora + timedelta(days=30)).isoformat(),
        "senha_hash": hash_senha(uuid.uuid4().hex), "created_at": agora.isoformat(),
    })
    return {"Authorization": f"Bearer {criar_tokens(uid)[0]}"}


async def painel(c, h):
    return (await c.get("/api/dashboard", headers=h)).json()


async def item(c, h, emp_id):
    r = await c.get("/api/emprestimos", headers=h)
    return next(i for i in r.json()["items"] if i["id"] == emp_id)


async def cenario(c, h, cliente_id):
    print("\n[1] R$ 15.000,00 a 13,4% em 1x, juros simples")
    r = await c.post("/api/emprestimos", headers=h, json={
        "cliente_id": cliente_id, "valor_principal": 15000, "taxa_juros_mensal": 13.4,
        "prazo_meses": 1, "metodo_calculo": "juros_simples", "periodicidade": "mensal",
    })
    conferir(r.status_code == 200, f"cria empréstimo -> {r.status_code} {'' if r.status_code == 200 else r.text[:200]}")
    if r.status_code != 200:
        return
    emp_id = r.json()["id"]
    parcela = await db.parcelas.find_one({"emprestimo_id": emp_id}, {"_id": 0})
    conferir(parcela["valor_juros_centavos"] == 201_000, f"juros da parcela = {parcela['valor_juros_centavos']} centavos")
    d = await painel(c, h)
    conferir(d["total_capital_emprestado"] == 15000, f"capital antes = {d['total_capital_emprestado']}")
    conferir(d["total_juros_a_receber"] == 2010, f"juros a receber antes = {d['total_juros_a_receber']}")

    print("\n[2] Pagamento parcial de R$ 10.010,00")
    r = await c.post("/api/pagamentos", headers=h, json={"parcela_id": parcela["id"], "valor_pago": 10010, "metodo_pagamento": "pix"})
    conferir(r.status_code == 200, f"registra pagamento -> {r.status_code}")
    d = await painel(c, h)
    conferir(d["total_capital_emprestado"] == 7000, f"capital em aberto = {d['total_capital_emprestado']} (esperado 7000)")
    conferir(d["total_juros_recebidos"] == 2010, f"juros recebidos = {d['total_juros_recebidos']} (esperado 2010)")
    conferir(d["total_juros_a_receber"] == 0, f"juros a receber = {d['total_juros_a_receber']} (esperado 0)")
    conferir(d["juros_recebidos_mes"] == 2010, f"juros recebidos no mês = {d['juros_recebidos_mes']}")
    conferir(d["recebido_mes_atual"] == 10010, f"recebido no mês = {d['recebido_mes_atual']}")
    conferir(d["evolucao_ganhos_mensal"][-1]["juros"] == 2010, f"gráfico de ganhos, mês atual = {d['evolucao_ganhos_mensal'][-1]['juros']}")
    conferir(d["total_a_receber"] == 7000 and d["encargos_a_receber"] == 0, f"total a receber = {d['total_a_receber']} (esperado 7000)")
    i = await item(c, h, emp_id)
    conferir(i["saldo_restante"] == 7000 and i["juros_pagos"] == 2010 and i["juros_em_aberto"] == 0,
             f"card: falta {i['saldo_restante']}, juros pagos {i['juros_pagos']}, em aberto {i['juros_em_aberto']}")

    print("\n[3] Segundo pagamento de R$ 7.000,00 quita")
    r = await c.post("/api/pagamentos", headers=h, json={"parcela_id": parcela["id"], "valor_pago": 7000, "metodo_pagamento": "pix"})
    d = await painel(c, h)
    conferir(r.status_code == 200 and d["total_capital_emprestado"] == 0, f"capital em aberto = {d['total_capital_emprestado']}")
    conferir(d["juros_recebidos_mes"] == 2010, f"os juros não contam duas vezes: {d['juros_recebidos_mes']}")
    conferir(d["recebido_mes_atual"] == 17010, f"recebido no mês = {d['recebido_mes_atual']}")

    print("\n[4] Empréstimo aberto: R$ 300,00 a 33,5% ao mês")
    r = await c.post("/api/emprestimos", headers=h, json={
        "cliente_id": cliente_id, "valor_principal": 300, "taxa_juros_mensal": 33.5,
        "sem_prazo": True, "metodo_calculo": "apenas_juros", "periodicidade": "mensal",
    })
    conferir(r.status_code == 200, f"cria aberto -> {r.status_code} {'' if r.status_code == 200 else r.text[:200]}")
    if r.status_code != 200:
        return
    aberto_id = r.json()["id"]
    p1 = await db.parcelas.find_one({"emprestimo_id": aberto_id, "deleted": {"$ne": True}}, {"_id": 0}, sort=[("numero_parcela", 1)])
    r = await c.post("/api/pagamentos", headers=h, json={"parcela_id": p1["id"], "valor_pago": 100.5, "metodo_pagamento": "pix"})
    conferir(r.status_code == 200, f"paga os juros do mês -> {r.status_code}")
    i = await item(c, h, aberto_id)
    conferir(i["juros_pagos"] == 100.5, f"card: juros pagos = {i['juros_pagos']}")
    conferir(i["juros_em_aberto"] >= 0 and "juros_pagos_centavos" not in i, f"card: juros em aberto = {i['juros_em_aberto']}, sem vazar _centavos")
    d = await painel(c, h)
    conferir(d["total_capital_emprestado"] == 300, f"capital do aberto continua inteiro: {d['total_capital_emprestado']}")
    soma = round(d["total_capital_emprestado"] + d["total_juros_a_receber"] + d["encargos_a_receber"], 2)
    conferir(d["total_a_receber"] == soma == 300 + i["juros_em_aberto"],
             f"total a receber = {d['total_a_receber']} = capital + juros + multa/mora ({soma})")
    conferir(len({g["mes"] for g in d["evolucao_ganhos_mensal"]}) == 12, "gráfico com 12 meses distintos")


async def main():
    s = uuid.uuid4().hex[:8]
    uid = f"e2e-painel-{s}"
    h = await criar_credor(uid)
    cliente_id = f"cli-{s}"
    await db.clientes.insert_one({"id": cliente_id, "usuario_id": uid, "nome": "Cliente Painel", "telefone": "11999999999",
                                  "status": "ativo", "deleted": False, "created_at": datetime.now(timezone.utc).isoformat()})
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://teste") as c:
            await cenario(c, h, cliente_id)
    except Exception as e:  # exceção no meio do cenário também é falha, nunca sucesso silencioso
        conferir(False, f"exceção no cenário: {type(e).__name__}: {e}")
    finally:
        for colecao in ("clientes", "emprestimos", "parcelas", "pagamentos", "auditoria", "contratos",
                        "scores_historico", "notificacoes"):
            await db[colecao].delete_many({"usuario_id": uid})
        await db.usuarios.delete_many({"id": uid})


asyncio.run(main())
# O veredito fica fora de main(): nenhum return antecipado pode pular o código de saída.
print(f"\n{'TUDO OK' if not FALHAS else f'{len(FALHAS)} FALHA(S)'}")
sys.exit(1 if FALHAS else 0)
