"""
Serviço de auditoria
"""
from datetime import datetime, timezone
from config import db
from models.auditoria import AuditLog


async def registrar_auditoria(
    usuario_id: str,
    usuario_email: str,
    acao: str,
    entidade: str,
    detalhes: str,
    entidade_id: str = None,
    dados_anteriores: dict = None,
    dados_novos: dict = None,
    ip: str = None,
    user_agent: str = None
) -> AuditLog:
    """Registra uma ação no log de auditoria"""
    log = AuditLog(
        usuario_id=usuario_id,
        usuario_email=usuario_email,
        acao=acao,
        entidade=entidade,
        entidade_id=entidade_id,
        detalhes=detalhes,
        dados_anteriores=dados_anteriores,
        dados_novos=dados_novos,
        ip=ip,
        user_agent=user_agent
    )
    log_doc = log.model_dump()
    log_doc["created_at"] = log_doc["created_at"].isoformat()
    await db.auditoria.insert_one(log_doc)
    return log
