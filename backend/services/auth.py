"""
Serviço de autenticação com Refresh Tokens
"""
import jwt
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Tuple, TYPE_CHECKING
from passlib.context import CryptContext

from config import db, JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRATION_HOURS

# Configuração de senha usando passlib (mesma config do seeder)
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

if TYPE_CHECKING:
    from models.usuario import Usuario

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)

# Configurações de tokens
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # Token de acesso expira em 8 horas
REFRESH_TOKEN_EXPIRE_DAYS = 30        # Refresh token expira em 30 dias


def hash_senha(senha: str) -> str:
    """Gera hash da senha"""
    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash: str) -> bool:
    """Verifica se a senha corresponde ao hash"""
    return pwd_context.verify(senha, hash)


def criar_tokens(usuario_id: str) -> Tuple[str, str]:
    """
    Cria access token e refresh token
    
    Returns:
        Tuple[str, str]: (access_token, refresh_token)
    """
    jti = str(uuid.uuid4())  # JWT ID único
    current_time = datetime.now(timezone.utc)
    
    # Access Token (curta duração)
    access_payload = {
        "sub": usuario_id,
        "jti": jti,
        "type": "access",
        "exp": current_time + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": current_time
    }
    access_token = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    # Refresh Token (longa duração)
    refresh_payload = {
        "sub": usuario_id,
        "jti": jti,
        "type": "refresh",
        "exp": current_time + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": current_time
    }
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    return access_token, refresh_token


def criar_token(usuario_id: str) -> str:
    """
    Cria token JWT (compatibilidade com código legado)
    
    DEPRECATED: Use criar_tokens() para nova implementação
    """
    # Para compatibilidade, criar apenas access token
    access_token, _ = criar_tokens(usuario_id)
    return access_token


async def revogar_token(jti: str):
    """
    Revoga um token adicionando-o à lista negra
    
    Em produção, usar Redis para melhor performance
    """
    await db.tokens_revogados.insert_one({
        "jti": jti,
        "revogado_em": datetime.now(timezone.utc).isoformat(),
        "expira_em": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    })


async def verificar_token_revogado(jti: str) -> bool:
    """Verifica se token foi revogado"""
    token = await db.tokens_revogados.find_one({"jti": jti})
    return token is not None


async def refresh_access_token(refresh_token: str) -> str:
    """
    Gera novo access token a partir do refresh token
    
    Args:
        refresh_token: Refresh token válido
    
    Returns:
        str: Novo access token
    
    Raises:
        HTTPException: Se refresh token inválido ou expirado
    """
    try:
        payload = jwt.decode(refresh_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Verificar tipo do token
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Token inválido")
        
        # Verificar se token foi revogado
        jti = payload.get("jti")
        if jti and await verificar_token_revogado(jti):
            raise HTTPException(status_code=401, detail="Token revogado")
        
        usuario_id = payload.get("sub")
        if not usuario_id:
            raise HTTPException(status_code=401, detail="Token inválido")
        
        # Verificar se usuário ainda existe e está ativo
        usuario = await db.usuarios.find_one({"id": usuario_id})
        if not usuario or not usuario.get("ativo", False):
            raise HTTPException(status_code=401, detail="Usuário inativo ou não encontrado")
        
        # Gerar novo access token (mantém o mesmo JTI)
        new_jti = payload.get("jti", str(uuid.uuid4()))
        access_payload = {
            "sub": usuario_id,
            "jti": new_jti,
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            "iat": datetime.now(timezone.utc)
        }
        return jwt.encode(access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Refresh token inválido")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Obtém usuário atual a partir do token"""
    # Import aqui para evitar circular import
    from models.usuario import Usuario
    
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Verificar tipo do token (deve ser access)
        token_type = payload.get("type")
        if token_type and token_type != "access":
            raise HTTPException(status_code=401, detail="Tipo de token inválido")
        
        # Verificar se token foi revogado
        jti = payload.get("jti")
        if jti and await verificar_token_revogado(jti):
            raise HTTPException(status_code=401, detail="Token revogado")
        
        usuario_id = payload.get("sub")
        
        usuario = await db.usuarios.find_one({"id": usuario_id}, {"_id": 0})
        if not usuario:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
        
        if not usuario.get("ativo", False):
            raise HTTPException(status_code=401, detail="Usuário inativo")
        
        usuario["created_at"] = datetime.fromisoformat(usuario["created_at"])
        return Usuario(**usuario)
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")


async def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security_optional)):
    """Obtém usuário atual de forma opcional (não gera erro se não houver token)"""
    if not credentials:
        return None
    
    # Import aqui para evitar circular import
    from models.usuario import Usuario
    
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Verificar tipo do token (deve ser access)
        token_type = payload.get("type")
        if token_type and token_type != "access":
            return None
        
        # Verificar se token foi revogado
        jti = payload.get("jti")
        if jti and await verificar_token_revogado(jti):
            return None
        
        usuario_id = payload.get("sub")
        
        usuario = await db.usuarios.find_one({"id": usuario_id}, {"_id": 0})
        if not usuario or not usuario.get("ativo", False):
            return None
        
        usuario["created_at"] = datetime.fromisoformat(usuario["created_at"])
        return Usuario(**usuario)
    
    except:
        return None


async def require_admin(current_user = Depends(get_current_user)):
    """Verifica se o usuário é administrador ou superadmin"""
    if current_user.perfil not in ["admin", "superadmin"]:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return current_user


def get_user_filter(current_user) -> dict:
    """Retorna filtro para isolamento de dados por usuário"""
    return {"usuario_id": current_user.id}
