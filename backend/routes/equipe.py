"""
Rotas para Gerenciamento de Equipe (Funcionários)
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime, timezone
import uuid

from config import db
from models.usuario import Usuario
from services.auth import get_current_user
from services.auth_utils import get_user_context, is_owner
from services.permissao_service import permissao_service
from services.email_service import enviar_email_convite
from services.auth import hash_senha # Importar hash_senha

router = APIRouter()

# --- Models ---

class ConviteEquipe(BaseModel):
    email: EmailStr
    nome: str
    cargo: str = "Colaborador"
    permissoes: List[str] = []
    senha: Optional[str] = None # Senha opcional para cadastro manual

class AceitarConvite(BaseModel):
    token: str
    senha: str
    nome: Optional[str] = None # Permitir confirmar/corrigir nome

class MembroEquipe(BaseModel):
    id: str
    nome: str
    email: str
    cargo: Optional[str]
    ativo: bool
    convite_pendente: bool
    created_at: Optional[str]

class PermissoesUpdate(BaseModel):
    permissoes: List[str]

# --- Rotas ---

@router.post("/convidar")
async def convidar_membro(
    dados: ConviteEquipe,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Convida um novo membro para a equipe.
    O usuário convidado receberá um email para definir senha.
    """
    # Apenas donos podem convidar (por enquanto)
    # Futuro: Gerentes com permissão de 'gerir_equipe'
    if not is_owner(current_user):
         raise HTTPException(status_code=403, detail="Apenas o dono da conta pode convidar membros.")

    # Verificar limite de usuários do plano (se aplicável - enterprise é illimitado geralmente)
    # Por simplificação, vamos assumir que apenas planos Enterprise ou Multi-usuários podem
    pode, msg = await permissao_service.verificar_recurso(current_user, "multi_usuarios")
    if not pode:
        raise HTTPException(status_code=403, detail=msg)
        
    # Verificar se email já existe no sistema
    existing = await db.usuarios.find_one({"email": dados.email})
    if existing:
        raise HTTPException(status_code=400, detail="Este email já está cadastrado no sistema.")
    
    # Criar usuário "convidado"
    # Se senha foi fornecida (cadastro manual), definimos já
    hashed_password = None
    if dados.senha:
        hashed_password = hash_senha(dados.senha)
        verification_token = None # Não precisa de token se já tem senha
    else:
        # Fluxo de convite por email
        verification_token = str(uuid.uuid4())
    
    novo_membro = {
        "id": str(uuid.uuid4()),
        "nome": dados.nome,
        "email": dados.email,
        "senha": hashed_password, # Salvar senha hashada
        "perfil": "usuario",
        "plano": "equipe", # Plano dummy, usa limites do dono
        "plano_ativo": True,
        "ativo": True,
        "email_verificado": True if dados.senha else False, # Se manual, já considera verificado
        "convite_pendente": False if dados.senha else True, # Se manual, não é pendente
        "owner_id": current_user.id, # VINCULO COM O DONO
        "cargo": dados.cargo,
        "permissoes": dados.permissoes,
        "email_verification_token": verification_token,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.usuarios.insert_one(novo_membro)
    
    # Enviar Email de Convite APENAS se NÃO for cadastro manual
    if not dados.senha:
        try:
            await enviar_email_convite(dados.email, current_user.nome, verification_token)
        except Exception as e:
            print(f"Erro ao enviar convite: {e}")
            # Não falhamos a request se o email falhar, mas logamos
            
    return {"message": "Membro adicionado com sucesso." if dados.senha else f"Convite enviado para {dados.email}", "id": novo_membro["id"]}


@router.post("/aceitar-convite")
async def aceitar_convite(dados: AceitarConvite):
    """
    Finaliza o cadastro do membro convidado.
    Define a senha e ativa a conta.
    """
    user = await db.usuarios.find_one({"email_verification_token": dados.token, "convite_pendente": True})
    
    if not user:
        raise HTTPException(status_code=400, detail="Convite inválido ou expirado.")
        
    update_data = {
        "senha": hash_senha(dados.senha),
        "email_verificado": True,
        "convite_pendente": False,
        "email_verification_token": None,
        "ativo": True
    }
    
    if dados.nome:
        update_data["nome"] = dados.nome
        
    await db.usuarios.update_one(
        {"_id": user["_id"]},
        {"$set": update_data}
    )
    
    return {"message": "Cadastro concluído com sucesso! Você já pode fazer login."}


@router.get("")
async def listar_equipe(
    current_user: Usuario = Depends(get_current_user)
):
    """Lista todos os membros da equipe do usuário atual (ou do dono)."""
    
    context_id = get_user_context(current_user)
    
    # Se eu sou funcionário, não vejo a equipe? Ou vejo?
    # Regra: Apenas DONO vê equipe por padrão.
    if not is_owner(current_user):
        raise HTTPException(status_code=403, detail="Acesso restrito ao dono da conta.")
        
    membros = await db.usuarios.find(
        {"owner_id": context_id},
        {"_id": 0}
    ).to_list(100)
    
    # Obter limites para exibir no frontend
    limites = await permissao_service.obter_limites(current_user)
    
    # Definir limite numérico baseado na permissão booleana
    # Se tem permissão multi_usuarios, assumimos ilimitado (ou um número alto por enquanto)
    # Se não tem, limite é 0 (apenas o dono)
    limite_total = 999 if limites.multi_usuarios else 0
    
    return {
        "membros": membros,
        "limites": {
            "usado": len(membros),
            "total": limite_total
        }
    }


@router.delete("/{membro_id}")
async def remover_membro(
    membro_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Remove (desativa) um membro da equipe."""
    if not is_owner(current_user):
        raise HTTPException(status_code=403, detail="Acesso apenas para o dono.")
        
    # Verificar se o membro pertence a este dono
    membro = await db.usuarios.find_one({"id": membro_id, "owner_id": current_user.id})
    if not membro:
        raise HTTPException(status_code=404, detail="Membro não encontrado.")
        
    # Hard delete ou Soft delete? Vamos de soft delete (desativar)
    # Se convite pendente, pode deletar hard
    if membro.get("convite_pendente"):
        await db.usuarios.delete_one({"id": membro_id})
        return {"message": "Convite cancelado e usuário removido."}
    
    await db.usuarios.update_one(
        {"id": membro_id},
        {"$set": {"ativo": False}}
    )
    
    return {"message": "Membro desativado com sucesso."}

@router.put("/{membro_id}/permissoes")
async def atualizar_permissoes(
    membro_id: str,
    dados: PermissoesUpdate,
    current_user: Usuario = Depends(get_current_user)
):
    """Atualiza as permissões de um membro."""
    if not is_owner(current_user):
        raise HTTPException(status_code=403, detail="Acesso apenas para o dono.")

    result = await db.usuarios.update_one(
        {"id": membro_id, "owner_id": current_user.id},
        {"$set": {"permissoes": dados.permissoes}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Membro não encontrado.")
        
    return {"message": "Permissões atualizadas."}
