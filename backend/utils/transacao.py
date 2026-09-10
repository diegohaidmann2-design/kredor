"""Transação multi-documento para os caminhos de dinheiro.

Em replica set (produção) abre uma transação real. Em instância standalone o
servidor não suporta transações:
  - em produção isso é erro fatal (os caminhos de dinheiro exigem atomicidade);
  - em dev/teste degrada para sessão sem atomicidade, mas loga um aviso uma vez
    por processo para que a perda de atomicidade nunca passe despercebida.
A detecção do suporte é feita uma única vez por processo.
"""
from contextlib import asynccontextmanager

from config import client, ENVIRONMENT, MONGO_URL
from services.logging_service import get_logger

logger = get_logger("gestorcred.transacao")

_suporta_transacao: bool | None = None
_avisou_sem_replica = False


async def servidor_suporta_transacao() -> bool:
    global _suporta_transacao
    if _suporta_transacao is None:
        info = await client.admin.command("hello")
        _suporta_transacao = bool(info.get("setName"))
    return _suporta_transacao


@asynccontextmanager
async def transacao():
    """`async with transacao() as sessao:` — passe `session=sessao` em TODA operação do bloco."""
    global _avisou_sem_replica
    async with await client.start_session() as sessao:
        if await servidor_suporta_transacao():
            async with sessao.start_transaction():
                yield sessao
        else:
            if ENVIRONMENT == "production":
                raise RuntimeError(
                    "Transações indisponíveis: MongoDB não está em replica set. "
                    "Em produção os caminhos de dinheiro exigem atomicidade."
                )
            if not _avisou_sem_replica:
                _avisou_sem_replica = True
                logger.warning(
                    "MongoDB sem replica set: caminhos de dinheiro rodando SEM atomicidade",
                    data={"mongo_url_tem_replica_set": "replicaSet" in MONGO_URL},
                )
            yield sessao
