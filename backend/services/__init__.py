"""
Services da aplicação
"""
from .calculos import (
    calcular_juros_simples,
    calcular_juros_compostos,
    calcular_tabela_price,
    calcular_sac,
    gerar_parcelas_simulacao
)
from .auth import hash_senha, verificar_senha, criar_token, get_current_user, require_admin
from .auditoria import registrar_auditoria

__all__ = [
    'calcular_juros_simples',
    'calcular_juros_compostos', 
    'calcular_tabela_price',
    'calcular_sac',
    'gerar_parcelas_simulacao',
    'hash_senha',
    'verificar_senha',
    'criar_token',
    'get_current_user',
    'require_admin',
    'registrar_auditoria'
]
