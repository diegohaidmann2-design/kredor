"""
Fonte única de autorização.

Dois eixos ortogonais de privilégio:
- Operador da plataforma (`perfil == PERFIL_OPERADOR`): painel cross-tenant.
- Dono da conta (`is_owner`): todo cliente pagante é dono da própria conta.

Nunca use `is_owner` para guardar o painel administrativo — ele é True para
toda a base de clientes.
"""
from fastapi import Depends, HTTPException
from models.usuario import Usuario
from services.auth import get_current_user
from services.auth_utils import is_operador_plataforma, is_owner


def garantir_operador_plataforma(user: Usuario) -> None:
    if not is_operador_plataforma(user):
        raise HTTPException(status_code=403, detail="Acesso restrito ao operador da plataforma.")


async def require_operador_plataforma(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """Exige operador da plataforma (painel cross-tenant)."""
    garantir_operador_plataforma(current_user)
    return current_user


async def require_dono_da_conta(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """Exige dono da conta (tenant), em oposição a funcionário convidado."""
    if not is_owner(current_user):
        raise HTTPException(status_code=403, detail="Acesso restrito ao dono da conta.")
    return current_user
