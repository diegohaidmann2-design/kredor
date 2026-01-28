"""
Modelo de Contratos
"""
from pydantic import BaseModel
from typing import Optional, Literal


class ContratoRequest(BaseModel):
    emprestimo_id: str
    template: Literal["padrao", "garantia", "personalizado"] = "padrao"
    clausulas_adicionais: Optional[str] = None
