"""
Modelos para o Portal do Cliente (Self-Service)
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import uuid


class PortalAuth(BaseModel):
    """Modelo de autenticação do portal do cliente"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cliente_id: str = Field(..., description="ID do cliente")
    usuario_id: str = Field(..., description="ID do usuário (dono do cliente)")
    codigo_acesso: str = Field(..., min_length=6, max_length=6, description="Código de 6 dígitos")
    codigo_criado_em: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ultimo_acesso: Optional[datetime] = None
    tentativas_falhas: int = Field(default=0, description="Contador de tentativas de login")
    bloqueado_ate: Optional[datetime] = None
    ativo: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PortalLoginRequest(BaseModel):
    """Request de login no portal"""
    cpf_cnpj: str = Field(..., min_length=11, max_length=18, description="CPF ou CNPJ do cliente")
    codigo_acesso: str = Field(..., min_length=6, max_length=6, description="Código de acesso")


class PortalLoginResponse(BaseModel):
    """Response de login no portal"""
    access_token: str
    token_type: str = "bearer"
    cliente: dict


class PortalSolicitarCodigoRequest(BaseModel):
    """Request para solicitar código de acesso"""
    cpf_cnpj: str = Field(..., min_length=11, max_length=18, description="CPF ou CNPJ do cliente")
    email: str = Field(..., description="Email do cliente para confirmação")


class PortalAlterarCodigoRequest(BaseModel):
    """Request para alterar código de acesso"""
    codigo_atual: str = Field(..., min_length=6, max_length=6)
    codigo_novo: str = Field(..., min_length=6, max_length=6)
    codigo_novo_confirmacao: str = Field(..., min_length=6, max_length=6)


class PortalClienteInfo(BaseModel):
    """Informações do cliente para o portal"""
    id: str
    nome: str
    cpf_cnpj: str
    telefone: str
    email: Optional[str]
    status: str
    total_emprestimos: int = 0
    emprestimos_ativos: int = 0
    total_devido_centavos: int = 0
    proxima_parcela: Optional[dict] = None
