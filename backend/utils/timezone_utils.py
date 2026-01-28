"""
Utilitários para manipulação de timezone - São Paulo/Brasil
"""
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

# Timezone de São Paulo
TIMEZONE_SP = ZoneInfo("America/Sao_Paulo")


def now_sp() -> datetime:
    """
    Retorna o datetime atual no fuso de São Paulo
    
    Returns:
        datetime: Data/hora atual em São Paulo
    """
    return datetime.now(TIMEZONE_SP)


def now_utc() -> datetime:
    """
    Retorna o datetime atual em UTC
    
    Returns:
        datetime: Data/hora atual em UTC
    """
    return datetime.now(timezone.utc)


def to_sp(dt: datetime) -> datetime:
    """
    Converte datetime para o fuso de São Paulo
    
    Args:
        dt: datetime a ser convertido (com ou sem timezone)
        
    Returns:
        datetime: datetime convertido para São Paulo
    """
    if dt is None:
        return None
        
    # Se não tem timezone, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.astimezone(TIMEZONE_SP)


def to_utc(dt: datetime) -> datetime:
    """
    Converte datetime para UTC
    
    Args:
        dt: datetime a ser convertido
        
    Returns:
        datetime: datetime convertido para UTC
    """
    if dt is None:
        return None
        
    # Se não tem timezone, assume São Paulo
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TIMEZONE_SP)
    
    return dt.astimezone(timezone.utc)


def format_datetime_br(dt: datetime, include_time: bool = True) -> str:
    """
    Formata datetime no padrão brasileiro
    
    Args:
        dt: datetime a ser formatado
        include_time: incluir hora (padrão: True)
        
    Returns:
        str: Data formatada (ex: "21/01/2025" ou "21/01/2025 15:30")
    """
    if dt is None:
        return "-"
    
    dt_sp = to_sp(dt)
    
    if include_time:
        return dt_sp.strftime("%d/%m/%Y %H:%M")
    return dt_sp.strftime("%d/%m/%Y")


def parse_datetime_br(date_str: str, has_time: bool = False) -> datetime:
    """
    Parse string de data no formato brasileiro para datetime
    
    Args:
        date_str: String com data (ex: "21/01/2025" ou "21/01/2025 15:30")
        has_time: True se a string inclui hora
        
    Returns:
        datetime: datetime em UTC
    """
    if has_time:
        dt = datetime.strptime(date_str, "%d/%m/%Y %H:%M")
    else:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
    
    # Assume que a data está no fuso de São Paulo
    dt = dt.replace(tzinfo=TIMEZONE_SP)
    
    # Retorna em UTC para salvar no banco
    return to_utc(dt)


def inicio_dia_sp(dt: Optional[datetime] = None) -> datetime:
    """
    Retorna o início do dia (00:00:00) em São Paulo
    
    Args:
        dt: datetime de referência (padrão: hoje)
        
    Returns:
        datetime: início do dia em UTC
    """
    if dt is None:
        dt = now_sp()
    else:
        dt = to_sp(dt)
    
    inicio = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return to_utc(inicio)


def fim_dia_sp(dt: Optional[datetime] = None) -> datetime:
    """
    Retorna o fim do dia (23:59:59) em São Paulo
    
    Args:
        dt: datetime de referência (padrão: hoje)
        
    Returns:
        datetime: fim do dia em UTC
    """
    if dt is None:
        dt = now_sp()
    else:
        dt = to_sp(dt)
    
    fim = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    return to_utc(fim)


def get_offset_info() -> dict:
    """
    Retorna informações sobre o offset atual de São Paulo
    
    Returns:
        dict: Informações do timezone
    """
    agora = now_sp()
    offset = agora.utcoffset()
    
    return {
        "timezone": "America/Sao_Paulo",
        "offset_hours": offset.total_seconds() / 3600,
        "offset_str": agora.strftime("%z"),
        "is_dst": agora.dst() != timedelta(0),  # Horário de verão
        "datetime_local": agora.isoformat(),
        "datetime_utc": now_utc().isoformat()
    }


# Para compatibilidade com código existente
def datetime_sp_to_iso(dt: datetime) -> str:
    """Converte datetime para ISO string mantendo timezone SP"""
    return to_sp(dt).isoformat()


def datetime_utc_to_iso(dt: datetime) -> str:
    """Converte datetime para ISO string em UTC"""
    return to_utc(dt).isoformat()
