"""E2E: multa e mora pela data em que o cliente pagou, não pela data do lançamento.

Caso relatado em 12/09/2026: o cliente pagou no dia do vencimento, o credor só lançou dias depois,
e o sistema cobrava a mora dos dias de atraso do LANÇAMENTO — a parcela ficava "parcial" mesmo
tendo sido paga em dia.

Não é coletado pelo pytest (não começa com test_). Rodar da raiz do repositório:

    docker run --rm --network kredor_network --env-file backend/.env \\
      -e MONGO_URL='mongodb://kredor_mongodb:27017/kredor_test?replicaSet=rs0' \\
      -e DB_NAME=kredor_test -e PYTHONPATH=/app --tmpfs /app/static:mode=1777 \\
      -v "$PWD/backend:/app" -w /app --entrypoint python kredor-backend tests/e2e_pagamento_na_data.py

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
from services.juros_mora_service import atualizar_todas_parcelas_atrasadas

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


async def emprestimo_vencido(c, h, cliente_id, uid):
    """Empréstimo de R$ 1.000 a 10% em 1x, com a parcela vencida há 10 dias e mora já gravada."""
    r = await c.post("/api/emprestimos", headers=h, json={
        "cliente_id": cliente_id, "valor_principal": 1000, "taxa_juros_mensal": 10,
        "prazo_meses": 1, "metodo_calculo": "juros_simples", "periodicidade": "mensal",
        "data_inicio": (datetime.now(timezone.utc) - timedelta(days=40)).isoformat(),
    })
    assert r.status_code == 200, r.text[:300]
    parcela = await db.parcelas.find_one({"emprestimo_id": r.json()["id"]}, {"_id": 0})
    await atualizar_todas_parcelas_atrasadas(uid)   # o job diário grava multa e mora de hoje
    return await db.parcelas.find_one({"id": parcela["id"]}, {"_id": 0})


async def cenario(c, h, cliente_id, uid):
    print("\n[1] Parcela vencida há 10 dias, com multa e mora gravadas pelo job")
    p = await emprestimo_vencido(c, h, cliente_id, uid)
    encargos_hoje = (p.get("valor_multa_centavos") or 0) + (p.get("valor_juros_mora_centavos") or 0)
    conferir(p["status"] == "atrasado" and encargos_hoje > 0,
             f"status {p['status']}, multa+mora de hoje = {encargos_hoje} centavos ({p.get('dias_atraso')} dias)")
    vencimento = datetime.fromisoformat(p["data_vencimento"])

    print("\n[2] Lançado depois, mas informando que o cliente pagou NO VENCIMENTO")
    r = await c.post("/api/pagamentos", headers=h, json={
        "parcela_id": p["id"], "valor_pago": p["valor_total_centavos"] / 100,
        "metodo_pagamento": "pix", "data_pagamento": vencimento.date().isoformat(),
    })
    conferir(r.status_code == 200, f"registra pagamento -> {r.status_code} {'' if r.status_code == 200 else r.text[:200]}")
    corpo = r.json() if r.status_code == 200 else {}
    conferir(corpo.get("status_parcela_apos") == "pago", f"parcela quitada com o valor da parcela -> {corpo.get('status_parcela_apos')}")
    conferir(corpo.get("saldo_parcela_restante") == 0, f"nada a pagar depois: {corpo.get('saldo_parcela_restante')}")
    depois = await db.parcelas.find_one({"id": p["id"]}, {"_id": 0})
    conferir((depois.get("valor_multa_centavos") or 0) == 0 and (depois.get("valor_juros_mora_centavos") or 0) == 0,
             f"multa e mora zeradas: multa={depois.get('valor_multa_centavos')} mora={depois.get('valor_juros_mora_centavos')}")
    conferir(depois.get("dias_atraso") == 0, f"dias de atraso = {depois.get('dias_atraso')}")

    print("\n[3] Pagamento realmente atrasado: informando 3 dias após o vencimento")
    p2 = await emprestimo_vencido(c, h, cliente_id, uid)
    r = await c.post("/api/pagamentos", headers=h, json={
        "parcela_id": p2["id"], "valor_pago": p2["valor_total_centavos"] / 100,
        "metodo_pagamento": "pix",
        "data_pagamento": (datetime.fromisoformat(p2["data_vencimento"]) + timedelta(days=3)).date().isoformat(),
    })
    corpo = r.json() if r.status_code == 200 else {}
    d2 = await db.parcelas.find_one({"id": p2["id"]}, {"_id": 0})
    encargos_3_dias = (d2.get("valor_multa_centavos") or 0) + (d2.get("valor_juros_mora_centavos") or 0)
    conferir(corpo.get("status_parcela_apos") == "parcial", f"só o valor da parcela não quita -> {corpo.get('status_parcela_apos')}")
    conferir(d2.get("dias_atraso") == 3, f"cobra 3 dias de atraso, não 10 -> {d2.get('dias_atraso')}")
    conferir(corpo.get("saldo_parcela_restante") == round(encargos_3_dias / 100, 2),
             f"falta exatamente a multa + mora de 3 dias: {corpo.get('saldo_parcela_restante')} (parcela: {encargos_3_dias / 100})")
    conferir(encargos_3_dias < (p2.get("valor_multa_centavos") or 0) + (p2.get("valor_juros_mora_centavos") or 0),
             "encargos menores que os de hoje (10 dias)")

    print("\n[4] Quitando o restante (multa + mora)")
    r = await c.post("/api/pagamentos", headers=h, json={
        "parcela_id": p2["id"], "valor_pago": encargos_3_dias / 100, "metodo_pagamento": "pix",
        "data_pagamento": (datetime.fromisoformat(p2["data_vencimento"]) + timedelta(days=3)).date().isoformat(),
    })
    corpo = r.json() if r.status_code == 200 else {}
    conferir(corpo.get("status_parcela_apos") == "pago", f"parcela quitada -> {corpo.get('status_parcela_apos')}")

    print("\n[5] Data no futuro é recusada")
    p3 = await emprestimo_vencido(c, h, cliente_id, uid)
    r = await c.post("/api/pagamentos", headers=h, json={
        "parcela_id": p3["id"], "valor_pago": 10, "metodo_pagamento": "pix",
        "data_pagamento": (datetime.now(timezone.utc) + timedelta(days=2)).date().isoformat(),
    })
    conferir(r.status_code == 422, f"-> {r.status_code} {r.json().get('detail') if r.status_code != 200 else ''}")

    print("\n[6] Sem informar data, vale hoje (comportamento antigo)")
    r = await c.post("/api/pagamentos", headers=h, json={
        "parcela_id": p3["id"], "valor_pago": p3["valor_total_centavos"] / 100, "metodo_pagamento": "pix",
    })
    corpo = r.json() if r.status_code == 200 else {}
    d3 = await db.parcelas.find_one({"id": p3["id"]}, {"_id": 0})
    conferir(corpo.get("status_parcela_apos") == "parcial"
             and (d3.get("dias_atraso") or 0) == (p3.get("dias_atraso") or 0),
             f"cobra o atraso até hoje -> {corpo.get('status_parcela_apos')}, "
             f"{d3.get('dias_atraso')} dias (o job havia calculado {p3.get('dias_atraso')})")


async def main():
    s = uuid.uuid4().hex[:8]
    uid = f"e2e-data-{s}"
    h = await criar_credor(uid)
    cliente_id = f"cli-{s}"
    await db.clientes.insert_one({"id": cliente_id, "usuario_id": uid, "nome": "Cliente Data", "telefone": "11999999999",
                                  "status": "ativo", "deleted": False, "created_at": datetime.now(timezone.utc).isoformat()})
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://teste") as c:
            await cenario(c, h, cliente_id, uid)
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
