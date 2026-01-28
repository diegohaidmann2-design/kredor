"""
Modelo de Relatórios
"""
from pydantic import BaseModel
from typing import Optional, Literal


class RelatorioRequest(BaseModel):
    tipo: Literal["emprestimos", "pagamentos", "clientes", "inadimplencia", "fluxo_caixa"]
    formato: Literal["pdf", "excel"]
    periodo: Literal["hoje", "semana", "mes", "trimestre", "ano", "personalizado"]
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None
