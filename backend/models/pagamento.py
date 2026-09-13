"""
Modelo de Pagamento
"""
from pydantic import BaseModel, Field
from utils.dinheiro import EntradaEmReais
from typing import Optional, Literal
from datetime import datetime, timezone
import uuid


class Pagamento(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parcela_id: Optional[str] = None  # None em amortizações/incorporações (movimento de capital)
    emprestimo_id: str
    data_pagamento: datetime
    valor_pago_centavos: int
    metodo_pagamento: str
    observacoes: Optional[str] = None
    tipo: Optional[str] = "pagamento"  # pagamento | amortizacao
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Campos opcionais do JOIN com outras tabelas
    cliente_id: Optional[str] = None
    cliente_nome: Optional[str] = None
    cliente_cpf: Optional[str] = None
    cliente_telefone: Optional[str] = None
    valor_emprestimo_centavos: Optional[int] = None
    taxa_juros: Optional[float] = None
    numero_parcela: Optional[int] = None
    total_parcelas: Optional[int] = None
    usuario_id: Optional[str] = None
    updated_at: Optional[datetime] = None
    deleted: Optional[bool] = None

    # Retrato da dívida logo após este pagamento. O recibo usa estes valores para mostrar
    # o saldo daquela data, não o atual (pagamentos posteriores mudariam o número).
    status_parcela_apos: Optional[str] = None  # parcial | pago
    saldo_parcela_restante_centavos: Optional[int] = None
    saldo_emprestimo_restante_centavos: Optional[int] = None

    # Desconto concedido na quitação: o que o credor abriu mão de receber neste pagamento.
    # Não é dinheiro recebido — fica separado do valor_pago justamente para não virar ganho.
    valor_perdoado_centavos: Optional[int] = None
    perdao_juros_centavos: Optional[int] = None
    perdao_capital_centavos: Optional[int] = None
    perdao_encargos_centavos: Optional[int] = None


class PagamentoCreate(EntradaEmReais):
    parcela_id: str
    valor_pago_centavos: int
    metodo_pagamento: Literal["dinheiro", "pix", "transferencia", "boleto", "cartao"]
    data_pagamento: Optional[datetime] = None
    observacoes: Optional[str] = None
    # Cliente pagou menos do que a parcela devia e o credor decidiu dar o restante por quitado
    # (normalmente a multa e a mora que ele não cobrou). Só tem efeito se sobrar saldo.
    quitar_ignorando_restante: bool = False


class PagamentoPrevia(EntradaEmReais):
    """Consulta, sem gravar nada, o que este pagamento faria na parcela.

    A tela precisa disso para perguntar antes de lançar: multa e mora dependem da data em que o
    cliente pagou, então só o servidor sabe quanto a parcela devia naquele dia.
    """
    parcela_id: str
    valor_pago_centavos: int = 0
    data_pagamento: Optional[datetime] = None
