"""
Gestor Cred - Sistema de Gestão de Empréstimos a Juros
API Principal - Versão 2.1 (Com Segurança Reforçada + Fase 2)
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from config import client, db, ENVIRONMENT, CORS_ORIGINS
from routes import api_router
from security import SecurityMiddleware, RateLimitMiddleware, rate_limiter, get_cors_origins
import asyncio
from services.logging_service import get_logger, setup_logging
from scheduler import setup_scheduler, shutdown_scheduler

# Configurar logging estruturado
setup_logging()
logger = get_logger("gestorcred.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação"""
    # Startup
    logger.info("Gestor Cred API v2.1 iniciando...", data={"version": "2.1.0", "environment": ENVIRONMENT})
    logger.info("Conectando ao MongoDB e criando índices...")
    
    # Criar índices otimizados para todas as queries frequentes
    try:
        # ==================== ÍNDICES DE USUÁRIOS ====================
        await db.usuarios.create_index("email", unique=True)
        await db.usuarios.create_index("id", unique=True)
        await db.usuarios.create_index([("status", 1), ("plano", 1)])
        
        # ==================== ÍNDICES DE CLIENTES ====================
        # ==================== ÍNDICES DE CLIENTES ====================
        # Busca por usuário + CPF/CNPJ (único, mas permitindo nulos via partialFilterExpression)
        try:
            await db.clientes.create_index(
                [("usuario_id", 1), ("cpf_cnpj", 1)], 
                unique=True,
                partialFilterExpression={"cpf_cnpj": {"$type": "string"}}
            )
        except Exception:
            # Se falhar (provavelmente conflito com índice antigo), tenta dropar e recriar
            try:
                await db.clientes.drop_index("usuario_id_1_cpf_cnpj_1")
                await db.clientes.create_index(
                    [("usuario_id", 1), ("cpf_cnpj", 1)], 
                    unique=True,
                    partialFilterExpression={"cpf_cnpj": {"$type": "string"}}
                )
                logger.info("Índice de CPF migrado para aceitar nulos")
            except Exception as e:
                logger.warning(f"Erro ao atualizar índice de CPF: {e}")
        # Busca por usuário + status (listagem filtrada)
        await db.clientes.create_index([("usuario_id", 1), ("status", 1)])
        # Busca por usuário + score (análise)
        await db.clientes.create_index([("usuario_id", 1), ("score_atual", -1)])
        # Busca por usuário + classificação (análise)
        await db.clientes.create_index([("usuario_id", 1), ("classificacao", 1)])
        # Soft delete filter
        await db.clientes.create_index([("usuario_id", 1), ("deleted", 1)])
        
        # ==================== ÍNDICES DE EMPRÉSTIMOS ====================
        # Busca por usuário (listagem)
        await db.emprestimos.create_index([("usuario_id", 1), ("created_at", -1)])
        # Busca por usuário + cliente (listagem filtrada)
        await db.emprestimos.create_index([("usuario_id", 1), ("cliente_id", 1)])
        # Busca por usuário + status (dashboard, filtros)
        await db.emprestimos.create_index([("usuario_id", 1), ("status", 1)])
        # Busca por usuário + cliente + status (verificação de empréstimos ativos)
        await db.emprestimos.create_index([("usuario_id", 1), ("cliente_id", 1), ("status", 1)])
        # Soft delete filter
        await db.emprestimos.create_index([("usuario_id", 1), ("deleted", 1)])
        
        # ==================== ÍNDICES DE PARCELAS ====================
        # Busca por empréstimo (listagem de parcelas)
        await db.parcelas.create_index([("usuario_id", 1), ("emprestimo_id", 1), ("numero_parcela", 1)])
        # Busca por status (parcelas pendentes/atrasadas)
        await db.parcelas.create_index([("usuario_id", 1), ("status", 1)])
        # Busca por data de vencimento (notificações)
        await db.parcelas.create_index([("usuario_id", 1), ("data_vencimento", 1), ("status", 1)])
        # Soft delete filter
        await db.parcelas.create_index([("usuario_id", 1), ("deleted", 1)])
        # 🔒 ÚNICO PARCIAL: impede duplicação de (emprestimo_id, numero_parcela)
        # para parcelas não-deletadas (corrige race condition do job de geração automática)
        # Normalizar campo deleted=false em parcelas que não o possuem (necessário p/ índice)
        await db.parcelas.update_many(
            {"deleted": {"$exists": False}},
            {"$set": {"deleted": False}}
        )
        try:
            await db.parcelas.create_index(
                [("emprestimo_id", 1), ("numero_parcela", 1)],
                unique=True,
                partialFilterExpression={"deleted": False},
                name="uniq_emprestimo_numero_parcela_ativa"
            )
        except Exception as e:
            logger.warning(
                "Índice único parcial de parcelas não criado (provável duplicata existente)",
                data={"error": str(e)}
            )
        
        # ==================== ÍNDICES DE PAGAMENTOS ====================
        # Busca por usuário (listagem)
        await db.pagamentos.create_index([("usuario_id", 1), ("data_pagamento", -1)])
        # Busca por parcela
        await db.pagamentos.create_index([("usuario_id", 1), ("parcela_id", 1)])
        # Busca por empréstimo
        await db.pagamentos.create_index([("usuario_id", 1), ("emprestimo_id", 1)])
        # Soft delete filter
        await db.pagamentos.create_index([("usuario_id", 1), ("deleted", 1)])
        
        # ==================== ÍNDICES DE NOTIFICAÇÕES ====================
        await db.notificacoes.create_index([("usuario_id", 1), ("lida", 1), ("created_at", -1)])
        await db.notificacoes.create_index([("usuario_id", 1), ("tipo", 1)])
        
        # ==================== ÍNDICES DE AUDITORIA ====================
        await db.auditoria.create_index([("usuario_id", 1), ("created_at", -1)])
        await db.auditoria.create_index([("entidade", 1), ("entidade_id", 1)])
        await db.auditoria.create_index([("acao", 1), ("created_at", -1)])
        # TTL index para limpar logs antigos (365 dias)
        await db.auditoria.create_index("created_at", expireAfterSeconds=31536000)
        
        # ==================== ÍNDICES DE SCORES ====================
        await db.scores_historico.create_index([("usuario_id", 1), ("cliente_id", 1), ("created_at", -1)])
        await db.scores_historico.create_index([("usuario_id", 1), ("created_at", -1)])
        # TTL index para limpar histórico antigo (2 anos)
        await db.scores_historico.create_index("created_at", expireAfterSeconds=63072000)
        
        # ==================== ÍNDICES DE SEGURANÇA ====================
        await db.security_logs.create_index([("created_at", -1)])
        await db.security_logs.create_index([("ip", 1), ("created_at", -1)])
        # TTL index para limpar logs antigos (90 dias)
        await db.security_logs.create_index("created_at", expireAfterSeconds=7776000)
        
        # ==================== ÍNDICES DE ASSINATURAS ====================
        await db.assinaturas.create_index([("usuario_id", 1), ("status", 1)])
        await db.assinaturas.create_index("stripe_subscription_id")
        await db.assinaturas.create_index("mercadopago_subscription_id")
        
        # ==================== ÍNDICES DE CONTRATOS ====================
        await db.contratos.create_index([("usuario_id", 1), ("emprestimo_id", 1)])
        
        # ==================== ÍNDICES DE TRANSAÇÕES CHECKOUT ====================
        await db.transacoes_checkout.create_index([("usuario_id", 1), ("created_at", -1)])
        await db.transacoes_checkout.create_index([("usuario_email", 1), ("criado_em", -1)])
        await db.transacoes_checkout.create_index([("status", 1), ("metodo_pagamento", 1)])
        await db.transacoes_checkout.create_index([("payment_id", 1)])
        await db.transacoes_checkout.create_index([("order_id", 1)])
        await db.transacoes_checkout.create_index([("criado_em", -1)])
        # TTL index para limpar transações muito antigas (1 ano)
        await db.transacoes_checkout.create_index("criado_em", expireAfterSeconds=31536000)
        
        # ==================== ÍNDICES DO PORTAL DO CLIENTE ====================
        await db.portal_auth.create_index("cliente_id", unique=True)
        await db.portal_auth.create_index([("usuario_id", 1), ("cliente_id", 1)])
        await db.portal_auth.create_index([("ativo", 1), ("bloqueado_ate", 1)])
        
        logger.info("Índices MongoDB criados com sucesso", data={"total_collections": 12})
        
    except Exception as e:
        logger.warning(f"Alguns índices já existem ou erro ao criar", data={"error": str(e)})
    
    # Iniciar o scheduler de jobs automáticos
    # 🔒 RUN_SCHEDULER=true deve ser definido em APENAS UMA réplica/worker em produção
    # (default true em dev/single-instance). Isso previne race conditions em jobs que
    # criam dados (ex.: geração automática de parcelas para empréstimos sem prazo).
    run_scheduler = os.environ.get("RUN_SCHEDULER", "true").lower() == "true"
    if run_scheduler:
        try:
            setup_scheduler()
            logger.info("Scheduler de jobs iniciado", data={"status": "running"})
        except Exception as e:
            logger.error(f"Erro ao iniciar scheduler: {e}", data={"error": str(e)})
    else:
        logger.info("Scheduler DESABILITADO nesta instância (RUN_SCHEDULER=false)")
    
    logger.info("Gestor Cred API v2.1 pronta!", data={"status": "ready"})
    
    # Iniciar limpeza do rate limiter em background
    asyncio.create_task(rate_limiter._cleanup_loop())
    
    yield
    
    # Shutdown
    if run_scheduler:
        logger.info("Parando scheduler de jobs...")
        shutdown_scheduler()
    
    logger.info("Encerrando conexão com MongoDB...")
    client.close()
    logger.info("Gestor Cred API encerrada.")



# Criar aplicação FastAPI
app = FastAPI(
    title="Gestor Cred API",
    description="Sistema de Gestão de Empréstimos a Juros - API RESTful",
    version="2.1.0",
    lifespan=lifespan,
    # Desabilitar docs em produção
    docs_url="/docs" if ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if ENVIRONMENT != "production" else None,
)

# 0. Logger de Depuração de Webhooks (PRIMEIRO MIDDLEWARE)
@app.middleware("http")
async def debug_webhooks(request: Request, call_next):
    path = request.url.path
    if "webhook" in path.lower():
        logger.info(f"🔍 [WEBHOOK DEBUG] {request.method} {path} - IP: {request.client.host if request.client else 'unknown'}")
    return await call_next(request)

# 1. Rate Limiting (primeiro para bloquear abusos)
app.add_middleware(RateLimitMiddleware)

# 2. Headers de Segurança
app.add_middleware(SecurityMiddleware)

# 3. CORS configurado corretamente
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)


# ==================== ROTAS ====================

# Incluir rotas da API
app.include_router(api_router, prefix="/api")

# Mount static files
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "app": "Gestor Cred - Sistema de Gestão de Empréstimos a Juros",
        "version": "2.1.0",
        "status": "online",
        "features": ["soft_delete", "pagination", "structured_logging", "optimized_indexes"],
        "docs": "/docs" if ENVIRONMENT != "production" else None
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "version": "2.1.0"}


@app.get("/api/timezone-info")
async def timezone_info():
    """Retorna informações sobre o timezone configurado"""
    from utils.timezone_utils import get_offset_info, now_sp, now_utc, format_datetime_br
    
    info = get_offset_info()
    info["now_sp_formatted"] = format_datetime_br(now_sp())
    info["now_utc_formatted"] = format_datetime_br(now_utc())
    
    return info
