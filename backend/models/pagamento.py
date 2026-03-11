"""
Modelo de Pagamento
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime, timezone
import uuid


class Pagamento(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parcela_id: str
    emprestimo_id: str
    data_pagamento: datetime
    valor_pago: float
    metodo_pagamento: Literal["dinheiro", "pix", "transferencia", "boleto", "cartao"]
    observacoes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Campos opcionais do JOIN com outras tabelas
    cliente_id: Optional[str] = None
    cliente_nome: Optional[str] = None
    cliente_cpf: Optional[str] = None
    cliente_telefone: Optional[str] = None
    valor_emprestimo: Optional[float] = None
    taxa_juros: Optional[float] = None
    numero_parcela: Optional[int] = None
    total_parcelas: Optional[int] = None
    usuario_id: Optional[str] = None
    updated_at: Optional[datetime] = None
    deleted: Optional[bool] = None


class PagamentoCreate(BaseModel):
    parcela_id: str
    valor_pago: float
    metodo_pagamento: Literal["dinheiro", "pix", "transferencia", "boleto", "cartao"]
    data_pagamento: Optional[datetime] = None
    observacoes: Optional[str] = None
