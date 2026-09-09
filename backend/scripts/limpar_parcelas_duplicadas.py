"""
Script de limpeza de parcelas duplicadas causadas pela race condition
do scheduler job_gerar_parcelas_emprestimos_abertos.

Estratégia:
- Para cada grupo (emprestimo_id, numero_parcela) com count > 1:
  - Calcula um "peso" para cada parcela: prioriza a que tem pagamentos referenciados,
    em segundo lugar a com valor_pago_centavos > 0, em terceiro a mais antiga (created_at).
  - Mantém a vencedora; soft-delete (deleted=True) nas restantes.

Execução:
  python -m scripts.limpar_parcelas_duplicadas             # dry-run
  python -m scripts.limpar_parcelas_duplicadas --apply     # aplica
"""
import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / '.env')

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'gestorcred_dev')


async def main(apply: bool):
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print(f"📌 DB: {DB_NAME} | apply={apply}")

    # Encontrar grupos duplicados (apenas não deletadas)
    pipeline = [
        {"$match": {"deleted": {"$ne": True}}},
        {"$group": {
            "_id": {"emp": "$emprestimo_id", "num": "$numero_parcela"},
            "count": {"$sum": 1},
            "docs": {"$push": {
                "id": "$id",
                "created_at": "$created_at",
                "valor_pago_centavos": {"$ifNull": ["$valor_pago_centavos", 0]},
                "status": "$status"
            }}
        }},
        {"$match": {"count": {"$gt": 1}}}
    ]
    dups = await db.parcelas.aggregate(pipeline).to_list(None)
    print(f"🔎 Grupos duplicados encontrados: {len(dups)}")

    total_to_remove = 0
    actions = []
    for g in dups:
        emp = g["_id"]["emp"]
        num = g["_id"]["num"]
        docs = g["docs"]

        # Coletar IDs de parcelas com pagamentos referenciados
        ids = [d["id"] for d in docs]
        pagamentos_count = {}
        cursor = db.pagamentos.find(
            {"parcela_id": {"$in": ids}},
            {"parcela_id": 1, "_id": 0}
        )
        async for p in cursor:
            pagamentos_count[p["parcela_id"]] = pagamentos_count.get(p["parcela_id"], 0) + 1

        def score(d):
            # Quanto MAIOR o score, mais "vencedor" o documento é
            return (
                pagamentos_count.get(d["id"], 0),
                float(d.get("valor_pago_centavos", 0) or 0),
                # mais antigo vence -> usar negativo da timestamp como segundo critério
                -1 * (datetime.fromisoformat(d["created_at"].replace("Z", "+00:00")).timestamp()
                      if isinstance(d["created_at"], str) else 0)
            )

        docs_sorted = sorted(docs, key=score, reverse=True)
        keeper = docs_sorted[0]
        losers = docs_sorted[1:]

        actions.append({
            "emprestimo_id": emp,
            "numero_parcela": num,
            "keeper": keeper["id"],
            "losers": [l["id"] for l in losers],
            "pagamentos_no_keeper": pagamentos_count.get(keeper["id"], 0),
            "pagamentos_nos_losers": [pagamentos_count.get(l["id"], 0) for l in losers],
        })
        total_to_remove += len(losers)

    # Exibir plano
    print(f"\n📋 Plano de limpeza ({total_to_remove} parcela(s) a soft-delete):")
    for a in actions:
        print(f"  - emp {a['emprestimo_id'][:8]} #{a['numero_parcela']}: keeper={a['keeper'][:8]} "
              f"(pgto={a['pagamentos_no_keeper']}) | losers={[l[:8] for l in a['losers']]} "
              f"(pgtos={a['pagamentos_nos_losers']})")

    if not apply:
        print("\n⚠️ DRY-RUN. Rode com --apply para executar.")
        client.close()
        return

    # Aplicar: re-vincular pagamentos + soft-delete dos losers
    now = datetime.now(timezone.utc).isoformat()
    total_atualizados = 0
    total_pgto_relink = 0
    for a in actions:
        keeper_id = a["keeper"]
        for loser_id in a["losers"]:
            # 1. Re-vincular pagamentos do loser para o keeper (preserva histórico)
            res_pgto = await db.pagamentos.update_many(
                {"parcela_id": loser_id},
                {"$set": {"parcela_id": keeper_id},
                 "$push": {"observacoes_sistema": f"Re-vinculado de parcela duplicada {loser_id} em {now}"}}
            )
            total_pgto_relink += res_pgto.modified_count

            # 2. Soft-delete do loser
            res = await db.parcelas.update_one(
                {"id": loser_id, "deleted": {"$ne": True}},
                {"$set": {
                    "deleted": True,
                    "deleted_at": now,
                    "deleted_by": "system:limpar_parcelas_duplicadas",
                    "deleted_motivo": f"Duplicata por race condition do job (mantida {keeper_id})"
                }}
            )
            total_atualizados += res.modified_count

        # 3. Recalcular valor_pago_centavos e status do keeper a partir dos pagamentos
        soma = await db.pagamentos.aggregate([
            {"$match": {"parcela_id": keeper_id, "deleted": {"$ne": True}}},
            {"$group": {"_id": None, "total": {"$sum": "$valor_pago_centavos"}}}
        ]).to_list(1)
        soma_pago = soma[0]["total"] if soma else 0

        keeper_doc = await db.parcelas.find_one({"id": keeper_id}, {"_id": 0})
        if keeper_doc:
            valor_devido = (
                keeper_doc.get("valor_total_centavos", 0)
                + keeper_doc.get("valor_multa_centavos", 0)
                + keeper_doc.get("valor_juros_mora_centavos", 0)
            )
            novo_status = keeper_doc.get("status")
            if soma_pago > 0:
                novo_status = "pago" if soma_pago >= valor_devido else "parcial"
            await db.parcelas.update_one(
                {"id": keeper_id},
                {"$set": {"valor_pago_centavos": soma_pago, "status": novo_status}}
            )

    print(f"\n✅ Aplicado:")
    print(f"   - {total_atualizados} parcela(s) marcada(s) como deleted=True")
    print(f"   - {total_pgto_relink} pagamento(s) re-vinculado(s) ao keeper")
    client.close()


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    asyncio.run(main(apply))
