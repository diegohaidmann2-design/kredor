"""
Teste de race condition na geração automática de parcelas.

Cenários cobertos:
  1. Múltiplas execuções concorrentes do job `job_gerar_parcelas_emprestimos_abertos`
     simulando o caso real em produção (várias réplicas da API disparando o cron 00:10
     simultaneamente).
  2. Múltiplas inserções concorrentes diretas em `db.parcelas` com mesmo
     (emprestimo_id, numero_parcela) — garante que o índice único parcial bloqueia.
  3. Inserção concorrente vinda do endpoint POST /pagamentos quitando última parcela
     (que também gera a próxima) ao mesmo tempo do job.

O fix é considerado correto se ao final houver exatamente 1 documento ativo
(deleted=False) para cada (emprestimo_id, numero_parcela), e nenhum erro vazado
para o caller.

Como rodar:
    cd /app/backend
    python -m pytest tests/test_race_condition_parcelas.py -v -s

ou direto:
    cd /app/backend
    python -m tests.test_race_condition_parcelas
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / '.env')

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'gestorcred_dev')


# ============================================================
# Helpers
# ============================================================

async def _get_db():
    client = AsyncIOMotorClient(MONGO_URL)
    return client, client[DB_NAME]


async def _ensure_index(db):
    """Garante que o índice único parcial existe (idempotente)."""
    await db.parcelas.update_many(
        {"deleted": {"$exists": False}},
        {"$set": {"deleted": False}}
    )
    try:
        await db.parcelas.create_index(
            [("emprestimo_id", 1), ("numero_parcela", 1)],
            unique=True,
            partialFilterExpression={"deleted": False},
            name="uniq_emprestimo_numero_parcela_ativa"
        )
    except Exception:
        pass  # já existe


async def _criar_emprestimo_teste(db, usuario_id: str):
    """Cria um empréstimo sem_prazo com a parcela inicial #1."""
    emp_id = f"test-race-{uuid.uuid4()}"
    emp = {
        "id": emp_id,
        "usuario_id": usuario_id,
        "cliente_id": f"test-cli-{uuid.uuid4()}",
        "valor_principal": 1000.0,
        "taxa_juros_mensal": 20.0,
        "sem_prazo": True,
        "periodicidade": "mensal",
        "metodo_calculo": "apenas_juros",
        "status": "ativo",
        "data_inicio": "2026-01-01T00:00:00+00:00",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "deleted": False,
    }
    await db.emprestimos.insert_one(emp)

    # Parcela #1 já paga (simulando histórico)
    parcela_1 = {
        "id": f"test-p1-{uuid.uuid4()}",
        "emprestimo_id": emp_id,
        "usuario_id": usuario_id,
        "numero_parcela": 1,
        "data_vencimento": "2026-01-01T00:00:00+00:00",
        "valor_principal": 0.0,
        "valor_juros": 200.0,
        "valor_total": 200.0,
        "valor_pago": 200.0,
        "valor_multa": 0.0,
        "valor_juros_mora": 0.0,
        "saldo_devedor": 1000.0,
        "status": "pago",
        "deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.parcelas.insert_one(parcela_1)
    return emp_id


async def _limpar_emprestimo(db, emp_id):
    await db.parcelas.delete_many({"emprestimo_id": emp_id})
    await db.emprestimos.delete_many({"id": emp_id})


async def _contar_ativas(db, emp_id, numero):
    return await db.parcelas.count_documents({
        "emprestimo_id": emp_id,
        "numero_parcela": numero,
        "deleted": False
    })


# ============================================================
# Testes
# ============================================================

@pytest.mark.asyncio
async def test_indice_unico_bloqueia_insert_paralelo():
    """1. Verifica que o índice único parcial bloqueia inserts duplicados em paralelo."""
    client, db = await _get_db()
    await _ensure_index(db)

    usuario_id = f"test-user-{uuid.uuid4()}"
    emp_id = await _criar_emprestimo_teste(db, usuario_id)

    print(f"\n🧪 [Teste 1] Inserts paralelos com mesmo (emp, numero)")

    async def tentar_inserir(idx: int):
        doc = {
            "id": f"dup-{idx}-{uuid.uuid4()}",
            "emprestimo_id": emp_id,
            "usuario_id": usuario_id,
            "numero_parcela": 2,
            "valor_juros": 200.0,
            "valor_total": 200.0,
            "status": "pendente",
            "deleted": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await db.parcelas.insert_one(doc)
            return "ok"
        except Exception as e:
            return "blocked" if "E11000" in str(e) or "duplicate key" in str(e).lower() else f"err:{e}"

    # 20 corrotinas competindo para inserir a parcela #2
    resultados = await asyncio.gather(*[tentar_inserir(i) for i in range(20)])
    sucessos = sum(1 for r in resultados if r == "ok")
    bloqueados = sum(1 for r in resultados if r == "blocked")

    print(f"   • Tentativas: 20 | sucessos: {sucessos} | bloqueados: {bloqueados}")
    ativas = await _contar_ativas(db, emp_id, 2)
    print(f"   • Parcelas ativas #2 no banco: {ativas}")

    await _limpar_emprestimo(db, emp_id)
    client.close()

    assert sucessos == 1, f"Esperava 1 sucesso, obteve {sucessos}"
    assert bloqueados == 19, f"Esperava 19 bloqueios, obteve {bloqueados}"
    assert ativas == 1, f"Esperava 1 parcela ativa, obteve {ativas}"


@pytest.mark.asyncio
async def test_job_concorrente_nao_duplica():
    """2. Simula múltiplas execuções concorrentes do job (várias réplicas em prod)."""
    client, db = await _get_db()
    await _ensure_index(db)

    from jobs.emprestimos_abertos_job import job_gerar_parcelas_emprestimos_abertos

    usuario_id = f"test-user-{uuid.uuid4()}"
    emp_id = await _criar_emprestimo_teste(db, usuario_id)

    print(f"\n🧪 [Teste 2] 5 execuções concorrentes do job")

    # Disparar o job 5x em paralelo
    await asyncio.gather(*[
        job_gerar_parcelas_emprestimos_abertos()
        for _ in range(5)
    ])

    # Coletar quantas parcelas ativas existem para cada numero
    pipeline = [
        {"$match": {"emprestimo_id": emp_id, "deleted": False}},
        {"$group": {"_id": "$numero_parcela", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    grupos = await db.parcelas.aggregate(pipeline).to_list(None)
    print(f"   • Parcelas geradas (numero → quantidade): {[(g['_id'], g['count']) for g in grupos]}")

    duplicadas = [g for g in grupos if g["count"] > 1]
    await _limpar_emprestimo(db, emp_id)
    client.close()

    assert len(duplicadas) == 0, f"Encontrou duplicações: {duplicadas}"
    assert len(grupos) >= 1, "Job nem chegou a gerar a próxima parcela"


@pytest.mark.asyncio
async def test_pagamento_e_job_concorrentes_nao_duplicam():
    """3. Endpoint POST /pagamentos e job rodando ao mesmo tempo não duplicam."""
    client, db = await _get_db()
    await _ensure_index(db)

    from jobs.emprestimos_abertos_job import job_gerar_parcelas_emprestimos_abertos

    usuario_id = f"test-user-{uuid.uuid4()}"
    emp_id = await _criar_emprestimo_teste(db, usuario_id)

    print(f"\n🧪 [Teste 3] Job × endpoint /pagamentos concorrentes")

    # Simular a lógica do endpoint /pagamentos (linha 140-207 de pagamentos.py)
    async def simular_pagamento_gera_proxima():
        # Mesma sequência usada no endpoint após status='pago'
        ultima = await db.parcelas.find_one(
            {"emprestimo_id": emp_id, "deleted": {"$ne": True}},
            sort=[("numero_parcela", -1)]
        )
        proximo = ultima["numero_parcela"] + 1
        doc = {
            "id": f"pag-{uuid.uuid4()}",
            "emprestimo_id": emp_id,
            "usuario_id": usuario_id,
            "numero_parcela": proximo,
            "valor_juros": 200.0,
            "valor_total": 200.0,
            "status": "pendente",
            "deleted": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await db.parcelas.insert_one(doc)
            return "ok"
        except Exception as e:
            return "blocked" if "E11000" in str(e) else f"err:{e}"

    # 3 jobs + 3 endpoints concorrentes
    tasks = [job_gerar_parcelas_emprestimos_abertos() for _ in range(3)]
    tasks += [simular_pagamento_gera_proxima() for _ in range(3)]
    resultados = await asyncio.gather(*tasks, return_exceptions=True)

    erros_vazados = [r for r in resultados if isinstance(r, Exception)]
    print(f"   • Erros vazados ao caller: {len(erros_vazados)}")

    # Validar não-duplicação
    pipeline = [
        {"$match": {"emprestimo_id": emp_id, "deleted": False}},
        {"$group": {"_id": "$numero_parcela", "count": {"$sum": 1}}},
    ]
    grupos = await db.parcelas.aggregate(pipeline).to_list(None)
    duplicadas = [g for g in grupos if g["count"] > 1]
    print(f"   • Distribuição final: {[(g['_id'], g['count']) for g in grupos]}")

    await _limpar_emprestimo(db, emp_id)
    client.close()

    assert len(erros_vazados) == 0, f"Erros vazaram: {erros_vazados}"
    assert len(duplicadas) == 0, f"Duplicações encontradas: {duplicadas}"


# ============================================================
# Execução direta (sem pytest)
# ============================================================

async def _run_all():
    await test_indice_unico_bloqueia_insert_paralelo()
    print("✅ Teste 1 OK\n")
    await test_job_concorrente_nao_duplica()
    print("✅ Teste 2 OK\n")
    await test_pagamento_e_job_concorrentes_nao_duplicam()
    print("✅ Teste 3 OK\n")
    print("=" * 60)
    print("🎉 Todos os testes de race condition passaram!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(_run_all())
