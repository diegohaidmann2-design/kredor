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


class PagamentoCreate(BaseModel):
    parcela_id: str
    valor_pago: float
    metodo_pagamento: Literal["dinheiro", "pix", "transferencia", "boleto", "cartao"]
    data_pagamento: Optional[datetime] = None
    observacoes: Optional[str] = None
