from models.usuario import Usuario

# Privilégio de plataforma (acesso cross-tenant ao painel administrativo).
# NÃO confundir com "dono da conta" (is_owner), que é todo cliente pagante.
PERFIL_OPERADOR = "admin"

def get_user_context(user: Usuario) -> str:
    """
    Retorna o ID do dono dos dados (o próprio user ou seu chefe).
    Usado para filtrar queries no banco de dados.
    """
    return user.owner_id if user.owner_id else user.id

def is_owner(user: Usuario) -> bool:
    """Verifica se o usuário é o dono da conta (tenant), não um funcionário convidado."""
    return user.owner_id is None

def is_operador_plataforma(user: Usuario) -> bool:
    """Operador da plataforma: acesso cross-tenant. Todo cliente pagante é dono
    da conta (is_owner), mas NÃO é operador da plataforma."""
    return user.perfil == PERFIL_OPERADOR
