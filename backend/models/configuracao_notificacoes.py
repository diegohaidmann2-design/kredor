"""
Modelos de Configuração de Notificações - Sistema Gestor Cred
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class PeriodoNotificacao(BaseModel):
    """Período de envio de notificação"""
    dias: int = Field(..., description="Número de dias (positivo ou negativo)")
    momento: Literal["antes", "no_dia", "depois"] = Field(..., description="Momento em relação ao vencimento")
    ativo: bool = Field(default=True, description="Se este período está ativo")
    hora_envio: str = Field(default="09:00", description="Hora do dia para enviar (HH:MM)")


class CanaisNotificacao(BaseModel):
    """Canais de envio de notificações"""
    sistema: bool = Field(default=True, description="Notificações internas do sistema")
    whatsapp: bool = Field(default=False, description="Enviar via WhatsApp")
    email: bool = Field(default=False, description="Enviar via Email")


class HorarioComercial(BaseModel):
    """Configuração de horário comercial para envio de notificações"""
    ativo: bool = Field(default=True, description="Se deve respeitar horário comercial")
    hora_inicio: str = Field(default="08:00", description="Hora de início (HH:MM)")
    hora_fim: str = Field(default="20:00", description="Hora de término (HH:MM)")
    dias_permitidos: List[int] = Field(
        default=[1, 2, 3, 4, 5], 
        description="Dias da semana permitidos (0=domingo, 1=segunda, ..., 6=sábado)"
    )
    enviar_fora_horario: bool = Field(
        default=False, 
        description="Se permite envio fora do horário comercial"
    )


class ConfiguracaoNotificacoes(BaseModel):
    """Configuração completa de notificações automáticas"""
    periodos: List[PeriodoNotificacao] = Field(
        default_factory=lambda: [
            PeriodoNotificacao(dias=3, momento="antes", ativo=True, hora_envio="09:00"),
            PeriodoNotificacao(dias=0, momento="no_dia", ativo=True, hora_envio="09:00"),
            PeriodoNotificacao(dias=3, momento="depois", ativo=True, hora_envio="10:00")
        ],
        description="Períodos para envio de notificações"
    )
    canais: CanaisNotificacao = Field(
        default_factory=lambda: CanaisNotificacao(sistema=True, whatsapp=False, email=False),
        description="Canais de envio"
    )
    horario_comercial: HorarioComercial = Field(
        default_factory=lambda: HorarioComercial(),
        description="Configurações de horário comercial"
    )
    template_whatsapp: str = Field(
        default="Olá {cliente_nome}! 👋\n\nParcela #{numero} de R$ {valor} vence em {dias} dias.\n\nData de vencimento: {data_vencimento}",
        description="Template de mensagem WhatsApp"
    )
    template_whatsapp_atraso: str = Field(
        default="Olá {cliente_nome}! ⚠️\n\nA parcela #{numero} de R$ {valor} está em atraso há {dias} dias.\n\nData de vencimento: {data_vencimento}\n\nPor favor, regularize sua situação.",
        description="Template para mensagens de atraso"
    )
    template_email: Optional[str] = Field(
        default=None,
        description="Template de email (futuro)"
    )
    enviar_para_cliente: bool = Field(
        default=True,
        description="Enviar notificação para o cliente"
    )
    enviar_para_gestor: bool = Field(
        default=False,
        description="Enviar notificação também para o gestor"
    )
    ativo: bool = Field(
        default=True,
        description="Se o sistema de notificações automáticas está ativo"
    )


class ConfiguracaoNotificacoesUpdate(BaseModel):
    """Schema para atualização de configurações"""
    periodos: Optional[List[PeriodoNotificacao]] = None
    canais: Optional[CanaisNotificacao] = None
    horario_comercial: Optional[HorarioComercial] = None
    template_whatsapp: Optional[str] = None
    template_whatsapp_atraso: Optional[str] = None
    template_email: Optional[str] = None
    enviar_para_cliente: Optional[bool] = None
    enviar_para_gestor: Optional[bool] = None
    ativo: Optional[bool] = None
