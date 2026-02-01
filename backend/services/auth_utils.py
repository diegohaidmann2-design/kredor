from models.usuario import Usuario

def get_user_context(user: Usuario) -> str:
    """
    Retorna o ID do dono dos dados (o próprio user ou seu chefe).
    Usado para filtrar queries no banco de dados.
    """
    return user.owner_id if user.owner_id else user.id

def is_owner(user: Usuario) -> bool:
    """Verifica se o usuário é o dono da conta"""
    return user.owner_id is None
