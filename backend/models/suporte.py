from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class MensagemTicket(BaseModel):
    id: str
    remetente_id: str
    remetente_nome: str
    remetente_tipo: str  # usuario, admin
    conteudo: str
    tipo: str = "texto"  # texto, imagem, arquivo
    arquivo_url: Optional[str] = None
    enviado_em: datetime
    lida: bool = False

class Ticket(BaseModel):
    numero_ticket: str
    usuario_id: str
    usuario_nome: str
    usuario_email: str
    assunto: str
    categoria: str  # emprestimo, pagamento, tecnico, outro
    status: str = "aberto"  # aberto, em_atendimento, resolvido, fechado
    prioridade: str = "media"  # baixa, media, alta, urgente
    mensagens: List[MensagemTicket] = []
    criado_em: datetime
    atualizado_em: datetime
    atribuido_a: Optional[str] = None
    atribuido_nome: Optional[str] = None
    total_mensagens: int = 0
    mensagens_nao_lidas_usuario: int = 0
    mensagens_nao_lidas_admin: int = 0
    tags: List[str] = []

class CriarTicketRequest(BaseModel):
    assunto: str = Field(..., min_length=5, max_length=200)
    categoria: str
    mensagem: str = Field(..., min_length=10)
    prioridade: str = "media"

class CriarTicketAdminRequest(BaseModel):
    usuario_id: str
    assunto: str = Field(..., min_length=5, max_length=200)
    categoria: str
    mensagem: str = Field(..., min_length=10)
    prioridade: str = "media"

class ResponderTicketRequest(BaseModel):
    mensagem: str = Field(..., min_length=1)
    tipo: str = "texto"
    arquivo_url: Optional[str] = None

class AtualizarStatusRequest(BaseModel):
    status: str
    prioridade: Optional[str] = None
