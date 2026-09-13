"""E2E: quitar a parcela ignorando o que o credor não cobrou (mora, multa ou juros).

Pedido de 13/09/2026: juros e multa continuam sendo gerados, mas quando o credor lança um
pagamento sem esses valores o sistema tem que entender que a parcela foi quitada e perguntar se o
restante deve ser ignorado — se ele fosse lançado como recebido, o painel mostraria ganho que não
existiu; se ficasse em aberto, mostraria a receber algo que nunca vai entrar.

Não é coletado pelo pytest (não começa com test_). Rodar da raiz do repositório:

    docker run --rm --network kredor_network --env-file backend/.env \\
      -e MONGO_URL='mongodb://kredor_mongodb:27017/kredor_test?replicaSet=rs0' \\
      -e DB_NAME=kredor_test -e PYTHONPATH=/app --tmpfs /app/static:mode=1777 \\
      -v "$PWD/backend:/app" -w /app --entrypoint python kredor-backend tests/e2e_quitar_com_desconto.py

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


async def emprestimo_vencido(c, h, cliente_id, uid, dias=10):
    """Empréstimo de R$ 1.000 a 10% em 1x, parcela vencida há `dias`, com multa e mora gravadas."""
    r = await c.post("/api/emprestimos", headers=h, json={
        "cliente_id": cliente_id, "valor_principal": 1000, "taxa_juros_mensal": 10,
        "prazo_meses": 1, "metodo_calculo": "juros_simples", "periodicidade": "mensal",
        "data_inicio": (datetime.now(timezone.utc) - timedelta(days=30 + dias)).isoformat(),
    })
    assert r.status_code == 200, r.text[:300]
    await atualizar_todas_parcelas_atrasadas(uid)
    return await db.parcelas.find_one({"emprestimo_id": r.json()["id"]}, {"_id": 0})


async def painel(c, h):
    r = await c.get("/api/dashboard", headers=h)
    assert r.status_code == 200, r.text[:300]
    return r.json()


async def cenario(c, h, cliente_id, uid):
    print("\n[1] Prévia: o valor da parcela não cobre a mora do atraso")
    p = await emprestimo_vencido(c, h, cliente_id, uid)
    encargos = (p.get("valor_multa_centavos") or 0) + (p.get("valor_juros_mora_centavos") or 0)
    r = await c.post("/api/pagamentos/previa", headers=h, json={
        "parcela_id": p["id"], "valor_pago": p["valor_total_centavos"] / 100})
    conferir(r.status_code == 200, f"previa -> {r.status_code} {'' if r.status_code == 200 else r.text[:200]}")
    previa = r.json() if r.status_code == 200 else {}
    conferir(previa.get("quita") is False, f"avisa que não quita -> quita={previa.get('quita')}")
    conferir(previa.get("restante") == round(encargos / 100, 2),
             f"restante = multa + mora: {previa.get('restante')} (parcela tem {encargos / 100})")
    detalhe = previa.get("restante_detalhe") or {}
    conferir(detalhe.get("encargos") == round(encargos / 100, 2) and detalhe.get("juros") == 0,
             f"restante é tudo multa/mora: {detalhe}")
    imputacao = previa.get("imputacao") or {}
    conferir(imputacao.get("juros") == 100 and imputacao.get("capital") == 1000,
             f"imputação do pagamento: {imputacao}")

    print("\n[2] Quitando e ignorando a mora que o credor não cobrou")
    antes = await painel(c, h)
    r = await c.post("/api/pagamentos", headers=h, json={
        "parcela_id": p["id"], "valor_pago": p["valor_total_centavos"] / 100,
        "metodo_pagamento": "pix", "quitar_ignorando_restante": True})
    conferir(r.status_code == 200, f"registra -> {r.status_code} {'' if r.status_code == 200 else r.text[:200]}")
    corpo = r.json() if r.status_code == 200 else {}
    pagamento_id = corpo.get("id")
    conferir(corpo.get("status_parcela_apos") == "pago", f"parcela quitada -> {corpo.get('status_parcela_apos')}")
    conferir(corpo.get("valor_perdoado") == round(encargos / 100, 2),
             f"desconto gravado no pagamento: {corpo.get('valor_perdoado')}")
    conferir(corpo.get("saldo_parcela_restante") == 0, f"nada a pagar: {corpo.get('saldo_parcela_restante')}")
    parcela = await db.parcelas.find_one({"id": p["id"]}, {"_id": 0})
    conferir(parcela["status"] == "pago" and parcela.get("perdao_encargos_centavos") == encargos,
             f"parcela: status={parcela['status']} perdao_encargos={parcela.get('perdao_encargos_centavos')}")
    conferir(parcela.get("perdoado_por") == f"{uid}@kredor-e2e.com.br",
             f"quem deu o desconto fica registrado: {parcela.get('perdoado_por')}")

    depois = await painel(c, h)
    conferir(depois["total_juros_recebidos"] - antes["total_juros_recebidos"] == 100,
             f"juros recebidos +100 (os juros da parcela): {antes['total_juros_recebidos']} -> {depois['total_juros_recebidos']}")
    conferir(depois["encargos_a_receber"] == 0,
             f"multa e mora perdoadas saem do a receber: {depois['encargos_a_receber']}")
    conferir(depois["total_a_receber"] == 0, f"nada mais a receber: {depois['total_a_receber']}")
    conferir(depois["valor_em_atraso"] == 0, f"nada em atraso: {depois['valor_em_atraso']}")

    print("\n[3] Sem pedir para ignorar, a parcela continua parcial (comportamento antigo)")
    p2 = await emprestimo_vencido(c, h, cliente_id, uid)
    encargos2 = (p2.get("valor_multa_centavos") or 0) + (p2.get("valor_juros_mora_centavos") or 0)
    r = await c.post("/api/pagamentos", headers=h, json={
        "parcela_id": p2["id"], "valor_pago": p2["valor_total_centavos"] / 100, "metodo_pagamento": "pix"})
    corpo = r.json() if r.status_code == 200 else {}
    conferir(corpo.get("status_parcela_apos") == "parcial", f"-> {corpo.get('status_parcela_apos')}")
    conferir(corpo.get("valor_perdoado") is None, f"nenhum desconto gravado: {corpo.get('valor_perdoado')}")
    pos = await painel(c, h)
    conferir(pos["encargos_a_receber"] == round(encargos2 / 100, 2),
             f"multa e mora seguem a receber: {pos['encargos_a_receber']} (parcela tem {encargos2 / 100})")

    print("\n[4] Juros que o credor não cobrou não entram como juros recebidos")
    p3 = await emprestimo_vencido(c, h, cliente_id, uid, dias=0)   # vence hoje: sem multa e sem mora
    antes3 = await painel(c, h)
    r = await c.post("/api/pagamentos", headers=h, json={
        "parcela_id": p3["id"], "valor_pago": 1050, "metodo_pagamento": "pix",
        "quitar_ignorando_restante": True})   # parcela de R$ 1.100: R$ 50 de juros não cobrados
    corpo = r.json() if r.status_code == 200 else {}
    conferir(corpo.get("status_parcela_apos") == "pago", f"quitada -> {corpo.get('status_parcela_apos')}")
    conferir(corpo.get("perdao_juros") == 50, f"desconto lançado como juros não cobrados: {corpo.get('perdao_juros')}")
    depois3 = await painel(c, h)
    conferir(depois3["total_juros_recebidos"] - antes3["total_juros_recebidos"] == 50,
             f"juros recebidos +50, não +100: {antes3['total_juros_recebidos']} -> {depois3['total_juros_recebidos']}")
    conferir(depois3["total_capital_emprestado"] == antes3["total_capital_emprestado"] - 1000,
             f"capital devolvido inteiro: {antes3['total_capital_emprestado']} -> {depois3['total_capital_emprestado']}")

    print("\n[5] Recibo mostra o desconto concedido")
    r = await c.get(f"/api/pagamentos/{pagamento_id}/recibo", headers=h)
    conferir(r.status_code == 200 and r.content[:4] == b"%PDF", f"PDF do recibo -> {r.status_code}")

    print("\n[6] Estornar o pagamento desfaz o desconto")
    r = await c.delete(f"/api/pagamentos/{pagamento_id}", headers=h)
    conferir(r.status_code == 200, f"estorno -> {r.status_code}")
    estornada = await db.parcelas.find_one({"id": p["id"]}, {"_id": 0})
    conferir((estornada.get("valor_perdoado_centavos") or 0) == 0 and estornada["status"] != "pago",
             f"volta a dever: status={estornada['status']} perdoado={estornada.get('valor_perdoado_centavos')}")
    final = await painel(c, h)
    # Sobram os R$ 100 de juros do pagamento parcial do caso 3 e os R$ 50 cobrados no caso 4.
    conferir(final["total_juros_recebidos"] == 150,
             f"juros recebidos deixam de contar os R$ 100 estornados: {final['total_juros_recebidos']}")


async def main():
    s = uuid.uuid4().hex[:8]
    uid = f"e2e-desc-{s}"
    h = await criar_credor(uid)
    cliente_id = f"cli-{s}"
    await db.clientes.insert_one({"id": cliente_id, "usuario_id": uid, "nome": "Cliente Desconto",
                                  "telefone": "11999999999", "status": "ativo", "deleted": False,
                                  "created_at": datetime.now(timezone.utc).isoformat()})
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
