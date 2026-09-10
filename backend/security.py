"""
Módulo de Segurança - Kredor
Implementa: Rate Limiting, Headers de Segurança, Validação
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import asyncio
import hashlib
import os
from pymongo import ReturnDocument

# ==================== RATE LIMITING ====================

class RateLimiter:
    """
    Rate Limiter distribuído (compartilhado entre workers/instâncias) usando MongoDB.

    Usa janela fixa por (IP, bucket-de-minuto) com contador atômico ($inc + upsert).
    Como o estado vive no MongoDB, todos os processos gunicorn/uvicorn compartilham
    os mesmos contadores — diferente do antigo contador em memória, que era por-processo
    e podia ser contornado por balanceamento entre workers.

    Limpeza automática via índice TTL em `expire_at` (criado no startup).
    """
    def __init__(self):
        self.window_size = 60      # 1 minuto
        self.max_requests = 200    # rotas normais
        self.max_auth_requests = 50  # rotas de autenticação
        self.block_duration = 60   # bloqueio (s) ao exceder muito o limite

    async def _cleanup_loop(self):
        """No-op: a expiração é feita pelo índice TTL do MongoDB."""
        while True:
            await asyncio.sleep(3600)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _db(self):
        from config import db
        return db

    async def check_rate_limit(self, request: Request, is_auth_route: bool = False) -> bool:
        """Retorna True se permitido, False se excedeu o limite. Estado no MongoDB."""
        ip = self._get_client_ip(request)
        now = datetime.now(timezone.utc)
        bucket = int(now.timestamp() // self.window_size)
        key = f"{ip}:{bucket}"
        max_req = self.max_auth_requests if is_auth_route else self.max_requests

        db = self._db()
        try:
            doc = await db.rate_limits.find_one_and_update(
                {"_id": key},
                {
                    "$inc": {"count": 1},
                    "$setOnInsert": {
                        "ip": ip,
                        "expire_at": now + timedelta(seconds=self.window_size + self.block_duration),
                    },
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except Exception:
            # Fail-open: se o Mongo falhar, não derrubar a aplicação por rate limit
            return True

        return doc.get("count", 0) <= max_req

    def get_retry_after(self, request: Request) -> int:
        """Segundos até a próxima janela."""
        now = datetime.now(timezone.utc)
        return int(self.window_size - (now.timestamp() % self.window_size)) + 1


# Instância global do rate limiter
rate_limiter = RateLimiter()


# ==================== MIDDLEWARE DE SEGURANÇA ====================

class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware que adiciona headers de segurança"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Headers de Segurança
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy (ajustar conforme necessário)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        
        # HSTS (apenas em produção com HTTPS)
        if os.environ.get("ENVIRONMENT") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware de Rate Limiting"""
    
    async def dispatch(self, request: Request, call_next):
        # 🛡️ Ignorar OPTIONS para evitar problemas de CORS (Preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
            
        # Rotas de autenticação têm limite mais restrito
        path = request.url.path
        is_auth_route = "/auth/login" in path or "/auth/registro" in path
        
        # Ignorar rate limit para health checks e webhooks
        if path in ["/health", "/", "/docs", "/openapi.json"] or "/webhook" in path:
            return await call_next(request)
        
        # Verificar rate limit
        if not await rate_limiter.check_rate_limit(request, is_auth_route):
            retry_after = rate_limiter.get_retry_after(request)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Muitas requisições. Por favor, aguarde.",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )
        
        return await call_next(request)


# ==================== VALIDAÇÃO DE ENTRADA ====================

def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitiza string de entrada
    Remove caracteres perigosos e limita tamanho
    """
    if not value:
        return value
    
    # Limitar tamanho
    value = value[:max_length]
    
    # Remover caracteres de controle (exceto espaços e newlines)
    value = ''.join(char for char in value if char.isprintable() or char in '\n\r\t')
    
    return value.strip()


def validate_object_id(value: str) -> bool:
    """Valida se é um UUID válido"""
    import re
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(value))


def validate_email(email: str) -> bool:
    """Valida formato de email"""
    import re
    email_pattern = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    return bool(email_pattern.match(email))


def validate_cpf_cnpj(value: str) -> bool:
    """Valida CPF ou CNPJ"""
    # Remove caracteres não numéricos
    numbers = ''.join(filter(str.isdigit, value))
    
    if len(numbers) == 11:
        return _validate_cpf(numbers)
    elif len(numbers) == 14:
        return _validate_cnpj(numbers)
    
    return False


def _validate_cpf(cpf: str) -> bool:
    """Valida CPF"""
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    
    # Primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    d1 = 0 if resto < 2 else 11 - resto
    
    if int(cpf[9]) != d1:
        return False
    
    # Segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    d2 = 0 if resto < 2 else 11 - resto
    
    return int(cpf[10]) == d2


def _validate_cnpj(cnpj: str) -> bool:
    """Valida CNPJ"""
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    
    # Primeiro dígito verificador
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    resto = soma % 11
    d1 = 0 if resto < 2 else 11 - resto
    
    if int(cnpj[12]) != d1:
        return False
    
    # Segundo dígito verificador
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    resto = soma % 11
    d2 = 0 if resto < 2 else 11 - resto
    
    return int(cnpj[13]) == d2


# ==================== AUDITORIA DE SEGURANÇA ====================

async def log_security_event(
    db,
    event_type: str,
    description: str,
    user_id: str = None,
    ip_address: str = None,
    severity: str = "info",
    details: dict = None
):
    """Registra evento de segurança para auditoria"""
    import uuid
    
    event = {
        "id": str(uuid.uuid4()),
        "type": "security",
        "event_type": event_type,
        "description": description,
        "user_id": user_id,
        "ip_address": ip_address,
        "severity": severity,  # info, warning, error, critical
        "details": details or {},
        "created_at": datetime.now().isoformat()
    }
    
    try:
        await db.security_logs.insert_one(event)
    except Exception:
        pass  # Não falhar a requisição se não conseguir logar


# ==================== CONFIGURAÇÕES SEGURAS DE CORS ====================

def get_cors_origins():
    """Retorna origens permitidas baseado no ambiente"""
    env = os.environ.get("ENVIRONMENT", "development")
    
    if env == "production":
        # Em produção, especificar origens exatas
        allowed = os.environ.get("CORS_ORIGINS", "")
        if allowed:
            return [origin.strip() for origin in allowed.split(",")]
        return []
    
    # Em desenvolvimento, permitir localhost e preview
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    app_url = os.environ.get("APP_URL", "").strip().rstrip("/")
    if app_url:
        origins.append(app_url)
    # Origens extras explícitas (ex.: URL pública do preview quando difere de APP_URL)
    extras = os.environ.get("CORS_ORIGINS", "")
    for origem in extras.split(","):
        origem = origem.strip().rstrip("/")
        if origem and origem not in origins:
            origins.append(origem)
    return origins
