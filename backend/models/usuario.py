"""
Modelo de Usuário
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Literal, Optional, List
from datetime import datetime, timezone, timedelta
import uuid


class Usuario(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nome: str
    email: EmailStr
    perfil: Literal["superadmin", "admin", "usuario"] = "usuario"
    ativo: bool = True
    
    # Campo para hierarquia (Dono -> Funcionário)
    owner_id: Optional[str] = None  # Se None, é o dono da conta. Se preenchido, é um funcionário.
    permissoes: List[str] = []  # Lista de permissões específicas
    cargo: Optional[str] = None  # Ex: Vendedor, Gerente
    convite_pendente: bool = False  # Se True, usuário foi convidado mas não completou cadastro
    
    # Verificação de email
    email_verificado: bool = False
    email_verification_token: Optional[str] = None
    email_verification_sent_at: Optional[datetime] = None
    
    # Autenticação de Dois Fatores (2FA)
    two_factor_enabled: bool = False
    two_factor_activated_at: Optional[datetime] = None
    
    # Assinatura
    plano: str = "trial"  # trial, basico, profissional, enterprise
    plano_ativo: bool = True  # Trial começa ativo
    data_inicio_trial: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_fim_trial: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=7))
    data_vencimento_assinatura: Optional[datetime] = None
    data_expiracao_plano: Optional[datetime] = None  # Data de expiração unificada para planos pagos
    
    # Gateway IDs (Asaas + SyncPay)
    asaas_customer_id: Optional[str] = None
    asaas_subscription_id: Optional[str] = None
    syncpay_customer_id: Optional[str] = None
    syncpay_transaction_id: Optional[str] = None
    
    # Onboarding
    onboarding_completed: bool = False
    onboarding_step: int = 0  # Último step do tour completado
    onboarding_tasks: dict = Field(default_factory=lambda: {
        "perfil_completo": False,
        "primeiro_cliente": False,
        "primeiro_emprestimo": False,
        "primeiro_pagamento": False,
        "primeiro_contrato": False,
        "configuracoes": False
    })
    onboarding_tour_finished: bool = False
    onboarding_started_at: Optional[datetime] = None
    onboarding_completed_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class LoginResponse(BaseModel):
    token: str
    usuario: Usuario

