"""
Modelos de dados da aplicação
"""
from .usuario import Usuario, LoginRequest, LoginResponse
from .cliente import Cliente, ClienteCreate, ClienteUpdate, Endereco
from .emprestimo import (
    Emprestimo, EmprestimoCreate, Parcela, 
    SimulacaoRequest, SimulacaoResponse, ParcelaSimulacao
)
from .pagamento import Pagamento, PagamentoCreate
from .notificacao import Notificacao, NotificacaoCreate
from .auditoria import AuditLog
from .dashboard import DashboardStats
from .configuracao import LandingConfig
from .relatorio import RelatorioRequest
from .contrato import ContratoRequest

__all__ = [
    'Usuario', 'LoginRequest', 'LoginResponse',
    'Cliente', 'ClienteCreate', 'ClienteUpdate', 'Endereco',
    'Emprestimo', 'EmprestimoCreate', 'Parcela',
    'SimulacaoRequest', 'SimulacaoResponse', 'ParcelaSimulacao',
    'Pagamento', 'PagamentoCreate',
    'Notificacao', 'NotificacaoCreate',
    'AuditLog',
    'DashboardStats',
    'LandingConfig',
    'RelatorioRequest',
    'ContratoRequest'
]
