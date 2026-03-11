"""
Modelos para WhatsApp e Evolution API
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, timezone
import uuid


class EvolutionAPIConfig(BaseModel):
    """Configuração global da Evolution API (Super Admin)"""
    habilitado: bool = False
    api_url: str = ""  # Ex: https://evo.exemplo.com
    api_key: str = ""
    global_webhook_url: str = ""  # Webhook global para eventos
    timeout: int = 30
    max_tentativas_envio: int = 3


class WhatsAppConexao(BaseModel):
    """Conexão WhatsApp de um usuário"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    usuario_id: str
    instance_name: str  # Nome da instância na Evolution API
    instance_id: Optional[str] = None  # ID retornado pela Evolution
    numero_telefone: Optional[str] = None
    status: Literal["desconectado", "qrcode", "conectado", "erro"] = "desconectado"
    qr_code: Optional[str] = None  # Base64 do QR Code
    qr_code_expiracao: Optional[datetime] = None
    data_conexao: Optional[datetime] = None
    data_ultima_mensagem: Optional[datetime] = None
    ativo: bool = True
    webhook_url: Optional[str] = None
    deleted: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WhatsAppMensagem(BaseModel):
    """Histórico de mensagens enviadas"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    usuario_id: str
    conexao_id: str
    cliente_id: Optional[str] = None
    emprestimo_id: Optional[str] = None
    parcela_id: Optional[str] = None
    numero_destino: str
    mensagem: str
    tipo: Literal["cobranca", "lembrete", "confirmacao", "manual"] = "manual"
    status: Literal["enviando", "enviado", "entregue", "lido", "falha"] = "enviando"
    message_id: Optional[str] = None  # ID retornado pela API
    erro: Optional[str] = None
    tentativas: int = 0
    data_envio: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_entrega: Optional[datetime] = None
    data_leitura: Optional[datetime] = None


class EnviarMensagemRequest(BaseModel):
    """Request para enviar mensagem"""
    numero_destino: str
    mensagem: str
    cliente_id: Optional[str] = None
    emprestimo_id: Optional[str] = None
    parcela_id: Optional[str] = None
    tipo: Literal["cobranca", "lembrete", "confirmacao", "manual"] = "manual"
