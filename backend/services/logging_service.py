"""
Sistema de Logging Estruturado - Gestor Cred
Implementa logging profissional para monitoramento e debugging
"""
import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from functools import wraps
import traceback
import os

# Configuração do nível de log baseado no ambiente
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")


class JSONFormatter(logging.Formatter):
    """Formatter que gera logs em formato JSON estruturado"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "environment": ENVIRONMENT
        }
        
        # Adicionar informações de exceção se existir
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info) if record.exc_info[0] else None
            }
        
        # Adicionar campos extras se existirem
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data
        
        return json.dumps(log_entry, ensure_ascii=False, default=str)


class ColoredFormatter(logging.Formatter):
    """Formatter com cores para desenvolvimento"""
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        
        # Formato: [TIMESTAMP] LEVEL - MODULE - MESSAGE
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        formatted = f"{color}[{timestamp}] {record.levelname:8s}{self.RESET} - {record.module}.{record.funcName} - {record.getMessage()}"
        
        # Adicionar dados extras se existirem
        if hasattr(record, "extra_data") and record.extra_data:
            formatted += f"\n    📋 Data: {json.dumps(record.extra_data, default=str)}"
        
        # Adicionar exceção se existir
        if record.exc_info:
            formatted += f"\n    ❌ Exception: {record.exc_info[1]}"
        
        return formatted


def setup_logging():
    """Configura o sistema de logging global"""
    
    # Remover handlers existentes
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Handler para stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, LOG_LEVEL))
    
    # Usar formatter colorido em dev, JSON em produção
    if ENVIRONMENT == "production":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(ColoredFormatter())
    
    # Configurar root logger
    root_logger.setLevel(getattr(logging, LOG_LEVEL))
    root_logger.addHandler(console_handler)
    
    # Reduzir verbosidade de bibliotecas externas
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    return root_logger


class StructuredLogger:
    """Logger estruturado com suporte a campos extras"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _log(self, level: int, message: str, **kwargs):
        """Log com dados estruturados"""
        extra_data = kwargs.pop("data", None)
        exc_info = kwargs.pop("exc_info", None)
        
        record = self.logger.makeRecord(
            self.logger.name,
            level,
            "",
            0,
            message,
            (),
            exc_info
        )
        
        if extra_data:
            record.extra_data = extra_data
        
        self.logger.handle(record)
    
    def debug(self, message: str, **kwargs):
        """Log de debug"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log informativo"""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log de aviso"""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log de erro"""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log crítico"""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log de exceção com traceback"""
        kwargs["exc_info"] = sys.exc_info()
        self._log(logging.ERROR, message, **kwargs)
    
    # Métodos de conveniência para contextos específicos
    
    def api_request(self, method: str, path: str, user_id: str = None, **kwargs):
        """Log de requisição API"""
        self.info(
            f"API Request: {method} {path}",
            data={
                "type": "api_request",
                "method": method,
                "path": path,
                "user_id": user_id,
                **kwargs
            }
        )
    
    def api_response(self, method: str, path: str, status_code: int, duration_ms: float = None, **kwargs):
        """Log de resposta API"""
        level = logging.INFO if status_code < 400 else logging.WARNING if status_code < 500 else logging.ERROR
        self._log(
            level,
            f"API Response: {method} {path} -> {status_code}",
            data={
                "type": "api_response",
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                **kwargs
            }
        )
    
    def db_query(self, collection: str, operation: str, duration_ms: float = None, **kwargs):
        """Log de operação no banco de dados"""
        self.debug(
            f"DB {operation} on {collection}",
            data={
                "type": "db_query",
                "collection": collection,
                "operation": operation,
                "duration_ms": duration_ms,
                **kwargs
            }
        )
    
    def auth_event(self, event: str, user_id: str = None, email: str = None, success: bool = True, **kwargs):
        """Log de evento de autenticação"""
        level = logging.INFO if success else logging.WARNING
        self._log(
            level,
            f"Auth Event: {event}",
            data={
                "type": "auth_event",
                "event": event,
                "user_id": user_id,
                "email": email,
                "success": success,
                **kwargs
            }
        )
    
    def business_event(self, event: str, entity: str = None, entity_id: str = None, **kwargs):
        """Log de evento de negócio"""
        self.info(
            f"Business Event: {event}",
            data={
                "type": "business_event",
                "event": event,
                "entity": entity,
                "entity_id": entity_id,
                **kwargs
            }
        )
    
    def security_event(self, event: str, severity: str = "medium", **kwargs):
        """Log de evento de segurança"""
        level = logging.WARNING if severity in ["low", "medium"] else logging.ERROR
        self._log(
            level,
            f"Security Event: {event}",
            data={
                "type": "security_event",
                "event": event,
                "severity": severity,
                **kwargs
            }
        )
    
    def performance(self, operation: str, duration_ms: float, threshold_ms: float = 1000, **kwargs):
        """Log de performance (avisa se acima do threshold)"""
        level = logging.INFO if duration_ms < threshold_ms else logging.WARNING
        self._log(
            level,
            f"Performance: {operation} took {duration_ms:.2f}ms",
            data={
                "type": "performance",
                "operation": operation,
                "duration_ms": duration_ms,
                "threshold_ms": threshold_ms,
                "above_threshold": duration_ms >= threshold_ms,
                **kwargs
            }
        )


# Decorator para logging de funções
def log_function(logger: StructuredLogger = None):
    """Decorator para logging automático de funções"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            _logger = logger or StructuredLogger(func.__module__)
            start_time = datetime.now()
            
            try:
                result = await func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds() * 1000
                _logger.debug(
                    f"Function {func.__name__} completed",
                    data={"duration_ms": duration}
                )
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                _logger.exception(
                    f"Function {func.__name__} failed",
                    data={"duration_ms": duration, "error": str(e)}
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            _logger = logger or StructuredLogger(func.__module__)
            start_time = datetime.now()
            
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds() * 1000
                _logger.debug(
                    f"Function {func.__name__} completed",
                    data={"duration_ms": duration}
                )
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                _logger.exception(
                    f"Function {func.__name__} failed",
                    data={"duration_ms": duration, "error": str(e)}
                )
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# Instância global para uso geral
def get_logger(name: str = "jurofacil") -> StructuredLogger:
    """Obtém um logger estruturado"""
    return StructuredLogger(name)


# Inicializar logging ao importar
setup_logging()

# Logger padrão da aplicação
app_logger = get_logger("jurofacil")
