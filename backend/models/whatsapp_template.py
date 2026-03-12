"""
Modelo de Templates de Mensagens WhatsApp
Permite que cada tenant crie e edite seus próprios templates
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime

class WhatsAppTemplate(BaseModel):
    """Template de mensagem WhatsApp"""
    id: Optional[str] = None
    usuario_id: str
    nome: str = Field(..., description="Nome do template")
    tipo: Literal["cobranca", "lembrete", "confirmacao", "boas_vindas", "atraso", "custom"] = "cobranca"
    mensagem: str = Field(..., description="Texto do template com variáveis")
    descricao: Optional[str] = Field(None, description="Descrição do template")
    variaveis_disponiveis: List[str] = Field(
        default=[
            "{cliente_nome}",
            "{numero_parcela}",
            "{total_parcelas}",
            "{valor}",
            "{data_vencimento}",
            "{dias}"
        ],
        description="Variáveis que podem ser usadas"
    )
    ativo: bool = Field(default=True, description="Template ativo")
    padrao: bool = Field(default=False, description="Template padrão do sistema")
    exemplo_preview: Optional[str] = Field(None, description="Preview com dados exemplo")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

# Templates padrão do sistema
TEMPLATES_PADRAO = [
    {
        "nome": "Cobrança - Lembrete Antes do Vencimento",
        "tipo": "lembrete",
        "mensagem": (
            "Olá {cliente_nome}! 👋\n\n"
            "Lembrete amigável:\n"
            "📅 Parcela #{numero_parcela}/{total_parcelas}\n"
            "💰 Valor: R$ {valor}\n"
            "📆 Vence em {dias} dias ({data_vencimento})\n\n"
            "Qualquer dúvida, estou à disposição!"
        ),
        "descricao": "Enviado alguns dias antes do vencimento",
        "ativo": True,
        "padrao": True
    },
    {
        "nome": "Cobrança - Vencimento Hoje",
        "tipo": "cobranca",
        "mensagem": (
            "Olá {cliente_nome}! 📢\n\n"
            "A parcela #{numero_parcela}/{total_parcelas} vence HOJE!\n\n"
            "💰 Valor: R$ {valor}\n"
            "📅 Vencimento: {data_vencimento}\n\n"
            "Por favor, realize o pagamento para evitar juros."
        ),
        "descricao": "Enviado no dia do vencimento",
        "ativo": True,
        "padrao": True
    },
    {
        "nome": "Cobrança - Parcela em Atraso",
        "tipo": "atraso",
        "mensagem": (
            "Olá {cliente_nome}! ⚠️\n\n"
            "A parcela #{numero_parcela}/{total_parcelas} está em atraso há {dias} dias.\n\n"
            "💰 Valor original: R$ {valor}\n"
            "📅 Vencimento: {data_vencimento}\n\n"
            "Por favor, regularize sua situação para evitar acréscimos.\n\n"
            "Estou à disposição para negociar!"
        ),
        "descricao": "Enviado quando parcela está atrasada",
        "ativo": True,
        "padrao": True
    },
    {
        "nome": "Confirmação de Pagamento",
        "tipo": "confirmacao",
        "mensagem": (
            "Olá {cliente_nome}! ✅\n\n"
            "Pagamento confirmado!\n\n"
            "💚 Parcela #{numero_parcela}/{total_parcelas}\n"
            "💰 Valor: R$ {valor}\n"
            "📅 Data: {data_vencimento}\n\n"
            "Obrigado pela pontualidade! 🎉"
        ),
        "descricao": "Enviado após confirmação de pagamento",
        "ativo": True,
        "padrao": True
    },
    {
        "nome": "Boas-vindas - Novo Cliente",
        "tipo": "boas_vindas",
        "mensagem": (
            "Olá {cliente_nome}! 🎉\n\n"
            "Seja bem-vindo(a)!\n\n"
            "Seu empréstimo foi aprovado com sucesso.\n"
            "Total de parcelas: {total_parcelas}\n\n"
            "Em breve você receberá lembretes sobre os vencimentos.\n\n"
            "Conte comigo para qualquer dúvida! 😊"
        ),
        "descricao": "Enviado quando novo empréstimo é criado",
        "ativo": True,
        "padrao": True
    },
    {
        "nome": "Cobrança Simples",
        "tipo": "cobranca",
        "mensagem": (
            "Oi {cliente_nome}!\n\n"
            "Parcela {numero_parcela}: R$ {valor}\n"
            "Vence em {dias} dias\n\n"
            "Obrigado! 😊"
        ),
        "descricao": "Template simplificado e direto",
        "ativo": True,
        "padrao": True
    }
]
