"""Atomicidade do registro de pagamento.

Exige um MongoDB em replica set (transações). Defina MONGO_URL_TESTE_RS
(ex.: mongodb://localhost:27018/?replicaSet=rs0); sem ela o teste é pulado.
Simula falha no meio do fluxo (após o insert do pagamento) e verifica que
NADA foi persistido: nem pagamento, nem baixa da parcela.
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

import pytest

URL_RS = os.environ.get("MONGO_URL_TESTE_RS")
pytestmark = pytest.mark.skipif(not URL_RS, reason="MONGO_URL_TESTE_RS não definida (replica set necessário)")

if URL_RS:
    os.environ["MONGO_URL"] = URL_RS
    os.environ["DB_NAME"] = "kredor_teste_transacao"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_LOOP = asyncio.new_event_loop()


def _rodar(coro):
    """Motor amarra o client ao primeiro loop; usamos um único loop para todos os testes."""
    return _LOOP.run_until_complete(coro)


class _Usuario:
    id = "u-teste"
    email = "teste@kredor.com.br"
    perfil = "admin"
    owner_id = None


class _Client:
    host = "127.0.0.1"


class _Request:
    client = _Client()
    headers = {}


async def _cenario(db):
    await db.parcelas.delete_many({})
    await db.pagamentos.delete_many({})
    await db.emprestimos.delete_many({})
    emp_id, parc_id = str(uuid.uuid4()), str(uuid.uuid4())
    await db.emprestimos.insert_one({"id": emp_id, "usuario_id": "u-teste", "cliente_id": "c1", "status": "ativo",
                                     "valor_principal_centavos": 100000, "sem_prazo": False})
    await db.parcelas.insert_one({"id": parc_id, "emprestimo_id": emp_id, "usuario_id": "u-teste", "numero_parcela": 1,
                                  "status": "pendente", "valor_total_centavos": 10000, "valor_pago_centavos": 0,
                                  "data_vencimento": datetime.now(timezone.utc).isoformat()})
    return emp_id, parc_id


def test_servidor_suporta_transacao():
    from utils.transacao import servidor_suporta_transacao
    assert _rodar(servidor_suporta_transacao()) is True


def test_falha_no_meio_nao_persiste_nada(monkeypatch):
    from config import db
    import routes.pagamentos as rp
    from models.pagamento import PagamentoCreate
    from services import auth_utils

    monkeypatch.setattr(rp, "is_owner", lambda u: True)
    monkeypatch.setattr(rp, "get_user_context", lambda u: "u-teste")

    from motor.motor_asyncio import AsyncIOMotorCollection

    original_update_one = AsyncIOMotorCollection.update_one

    async def update_one_explode(self, *args, **kwargs):
        raise RuntimeError("falha simulada após o insert do pagamento")

    async def executar():
        emp_id, parc_id = await _cenario(db)
        # `db.parcelas` cria um objeto novo a cada acesso; o patch precisa ser na classe.
        monkeypatch.setattr(AsyncIOMotorCollection, "update_one", update_one_explode)
        with pytest.raises(RuntimeError):
            await rp.registrar_pagamento(
                PagamentoCreate(parcela_id=parc_id, valor_pago=100.0, metodo_pagamento="pix"),
                _Request(), _Usuario(),
            )
        monkeypatch.setattr(AsyncIOMotorCollection, "update_one", original_update_one)
        assert await db.pagamentos.count_documents({"parcela_id": parc_id}) == 0
        parcela = await db.parcelas.find_one({"id": parc_id})
        assert parcela["valor_pago_centavos"] == 0
        assert parcela["status"] == "pendente"

    _rodar(executar())


def test_fluxo_completo_persiste_tudo(monkeypatch):
    from config import db
    import routes.pagamentos as rp
    from models.pagamento import PagamentoCreate

    monkeypatch.setattr(rp, "is_owner", lambda u: True)
    monkeypatch.setattr(rp, "get_user_context", lambda u: "u-teste")

    async def registrar_auditoria_fake(**kwargs):
        return None

    monkeypatch.setattr(rp, "registrar_auditoria", registrar_auditoria_fake)

    async def executar():
        emp_id, parc_id = await _cenario(db)
        await rp.registrar_pagamento(
            PagamentoCreate(parcela_id=parc_id, valor_pago=100.0, metodo_pagamento="pix"),
            _Request(), _Usuario(),
        )
        assert await db.pagamentos.count_documents({"parcela_id": parc_id}) == 1
        parcela = await db.parcelas.find_one({"id": parc_id})
        assert parcela["valor_pago_centavos"] == 10000 and parcela["status"] == "pago"
        emp = await db.emprestimos.find_one({"id": emp_id})
        assert emp["status"] == "quitado"

    _rodar(executar())
