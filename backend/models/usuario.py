"""
Modelo de Usuário
"""
from pydantic import BaseModel, BeforeValidator, Field, EmailStr
from typing import Annotated, Literal, Optional, List
from datetime import datetime, timezone, timedelta

from config import TRIAL_DIAS
import uuid


def normalizar_email(email: Optional[str]) -> Optional[str]:
    """Email em minúsculas e sem espaço nas pontas.

    O índice único de `usuarios.email` é sensível a maiúsculas: sem isto, "Joao@x.com" e
    "joao@x.com" são duas contas, a checagem de duplicado não pega e quem foi cadastrado com
    inicial maiúscula não entra digitando minúscula. Normaliza-se em TODA fronteira que
    grava ou busca por email.
    """
    if email is None:
        return None
    return email.strip().lower()


def _normalizar(valor):
    return normalizar_email(valor) if isinstance(valor, str) else valor


# Tipo usado em todo modelo que recebe email da borda: a normalização acontece na validação,
# antes de qualquer find_one ou insert, então nenhuma rota precisa lembrar de chamá-la.
EmailNormalizado = Annotated[EmailStr, BeforeValidator(_normalizar)]


class Usuario(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nome: str
    email: EmailNormalizado
    perfil: Literal["admin", "usuario"] = "usuario"
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
    # Bypass manual de limites de plano (enterprise vitalício). NÃO dá acesso ao painel da plataforma.
    plano_ilimitado: bool = False
    data_inicio_trial: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_fim_trial: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=TRIAL_DIAS))
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


class UsuarioPublico(BaseModel):
    """Modelo público do usuário — sem campos sensíveis"""
    id: str
    nome: str
    email: str
    perfil: str
    ativo: bool
    owner_id: Optional[str] = None
    permissoes: List[str] = []
    cargo: Optional[str] = None
    email_verificado: bool = False
    two_factor_enabled: bool = False
    plano: str = "trial"
    plano_ativo: bool = True
    plano_ilimitado: bool = False
    data_inicio_trial: Optional[datetime] = None
    data_fim_trial: Optional[datetime] = None
    data_vencimento_assinatura: Optional[datetime] = None
    data_expiracao_plano: Optional[datetime] = None
    asaas_customer_id: Optional[str] = None
    syncpay_customer_id: Optional[str] = None
    onboarding_completed: bool = False
    onboarding_step: int = 0
    onboarding_tasks: dict = Field(default_factory=dict)
    onboarding_tour_finished: bool = False
    created_at: Optional[datetime] = None


class UsuarioCreate(BaseModel):
    nome: str
    email: EmailNormalizado
    senha: str
    turnstile_token: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailNormalizado
    senha: str
    turnstile_token: Optional[str] = None


class LoginResponse(BaseModel):
    token: str
    usuario: Usuario

