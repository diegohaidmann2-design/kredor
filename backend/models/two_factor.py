"""
Modelo para Autenticação de Dois Fatores (2FA)
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid


class TwoFactorCode(BaseModel):
    """
    Código de verificação 2FA
    - Código de 6 dígitos
    - Expira em 10 minutos
    - Máximo 3 tentativas
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    usuario_id: str
    codigo: str  # 6 dígitos
    tentativas: int = 0
    max_tentativas: int = 3
    usado: bool = False
    criado_em: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expira_em: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=10))
    usado_em: Optional[datetime] = None


class TwoFactorVerifyRequest(BaseModel):
    """Request para verificar código 2FA"""
    email: str
    codigo: str


class TwoFactorResendRequest(BaseModel):
    """Request para reenviar código 2FA"""
    email: str


class TwoFactorToggleRequest(BaseModel):
    """Request para ativar/desativar 2FA"""
    enabled: bool
    senha: str  # Requer confirmação de senha
