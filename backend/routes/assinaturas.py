"""
Rotas de Assinaturas (Asaas + Mercado Pago)
"""
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import os
import uuid
import asyncio

from config import db
from models.usuario import Usuario
from services.auth import get_current_user, get_current_user_optional, hash_senha, criar_token, require_admin
from services.auth_utils import is_owner
from services.asaas_service import asaas_service
from services.plano_service import ativar_plano_pago

router = APIRouter()

# ==================== LIMPEZA AUTOMÁTICA ====================

async def limpar_usuarios_expirados():
    """
    Remove usuários com pagamento pendente há mais de 24 horas
    NÃO remove usuários trial
    """
    try:
        data_limite = datetime.now(timezone.utc) - timedelta(hours=24)
        
        # Buscar usuários pendentes expirados (EXCLUIR TRIAL)
        usuarios_expirados = await db.usuarios.find({
            "payment_status": "pending",
            "plano_ativo": False,
            "plano": {"$ne": "trial"},  # NÃO deletar trials
            "created_at": {"$lt": data_limite.isoformat()}
        }).to_list(100)
        
        if usuarios_expirados:
            ids_para_deletar = [u["id"] for u in usuarios_expirados]
            emails = [u["email"] for u in usuarios_expirados]
            
            resultado = await db.usuarios.delete_many({
                "id": {"$in": ids_para_deletar}
            })
            
            print(f"🧹 Limpeza: {resultado.deleted_count} usuários PAGOS pendentes expirados removidos")
            print(f"📧 Emails liberados: {emails}")
            
            return resultado.deleted_count
        
        return 0
    except Exception as e:
        print(f"❌ Erro na limpeza automática: {e}")
        return 0

@router.post("/limpar-expirados")
async def endpoint_limpar_expirados(current_user: Usuario = Depends(require_admin)):
    """
    Endpoint manual para limpar usuários expirados (apenas admin).
    """
    count = await limpar_usuarios_expirados()
    return {"removidos": count, "message": f"{count} usuários pendentes expirados foram removidos"}

class PlanoInfo(BaseModel):
    id: str
    nome: str
    preco: float
    intervalo: str
    recursos: List[str]
    clientes: int = 0  # -1 = ilimitado
    emprestimos: int = 0  # -1 = ilimitado
    destaque: bool = False

PLANOS = [
    PlanoInfo(
        id="trial",
        nome="Trial",
        preco=0,
        intervalo="7 dias",
        clientes=5,
        emprestimos=10,
        recursos=["Relatórios básicos", "Simulador de empréstimos"],
        destaque=False
    ),
    PlanoInfo(
        id="basico",
        nome="Básico",
        preco=49.90,
        intervalo="mês",
        clientes=50,
        emprestimos=100,
        recursos=["Relatórios PDF", "Suporte por email", "Contratos básicos"],
        destaque=False
    ),
    PlanoInfo(
        id="profissional",
        nome="Profissional",
        preco=99.90,
        intervalo="mês",
        clientes=-1,
        emprestimos=-1,
        recursos=["Relatórios PDF/Excel", "Contratos personalizados", "Suporte prioritário", "Assistente IA"],
        destaque=True
    ),
    PlanoInfo(
        id="enterprise",
        nome="Enterprise",
        preco=199.90,
        intervalo="mês",
        clientes=-1,
        emprestimos=-1,
        recursos=["Tudo do Profissional", "API de integração", "Multi-usuários", "Suporte dedicado", "Treinamento"],
        destaque=False
    )
]

@router.get("/planos")
async def listar_planos():
    """Lista planos disponíveis - busca do banco de dados"""
    return await get_planos_from_db()

@router.get("/social-proof")
async def obter_social_proof():
    """Retorna dados públicos para social proof no checkout"""
    total_usuarios = await db.usuarios.count_documents({"plano_ativo": True})
    total_transacoes = await db.transacoes_checkout.count_documents({})
    total_emprestimos = await db.emprestimos.count_documents({})

    # Buscar últimas assinaturas (anonimizar)
    recentes = await db.transacoes_checkout.find(
        {"status": {"$in": ["approved", "pending"]}},
        {"_id": 0, "nome": 1, "plano_id": 1, "criado_em": 1, "gateway": 1}
    ).sort("criado_em", -1).limit(5).to_list(5)

    atividade = []
    for r in recentes:
        nome = r.get("nome", "Usuario")
        # Anonimizar: mostrar só primeiro nome + inicial
        partes = nome.split()
        nome_curto = partes[0] if partes else "Usuario"
        if len(partes) > 1:
            nome_curto += f" {partes[1][0]}."
        atividade.append({
            "nome": nome_curto,
            "plano": (r.get("plano_id") or "basico").capitalize(),
            "tempo": r.get("criado_em", "")
        })

    return {
        "gestores_ativos": max(total_usuarios, 3),
        "transacoes_processadas": max(total_transacoes, 5),
        "emprestimos_gerenciados": max(total_emprestimos, 10),
        "atividade_recente": atividade
    }


async def get_planos_from_db():
    """
    Função auxiliar para buscar planos do banco de dados.
    Os preços devem vir da MESMA fonte que a landing page usa.
    
    PRIORIDADE:
    1. tipo: "landing" (config salva pelo admin no painel)
    2. Valores padrão do LandingConfig (mesmos que a landing page usa)
    """
    from models.configuracao import LandingConfig
    
    # Buscar configuração do admin (tipo: "landing")
    config_admin = await db.configuracoes.find_one({"tipo": "landing"})
    
    if config_admin and "dados" in config_admin:
        dados = config_admin["dados"]
    else:
        # Usar valores padrão do LandingConfig (mesmos que a landing page mostra)
        dados = LandingConfig().model_dump()
    
    return [
        PlanoInfo(
            id="trial",
            nome="Trial",
            preco=0,
            intervalo=f"{dados.get('plano_trial_dias', 7)} dias",
            clientes=5,
            emprestimos=10,
            recursos=["Relatórios básicos", "Simulador de empréstimos"],
            destaque=False
        ),
        PlanoInfo(
            id="basico",
            nome="Básico",
            preco=float(dados.get('plano_basico_preco', 97.0)),
            intervalo="mês",
            clientes=int(dados.get('plano_basico_clientes', 50)),
            emprestimos=int(dados.get('plano_basico_emprestimos', 100)),
            recursos=["Relatórios PDF", "Suporte por email", "Contratos básicos"],
            destaque=False
        ),
        PlanoInfo(
            id="profissional",
            nome="Profissional",
            preco=float(dados.get('plano_profissional_preco', 197.0)),
            intervalo="mês",
            clientes=int(dados.get('plano_profissional_clientes', 200)),
            emprestimos=int(dados.get('plano_profissional_emprestimos', 500)),
            recursos=["Relatórios PDF/Excel", "Contratos personalizados", "Suporte prioritário", "Assistente IA"],
            destaque=True
        ),
        PlanoInfo(
            id="enterprise",
            nome="Enterprise",
            preco=float(dados.get('plano_enterprise_preco', 497.0)),
            intervalo="mês",
            clientes=int(dados.get('plano_enterprise_clientes', -1)),
            emprestimos=int(dados.get('plano_enterprise_emprestimos', -1)),
            recursos=["Tudo do Profissional", "API de integração", "Multi-usuários", "Suporte dedicado", "Treinamento"],
            destaque=False
        )
    ]

async def get_plano_by_id(plano_id: str) -> Optional[PlanoInfo]:
    """
    Busca um plano específico pelo ID, primeiro do banco de dados.
    Se não encontrar configuração no banco, usa os planos padrão.
    """
    planos = await get_planos_from_db()
    return next((p for p in planos if p.id == plano_id), None)

@router.get("/status")
async def obter_status_assinatura(current_user: Usuario = Depends(get_current_user)):
    """Retorna status completo da assinatura do usuário"""
    from services.assinatura_middleware import status_assinatura
    return status_assinatura(current_user)

class CheckoutPublicoRequest(BaseModel):
    plano_id: str
    nome: str
    email: str
    senha: str
    origin_url: str
    codigo_cupom: Optional[str] = None  # 🆕 Campo para cupom

class CheckoutRequest(BaseModel):
    plano_id: str
    success_url: str
    cancel_url: str

# ==================== CUPONS (PÚBLICO) ====================

@router.get("/cupom/validar/{codigo}")
async def validar_cupom_publico(codigo: str, email: Optional[str] = None):
    """
    Valida um cupom de desconto (endpoint público para checkout)
    """
    try:
        # Buscar cupom
        cupom = await db.cupons.find_one({"codigo": codigo.upper()})
        
        if not cupom:
            return {
                "valido": False,
                "erro": "Cupom não encontrado"
            }
        
        # Verificar se já foi usado
        if cupom.get("usado", False):
            return {
                "valido": False,
                "erro": "Cupom já foi utilizado"
            }
        
        # Verificar validade
        if cupom.get("valido_ate"):
            valido_ate = cupom["valido_ate"]
            if isinstance(valido_ate, str):
                valido_ate = datetime.fromisoformat(valido_ate.replace('Z', '+00:00'))
            
            if valido_ate.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
                return {
                    "valido": False,
                    "erro": "Cupom expirado"
                }
        
        # Verificar se é específico para um email
        if email and cupom.get("usuario_email"):
            if cupom["usuario_email"].lower() != email.lower():
                return {
                    "valido": False,
                    "erro": "Cupom não é válido para este email"
                }
        
        return {
            "valido": True,
            "codigo": cupom["codigo"],
            "desconto_percentual": cupom["desconto_percentual"],
            "valido_ate": cupom["valido_ate"] if cupom.get("valido_ate") else None
        }
        
    except Exception as e:
        print(f"❌ Erro ao validar cupom: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/minha")
async def obter_minha_assinatura(current_user: Usuario = Depends(get_current_user)):
    """Retorna assinatura atual do usuário de forma consistente"""
    from services.plano_service import obter_status_plano
    
    # Usar serviço centralizado para obter status consistente
    status = await obter_status_plano(current_user.id)
    
    if not status.get("success"):
        return {
            "plano": "trial",
            "status": "ativa",
            "mensagem": "Você está usando o plano trial"
        }
    
    plano_atual = status.get("plano", "trial")
    plano_ativo = status.get("plano_ativo", False)
    data_expiracao = status.get("data_expiracao")
    
    # Se tem plano pago (não é trial), buscar detalhes da assinatura
    if plano_atual != "trial":
        # Buscar assinatura ativa (pode estar em assinaturas ou assinaturas_admin)
        assinatura = await db.assinaturas.find_one(
            {"usuario_id": current_user.id, "status": "ativa"},
            {"_id": 0}
        )
        
        if not assinatura:
            assinatura = await db.assinaturas_admin.find_one(
                {"usuario_id": current_user.id, "status": "ativa"},
                {"_id": 0}
            )
        
        return {
            "plano": plano_atual,
            "plano_nome": plano_atual.capitalize(),
            "status": "ativa" if plano_ativo else "inativa",
            "plano_ativo": plano_ativo,
            "email_verificado": current_user.email_verificado,
            "data_fim": data_expiracao,
            "data_expiracao": data_expiracao,
            "dias_restantes": status.get("dias_restantes"),
            "expirado": status.get("expirado", False),
            "gateway": status.get("gateway"),
            "assinatura_detalhes": assinatura
        }
    
    # Plano trial
    return {
        "plano": "trial",
        "plano_nome": "TRIAL",
        "status": "ativa" if plano_ativo else "inativa",
        "plano_ativo": plano_ativo,
        "email_verificado": current_user.email_verificado,
        "data_fim": data_expiracao,
        "dias_restantes": status.get("dias_restantes"),
        "expirado": status.get("expirado", False),
        "mensagem": "Você está usando o plano trial gratuito"
    }

@router.post("/cancelar")
async def cancelar_minha_assinatura(current_user: Usuario = Depends(get_current_user)):
    """Cancela a própria assinatura do usuário"""
    agora = datetime.now(timezone.utc).isoformat()
    
    # 1. Marcar como cancelada nas coleções de assinaturas
    await db.assinaturas.update_many(
        {"usuario_id": current_user.id, "status": "ativa"},
        {"$set": {"status": "cancelada", "data_cancelamento": agora}}
    )
    
    await db.assinaturas_admin.update_many(
        {"usuario_id": current_user.id, "status": "ativa"},
        {"$set": {"status": "cancelada", "data_cancelamento": agora}}
    )
    
    # 2. Rebaixar usuário para trial
    await db.usuarios.update_one(
        {"id": current_user.id},
        {"$set": {
            "plano": "trial",
            "plano_ativo": False,
            "updated_at": agora
        }}
    )
    
    return {"message": "Sua assinatura foi cancelada com sucesso."}

@router.get("/historico")
async def historico_assinaturas(current_user: Usuario = Depends(get_current_user)):
    """Retorna histórico de assinaturas"""
    assinaturas = await db.assinaturas.find(
        {"usuario_id": current_user.id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    return assinaturas


# ============================================
# SISTEMA DE PAGAMENTO DUPLO (ASAAS + MERCADO PAGO)
# ============================================

from models.configuracao import AssinaturaGatewayConfig
# from services.mercadopago import MercadoPagoService  # DEPRECATED: MercadoPago removido
from pydantic import ValidationError

def _sanitizar_dados_assinatura_gateway(dados):
    """
    Sanitiza dados de configuração de gateway, migrando estratégias obsoletas.
    
    ATENÇÃO: Esta função DEVE preservar valores válidos do banco de dados.
    Apenas migra estratégias obsoletas (stripe_only, mercadopago_only) para as atuais.
    """
    if not isinstance(dados, dict):
        return {}

    dados = dict(dados)
    estrategia = dados.get("estrategia")
    
    # Migrar APENAS estratégias obsoletas (não válidas)
    if estrategia in ("stripe_only", "stripe"):
        # Stripe foi removido → migrar para Asaas
        if dados.get("asaas_habilitado", True):
            dados["estrategia"] = "asaas_only"
        else:
            dados["estrategia"] = "rotacao"
    elif estrategia == "mercadopago_only":
        # MercadoPago foi removido → migrar para SyncPay ou Asaas
        if dados.get("syncpay_habilitado"):
            dados["estrategia"] = "syncpay_only"
        elif dados.get("asaas_habilitado", True):
            dados["estrategia"] = "asaas_only"
        else:
            dados["estrategia"] = "rotacao"
    elif estrategia not in ("asaas_only", "syncpay_only", "rotacao", "fallback"):
        # Estratégia inválida/desconhecida → fallback para asaas_only
        print(f"⚠️ Estratégia inválida '{estrategia}' → fallback para 'asaas_only'")
        dados["estrategia"] = "asaas_only"
    # IMPORTANTE: Se estratégia é válida (asaas_only, syncpay_only, rotacao, fallback),
    # NÃO SOBRESCREVER! Preservar valor do banco de dados.

    # Sanitizar gateway_primario
    gateway_primario = dados.get("gateway_primario")
    if gateway_primario == "stripe":
        dados["gateway_primario"] = "asaas"
    elif gateway_primario == "mercadopago":
        dados["gateway_primario"] = "syncpay" if dados.get("syncpay_habilitado") else "asaas"
    elif gateway_primario not in ("asaas", "syncpay"):
        # Gateway primário inválido → fallback para asaas
        dados["gateway_primario"] = "asaas"

    return dados

async def get_assinatura_gateway_config() -> AssinaturaGatewayConfig:
    """Obtém configurações de gateway para assinaturas do banco"""
    config_doc = await db.configuracoes.find_one({"tipo": "assinatura_gateway"})
    if config_doc and "dados" in config_doc:
        dados_brutos = config_doc.get("dados")
        dados = _sanitizar_dados_assinatura_gateway(dados_brutos)
        try:
            config = AssinaturaGatewayConfig(**dados)
        except ValidationError as e:
            print(f"Erro validação gateway config: {e}")
            config = AssinaturaGatewayConfig(estrategia="asaas_only", asaas_habilitado=False, syncpay_habilitado=False)

        # DESABILITADO: auto-save sobrescreve valores corretos do DB
        # if dados_brutos != config.model_dump():
        #     await db.configuracoes.update_one(
        #         {"tipo": "assinatura_gateway"},
        #         {"$set": {"dados": config.model_dump()}},
        #         upsert=True,
        #     )

        return config
    
    # Retorna config padrão com Asaas
    return AssinaturaGatewayConfig(
        estrategia="asaas_only",
        asaas_habilitado=False
    )

async def escolher_gateway_assinatura(config: AssinaturaGatewayConfig, gateway_especifico: Optional[str] = None) -> str:
    """Escolhe qual gateway usar para assinaturas baseado na configuração"""
    if gateway_especifico:
        return gateway_especifico
    
    if config.estrategia == "asaas_only":
        return "asaas"
    elif config.estrategia == "syncpay_only":
        return "syncpay"
    elif config.estrategia == "mercadopago_only":
        # MercadoPago foi removido - fallback para syncpay ou asaas
        if config.syncpay_habilitado:
            return "syncpay"
        return "asaas"
    elif config.estrategia == "rotacao":
        # Alterna entre os gateways
        gateways = []
        if config.asaas_habilitado:
            gateways.append("asaas")
        if config.syncpay_habilitado:
            gateways.append("syncpay")
        
        if not gateways:
            return "asaas"  # fallback
        
        gateway_escolhido = gateways[config.rotacao_contador % len(gateways)]
        
        # Incrementa contador
        await db.configuracoes.update_one(
            {"tipo": "assinatura_gateway"},
            {"$inc": {"dados.rotacao_contador": 1}}
        )
        
        return gateway_escolhido
    elif config.estrategia == "fallback":
        return config.gateway_primario
    
    return "asaas"

@router.get("/gateway/config")
async def obter_config_gateway_assinatura(current_user: Usuario = Depends(get_current_user)):
    """Obtém configurações de gateway para assinaturas (admin only)"""
    if current_user.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    config = await get_assinatura_gateway_config()
    return config.model_dump()

@router.put("/gateway/config")
async def atualizar_config_gateway_assinatura(
    config: AssinaturaGatewayConfig,
    current_user: Usuario = Depends(get_current_user)
):
    """Atualiza configurações de gateway para assinaturas (admin only)"""
    if current_user.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    await db.configuracoes.update_one(
        {"tipo": "assinatura_gateway"},
        {"$set": {"tipo": "assinatura_gateway", "dados": config.model_dump()}},
        upsert=True
    )
    
    return {"message": "Configurações de gateway de assinatura atualizadas"}

@router.get("/gateway/disponiveis")
async def listar_gateways_disponiveis():
    """
    Retorna o gateway que deve ser usado para checkout público.
    O gateway é escolhido automaticamente baseado na estratégia configurada pelo admin.
    O cliente NÃO escolhe o gateway manualmente.
    """
    config = await get_assinatura_gateway_config()
    
    # Escolher gateway baseado na estratégia do admin
    gateway_id = await escolher_gateway_assinatura(config)
    
    gateway_info = None
    
    # Montar informações do gateway selecionado
    if gateway_id == "asaas" and config.asaas_habilitado:
        gateway_info = {
            "id": "asaas",
            "nome": "Asaas",
            "descricao": "PIX, Boleto e Cartão",
            "metodos": ["pix", "boleto", "cartao"],
            "icone": "wallet"
        }
    
    elif gateway_id == "syncpay" and config.syncpay_habilitado:
        gateway_info = {
            "id": "syncpay",
            "nome": "SyncPay",
            "descricao": "PIX Instantâneo",
            "metodos": ["pix"],  # SyncPay suporta APENAS PIX
            "icone": "wallet"
        }
    
    elif gateway_id == "mercadopago" and config.mercadopago_habilitado:
        metodos = []
        if config.mp_cartao_habilitado:
            metodos.append("cartao")
        if config.mp_pix_habilitado:
            metodos.append("pix")
        
        if metodos:
            gateway_info = {
                "id": "mercadopago",
                "nome": "Mercado Pago",
                "descricao": "PIX e/ou Cartão de Crédito",
                "metodos": metodos,
                "icone": "wallet",
                "public_key": config.mercadopago_public_key
            }
    
    # Se nenhum gateway foi configurado ou selecionado
    if not gateway_info:
        raise HTTPException(
            status_code=503, 
            detail="Sistema de pagamento não configurado. Entre em contato com o suporte."
        )
    
    return {
        "gateway": gateway_info,  # Retorna UM único gateway, não array
        "estrategia": config.estrategia,
        "permite_escolha": False  # Cliente nunca escolhe gateway
    }

class CheckoutPublicoMPRequest(BaseModel):
    """DEPRECATED: MercadoPago foi removido. Use SyncPay ou Asaas."""
    plano_id: str
    nome: str
    email: str
    senha: str
    origin_url: str
    metodo_pagamento: str = "cartao"

@router.post("/checkout-mercadopago")
async def checkout_mercadopago(request: CheckoutPublicoMPRequest):
    """
    DEPRECATED: MercadoPago foi removido do sistema.
    Use /checkout-asaas-publico ou aguarde implementação do SyncPay checkout.
    """
    raise HTTPException(
        status_code=410,
        detail="MercadoPago foi descontinuado. Use Asaas ou SyncPay como gateway de pagamento."
    )

@router.post("/webhook-mercadopago")
async def webhook_mercadopago(request: Request):
    """
    DEPRECATED: Webhook do Mercado Pago - Gateway descontinuado.
    Este endpoint está desabilitado. Use /webhook-asaas ou /webhook-syncpay.
    """
    print("⚠️ Tentativa de usar webhook MercadoPago (descontinuado)")
    raise HTTPException(
        status_code=410,
        detail="MercadoPago webhook foi descontinuado. Gateway não está mais disponível."
    )

@router.get("/verificar-assinatura-mp/{subscription_id}")
async def verificar_assinatura_mp(
    subscription_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """
    DEPRECATED: Endpoint de verificação do MercadoPago descontinuado.
    """
    raise HTTPException(
        status_code=410,
        detail="MercadoPago foi descontinuado. Use Asaas ou SyncPay."
    )
    
    # Código legacy removido - endpoint descontinuado


# =========================================
# CHECKOUT TRANSPARENTE MERCADO PAGO
# =========================================

# Helper: Registrar transação para monitoramento
async def registrar_transacao(
    usuario_id: Optional[str],
    usuario_email: str,
    usuario_nome: str,
    usuario_cpf: Optional[str],
    usuario_telefone: Optional[str],
    plano_id: str,
    plano_nome: str,
    valor: float,
    metodo_pagamento: str,
    status: str,
    payment_id: Optional[str] = None,
    order_id: Optional[str] = None,
    dados_pagamento: dict = {},
    motivo_recusa: Optional[str] = None,
    mensagem_erro: Optional[str] = None,
    ip_origem: Optional[str] = None
):
    """
    Registra uma transação no sistema de monitoramento
    """
    transacao_id = str(uuid.uuid4())
    transacao = {
        "id": transacao_id,
        "usuario_id": usuario_id,
        "usuario_email": usuario_email,
        "usuario_nome": usuario_nome,
        "usuario_cpf": usuario_cpf,
        "usuario_telefone": usuario_telefone,
        "plano_id": plano_id,
        "plano_nome": plano_nome,
        "valor": valor,
        "metodo_pagamento": metodo_pagamento,
        "status": status,
        "payment_id": payment_id,
        "order_id": order_id,
        "dados_pagamento": dados_pagamento,
        "motivo_recusa": motivo_recusa,
        "mensagem_erro": mensagem_erro,
        "tentativas": 1,
        "email_enviado": False,
        "cupom_gerado": None,
        "data_email": None,
        "criado_em": datetime.utcnow(),
        "atualizado_em": datetime.utcnow(),
        "expira_em": datetime.utcnow() + timedelta(minutes=30) if metodo_pagamento == "pix" else None,
        "ip_origem": ip_origem,
        "user_agent": None
    }
    
    await db.transacoes_checkout.insert_one(transacao)
    return transacao_id

# Helper: Atualizar status de transação existente
async def atualizar_status_transacao(
    payment_id: str,
    novo_status: str,
    motivo_recusa: Optional[str] = None,
    dados_pagamento: dict = {}
):
    """
    Atualiza o status de uma transação existente
    Usado principalmente pelo webhook para status em tempo real
    """
    update_data = {
        "status": novo_status,
        "atualizado_em": datetime.utcnow(),
        "dados_pagamento": dados_pagamento
    }
    
    if motivo_recusa:
        update_data["motivo_recusa"] = motivo_recusa
    
    result = await db.transacoes_checkout.update_one(
        {"payment_id": payment_id},
        {"$set": update_data}
    )
    
    return result.modified_count > 0

class CheckoutTransparentePixRequest(BaseModel):
    plano_id: str
    nome: str
    email: str
    senha: str
    cpf: str
    telefone: Optional[str] = None

class CheckoutTransparenteCardRequest(BaseModel):
    plano_id: str
    nome: str
    email: str
    senha: str
    cpf: str
    telefone: Optional[str] = None
    card_token: str
    installments: int = 1
    payment_method_id: str  # visa, master, etc

@router.post("/checkout-transparente-pix")
async def checkout_transparente_pix(
    request: CheckoutTransparentePixRequest, 
    background_tasks: BackgroundTasks
):
    """
    Cria checkout transparente com PIX - Cliente fica no nosso site.
    Retorna QR Code e Pix Copia e Cola para pagamento imediato.
    """
    # Adicionar limpeza automática em background
    background_tasks.add_task(limpar_usuarios_expirados)
    
    config = await get_assinatura_gateway_config()
    
    if not config.mercadopago_habilitado:
        raise HTTPException(status_code=400, detail="Mercado Pago não está habilitado")
    
    # Verificar se email já existe
    usuario_existente = await db.usuarios.find_one({"email": request.email})
    usuario_id_para_usar = None  # Para saber se é upgrade ou novo usuário
    
    if usuario_existente:
        # Verificar se é trial ativo - permitir upgrade para pago
        if usuario_existente.get("plano") == "trial" and usuario_existente.get("plano_ativo", False):
            # Permitir - é um upgrade de trial para pago
            print(f"🔄 Upgrade de trial para pago: {request.email}")
            usuario_id_para_usar = usuario_existente["id"]  # ✅ Reutilizar o ID do usuário trial
        
        # Se existe mas está pendente e expirado (PLANO PAGO), permitir re-registro
        elif usuario_existente.get("payment_status") == "pending" and not usuario_existente.get("plano_ativo", False):
            created_at = datetime.fromisoformat(usuario_existente["created_at"].replace("Z", "+00:00"))
            idade_horas = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
            
            if idade_horas > 24:
                # Expirado - permitir re-registro (reutilizar o usuário)
                print(f"🔄 Re-registro permitido: email {request.email} tinha pagamento pendente expirado")
                usuario_id_para_usar = usuario_existente["id"]
            else:
                # Ainda dentro das 24h
                raise HTTPException(
                    status_code=400, 
                    detail=f"Email já cadastrado com pagamento pendente. Aguarde a expiração (ainda faltam {24 - int(idade_horas)} horas) ou use outro email."
                )
        else:
            # Email já cadastrado com pagamento ativo ou conta ativa (não-trial)
            raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    # Verificar plano - busca do banco de dados
    plano = await get_plano_by_id(request.plano_id)
    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    
    if plano.preco == 0:
        raise HTTPException(status_code=400, detail="Use o registro normal para plano trial gratuito")
    
    usuario = None  # Inicializar para rollback
    
    try:
        # 1. PRIMEIRO: Criar pagamento PIX (antes de criar usuário)
        import httpx
        
        mp_access_token = config.mercadopago_access_token
        
        headers = {
            "Authorization": f"Bearer {mp_access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": str(uuid.uuid4())
        }
        
        # Gerar ID temporário para external_reference
        temp_user_id = str(uuid.uuid4())
        
        # Usar API de Payments (mais simples e direta para PIX)
        payload = {
            "transaction_amount": float(plano.preco),
            "description": f"Assinatura Gestor Cred - Plano {plano.nome}",
            "payment_method_id": "pix",
            "date_of_expiration": (datetime.now(timezone.utc) + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "payer": {
                "email": request.email,
                "first_name": request.nome.split()[0] if request.nome else "Cliente",
                "last_name": " ".join(request.nome.split()[1:]) if len(request.nome.split()) > 1 else "Gestor Cred",
                "identification": {
                    "type": "CPF",
                    "number": request.cpf.replace(".", "").replace("-", "")
                }
            },
            "external_reference": temp_user_id,
            "notification_url": f"{os.environ.get('BACKEND_URL', 'https://gestorcred-preview.preview.emergentagent.com')}/api/assinaturas/webhook-mercadopago"
        }
        
        print(f"📤 Enviando PIX para MP (antes de criar usuário): {payload}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.mercadopago.com/v1/payments",
                headers=headers,
                json=payload,
                timeout=30.0
            )
        
        if response.status_code not in [200, 201]:
            error_data = response.json() if response.text else {}
            print(f"❌ Erro MP: {error_data}")
            
            # Verificar se é erro de CPF inválido
            error_message = error_data.get('message', response.text)
            if 'identification' in str(error_data).lower() or 'cpf' in str(error_data).lower():
                error_message = "CPF inválido. Por favor, verifique o CPF informado."
            
            # NÃO criar usuário se falhar aqui
            raise HTTPException(
                status_code=400,
                detail=error_message
            )
        
        mp_response = response.json()
        print(f"✅ Resposta MP PIX: {mp_response}")
        
        # Extrair informações do PIX da API de Payments
        payment_id = str(mp_response.get("id"))
        
        # Dados do PIX estão em point_of_interaction.transaction_data
        point_of_interaction = mp_response.get("point_of_interaction", {})
        transaction_data = point_of_interaction.get("transaction_data", {})
        
        qr_code = transaction_data.get("qr_code", "")
        qr_code_base64 = transaction_data.get("qr_code_base64", "")
        ticket_url = transaction_data.get("ticket_url", "")
        
        if not qr_code:
            # NÃO criar usuário se falhar aqui
            raise HTTPException(
                status_code=500,
                detail="Resposta do Mercado Pago não contém QR Code PIX"
            )
        
        # 2. AGORA SIM: Criar/Atualizar usuário (pagamento foi criado com sucesso)
        if usuario_id_para_usar:
            # É um UPGRADE de trial ou re-registro - atualizar usuário existente
            print("✅ PIX criado! Atualizando usuário existente (upgrade)...")
            
            await db.usuarios.update_one(
                {"id": usuario_id_para_usar},
                {"$set": {
                    "nome": request.nome,
                    "plano": request.plano_id,
                    "plano_ativo": False,  # Vai ativar após pagamento
                    "mercadopago_payment_id": payment_id,
                    "payment_status": "pending",
                    "senha_hash": hash_senha(request.senha),
                    "data_fim_trial": None  # ✅ Limpar trial
                }}
            )
            
            usuario_id = usuario_id_para_usar
            print(f"✅ Usuário atualizado (upgrade trial→pago): {request.email}")
            
        else:
            # É um usuário NOVO - criar do zero
            print("✅ PIX criado! Criando novo usuário...")
            
            usuario = Usuario(
                nome=request.nome,
                email=request.email,
                perfil="usuario",
                plano=request.plano_id,
                plano_ativo=False,  # Vai ativar após pagamento confirmado
                mercadopago_payment_id=payment_id,
                payment_status="pending"
            )
            
            # Usar o ID temporário como o ID real do usuário
            usuario.id = temp_user_id
            
            doc = usuario.model_dump()
            doc["senha_hash"] = hash_senha(request.senha)
            doc["created_at"] = doc["created_at"].isoformat()
            
            await db.usuarios.insert_one(doc)
            usuario_id = usuario.id
            print(f"✅ Usuário criado: {request.email}")
        
        # 3. Registrar transação para monitoramento
        await registrar_transacao(
            usuario_id=usuario_id,
            usuario_email=request.email,  # ✅ Usar request ao invés de usuario
            usuario_nome=request.nome,    # ✅ Usar request ao invés de usuario
            usuario_cpf=request.cpf,
            usuario_telefone=request.telefone,
            plano_id=plano.id,
            plano_nome=plano.nome,
            valor=plano.preco,
            metodo_pagamento="pix",
            status="pendente",
            payment_id=payment_id,
            dados_pagamento={
                "qr_code": qr_code,
                "qr_code_base64": qr_code_base64,
                "ticket_url": ticket_url
            }
        )
        
        # 4. Criar token de autenticação para login automático após pagamento
        token = criar_token(usuario_id)  # ✅ Usar usuario_id
        
        return {
            "success": True,
            "usuario_id": usuario_id,  # ✅ Usar usuario_id
            "payment_id": payment_id,
            "qr_code": qr_code,
            "qr_code_base64": qr_code_base64,
            "ticket_url": ticket_url,
            "amount": plano.preco,
            "plano_nome": plano.nome,
            "token": token,
            "message": "Pagamento PIX criado com sucesso. Aguardando pagamento."
        }
        
    except HTTPException:
        # Propagar HTTPException sem fazer nada
        # Usuário NÃO foi criado ainda se erro aconteceu antes
        raise
    except Exception as e:
        # Se houver erro APÓS criar usuário, fazer rollback
        if usuario is not None and hasattr(usuario, 'id'):
            print(f"⚠️ ROLLBACK: Deletando usuário {usuario.email} devido a erro")
            await db.usuarios.delete_one({"id": usuario.id})
        print(f"❌ Erro checkout PIX: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar checkout PIX: {str(e)}")

@router.post("/upgrade-pix")
async def upgrade_plano_pix(
    plano_id: str,
    cpf: str = None,
    telefone: str = None,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Upgrade de plano para usuário já logado usando PIX
    """
    # Apenas o dono da conta pode fazer upgrade
    if not is_owner(current_user):
        raise HTTPException(status_code=403, detail="Apenas o dono da conta pode realizar upgrades.")

    config = await get_assinatura_gateway_config()
    
    if not config.mercadopago_habilitado:
        raise HTTPException(status_code=400, detail="Mercado Pago não está habilitado")
    
    # Verificar plano
    plano = await get_plano_by_id(plano_id)
    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    
    if plano.preco == 0:
        raise HTTPException(status_code=400, detail="Plano trial não requer pagamento")
    
    try:
        import httpx
        
        # Buscar dados do usuário do banco
        usuario_db = await db.usuarios.find_one({"id": current_user.id})
        
        # Usar CPF e telefone do parâmetro ou do banco
        cpf_final = cpf or usuario_db.get("cpf", "")
        telefone_final = telefone or usuario_db.get("telefone", "")
        
        # Criar pagamento PIX
        mp_data = {
            "transaction_amount": float(plano.preco),
            "description": f"Gestor Cred - Plano {plano.nome}",
            "payment_method_id": "pix",
            "date_of_expiration": (datetime.now(timezone.utc) + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "payer": {
                "email": current_user.email,
                "first_name": current_user.nome.split()[0] if current_user.nome else "Cliente",
                "last_name": " ".join(current_user.nome.split()[1:]) if len(current_user.nome.split()) > 1 else "Gestor Cred"
            }
        }
        
        # Adicionar identificação se tiver CPF
        if cpf_final:
            mp_data["payer"]["identification"] = {
                "type": "CPF",
                "number": cpf_final
            }
        
        headers = {
            "Authorization": f"Bearer {config.mercadopago_access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": f"upgrade-{current_user.id}-{plano_id}-{datetime.now(timezone.utc).timestamp()}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.mercadopago.com/v1/payments",
                json=mp_data,
                headers=headers,
                timeout=30.0
            )
        
        if response.status_code not in [200, 201]:
            error_data = response.json() if response.text else {}
            print(f"❌ Erro MP: {error_data}")
            
            error_message = error_data.get('message', response.text)
            if 'identification' in str(error_data).lower() or 'cpf' in str(error_data).lower():
                error_message = "CPF inválido. Por favor, verifique o CPF informado."
            
            raise HTTPException(status_code=400, detail=error_message)
        
        mp_response = response.json()
        payment_id = str(mp_response.get("id"))
        
        # Extrair dados do PIX
        point_of_interaction = mp_response.get("point_of_interaction", {})
        transaction_data = point_of_interaction.get("transaction_data", {})
        
        qr_code = transaction_data.get("qr_code", "")
        qr_code_base64 = transaction_data.get("qr_code_base64", "")
        ticket_url = transaction_data.get("ticket_url", "")
        
        if not qr_code:
            raise HTTPException(status_code=500, detail="Resposta do Mercado Pago não contém QR Code PIX")
        
        # Atualizar informações do pagamento no usuário
        await db.usuarios.update_one(
            {"id": current_user.id},
            {"$set": {
                "mercadopago_payment_id": payment_id,
                "payment_status": "pending",
                "plano_upgrade_pendente": plano_id
            }}
        )
        
        # Registrar transação
        await registrar_transacao(
            usuario_id=current_user.id,
            usuario_email=current_user.email,
            usuario_nome=current_user.nome,
            usuario_cpf=cpf_final,
            usuario_telefone=telefone_final,
            plano_id=plano.id,
            plano_nome=plano.nome,
            valor=plano.preco,
            metodo_pagamento="pix",
            status="pendente",
            payment_id=payment_id,
            dados_pagamento={
                "qr_code": qr_code,
                "qr_code_base64": qr_code_base64,
                "ticket_url": ticket_url,
                "tipo": "upgrade"
            }
        )
        
        return {
            "success": True,
            "payment_id": payment_id,
            "qr_code": qr_code,
            "qr_code_base64": qr_code_base64,
            "ticket_url": ticket_url,
            "amount": plano.preco,
            "plano_nome": plano.nome,
            "message": "Pagamento PIX criado com sucesso. Aguardando pagamento."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro upgrade PIX: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar pagamento: {str(e)}")

@router.post("/checkout-transparente-card")
async def checkout_transparente_card(request: CheckoutTransparenteCardRequest):
    """
    Cria checkout transparente com Cartão - Cliente fica no nosso site.
    Recebe token do cartão gerado no frontend via SDK do Mercado Pago.
    """
    config = await get_assinatura_gateway_config()
    
    if not config.mercadopago_habilitado:
        raise HTTPException(status_code=400, detail="Mercado Pago não está habilitado")
    
    # Verificar se email já existe
    existing = await db.usuarios.find_one({"email": request.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    # Verificar plano - busca do banco de dados
    plano = await get_plano_by_id(request.plano_id)
    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    
    if plano.preco == 0:
        raise HTTPException(status_code=400, detail="Use o registro normal para plano trial gratuito")
    
    try:
        # 1. Criar usuário
        usuario = Usuario(
            nome=request.nome,
            email=request.email,
            perfil="usuario",
            plano=request.plano_id,
            plano_ativo=False  # Vai ativar após pagamento
        )
        
        doc = usuario.model_dump()
        doc["senha_hash"] = hash_senha(request.senha)
        doc["created_at"] = doc["created_at"].isoformat()
        
        await db.usuarios.insert_one(doc)
        
        # 2. Criar pagamento com Cartão via API do Mercado Pago
        import httpx
        import uuid
        
        mp_access_token = config.mercadopago_access_token
        
        headers = {
            "Authorization": f"Bearer {mp_access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": str(uuid.uuid4())
        }
        
        payload = {
            "total_amount": str(plano.preco),
            "external_reference": usuario.id,
            "processing_mode": "automatic",
            "marketplace": "NONE",
            "payer": {
                "email": request.email,
                "first_name": request.nome
            },
            "transaction": {
                "payments": [
                    {
                        "amount": str(plano.preco),
                        "description": f"Gestor Cred - Plano {plano.nome}",
                        "installments": request.installments,
                        "payment_method": {
                            "id": request.payment_method_id,
                            "type": "credit_card",
                            "token": request.card_token
                        }
                    }
                ]
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.mercadopago.com/v1/payments",
                headers=headers,
                json=payload,
                timeout=30.0
            )
        
        if response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Erro ao processar pagamento: {response.text}"
            )
        
        mp_response = response.json()
        
        # Extrair informações do pagamento
        payment = mp_response.get("transaction", {}).get("payments", [{}])[0]
        payment_id = payment.get("id")
        payment_status = payment.get("status")
        status_detail = payment.get("status_detail")
        
        # 2.5 OBSERVER: Registrar transação no sistema de monitoramento
        motivo_recusa = None
        if payment_status in ["rejected", "cancelled"]:
            motivo_recusa = status_detail or "Pagamento recusado"
        
        await registrar_transacao(
            usuario_id=usuario.id,
            usuario_email=request.email,
            usuario_nome=request.nome,
            usuario_cpf=request.cpf,
            usuario_telefone=request.telefone,
            plano_id=plano.id,
            plano_nome=plano.nome,
            valor=plano.preco,
            metodo_pagamento="cartao_credito",
            status=payment_status,
            payment_id=payment_id,
            order_id=mp_response.get("id"),
            dados_pagamento=mp_response,
            motivo_recusa=motivo_recusa,
            ip_origem=None  # Pode capturar do request se necessário
        )
        
        # 3. Salvar informações do pagamento no usuário
        await db.usuarios.update_one(
            {"id": usuario.id},
            {"$set": {
                "mercadopago_payment_id": payment_id,
                "mercadopago_order_id": mp_response.get("id"),
                "payment_status": payment_status
            }}
        )
        
        # 4. Se pagamento aprovado, ativar plano
        if payment_status == "approved":
            data_expiracao = datetime.now(timezone.utc) + timedelta(days=30)
            await db.usuarios.update_one(
                {"id": usuario.id},
                {"$set": {
                    "plano": request.plano_id,  # ✅ Garantir que o plano está correto
                    "plano_ativo": True,
                    "data_expiracao_plano": data_expiracao.isoformat(),
                    "gateway_pagamento": "mercadopago",
                    "data_fim_trial": None  # ✅ Limpar trial se existir
                }}
            )
        
        # 5. Criar token de autenticação
        token = criar_token(usuario.id)
        
        return {
            "success": payment_status == "approved",
            "usuario_id": usuario.id,
            "payment_id": payment_id,
            "order_id": mp_response.get("id"),
            "payment_status": payment_status,
            "status_detail": status_detail,
            "token": token,
            "message": "Pagamento aprovado!" if payment_status == "approved" else f"Pagamento {payment_status}: {status_detail}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Se houver erro, deletar usuário criado
        if 'usuario' in locals():
            await db.usuarios.delete_one({"id": usuario.id})
        raise HTTPException(status_code=500, detail=f"Erro ao processar pagamento: {str(e)}")

@router.get("/payment-status/{payment_id}")
async def verificar_status_pagamento(payment_id: str):
    """
    Verifica o status de um pagamento no Mercado Pago.
    Usado para polling no frontend (PIX).
    """
    config = await get_assinatura_gateway_config()
    
    if not config.mercadopago_habilitado:
        raise HTTPException(status_code=400, detail="Mercado Pago não está habilitado")
    
    try:
        import httpx
        
        mp_access_token = config.mercadopago_access_token
        
        headers = {
            "Authorization": f"Bearer {mp_access_token}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.mercadopago.com/v1/payments/{payment_id}",
                headers=headers,
                timeout=10.0
            )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="Erro ao verificar status do pagamento"
            )
        
        payment_data = response.json()
        status = payment_data.get("status")
        status_detail = payment_data.get("status_detail")
        valor = payment_data.get("transaction_amount", 0)
        
        # Se pagamento foi aprovado, ativar plano do usuário usando serviço centralizado
        if status == "approved":
            from services.plano_service import ativar_plano_pago
            
            # Buscar usuário pelo payment_id
            usuario = await db.usuarios.find_one({
                "$or": [
                    {"mercadopago_payment_id": payment_id},
                    {"mercadopago_payment_id": str(payment_id)}
                ]
            })
            
            if usuario:
                # Buscar dados da transação para pegar o plano que foi comprado
                transacao = await db.transacoes_checkout.find_one({"payment_id": payment_id})
                plano_id_comprado = transacao.get("plano_id") if transacao else usuario.get("plano", "basico")
                
                # Se o plano atual é trial e não temos plano na transação, usar o plano do usuário
                if plano_id_comprado == "trial":
                    plano_id_comprado = usuario.get("plano", "basico")
                    if plano_id_comprado == "trial":
                        plano_id_comprado = "basico"  # Fallback seguro
                
                # Ativar plano usando serviço centralizado (apenas se ainda não está ativo)
                if not usuario.get("plano_ativo") or usuario.get("plano") == "trial":
                    resultado = await ativar_plano_pago(
                        usuario_id=usuario["id"],
                        plano_id=plano_id_comprado,
                        payment_id=payment_id,
                        gateway="mercadopago",
                        dias_validade=30,
                        valor=valor,
                        origem="polling_pix"
                    )
                    
                    if resultado.get("success"):
                        print(f"✅ [Polling PIX] Plano ativado: {usuario['email']} → {plano_id_comprado}")
                    else:
                        print(f"⚠️ [Polling PIX] Erro: {resultado.get('error')}")
                
                # Criar/atualizar assinatura em assinaturas_admin (para aparecer no painel admin)
                assinatura_existente = await db.assinaturas_admin.find_one({
                    "usuario_id": usuario["id"],
                    "payment_id": payment_id
                })
                
                if not assinatura_existente:
                    data_expiracao = datetime.now(timezone.utc) + timedelta(days=30)
                    nova_assinatura = {
                        "id": str(uuid.uuid4()),
                        "usuario_id": usuario["id"],
                        "plano": plano_id_comprado,
                        "status": "ativa",
                        "valor": valor,
                        "data_inicio": datetime.now(timezone.utc).isoformat(),
                        "data_expiracao": data_expiracao.isoformat(),
                        "gateway": "mercadopago",
                        "payment_id": payment_id,
                        "metodo_pagamento": "pix",
                        "observacoes": "Assinatura via checkout PIX",
                        "criado_em": datetime.now(timezone.utc).isoformat(),
                        "criado_por": "sistema"
                    }
                    await db.assinaturas_admin.insert_one(nova_assinatura)
            
            # Atualizar também o status da transação em transacoes_checkout
            await db.transacoes_checkout.update_one(
                {"payment_id": payment_id},
                {"$set": {
                    "status": "approved",
                    "atualizado_em": datetime.now(timezone.utc),
                    "status_detail": status_detail,
                    "plano_ativado": True
                }}
            )
        elif status in ["rejected", "cancelled"]:
            # Atualizar transação como rejeitada/cancelada
            await db.transacoes_checkout.update_one(
                {"payment_id": payment_id},
                {"$set": {
                    "status": status,
                    "atualizado_em": datetime.now(timezone.utc),
                    "status_detail": status_detail,
                    "motivo_recusa": status_detail
                }}
            )
        
        return {
            "payment_id": payment_id,
            "status": status,
            "status_detail": status_detail,
            "approved": status == "approved"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao verificar pagamento: {str(e)}")

# =========================================
# ENDPOINTS DE RECONCILIAÇÃO E AUDITORIA
# =========================================

@router.get("/admin/reconciliacao")
async def gerar_relatorio_reconciliacao_endpoint(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Gera relatório de reconciliação entre transações e status de assinatura.
    Identifica inconsistências para correção manual ou automática.
    Apenas admin pode acessar.
    """
    if current_user.perfil not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    
    from services.plano_service import gerar_relatorio_reconciliacao
    return await gerar_relatorio_reconciliacao()

@router.post("/admin/corrigir-inconsistencia/{usuario_id}")
async def corrigir_inconsistencia_usuario(
    usuario_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Verifica e corrige inconsistências no plano de um usuário específico.
    Apenas admin pode executar.
    """
    if current_user.perfil not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    
    from services.plano_service import verificar_e_corrigir_inconsistencias
    return await verificar_e_corrigir_inconsistencias(usuario_id)

@router.get("/admin/status-plano/{usuario_id}")
async def obter_status_plano_usuario(
    usuario_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtém status detalhado do plano de um usuário.
    Apenas admin pode acessar.
    """
    if current_user.perfil not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    
    from services.plano_service import obter_status_plano
    return await obter_status_plano(usuario_id)

@router.get("/admin/logs-planos")
async def listar_logs_planos(
    usuario_id: Optional[str] = None,
    limit: int = 50,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista logs de alterações de planos para auditoria.
    Apenas admin pode acessar.
    """
    if current_user.perfil not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    
    query = {}
    if usuario_id:
        query["usuario_id"] = usuario_id
    
    logs = await db.logs_planos.find(
        query, {"_id": 0}
    ).sort("data_acao", -1).limit(limit).to_list(limit)
    
    return {"logs": logs, "total": len(logs)}

# ==================== ASAAS INTEGRATION ====================

class CheckoutAsaasRequest(BaseModel):
    email: str
    nome: str
    cpf: str
    senha: str
    plano_id: str
    codigo_cupom: Optional[str] = None
    metodo_pagamento: str = "UNDEFINED"  # UNDEFINED, PIX, BOLETO, CREDIT_CARD
    telefone: Optional[str] = None

@router.post("/checkout-asaas")
async def checkout_asaas(request: CheckoutAsaasRequest, current_user: Optional[Usuario] = Depends(get_current_user_optional)):
    """
    Cria conta + assinatura usando Asaas
    Suporta PIX, Boleto e Cartão de Crédito
    """
    usuario_id = None
    
    # 1. Se o usuário estiver logado, usamos o ID dele diretamente (upgrade)
    if current_user:
        print(f"🔄 Upgrade de plano para usuário logado: {current_user.email}")
        usuario_id = current_user.id
        request.email = current_user.email
    else:
        # 2. Verificar se o email já existe
        usuario_existente = await db.usuarios.find_one({"email": request.email})
        
        if usuario_existente:
            raise HTTPException(
                status_code=400, 
                detail="Este email já possui uma conta. Por favor, faça login para alterar seu plano."
            )
        
        # 3. Criar novo usuário
        usuario = Usuario(
            nome=request.nome,
            email=request.email,
            perfil="usuario",
            plano="trial",
            plano_ativo=False
        )
        
        doc = usuario.model_dump()
        doc["senha_hash"] = hash_senha(request.senha)
        doc["created_at"] = doc["created_at"].isoformat()
        doc["payment_status"] = "pending"
        doc["plano_pendente"] = request.plano_id
        
        await db.usuarios.insert_one(doc)
        usuario_id = usuario.id

    # Verificar plano
    plano = await get_plano_by_id(request.plano_id)
    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    
    if plano.preco == 0:
        # Trial gratuito - ativar diretamente
        await db.usuarios.update_one(
            {"id": usuario_id},
            {"$set": {
                "plano": "trial",
                "plano_ativo": True,
                "trial_inicio": datetime.now(timezone.utc).isoformat(),
                "trial_expira": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
            }}
        )
        
        token = criar_token(usuario_id)
        return {
            "success": True,
            "trial": True,
            "token": token,
            "message": "Trial ativado com sucesso!"
        }
    
    # VALIDAR E APLICAR CUPOM
    valor_final = plano.preco
    desconto_aplicado = 0
    cupom_usado = None
    
    if request.codigo_cupom:
        codigo_cupom = request.codigo_cupom.strip().upper()
        cupom = await db.cupons.find_one({"codigo": codigo_cupom})
        
        if cupom and not cupom.get("usado", False):
            valido_ate = cupom.get("valido_ate")
            cupom_valido = True
            
            if valido_ate:
                try:
                    if isinstance(valido_ate, str):
                        valido_ate_dt = datetime.fromisoformat(valido_ate.replace('Z', '+00:00'))
                    else:
                        valido_ate_dt = valido_ate
                    
                    if valido_ate_dt.tzinfo is None:
                        valido_ate_dt = valido_ate_dt.replace(tzinfo=timezone.utc)
                        
                    if valido_ate_dt < datetime.now(timezone.utc):
                        cupom_valido = False
                except Exception:
                    pass
            
            if cupom_valido:
                cupom_email = cupom.get("usuario_email")
                if not cupom_email or cupom_email.lower() == request.email.lower():
                    desconto_percentual = cupom.get("desconto_percentual", 0)
                    desconto_aplicado = (plano.preco * desconto_percentual) / 100
                    valor_final = plano.preco - desconto_aplicado
                    cupom_usado = codigo_cupom
                    print(f"🎟️ Cupom aplicado: {codigo_cupom} ({desconto_percentual}% de desconto)")
    
    try:
        # Criar cliente no Asaas
        cliente_asaas = await asaas_service.criar_cliente(
            nome=request.nome,
            email=request.email,
            cpf_cnpj=request.cpf,
            telefone=request.telefone
        )
        
        customer_id = cliente_asaas["id"]
        
        # Criar assinatura recorrente no Asaas
        descricao = f"Gestor Cred - Plano {plano.nome}"
        
        assinatura_asaas = await asaas_service.criar_assinatura(
            customer_id=customer_id,
            valor=valor_final,
            descricao=descricao,
            ciclo="MONTHLY",
            metodo_pagamento=request.metodo_pagamento
        )
        
        # Atualizar usuário com dados da assinatura
        await db.usuarios.update_one(
            {"id": usuario_id},
            {"$set": {
                "plano": request.plano_id,
                "plano_ativo": False,  # Ativa quando webhook confirmar pagamento
                "asaas_customer_id": customer_id,
                "asaas_subscription_id": assinatura_asaas["id"],
                "payment_status": "pending"
            }}
        )
        
        # Salvar transação
        transacao_id = str(uuid.uuid4())
        await db.transacoes_checkout.insert_one({
            "id": transacao_id,
            "usuario_id": usuario_id,
            "plano_id": request.plano_id,
            "gateway": "asaas",
            "asaas_subscription_id": assinatura_asaas["id"],
            "asaas_customer_id": customer_id,
            "valor": valor_final,
            "valor_original": plano.preco,
            "desconto_aplicado": desconto_aplicado,
            "cupom_usado": cupom_usado,
            "status": "pending",
            "metodo_pagamento": request.metodo_pagamento,
            "criado_em": datetime.now(timezone.utc).isoformat(),
            "email": request.email,
            "nome": request.nome
        })
        
        # Marcar cupom como usado
        if cupom_usado:
            await db.cupons.update_one(
                {"codigo": cupom_usado},
                {"$set": {"usado": True, "usado_por": request.email, "usado_em": datetime.now(timezone.utc).isoformat()}}
            )
        
        # Gerar token para login
        token = criar_token(usuario_id)
        
        # Buscar a primeira cobrança gerada pela assinatura
        # O Asaas cria automaticamente a primeira cobrança
        
        # Retornar dados para o frontend
        response_data = {
            "success": True,
            "token": token,
            "customer_id": customer_id,
            "subscription_id": assinatura_asaas["id"],
            "transacao_id": transacao_id,
            "status": "pending",
            "message": "Assinatura criada! Aguardando pagamento."
        }
        
        # Se for PIX, retornar QR Code
        if request.metodo_pagamento == "PIX":
            # Buscar a primeira cobrança da assinatura
            # Asaas retorna o ID da primeira cobrança no objeto
            if assinatura_asaas.get("nextInvoiceId"):
                try:
                    qrcode_data = await asaas_service.obter_qrcode_pix(assinatura_asaas["nextInvoiceId"])
                    response_data["pix"] = {
                        "qrcode": qrcode_data.get("encodedImage"),
                        "payload": qrcode_data.get("payload"),
                        "expirationDate": qrcode_data.get("expirationDate")
                    }
                except Exception as e:
                    print(f"⚠️ Erro ao obter QR Code PIX: {e}")
        
        # Se for BOLETO, retornar link
        elif request.metodo_pagamento == "BOLETO":
            if assinatura_asaas.get("nextInvoiceId"):
                try:
                    boleto_url = await asaas_service.obter_link_boleto(assinatura_asaas["nextInvoiceId"])
                    response_data["boleto"] = {
                        "url": boleto_url
                    }
                except Exception as e:
                    print(f"⚠️ Erro ao obter boleto: {e}")
        
        return response_data
        
    except Exception as e:
        # Se der erro, remover usuário criado (apenas se for novo)
        if not current_user:
            await db.usuarios.delete_one({"id": usuario_id})
        
        print(f"❌ Erro no checkout Asaas: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar assinatura: {str(e)}")

@router.post("/webhook-asaas")
async def webhook_asaas(request: Request):
    """
    Webhook do Asaas para receber notificações de pagamento
    Eventos: PAYMENT_RECEIVED, PAYMENT_CONFIRMED, PAYMENT_OVERDUE, etc.
    🔒 COM VALIDAÇÃO DE ACCESS TOKEN
    """
    try:
        # 🔒 SEGURANÇA: Buscar webhook_token do banco de dados
        config = await db.configuracoes.find_one({"tipo": "assinatura_gateway"})
        
        if not config or not config.get("dados"):
            print("⚠️ Configuração de gateway não encontrada")
            raise HTTPException(status_code=500, detail="Gateway configuration not found")
        
        dados_config = config["dados"]
        webhook_token = dados_config.get("asaas_webhook_token", "")
        
        if webhook_token and webhook_token.strip():
            # Obter header de autenticação do Asaas
            asaas_access_token = request.headers.get("asaas-access-token")
            
            if not asaas_access_token:
                print("⚠️ Webhook Asaas sem access token - rejeitado")
                raise HTTPException(status_code=401, detail="Missing asaas-access-token header")
            
            # Validar token (constant-time comparison para evitar timing attacks)
            import hmac
            if not hmac.compare_digest(webhook_token, asaas_access_token):
                print("⚠️ Token Asaas inválido!")
                print(f"   Esperado: {webhook_token[:10]}...")
                print(f"   Recebido: {asaas_access_token[:10]}...")
                raise HTTPException(status_code=401, detail="Invalid access token")
            
            print("✅ Webhook Asaas autenticado")
        else:
            print("⚠️ ASAAS WEBHOOK TOKEN NÃO CONFIGURADO - Validação desabilitada (INSEGURO!)")
        
        payload = await request.json()
        event = payload.get("event")
        
        print(f"📥 Webhook Asaas recebido: {event}")
        
        # Extrair dados do pagamento
        payment_data = payload.get("payment", {})
        payment_id = payment_data.get("id")
        payment_status = payment_data.get("status")
        subscription_id = payment_data.get("subscription")
        external_reference = payment_data.get("externalReference") or ""
        
        if not payment_id:
            print("⚠️ Webhook sem payment ID")
            return {"status": "ignored"}

        # ==================== RECARGA DE CARTEIRA ====================
        if external_reference.startswith("carteira_recarga_"):
            recarga = await db.carteira_recargas.find_one(
                {"$or": [{"external_reference": external_reference}, {"payment_id": payment_id}]}
            )
            if not recarga:
                print(f"⚠️ Recarga de carteira não encontrada: {external_reference}")
                return {"status": "recharge_not_found"}

            status_lower = (payment_status or "").upper()
            if event in ("PAYMENT_CONFIRMED", "PAYMENT_RECEIVED") or status_lower in ("RECEIVED", "CONFIRMED", "RECEIVED_IN_CASH"):
                from services.carteira_service import creditar_recarga
                await creditar_recarga(
                    owner_id=recarga["owner_id"],
                    valor=float(recarga["valor"]),
                    gateway="asaas",
                    payment_id=payment_id,
                    metadata={"recarga_id": recarga["id"], "event": event},
                )
                await db.carteira_recargas.update_one(
                    {"id": recarga["id"]},
                    {"$set": {"status": "paid", "paid_at": datetime.now(timezone.utc).isoformat(), "webhook_data": payload}}
                )
                print(f"✅ Recarga carteira creditada: {recarga['id']} R$ {recarga['valor']:.2f}")
            return {"status": "carteira_recarga_processed"}

        # Buscar usuário pela assinatura Asaas
        usuario = await db.usuarios.find_one({"asaas_subscription_id": subscription_id})
        
        if not usuario:
            print(f"⚠️ Usuário não encontrado para subscription: {subscription_id}")
            return {"status": "user_not_found"}
        
        usuario_id = usuario["id"]
        
        # Atualizar transação
        await db.transacoes_checkout.update_one(
            {"asaas_subscription_id": subscription_id, "usuario_id": usuario_id},
            {"$set": {
                "status": payment_status.lower() if payment_status else "pending",
                "asaas_payment_id": payment_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "webhook_data": payload
            }}
        )
        
        # Processar eventos
        if event == "PAYMENT_CONFIRMED" or event == "PAYMENT_RECEIVED":
            # Pagamento confirmado - ativar plano
            plano_id = usuario.get("plano", "basico")
            
            await db.usuarios.update_one(
                {"id": usuario_id},
                {"$set": {
                    "plano_ativo": True,
                    "payment_status": "paid",
                    "assinatura_ativa_desde": datetime.now(timezone.utc).isoformat(),
                    "proxima_cobranca": payment_data.get("dueDate")
                }}
            )
            
            print(f"✅ Plano ativado para usuário: {usuario['email']}")
            
            # Criar notificação para o usuário
            await db.notificacoes.insert_one({
                "id": str(uuid.uuid4()),
                "usuario_id": usuario_id,
                "tipo": "sistema",
                "titulo": "Pagamento Confirmado! 🎉",
                "mensagem": f"Seu plano {plano_id.title()} foi ativado com sucesso. Aproveite todos os recursos!",
                "lida": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            
        elif event == "PAYMENT_OVERDUE":
            # Pagamento vencido - desativar plano
            await db.usuarios.update_one(
                {"id": usuario_id},
                {"$set": {
                    "plano_ativo": False,
                    "payment_status": "overdue"
                }}
            )
            
            print(f"⚠️ Plano desativado por falta de pagamento: {usuario['email']}")
            
        elif event == "PAYMENT_DELETED":
            # Cobrança cancelada
            await db.usuarios.update_one(
                {"id": usuario_id},
                {"$set": {
                    "payment_status": "cancelled"
                }}
            )
            
            print(f"🚫 Pagamento cancelado: {usuario['email']}")
        
        return {"status": "processed", "event": event}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro ao processar webhook Asaas: {e}")

@router.get("/transacao/{transacao_id}")
async def obter_transacao(
    transacao_id: str,
    current_user: Optional[Usuario] = Depends(get_current_user_optional)
):
    """Busca detalhes de uma transação para exibir na página de pagamento"""
    try:
        transacao = await db.transacoes_checkout.find_one({"id": transacao_id})
        
        if not transacao:
            raise HTTPException(status_code=404, detail="Transação não encontrada")
        
        # Buscar informações do plano
        plano = await db.planos.find_one({"id": transacao["plano_id"]})
        
        response = {
            "id": transacao["id"],
            "valor": transacao["valor"],
            "status": transacao["status"],
            "plano_nome": plano["nome"] if plano else transacao["plano_id"],
            "metodo_pagamento": transacao.get("metodo_pagamento"),
            "criado_em": transacao["criado_em"]
        }
        
        # Se tiver dados PIX armazenados no webhook
        if transacao.get("webhook_data"):
            webhook_data = transacao["webhook_data"]
            payment_data = webhook_data.get("payment", {})
            
            # Tentar buscar QR Code PIX se disponível
            if transacao.get("metodo_pagamento") == "PIX":
                try:
                    from services.asaas_service import asaas_service
                    payment_id = transacao.get("asaas_payment_id")
                    if payment_id:
                        qrcode_data = await asaas_service.obter_qrcode_pix(payment_id)
                        response["pix"] = qrcode_data
                except Exception as e:
                    print(f"Erro ao buscar QR Code: {e}")
            
            # Se tiver boleto
            if transacao.get("metodo_pagamento") == "BOLETO":
                response["boleto"] = {
                    "url": payment_data.get("bankSlipUrl")
                }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Erro ao buscar transação: {e}")
        raise HTTPException(status_code=500, detail=str(e))

        raise HTTPException(status_code=500, detail=str(e))

@router.get("/asaas/cobranca/{payment_id}")
async def verificar_cobranca_asaas(
    payment_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Verifica status de uma cobrança no Asaas"""
    try:
        cobranca = await asaas_service.buscar_cobranca(payment_id)
        return {
            "success": True,
            "cobranca": cobranca
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar cobrança: {str(e)}")


# ==================== CHECKOUT SYNCPAY PIX ====================

class CheckoutSyncPayRequest(BaseModel):
    plano_id: str
    nome: str
    email: str
    senha: str
    cpf: Optional[str] = None
    telefone: Optional[str] = None
    codigo_cupom: Optional[str] = None

@router.post("/checkout-syncpay")
async def checkout_syncpay(request: CheckoutSyncPayRequest, background_tasks: BackgroundTasks):
    """
    Cria checkout via SyncPay PIX.
    Cria usuário + cobrança PIX e retorna QR Code.
    """
    background_tasks.add_task(limpar_usuarios_expirados)

    # 1. Verificar se SyncPay está habilitado
    config = await get_assinatura_gateway_config()
    if not config.syncpay_habilitado:
        raise HTTPException(status_code=400, detail="SyncPay não está habilitado")

    # 2. Verificar plano
    plano = await get_plano_by_id(request.plano_id)
    if not plano:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    if plano.preco == 0:
        raise HTTPException(status_code=400, detail="Use o registro normal para plano trial gratuito")

    # 3. Verificar email
    usuario_existente = await db.usuarios.find_one({"email": request.email})
    usuario_id_para_usar = None

    if usuario_existente:
        # Permitir upgrade se é trial ativo
        if usuario_existente.get("plano") == "trial" and usuario_existente.get("plano_ativo", False):
            usuario_id_para_usar = usuario_existente["id"]
        # Permitir upgrade se já tem plano pago ativo (troca de plano)
        elif usuario_existente.get("plano_ativo", False):
            usuario_id_para_usar = usuario_existente["id"]
        elif usuario_existente.get("payment_status") == "pending" and not usuario_existente.get("plano_ativo", False):
            created_at = datetime.fromisoformat(usuario_existente["created_at"].replace("Z", "+00:00"))
            idade_horas = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
            if idade_horas > 24:
                usuario_id_para_usar = usuario_existente["id"]
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Email já cadastrado com pagamento pendente. Aguarde {24 - int(idade_horas)}h ou use outro email."
                )
        else:
            raise HTTPException(status_code=400, detail="Email já cadastrado")

    # 4. Aplicar cupom se houver
    valor_final = plano.preco
    cupom_usado = None
    desconto_aplicado = 0

    if request.codigo_cupom:
        codigo = request.codigo_cupom.strip().upper()
        cupom = await db.cupons.find_one({"codigo": codigo})
        if cupom and not cupom.get("usado", False):
            cupom_email = cupom.get("usuario_email")
            if not cupom_email or cupom_email.lower() == request.email.lower():
                desconto_percentual = cupom.get("desconto_percentual", 0)
                desconto_aplicado = (plano.preco * desconto_percentual) / 100
                valor_final = plano.preco - desconto_aplicado
                cupom_usado = codigo

    # 5. Obter SyncPay service
    from services.syncpay import obter_syncpay_service
    syncpay = await obter_syncpay_service()
    if not syncpay:
        raise HTTPException(status_code=503, detail="SyncPay não configurado corretamente. Verifique as credenciais.")

    usuario_criado = False
    usuario_id = None

    try:
        # 6. Criar/atualizar usuário
        if usuario_id_para_usar:
            update_fields = {
                "nome": request.nome,
                "plano_pendente": request.plano_id,
                "payment_status": "pending",
                "data_fim_trial": None
            }
            # Só atualizar senha se fornecida e se NÃO é upgrade de plano ativo
            if request.senha and not usuario_existente.get("plano_ativo", False):
                update_fields["senha_hash"] = hash_senha(request.senha)
                update_fields["plano"] = request.plano_id
                update_fields["plano_ativo"] = False
            
            await db.usuarios.update_one(
                {"id": usuario_id_para_usar},
                {"$set": update_fields}
            )
            usuario_id = usuario_id_para_usar
        else:
            usuario = Usuario(
                nome=request.nome,
                email=request.email,
                perfil="usuario",
                plano="trial",
                plano_ativo=False
            )
            doc = usuario.model_dump()
            doc["senha_hash"] = hash_senha(request.senha)
            doc["created_at"] = doc["created_at"].isoformat()
            doc["payment_status"] = "pending"
            doc["plano_pendente"] = request.plano_id
            await db.usuarios.insert_one(doc)
            usuario_id = usuario.id
            usuario_criado = True

        # 7. Criar cobrança PIX no SyncPay
        descricao = f"Gestor Cred - Plano {plano.nome}"
        webhook_url = f"{os.environ.get('BASE_URL', os.environ.get('APP_URL', ''))}/api/assinaturas/webhook-syncpay"
        cobranca = await syncpay.criar_cobranca_pix(
            valor=valor_final,
            descricao=descricao,
            external_id=usuario_id,
            customer_name=request.nome,
            customer_cpf=request.cpf,
            customer_email=request.email,
            webhook_url=webhook_url
        )

        transaction_id = cobranca.get("identifier", "")
        pix_code = cobranca.get("pix_code", "")

        # 8. Salvar transaction_id no usuário
        await db.usuarios.update_one(
            {"id": usuario_id},
            {"$set": {
                "syncpay_transaction_id": transaction_id,
                "plano_pendente": request.plano_id
            }}
        )

        # 9. Registrar transação
        transacao_id = str(uuid.uuid4())
        await db.transacoes_checkout.insert_one({
            "id": transacao_id,
            "usuario_id": usuario_id,
            "plano_id": request.plano_id,
            "gateway": "syncpay",
            "payment_id": transaction_id,
            "valor": valor_final,
            "valor_original": plano.preco,
            "desconto_aplicado": desconto_aplicado,
            "cupom_usado": cupom_usado,
            "status": "pending",
            "metodo_pagamento": "pix",
            "criado_em": datetime.now(timezone.utc).isoformat(),
            "email": request.email,
            "nome": request.nome
        })

        # 10. Marcar cupom como usado
        if cupom_usado:
            await db.cupons.update_one(
                {"codigo": cupom_usado},
                {"$set": {"usado": True, "usado_por": request.email, "usado_em": datetime.now(timezone.utc).isoformat()}}
            )

        # 11. Gerar token
        token = criar_token(usuario_id)

        return {
            "success": True,
            "token": token,
            "transacao_id": transacao_id,
            "transaction_id": transaction_id,
            "pix_code": pix_code,
            "amount": valor_final,
            "plano_nome": plano.nome,
            "message": "Cobrança PIX criada. Copie o código PIX para pagar."
        }

    except HTTPException:
        raise
    except Exception as e:
        # Rollback: deletar usuário se foi criado nesta operação
        if usuario_criado and usuario_id:
            await db.usuarios.delete_one({"id": usuario_id})
        print(f"❌ Erro checkout SyncPay: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao criar cobrança SyncPay: {str(e)}")


@router.get("/syncpay-status/{transaction_id}")
async def verificar_status_syncpay(transaction_id: str):
    """
    Verifica status de uma transação SyncPay para polling no frontend.
    """
    from services.syncpay import obter_syncpay_service
    syncpay = await obter_syncpay_service()
    if not syncpay:
        raise HTTPException(status_code=503, detail="SyncPay não configurado")

    try:
        resultado = await syncpay.consultar_transacao(transaction_id)
        status = resultado.get("status", "pending")

        # Mapear status SyncPay para nosso padrão
        # SyncPay: pending, completed, failed, refunded, med
        is_approved = status in ("completed",)

        # Se aprovado, ativar plano
        if is_approved:
            usuario = await db.usuarios.find_one({"syncpay_transaction_id": transaction_id})
            if usuario and not usuario.get("plano_ativo"):
                plano_id = usuario.get("plano_pendente") or usuario.get("plano", "basico")
                valor = resultado.get("amount", 0)

                await ativar_plano_pago(
                    usuario_id=usuario["id"],
                    plano_id=plano_id,
                    payment_id=transaction_id,
                    gateway="syncpay",
                    dias_validade=30,
                    valor=float(valor),
                    origem="polling_syncpay"
                )

            # Atualizar transação
            await db.transacoes_checkout.update_one(
                {"payment_id": transaction_id},
                {"$set": {"status": "approved", "updated_at": datetime.now(timezone.utc).isoformat()}}
            )

        return {
            "transaction_id": transaction_id,
            "status": status,
            "approved": is_approved,
            "data": resultado
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao verificar status: {str(e)}")


# ==================== WEBHOOK SYNCPAY PIX ====================

@router.post("/webhook-syncpay")
async def webhook_syncpay(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook SyncPay para processar eventos de pagamento PIX
    Eventos: cashin.onCreate, cashin.onUpdate
    """
    try:
        body = await request.body()
        
        # Buscar config para validar assinatura
        config_doc = await db.configuracoes.find_one({"tipo": "assinatura_gateway"})
        if not config_doc:
            print("⚠️ [SyncPay] Config não encontrada")
            return {"received": True}  # Retorna 200 para não retriar
        
        config_data = config_doc.get("dados", {})
        webhook_secret = config_data.get("syncpay_webhook_secret", "")
        
        # Validar assinatura HMAC (se configurado)
        if webhook_secret:
            import hmac
            import hashlib
            
            # Verificar header de assinatura (ajustar nome baseado na doc real)
            signature_header = request.headers.get("X-Signature") or request.headers.get("X-Syncpay-Signature")
            
            if signature_header:
                expected_signature = hmac.new(
                    webhook_secret.encode('utf-8'),
                    body,
                    hashlib.sha256
                ).hexdigest()
                
                if not hmac.compare_digest(signature_header, expected_signature):
                    print("⚠️ [SyncPay] Assinatura inválida")
                    raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Parse JSON
        data = await request.json()
        
        print(f"📨 [SyncPay Webhook] Recebido: {data.get('event', 'unknown')}")
        
        # Processar evento
        event_type = data.get("event") or data.get("type")
        
        if not event_type:
            print("⚠️ [SyncPay] Evento sem tipo")
            return {"received": True}
        
        # Eventos de CashIn (PIX recebido)
        if "cashin" in event_type.lower() or "approved" in event_type.lower():
            transaction_id = data.get("transaction_id") or data.get("id")
            external_ref = data.get("external_reference") or data.get("external_id")
            status = data.get("status")
            amount = data.get("amount") or data.get("value", 0)
            
            print(f"💰 [SyncPay] CashIn - Transaction: {transaction_id}, Status: {status}, Amount: {amount}")
            
            # Se pagamento aprovado (SyncPay v2 status: completed)
            if status in ["completed", "approved", "confirmed", "paid", "success"]:
                # ==================== RECARGA DE CARTEIRA (SyncPay) ====================
                if external_ref and external_ref.startswith("carteira_recarga_"):
                    recarga = await db.carteira_recargas.find_one(
                        {"$or": [{"external_reference": external_ref}, {"payment_id": transaction_id}]}
                    )
                    if recarga:
                        from services.carteira_service import creditar_recarga
                        await creditar_recarga(
                            owner_id=recarga["owner_id"],
                            valor=float(recarga["valor"]),
                            gateway="syncpay",
                            payment_id=transaction_id or recarga.get("payment_id"),
                            metadata={"recarga_id": recarga["id"]},
                        )
                        await db.carteira_recargas.update_one(
                            {"id": recarga["id"]},
                            {"$set": {"status": "paid", "paid_at": datetime.now(timezone.utc).isoformat(), "webhook_data": data}}
                        )
                        print(f"✅ [SyncPay] Recarga carteira creditada: {recarga['id']}")
                        return {"received": True, "status": "carteira_recarga_processed"}

                # Buscar usuário pelo external_reference (pode ser user_id ou assinatura_id)
                if external_ref:
                    # Tentar encontrar usuário
                    usuario = await db.usuarios.find_one({
                        "$or": [
                            {"id": external_ref},
                            {"syncpay_transaction_id": transaction_id}
                        ]
                    })
                    
                    if usuario:
                        # Atualizar transação
                        await db.transacoes_checkout.update_one(
                            {"payment_id": transaction_id},
                            {
                                "$set": {
                                    "status": "approved",
                                    "updated_at": datetime.now(timezone.utc).isoformat(),
                                    "webhook_data": data
                                }
                            },
                            upsert=True
                        )
                        
                        # Ativar plano
                        plano_id = usuario.get("plano_pendente") or usuario.get("plano") or "basico"
                        
                        resultado = await ativar_plano_pago(
                            usuario_id=usuario["id"],
                            plano_id=plano_id,
                            payment_id=transaction_id,
                            gateway="syncpay",
                            dias_validade=30,
                            valor=float(amount),
                            origem="webhook_syncpay"
                        )
                        
                        if resultado.get("success"):
                            print(f"✅ [SyncPay] Plano ativado: {usuario['email']} - {plano_id}")
                        else:
                            print(f"⚠️ [SyncPay] Erro ao ativar plano: {resultado.get('error')}")
                    else:
                        print(f"⚠️ [SyncPay] Usuário não encontrado para ref: {external_ref}")
                else:
                    print("⚠️ [SyncPay] Webhook sem external_reference")
        
        return {"received": True, "status": "processed"}
        
    except Exception as e:
        print(f"❌ [SyncPay Webhook] Erro: {e}")
        import traceback
        traceback.print_exc()
        # Retornar 200 para não retriar infinitamente
        return {"received": True, "error": str(e)}
