"""
Serviço de Proteção contra Brute Force
"""
from datetime import datetime, timezone, timedelta
from config import db
from typing import Tuple, Optional

# Configurações
MAX_TENTATIVAS = 5  # Máximo de tentativas falhas
JANELA_TEMPO = 15  # Minutos para resetar contador
BLOQUEIO_DURACAO = 30  # Minutos de bloqueio após exceder tentativas

# Proteção por IP (anti credential-stuffing / automação distribuída)
# Um mesmo IP tentando muitas contas diferentes é bloqueado, sem permitir
# que um atacante derrube a conta de uma vítima específica.
MAX_TENTATIVAS_IP = 20      # falhas de login (qualquer conta) por IP na janela
BLOQUEIO_DURACAO_IP = 30    # minutos de bloqueio do IP


def extrair_ip(request) -> Optional[str]:
    """Obtém o IP real do cliente considerando proxy (X-Forwarded-For)."""
    if request is None:
        return None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


async def verificar_bloqueio_ip(ip: Optional[str]) -> Tuple[bool, int]:
    """Verifica se o IP está bloqueado por excesso de falhas de login."""
    if not ip:
        return False, 0
    agora = datetime.now(timezone.utc)
    registro = await db.login_attempts_ip.find_one({"ip": ip})
    if not registro:
        return False, 0
    bloqueado_ate = registro.get("bloqueado_ate")
    if bloqueado_ate:
        if isinstance(bloqueado_ate, str):
            bloqueado_ate = datetime.fromisoformat(bloqueado_ate)
        if agora < bloqueado_ate:
            return True, int((bloqueado_ate - agora).total_seconds())
        await db.login_attempts_ip.update_one(
            {"ip": ip}, {"$set": {"tentativas": 0, "bloqueado_ate": None,
                                  "primeira_tentativa": agora.isoformat()}}
        )
    return False, 0


async def registrar_tentativa_falha_ip(ip: Optional[str]) -> None:
    """Conta falhas de login por IP e bloqueia o IP se exceder o limite."""
    if not ip:
        return
    agora = datetime.now(timezone.utc)
    janela_inicio = agora - timedelta(minutes=JANELA_TEMPO)
    registro = await db.login_attempts_ip.find_one({"ip": ip})
    if not registro:
        await db.login_attempts_ip.insert_one({
            "ip": ip, "tentativas": 1,
            "primeira_tentativa": agora.isoformat(),
            "ultima_tentativa": agora.isoformat(), "bloqueado_ate": None,
        })
        return
    primeira = registro.get("primeira_tentativa")
    if isinstance(primeira, str):
        primeira = datetime.fromisoformat(primeira)
    if primeira and primeira < janela_inicio:
        await db.login_attempts_ip.update_one(
            {"ip": ip}, {"$set": {"tentativas": 1,
                                  "primeira_tentativa": agora.isoformat(),
                                  "ultima_tentativa": agora.isoformat()}}
        )
        return
    tentativas = registro.get("tentativas", 0) + 1
    bloqueado_ate = None
    if tentativas >= MAX_TENTATIVAS_IP:
        bloqueado_ate = (agora + timedelta(minutes=BLOQUEIO_DURACAO_IP)).isoformat()
    await db.login_attempts_ip.update_one(
        {"ip": ip}, {"$set": {"tentativas": tentativas,
                              "ultima_tentativa": agora.isoformat(),
                              "bloqueado_ate": bloqueado_ate}}
    )


async def registrar_sucesso_ip(ip: Optional[str]) -> None:
    """Zera o contador de falhas do IP após um login bem-sucedido."""
    if not ip:
        return
    await db.login_attempts_ip.delete_one({"ip": ip})


async def verificar_bloqueio(email: str, ip: Optional[str] = None) -> Tuple[bool, int]:
    """
    Verifica se email ou IP está bloqueado por brute force
    
    Returns:
        (bloqueado: bool, segundos_restantes: int)
    """
    agora = datetime.now(timezone.utc)
    
    # Buscar tentativas por email
    registro = await db.login_attempts.find_one({"email": email})
    
    if not registro:
        return False, 0
    
    # Verificar se está bloqueado
    bloqueado_ate = registro.get("bloqueado_ate")
    if bloqueado_ate:
        if isinstance(bloqueado_ate, str):
            bloqueado_ate = datetime.fromisoformat(bloqueado_ate)
        
        if agora < bloqueado_ate:
            segundos = int((bloqueado_ate - agora).total_seconds())
            return True, segundos
        else:
            # Bloqueio expirou, limpar
            await db.login_attempts.update_one(
                {"email": email},
                {"$set": {"tentativas": 0, "bloqueado_ate": None}}
            )
            return False, 0
    
    return False, 0


async def registrar_tentativa_falha(email: str, ip: Optional[str] = None) -> None:
    """
    Registra tentativa de login falha e aplica bloqueio se necessário
    """
    agora = datetime.now(timezone.utc)
    janela_inicio = agora - timedelta(minutes=JANELA_TEMPO)
    
    # Buscar registro existente
    registro = await db.login_attempts.find_one({"email": email})
    
    if not registro:
        # Criar novo registro
        await db.login_attempts.insert_one({
            "email": email,
            "ip": ip,
            "tentativas": 1,
            "primeira_tentativa": agora.isoformat(),
            "ultima_tentativa": agora.isoformat(),
            "bloqueado_ate": None
        })
        return
    
    # Verificar se está dentro da janela de tempo
    primeira_tentativa = registro.get("primeira_tentativa")
    if isinstance(primeira_tentativa, str):
        primeira_tentativa = datetime.fromisoformat(primeira_tentativa)
    
    # Se passou da janela, resetar contador
    if primeira_tentativa < janela_inicio:
        await db.login_attempts.update_one(
            {"email": email},
            {"$set": {
                "tentativas": 1,
                "primeira_tentativa": agora.isoformat(),
                "ultima_tentativa": agora.isoformat()
            }}
        )
        return
    
    # Incrementar tentativas
    tentativas = registro.get("tentativas", 0) + 1
    
    # Aplicar bloqueio se exceder limite
    bloqueado_ate = None
    if tentativas >= MAX_TENTATIVAS:
        bloqueado_ate = (agora + timedelta(minutes=BLOQUEIO_DURACAO)).isoformat()
    
    await db.login_attempts.update_one(
        {"email": email},
        {"$set": {
            "tentativas": tentativas,
            "ultima_tentativa": agora.isoformat(),
            "bloqueado_ate": bloqueado_ate,
            "ip": ip
        }}
    )


async def registrar_sucesso(email: str) -> None:
    """
    Limpa contador de tentativas após login bem-sucedido
    """
    await db.login_attempts.delete_one({"email": email})


async def limpar_bloqueios_expirados() -> int:
    """
    Remove bloqueios expirados (executar via scheduler)
    
    Returns:
        Número de bloqueios removidos
    """
    agora = datetime.now(timezone.utc)
    
    result = await db.login_attempts.delete_many({
        "bloqueado_ate": {"$lt": agora.isoformat()}
    })
    
    return result.deleted_count
