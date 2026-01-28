"""
Modelo de Notificação - Sistema Gestor Cred
Suporte a múltiplos tipos de notificações para usuários e admins
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, timezone
import uuid


# Tipos de notificação suportados
TIPOS_NOTIFICACAO = Literal[
    # Notificações de empréstimos/parcelas
    "vencimento",           # Parcela próxima do vencimento
    "atraso",               # Parcela em atraso
    "pagamento",            # Pagamento recebido
    
    # Notificações de sistema
    "sistema",              # Mensagem genérica do sistema
    "boas_vindas",          # Boas-vindas ao novo usuário
    
    # Notificações de assinatura
    "assinatura_expirando", # Assinatura próxima de expirar
    "assinatura_expirada",  # Assinatura expirou
    "trial_expirando",      # Trial próximo de expirar
    "trial_expirado",       # Trial expirou
    "plano_atualizado",     # Plano foi atualizado
    
    # Notificações de suporte
    "suporte_novo",         # Novo ticket de suporte (para admin)
    "suporte_resposta",     # Resposta no ticket
    "suporte_mensagem",     # Nova mensagem no ticket
    "suporte_resolvido",    # Ticket resolvido
    
    # Notificações para admin
    "admin_novo_usuario",   # Novo usuário cadastrado
    "admin_novo_cliente",   # Novo cliente cadastrado no sistema
    "admin_emprestimo_atraso", # Empréstimo em atraso (visão global)
    "admin_resumo_diario",  # Resumo diário do sistema
    "admin_alerta",         # Alerta importante para admin
]


class Notificacao(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    usuario_id: Optional[str] = None
    tipo: str  # Aceita qualquer string para flexibilidade
    titulo: str
    mensagem: str
    cliente_id: Optional[str] = None
    emprestimo_id: Optional[str] = None
    lida: bool = False
    link: Optional[str] = None  # Link para navegação
    dados_referencia: Optional[dict] = None
    prioridade: str = "normal"  # baixa, normal, alta, urgente
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NotificacaoCreate(BaseModel):
    tipo: str
    titulo: str
    mensagem: str
    link: Optional[str] = None
    dados_referencia: Optional[dict] = None
    prioridade: str = "normal"
