"""
Módulo de Segurança - Gestor Cred
Implementa: Rate Limiting, Headers de Segurança, Validação
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio
import hashlib
import os

# ==================== RATE LIMITING ====================

class RateLimiter:
    """
    Rate Limiter em memória
    Para produção, usar Redis para distribuição entre instâncias
    """
    def __init__(self):
        self.requests = defaultdict(list)
        self.blocked_ips = {}
        
        # Configurações
        self.window_size = 60  # 1 minuto
        self.max_requests = 200  # 200 req/min para rotas normais
        self.max_auth_requests = 50  # 50 tentativas de login/min
        self.block_duration = 60  # 1 minuto de bloqueio
        
        # Limpar dados antigos periodicamente
        # A tarefa de limpeza deve ser iniciada separadamente (no evento startup)
        # asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self):
        """Limpa dados antigos a cada minuto"""
        while True:
            await asyncio.sleep(60)
            self._cleanup()
    
    def _cleanup(self):
        """Remove registros expirados"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_size)
        
        # Limpar requests antigos
        for ip in list(self.requests.keys()):
            self.requests[ip] = [t for t in self.requests[ip] if t > cutoff]
            if not self.requests[ip]:
                del self.requests[ip]
        
        # Limpar bloqueios expirados
        for ip in list(self.blocked_ips.keys()):
            if self.blocked_ips[ip] < now:
                del self.blocked_ips[ip]
    
    def _get_client_ip(self, request: Request) -> str:
        """Obtém IP real do cliente (considerando proxies)"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _get_ip_hash(self, ip: str) -> str:
        """Hash do IP para privacidade em logs"""
        return hashlib.sha256(ip.encode()).hexdigest()[:16]
    
    def is_blocked(self, request: Request) -> bool:
        """Verifica se IP está bloqueado"""
        ip = self._get_client_ip(request)
        if ip in self.blocked_ips:
            if self.blocked_ips[ip] > datetime.now():
                return True
            del self.blocked_ips[ip]
        return False
    
    def check_rate_limit(self, request: Request, is_auth_route: bool = False) -> bool:
        """
        Verifica rate limit
        Retorna True se permitido, False se excedeu limite
        """
        ip = self._get_client_ip(request)
        now = datetime.now()
        
        # Verificar bloqueio
        if self.is_blocked(request):
            return False
        
        # Limpar requests antigos deste IP
        cutoff = now - timedelta(seconds=self.window_size)
        self.requests[ip] = [t for t in self.requests[ip] if t > cutoff]
        
        # Verificar limite
        max_req = self.max_auth_requests if is_auth_route else self.max_requests
        
        if len(self.requests[ip]) >= max_req:
            # Bloquear IP se exceder muito
            if len(self.requests[ip]) >= max_req * 2:
                self.blocked_ips[ip] = now + timedelta(seconds=self.block_duration)
            return False
        
        # Registrar request
        self.requests[ip].append(now)
        return True
    
    def get_retry_after(self, request: Request) -> int:
        """Retorna segundos até poder fazer nova requisição"""
        ip = self._get_client_ip(request)
        
        if ip in self.blocked_ips:
            return int((self.blocked_ips[ip] - datetime.now()).total_seconds())
        
        if self.requests[ip]:
            oldest = min(self.requests[ip])
            return int((oldest + timedelta(seconds=self.window_size) - datetime.now()).total_seconds())
        
        return self.window_size


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
        if not rate_limiter.check_rate_limit(request, is_auth_route):
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
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://gestorcred-build.preview.emergentagent.com"
    ]
