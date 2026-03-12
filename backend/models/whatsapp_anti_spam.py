"""
Modelo de configuração Anti-Spam para WhatsApp
Baseado nas melhores práticas de 2026
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class WhatsAppTier(BaseModel):
    """Níveis de envio do WhatsApp Business API"""
    tier: Literal[0, 1, 2, 3, 4] = 1
    limite_diario: int = 1000
    limite_por_segundo: int = 20
    descricao: str = "Tier 1 - Contas verificadas"

class ConfigAntiSpam(BaseModel):
    """Configuração de Anti-Spam por usuário"""
    tipo: str = "whatsapp_anti_spam"
    
    # Tier atual
    tier_atual: int = Field(default=1, ge=0, le=4)
    
    # Limites
    limite_diario: int = Field(default=1000, description="Mensagens por dia")
    limite_por_hora: int = Field(default=100, description="Mensagens por hora")
    limite_por_minuto: int = Field(default=20, description="Mensagens por minuto")
    
    # Delays (em segundos)
    delay_minimo: int = Field(default=30, description="Delay mínimo entre mensagens")
    delay_maximo: int = Field(default=90, description="Delay máximo entre mensagens")
    delay_entre_lotes: int = Field(default=300, description="Delay entre lotes (5min)")
    tamanho_lote: int = Field(default=50, description="Tamanho do lote")
    
    # Warming Up (Aquecimento)
    warming_up_ativo: bool = Field(default=False, description="Modo aquecimento ativo")
    warming_up_dia: int = Field(default=0, description="Dia atual do warming up (0-14)")
    warming_up_inicio: Optional[str] = Field(default=None, description="Data de início")
    
    # Horário comercial
    horario_inicio: str = Field(default="08:00", description="Início do horário comercial")
    horario_fim: str = Field(default="20:00", description="Fim do horário comercial")
    enviar_fora_horario: bool = Field(default=False, description="Permitir envio fora do horário")
    
    # Dias da semana (0=Dom, 6=Sáb)
    dias_permitidos: list = Field(default=[1,2,3,4,5], description="Dias da semana permitidos")
    
    # Qualidade
    max_mensagens_identicas: int = Field(default=0, description="Máx de msgs idênticas seguidas (0=sem limite)")
    exigir_variacao_template: bool = Field(default=True, description="Exigir variação nos templates")
    
    # Monitoramento
    contador_hoje: int = Field(default=0, description="Contador de mensagens hoje")
    contador_hora: int = Field(default=0, description="Contador da hora atual")
    contador_minuto: int = Field(default=0, description="Contador do minuto atual")
    ultima_mensagem: Optional[str] = Field(default=None, description="Timestamp da última mensagem")
    ultima_reset_dia: Optional[str] = Field(default=None, description="Último reset diário")
    
    # Estatísticas de qualidade
    total_enviadas: int = Field(default=0, description="Total de mensagens enviadas")
    total_bloqueios: int = Field(default=0, description="Total de bloqueios/reports")
    total_opt_outs: int = Field(default=0, description="Total de opt-outs")
    taxa_qualidade: float = Field(default=100.0, description="Taxa de qualidade (%)")
    
    # Fila
    fila_ativa: bool = Field(default=True, description="Sistema de fila ativo")
    processar_fila_automatico: bool = Field(default=True, description="Processar fila automaticamente")
    
    # Status
    status: Literal["ativo", "pausado", "bloqueado"] = "ativo"
    razao_bloqueio: Optional[str] = None


# Limites por Tier (baseado em 2026)
TIERS_WHATSAPP = {
    0: WhatsAppTier(
        tier=0,
        limite_diario=250,
        limite_por_segundo=10,
        descricao="Tier 0 - Contas não verificadas"
    ),
    1: WhatsAppTier(
        tier=1,
        limite_diario=1000,
        limite_por_segundo=20,
        descricao="Tier 1 - Contas verificadas"
    ),
    2: WhatsAppTier(
        tier=2,
        limite_diario=10000,
        limite_por_segundo=50,
        descricao="Tier 2 - Alto engajamento"
    ),
    3: WhatsAppTier(
        tier=3,
        limite_diario=100000,
        limite_por_segundo=80,
        descricao="Tier 3 - Estabelecido"
    ),
    4: WhatsAppTier(
        tier=4,
        limite_diario=999999,
        limite_por_segundo=1000,
        descricao="Tier 4 - Enterprise"
    )
}

# Limites de Warming Up por dia
WARMING_UP_LIMITS = {
    1: {"diario": 10, "descricao": "Dia 1-2: Início muito gradual"},
    2: {"diario": 20, "descricao": "Dia 3-4: Aumentando gradualmente"},
    3: {"diario": 50, "descricao": "Dia 5-6: Ramping up"},
    4: {"diario": 100, "descricao": "Dia 7-9: Aceleração"},
    5: {"diario": 250, "descricao": "Dia 10-12: Pré-normal"},
    6: {"diario": 500, "descricao": "Dia 13-14: Quase normal"},
    7: {"diario": 1000, "descricao": "Dia 15+: Normal (Tier completo)"}
}
