"""E2E do recibo de pagamento parcial e do resumo no card do empréstimo.

Cria credor, cliente e empréstimo reais (pela API), registra dois pagamentos parciais e
confere: resposta com o saldo, retrato do saldo imutável, listagem filtrada por empréstimo,
recibo em PDF, isolamento entre contas, WhatsApp sem conexão (409), estorno e pagamento
antigo sem retrato. Limpa só os documentos que criou.

Não é coletado pelo pytest (não começa com test_): precisa de banco com replica set.
Rodar a partir da raiz do repositório, contra o banco de teste:

    docker run --rm --network kredor_network --env-file backend/.env \\
      -e MONGO_URL='mongodb://kredor_mongodb:27017/kredor_test?replicaSet=rs0' \\
      -e DB_NAME=kredor_test -e PYTHONPATH=/app --tmpfs /app/static:mode=1777 \\
      -v "$PWD/backend:/app" -w /app --entrypoint python kredor-backend tests/e2e_recibo_parcial.py

PYTHONPATH=/app porque o script fica em tests/; o tmpfs porque o main.py cria static/uploads
ao ser importado e o código montado do host não é gravável pelo usuário do container.
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


async def criar_credor(sufixo):
    agora = datetime.now(timezone.utc)
    uid = f"e2e-{sufixo}"
    # Domínio comum: ".local"/".test" são de uso especial e o validador de e-mail do modelo recusa.
    await db.usuarios.insert_one({
        "id": uid, "nome": "Credor E2E", "email": f"{uid}@kredor-e2e.com.br", "perfil": "usuario",
        "ativo": True, "email_verificado": True, "plano": "enterprise", "plano_ativo": True,
        "data_inicio_trial": agora.isoformat(), "data_fim_trial": (agora + timedelta(days=30)).isoformat(),
        "senha_hash": hash_senha(uuid.uuid4().hex), "created_at": agora.isoformat(),
    })
    token, _ = criar_tokens(uid)
    return uid, {"Authorization": f"Bearer {token}"}


async def item_do_card(c, h, emp_id):
    r = await c.get("/api/emprestimos", headers=h)
    return next(i for i in r.json()["items"] if i["id"] == emp_id)


async def cenario(c, h, h_outro, cliente_id):
    print("\n[1] Empréstimo real pela API: R$ 1.000,00 a 2% a.m. em 3x (Price)")
    r = await c.post("/api/emprestimos", headers=h, json={
        "cliente_id": cliente_id, "valor_principal": 1000, "taxa_juros_mensal": 2,
        "prazo_meses": 3, "metodo_calculo": "tabela_price", "periodicidade": "mensal",
    })
    conferir(r.status_code == 200, f"cria empréstimo -> {r.status_code} {'' if r.status_code == 200 else r.text[:200]}")
    if r.status_code != 200:
        return
    emp_id = r.json()["id"]
    parcelas = await db.parcelas.find({"emprestimo_id": emp_id}, {"_id": 0}).sort("numero_parcela", 1).to_list(None)
    p1 = parcelas[0]
    total_p1 = p1["valor_total_centavos"]
    soma_total = sum(p["valor_total_centavos"] for p in parcelas)
    print(f"        parcela 1 = R$ {total_p1 / 100:.2f}   total do empréstimo = R$ {soma_total / 100:.2f}")

    print("\n[2] Pagamento PARCIAL de R$ 100,00 na parcela 1")
    r = await c.post("/api/pagamentos", headers=h, json={"parcela_id": p1["id"], "valor_pago": 100, "metodo_pagamento": "pix"})
    conferir(r.status_code == 200, f"registra pagamento -> {r.status_code}")
    pag1 = r.json()
    falta_parcela = (total_p1 - 10_000) / 100
    falta_emprestimo = (soma_total - 10_000) / 100
    conferir(pag1.get("status_parcela_apos") == "parcial", f"resposta diz 'parcial' -> {pag1.get('status_parcela_apos')}")
    conferir(pag1.get("saldo_parcela_restante") == falta_parcela,
             f"falta na parcela = {pag1.get('saldo_parcela_restante')} (esperado {falta_parcela})")
    conferir(pag1.get("saldo_emprestimo_restante") == falta_emprestimo,
             f"saldo do empréstimo = {pag1.get('saldo_emprestimo_restante')} (esperado {falta_emprestimo})")

    item = await item_do_card(c, h, emp_id)
    conferir(item.get("total_recebido") == 100.0, f"card: recebido = {item.get('total_recebido')}")
    conferir(item.get("saldo_restante") == falta_emprestimo, f"card: falta = {item.get('saldo_restante')}")
    conferir(item.get("qtd_pagamentos") == 1, f"card: qtd pagamentos = {item.get('qtd_pagamentos')}")
    conferir(item.get("parcelas_com_pagamento_parcial") == 1, f"card: parcelas parciais = {item.get('parcelas_com_pagamento_parcial')}")
    conferir("total_recebido_centavos" not in item, "card: nenhum campo _centavos vazou para o frontend")

    print(f"\n[3] Segundo pagamento de R$ {falta_parcela:.2f} quita a parcela 1")
    r = await c.post("/api/pagamentos", headers=h, json={"parcela_id": p1["id"], "valor_pago": falta_parcela, "metodo_pagamento": "dinheiro"})
    pag2 = r.json()
    conferir(r.status_code == 200 and pag2.get("status_parcela_apos") == "pago", f"resposta diz 'pago' -> {pag2.get('status_parcela_apos')}")
    conferir(pag2.get("saldo_parcela_restante") == 0, f"falta na parcela = {pag2.get('saldo_parcela_restante')}")

    print("\n[4] Histórico filtrado por empréstimo e retrato do saldo imutável")
    r = await c.get("/api/pagamentos", headers=h, params={"emprestimo_id": emp_id})
    lista = r.json()
    conferir(r.status_code == 200 and len(lista) == 2, f"lista {len(lista)} pagamentos do empréstimo")
    conferir(all(p["emprestimo_id"] == emp_id for p in lista), "todos são deste empréstimo")
    antigo = next(p for p in lista if p["id"] == pag1["id"])
    conferir(antigo.get("saldo_parcela_restante") == falta_parcela,
             f"1º pagamento ainda mostra o saldo DAQUELA data ({antigo.get('saldo_parcela_restante')}), não o atual (0)")

    print("\n[5] Recibo em PDF")
    r = await c.get(f"/api/pagamentos/{pag1['id']}/recibo", headers=h)
    conferir(r.status_code == 200 and r.headers.get("content-type") == "application/pdf" and r.content.startswith(b"%PDF"),
             f"PDF -> {r.status_code} {r.headers.get('content-type')} {len(r.content)} bytes")

    print("\n[6] Isolamento entre contas")
    r = await c.get(f"/api/pagamentos/{pag1['id']}/recibo", headers=h_outro)
    conferir(r.status_code == 404, f"outro credor pedindo o recibo -> {r.status_code}")
    r = await c.get("/api/pagamentos", headers=h_outro, params={"emprestimo_id": emp_id})
    conferir(r.status_code == 200 and r.json() == [], f"outro credor filtrando o empréstimo -> {len(r.json())} itens")

    print("\n[7] WhatsApp sem conexão")
    r = await c.post(f"/api/pagamentos/{pag1['id']}/recibo/whatsapp", headers=h)
    conferir(r.status_code in (400, 409), f"-> {r.status_code}: {r.json().get('detail')}")

    print("\n[8] Estorno do 2º pagamento")
    r = await c.delete(f"/api/pagamentos/{pag2['id']}", headers=h)
    conferir(r.status_code == 200, f"estorno -> {r.status_code}")
    item = await item_do_card(c, h, emp_id)
    conferir(item.get("qtd_pagamentos") == 1 and item.get("total_recebido") == 100.0,
             f"card volta: {item.get('qtd_pagamentos')} pagamento, recebido {item.get('total_recebido')}")
    conferir(item.get("parcelas_com_pagamento_parcial") == 1, f"card: parcela volta a parcial ({item.get('parcelas_com_pagamento_parcial')})")
    r = await c.get(f"/api/pagamentos/{pag2['id']}/recibo", headers=h)
    conferir(r.status_code == 404, f"pagamento estornado não gera recibo -> {r.status_code}")

    print("\n[9] Pagamento antigo, sem o retrato do saldo gravado")
    await db.pagamentos.update_one({"id": pag1["id"]}, {"$unset": {
        "saldo_parcela_restante_centavos": "", "saldo_emprestimo_restante_centavos": "", "status_parcela_apos": ""}})
    r = await c.get(f"/api/pagamentos/{pag1['id']}/recibo", headers=h)
    conferir(r.status_code == 200 and r.content.startswith(b"%PDF"), f"recibo com saldo na data de emissão -> {r.status_code}")


async def main():
    s = uuid.uuid4().hex[:8]
    uid, h = await criar_credor(s)
    uid_outro, h_outro = await criar_credor(s + "x")
    cliente_id = f"cli-{s}"
    await db.clientes.insert_one({
        "id": cliente_id, "usuario_id": uid, "nome": "Maria & Filhos", "telefone": "11999999999",
        "status": "ativo", "deleted": False, "created_at": datetime.now(timezone.utc).isoformat(),
    })
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://teste") as c:
            await cenario(c, h, h_outro, cliente_id)
    except Exception as e:  # uma exceção no meio do cenário também é falha, nunca sucesso silencioso
        conferir(False, f"exceção no cenário: {type(e).__name__}: {e}")
    finally:
        for colecao in ("clientes", "emprestimos", "parcelas", "pagamentos", "auditoria", "contratos",
                        "scores_historico", "notificacoes"):
            await db[colecao].delete_many({"usuario_id": {"$in": [uid, uid_outro]}})
        await db.usuarios.delete_many({"id": {"$in": [uid, uid_outro]}})


asyncio.run(main())
# O veredito fica fora de main(): nenhum return antecipado pode pular o código de saída.
print(f"\n{'TUDO OK' if not FALHAS else f'{len(FALHAS)} FALHA(S)'}")
sys.exit(1 if FALHAS else 0)
