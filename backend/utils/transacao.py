"""Transação multi-documento para os caminhos de dinheiro.

Em replica set (produção) abre uma transação real; em instância standalone o
servidor não suporta transações, então apenas a sessão é aberta e as operações
rodam sem atomicidade. A detecção é feita uma única vez por processo.
"""
from contextlib import asynccontextmanager

from config import client

_suporta_transacao: bool | None = None


async def servidor_suporta_transacao() -> bool:
    global _suporta_transacao
    if _suporta_transacao is None:
        info = await client.admin.command("hello")
        _suporta_transacao = bool(info.get("setName"))
    return _suporta_transacao


@asynccontextmanager
async def transacao():
    """`async with transacao() as sessao:` — passe `session=sessao` em TODA operação do bloco."""
    async with await client.start_session() as sessao:
        if await servidor_suporta_transacao():
            async with sessao.start_transaction():
                yield sessao
        else:
            yield sessao
