"""
Modelo de Auditoria
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import uuid


class AuditLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    usuario_id: str
    usuario_email: str
    acao: str  # criar, editar, deletar, login, logout
    entidade: str  # cliente, emprestimo, pagamento, etc.
    entidade_id: Optional[str] = None
    detalhes: str
    dados_anteriores: Optional[dict] = None
    dados_novos: Optional[dict] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
