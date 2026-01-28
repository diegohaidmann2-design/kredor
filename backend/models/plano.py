"""
Modelo de Planos e Limites
"""
from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime


class PlanoLimites(BaseModel):
    """Limites de cada plano"""
    max_clientes: int = 5  # -1 = ilimitado
    max_emprestimos: int = 10  # -1 = ilimitado
    max_emprestimos_mes: int = 10  # -1 = ilimitado
    relatorios_basicos: bool = True
    relatorios_avancados: bool = False
    contratos_pdf: bool = False
    contratos_personalizados: bool = False
    assistente_ia: bool = False
    api_acesso: bool = False
    multi_usuarios: bool = False
    notificacoes_email: bool = False
    notificacoes_whatsapp: bool = False
    suporte_email: bool = True
    suporte_prioritario: bool = False
    suporte_24_7: bool = False
    exportacao_dados: bool = False  # Exportação em massa de dados
    simulacao: bool = True  # Simulação de empréstimos


class Plano(BaseModel):
    """Modelo de Plano de Assinatura"""
    id: str
    nome: str
    slug: Literal["trial", "basico", "profissional", "enterprise"]
    preco_mensal: float
    preco_anual: Optional[float] = None  # Com desconto
    descricao: str
    recursos: List[str]  # Lista de recursos em texto para exibição
    limites: PlanoLimites
    destaque: bool = False
    ativo: bool = True
    ordem: int = 0  # Para ordenação na exibição
    cor: str = "blue"  # Cor do tema do plano
    icone: str = "star"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PlanoCreate(BaseModel):
    """Schema para criar plano"""
    nome: str
    slug: Literal["trial", "basico", "profissional", "enterprise"]
    preco_mensal: float
    preco_anual: Optional[float] = None
    descricao: str
    recursos: List[str]
    limites: PlanoLimites
    destaque: bool = False
    ordem: int = 0
    cor: str = "blue"
    icone: str = "star"


class PlanoUpdate(BaseModel):
    """Schema para atualizar plano"""
    nome: Optional[str] = None
    preco_mensal: Optional[float] = None
    preco_anual: Optional[float] = None
    descricao: Optional[str] = None
    recursos: Optional[List[str]] = None
    limites: Optional[PlanoLimites] = None
    destaque: Optional[bool] = None
    ativo: Optional[bool] = None
    ordem: Optional[int] = None
    cor: Optional[str] = None
    icone: Optional[str] = None


# ==================== DEFINIÇÃO DOS PLANOS PADRÃO ====================

PLANOS_PADRAO = {
    "trial": {
        "nome": "Trial",
        "slug": "trial",
        "preco_mensal": 0.0,
        "preco_anual": 0.0,
        "descricao": "Experimente grátis por 7 dias",
        "recursos": [
            "Até 5 clientes",
            "Até 10 empréstimos",
            "Relatórios básicos",
            "Simulação de empréstimos",
            "Suporte por email"
        ],
        "limites": PlanoLimites(
            max_clientes=5,
            max_emprestimos=10,
            max_emprestimos_mes=10,
            relatorios_avancados=False,
            contratos_pdf=False,
            contratos_personalizados=False,
            assistente_ia=False,
            api_acesso=False,
            multi_usuarios=False,
            notificacoes_email=False,
            notificacoes_whatsapp=False,
            suporte_email=True,
            suporte_prioritario=False,
            suporte_24_7=False,
            exportacao_dados=False,
            simulacao=True
        ),
        "destaque": False,
        "ordem": 0,
        "cor": "slate",
        "icone": "clock"
    },
    "basico": {
        "nome": "Básico",
        "slug": "basico",
        "preco_mensal": 97.0,
        "preco_anual": 970.0,
        "descricao": "Ideal para pequenos empreendedores",
        "recursos": [
            "Até 50 clientes",
            "Até 100 empréstimos",
            "Relatórios básicos",
            "Contratos PDF",
            "Exportação de dados",
            "Notificações por email",
            "Suporte por email"
        ],
        "limites": PlanoLimites(
            max_clientes=50,
            max_emprestimos=100,
            max_emprestimos_mes=50,
            relatorios_basicos=True,
            relatorios_avancados=False,
            contratos_pdf=True,
            contratos_personalizados=False,
            assistente_ia=False,
            api_acesso=False,
            multi_usuarios=False,
            notificacoes_email=True,
            notificacoes_whatsapp=False,
            suporte_email=True,
            suporte_prioritario=False,
            suporte_24_7=False,
            exportacao_dados=True,
            simulacao=True
        ),
        "destaque": False,
        "ordem": 1,
        "cor": "blue",
        "icone": "rocket"
    },
    "profissional": {
        "nome": "Profissional",
        "slug": "profissional",
        "preco_mensal": 197.0,
        "preco_anual": 1970.0,
        "descricao": "Para negócios em crescimento",
        "recursos": [
            "Até 200 clientes",
            "Até 500 empréstimos",
            "Relatórios avançados",
            "Contratos personalizados",
            "Assistente IA",
            "Exportação de dados",
            "Notificações WhatsApp",
            "Suporte prioritário"
        ],
        "limites": PlanoLimites(
            max_clientes=200,
            max_emprestimos=500,
            max_emprestimos_mes=200,
            relatorios_basicos=True,
            relatorios_avancados=True,
            contratos_pdf=True,
            contratos_personalizados=True,
            assistente_ia=True,
            api_acesso=False,
            multi_usuarios=False,
            notificacoes_email=True,
            notificacoes_whatsapp=True,
            suporte_email=True,
            suporte_prioritario=True,
            suporte_24_7=False,
            exportacao_dados=True,
            simulacao=True
        ),
        "destaque": True,
        "ordem": 2,
        "cor": "purple",
        "icone": "crown"
    },
    "enterprise": {
        "nome": "Enterprise",
        "slug": "enterprise",
        "preco_mensal": 497.0,
        "preco_anual": 4970.0,
        "descricao": "Solução completa para grandes operações",
        "recursos": [
            "Clientes ilimitados",
            "Empréstimos ilimitados",
            "Todos os relatórios",
            "API personalizada",
            "Multi-usuários",
            "Exportação ilimitada",
            "Suporte 24/7"
        ],
        "limites": PlanoLimites(
            max_clientes=-1,
            max_emprestimos=-1,
            max_emprestimos_mes=-1,
            relatorios_basicos=True,
            relatorios_avancados=True,
            contratos_pdf=True,
            contratos_personalizados=True,
            assistente_ia=True,
            api_acesso=True,
            multi_usuarios=True,
            notificacoes_email=True,
            notificacoes_whatsapp=True,
            suporte_email=True,
            suporte_prioritario=True,
            suporte_24_7=True,
            exportacao_dados=True,
            simulacao=True
        ),
        "destaque": False,
        "ordem": 3,
        "cor": "amber",
        "icone": "building"
    }
}


def get_plano_limites(plano_slug: str) -> PlanoLimites:
    """Retorna os limites de um plano pelo slug"""
    if plano_slug in PLANOS_PADRAO:
        return PLANOS_PADRAO[plano_slug]["limites"]
    return PLANOS_PADRAO["trial"]["limites"]


def get_plano_info(plano_slug: str) -> dict:
    """Retorna todas as informações de um plano"""
    if plano_slug in PLANOS_PADRAO:
        return PLANOS_PADRAO[plano_slug]
    return PLANOS_PADRAO["trial"]
