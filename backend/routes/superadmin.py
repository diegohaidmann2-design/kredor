"""
Rotas do Super Admin - Gerenciamento Completo do Sistema
Inclui: Usuários, Assinaturas, Tenants
"""
from services.logging_service import get_logger
logger = get_logger("gestorcred.superadmin")

from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Literal
from pydantic import BaseModel, EmailStr

PerfilValido = Literal["admin", "usuario"]
from passlib.context import CryptContext
import uuid
import re

from config import db
from models.usuario import Usuario
from services.auth import validar_forca_senha
from services.autorizacao import require_operador_plataforma
import smtplib
from email.message import EmailMessage
from email.header import Header
from email.utils import formataddr, formatdate, make_msgid
import ssl
import traceback
import time

router = APIRouter()
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


# ==================== MODELS ====================

class UsuarioCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    perfil: PerfilValido = "usuario"
    plano: str = "trial"
    ativo: bool = True

class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    senha: Optional[str] = None
    perfil: Optional[PerfilValido] = None
    plano: Optional[str] = None
    ativo: Optional[bool] = None
    plano_ativo: Optional[bool] = None

class AssinaturaCreate(BaseModel):
    usuario_id: str
    plano: str
    dias_validade: int = 30
    valor: Optional[float] = None
    observacoes: Optional[str] = None

class AssinaturaUpdate(BaseModel):
    plano: Optional[str] = None
    status: Optional[str] = None
    data_expiracao: Optional[str] = None  # Nova data de expiração
    dias_extras: Optional[int] = None      # Dias para adicionar
    valor: Optional[float] = None
    observacoes: Optional[str] = None


# ==================== VERIFICAÇÃO ADMIN ====================
# Autorização centralizada em services.autorizacao.require_operador_plataforma


# ==================== DASHBOARD ====================

@router.get("/dashboard")
async def super_admin_dashboard(current_user: Usuario = Depends(require_operador_plataforma)):
    """Dashboard do super admin com estatísticas globais"""
    
    # Estatísticas de usuários
    total_usuarios = await db.usuarios.count_documents({})
    usuarios_ativos = await db.usuarios.count_documents({"ativo": True})
    usuarios_admin = await db.usuarios.count_documents({"perfil": "admin"})
    
    # Estatísticas por plano
    usuarios_trial = await db.usuarios.count_documents({"plano": "trial"})
    usuarios_basico = await db.usuarios.count_documents({"plano": "basico"})
    usuarios_profissional = await db.usuarios.count_documents({"plano": "profissional"})
    usuarios_enterprise = await db.usuarios.count_documents({"plano": "enterprise"})
    
    # Receita mensal estimada
    precos_planos = {
        "basico": 49.0,
        "profissional": 99.0,
        "enterprise": 199.0
    }
    receita_mensal = (
        usuarios_basico * precos_planos["basico"] +
        usuarios_profissional * precos_planos["profissional"] +
        usuarios_enterprise * precos_planos["enterprise"]
    )
    
    # Assinaturas
    total_assinaturas = await db.assinaturas_admin.count_documents({})
    assinaturas_ativas = await db.assinaturas_admin.count_documents({"status": "ativa"})
    
    # Distribuição por plano
    distribuicao_planos = [
        {"plano": "trial", "quantidade": usuarios_trial},
        {"plano": "basico", "quantidade": usuarios_basico},
        {"plano": "profissional", "quantidade": usuarios_profissional},
        {"plano": "enterprise", "quantidade": usuarios_enterprise}
    ]
    
    # Usuários recentes
    usuarios_recentes = await db.usuarios.find(
        {}, {"_id": 0, "senha_hash": 0}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    # Alertas
    alertas = []
    
    # Trials expirando
    limite_trial = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    trials_expirando = await db.usuarios.count_documents({
        "plano": "trial",
        "data_fim_trial": {"$lte": limite_trial}
    })
    if trials_expirando > 0:
        alertas.append({
            "tipo": "warning",
            "mensagem": f"{trials_expirando} trial(s) expirando nos próximos 3 dias"
        })
    
    # Usuários inativos
    inativos = await db.usuarios.count_documents({"ativo": False})
    if inativos > 0:
        alertas.append({
            "tipo": "info",
            "mensagem": f"{inativos} usuário(s) inativo(s)"
        })
    
    return {
        "stats": {
            "total_usuarios": total_usuarios,
            "usuarios_ativos": usuarios_ativos,
            "usuarios_admin": usuarios_admin,
            "usuarios_trial": usuarios_trial,
            "usuarios_pagantes": usuarios_basico + usuarios_profissional + usuarios_enterprise,
            "receita_mensal": round(receita_mensal, 2),
            "total_assinaturas": total_assinaturas,
            "assinaturas_ativas": assinaturas_ativas,
            "distribuicao_planos": distribuicao_planos
        },
        "usuarios_recentes": usuarios_recentes,
        "alertas": alertas
    }


# ==================== USUÁRIOS ====================

@router.get("/usuarios")
async def listar_usuarios(
    perfil: Optional[str] = None,
    plano: Optional[str] = None,
    ativo: Optional[bool] = None,
    busca: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """Lista todos os usuários com filtros"""
    query = {}
    
    if perfil:
        query["perfil"] = perfil
    if plano:
        query["plano"] = plano
    if ativo is not None:
        query["ativo"] = ativo
    if busca:
        query["$or"] = [
            {"nome": {"$regex": re.escape(busca), "$options": "i"}},
            {"email": {"$regex": re.escape(busca), "$options": "i"}}
        ]
    
    total = await db.usuarios.count_documents(query)
    usuarios = await db.usuarios.find(
        query, {"_id": 0, "senha_hash": 0}
    ).skip(skip).limit(limit).sort("created_at", -1).to_list(limit)
    
    return {
        "total": total,
        "usuarios": usuarios
    }


@router.post("/usuarios")
async def criar_usuario(
    usuario: UsuarioCreate,
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """Cria um novo usuário"""
    # Verificar se email já existe
    existente = await db.usuarios.find_one({"email": usuario.email})
    if existente:
        raise HTTPException(status_code=400, detail="Email já está em uso")
    
    agora = datetime.now(timezone.utc)
    
    # Calcular fim do trial
    dias_trial = 7 if usuario.plano == "trial" else 365
    data_fim_trial = (agora + timedelta(days=dias_trial)).isoformat()
    
    novo_usuario = {
        "id": str(uuid.uuid4()),
        "nome": usuario.nome,
        "email": usuario.email,
        "senha_hash": pwd_context.hash(usuario.senha),
        "perfil": usuario.perfil,
        "plano": usuario.plano,
        "plano_ativo": True,
        "ativo": usuario.ativo,
        "email_verificado": True,  # Admin cria já verificado
        "created_at": agora.isoformat(),
        "data_inicio_trial": agora.isoformat(),
        "data_fim_trial": data_fim_trial
    }
    
    await db.usuarios.insert_one(novo_usuario)
    
    # Remover senha antes de retornar
    del novo_usuario["_id"]
    del novo_usuario["senha_hash"]
    
    return novo_usuario


@router.get("/usuarios/{usuario_id}")
async def obter_usuario(
    usuario_id: str,
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """Obtém detalhes de um usuário"""
    usuario = await db.usuarios.find_one({"id": usuario_id}, {"_id": 0, "senha_hash": 0})
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Estatísticas do usuário
    stats = {
        "clientes": await db.clientes.count_documents({"usuario_id": usuario_id}),
        "emprestimos": await db.emprestimos.count_documents({"usuario_id": usuario_id}),
        "pagamentos": await db.pagamentos.count_documents({"usuario_id": usuario_id}),
        "emprestimos_ativos": await db.emprestimos.count_documents({"usuario_id": usuario_id, "status": "ativo"})
    }
    
    # Histórico de assinaturas
    assinaturas = await db.assinaturas_admin.find(
        {"usuario_id": usuario_id}, {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    return {**usuario, "stats": stats, "assinaturas": assinaturas}


@router.put("/usuarios/{usuario_id}")
async def atualizar_usuario(
    usuario_id: str,
    update: UsuarioUpdate,
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """Atualiza um usuário"""
    usuario = await db.usuarios.find_one({"id": usuario_id})
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    update_data = {k: v for k, v in update.model_dump().items() if v is not None}
    
    # Se está atualizando senha, fazer hash
    if "senha" in update_data:
        update_data["senha_hash"] = pwd_context.hash(update_data.pop("senha"))
    
    # Se está atualizando email, verificar duplicidade
    if "email" in update_data:
        existente = await db.usuarios.find_one({
            "email": update_data["email"],
            "id": {"$ne": usuario_id}
        })
        if existente:
            raise HTTPException(status_code=400, detail="Email já está em uso por outro usuário")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.usuarios.update_one(
        {"id": usuario_id},
        {"$set": update_data}
    )
    
    return {"message": "Usuário atualizado com sucesso"}



@router.post("/usuarios/{usuario_id}/desativar-2fa")
async def desativar_2fa_usuario(
    usuario_id: str,
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """
    Desativa o 2FA de um usuário (útil quando o usuário perde acesso ao email)
    Apenas admins podem executar esta ação
    """
    # Verificar se usuário existe
    usuario = await db.usuarios.find_one({"id": usuario_id})
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Verificar se 2FA está ativo
    if not usuario.get("two_factor_enabled", False):
        raise HTTPException(status_code=400, detail="2FA já está desativado para este usuário")
    
    # Desativar 2FA
    await db.usuarios.update_one(
        {"id": usuario_id},
        {"$set": {
            "two_factor_enabled": False,
            "two_factor_activated_at": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Invalidar todos os códigos 2FA pendentes deste usuário
    await db.two_factor_codes.update_many(
        {"usuario_id": usuario_id, "usado": False},
        {"$set": {"usado": True}}
    )
    
    # Registrar na auditoria
    await db.auditoria.insert_one({
        "id": str(uuid.uuid4()),
        "usuario_id": current_user.id,
        "acao": "desativar_2fa_usuario",
        "detalhes": {
            "usuario_afetado": usuario_id,
            "usuario_afetado_nome": usuario.get("nome"),
            "usuario_afetado_email": usuario.get("email")
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": "2FA desativado com sucesso",
        "usuario_id": usuario_id,
        "usuario_nome": usuario.get("nome"),
        "usuario_email": usuario.get("email")
    }


@router.delete("/usuarios/{usuario_id}")
async def deletar_usuario(
    usuario_id: str,
    permanent: bool = False,
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """Deleta um usuário (e suas assinaturas)"""
    usuario = await db.usuarios.find_one({"id": usuario_id})
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Não permitir deletar a si mesmo
    if usuario_id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode deletar sua própria conta")
    
    if permanent:
        # Deletar permanentemente (e dados relacionados)
        await db.usuarios.delete_one({"id": usuario_id})
        await db.clientes.delete_many({"usuario_id": usuario_id})
        await db.emprestimos.delete_many({"usuario_id": usuario_id})
        await db.parcelas.delete_many({"usuario_id": usuario_id})
        await db.pagamentos.delete_many({"usuario_id": usuario_id})
        await db.notificacoes.delete_many({"usuario_id": usuario_id})
        
        # 🆕 DELETAR ASSINATURAS do usuário (ambas as collections)
        assinaturas_admin_deletadas = await db.assinaturas_admin.delete_many({"usuario_id": usuario_id})
        assinaturas_checkout_deletadas = await db.assinaturas.delete_many({"usuario_id": usuario_id})
        
        total_assinaturas = assinaturas_admin_deletadas.deleted_count + assinaturas_checkout_deletadas.deleted_count
        
        return {
            "message": "Usuário e dados relacionados deletados permanentemente",
            "assinaturas_removidas": total_assinaturas
        }
    else:
        # Soft delete - desativar usuário E cancelar assinaturas ativas
        await db.usuarios.update_one(
            {"id": usuario_id},
            {"$set": {
                "ativo": False, 
                "plano_ativo": False,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Cancelar assinaturas ativas (não deletar, apenas marcar como cancelada)
        await db.assinaturas_admin.update_many(
            {"usuario_id": usuario_id, "status": "ativa"},
            {"$set": {"status": "cancelada", "data_cancelamento": datetime.now(timezone.utc).isoformat()}}
        )
        await db.assinaturas.update_many(
            {"usuario_id": usuario_id, "status": "ativa"},
            {"$set": {"status": "cancelada", "data_cancelamento": datetime.now(timezone.utc).isoformat()}}
        )
        
        return {"message": "Usuário desativado e assinaturas canceladas com sucesso"}


@router.post("/usuarios/{usuario_id}/ativar")
async def ativar_usuario(
    usuario_id: str,
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """Ativa um usuário"""
    await db.usuarios.update_one(
        {"id": usuario_id},
        {"$set": {"ativo": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Usuário ativado com sucesso"}


@router.post("/usuarios/{usuario_id}/resetar-senha")
async def resetar_senha_usuario(
    usuario_id: str,
    nova_senha: str = Query(...),
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """Reseta a senha de um usuário"""
    usuario = await db.usuarios.find_one({"id": usuario_id})
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Mesma régua do cadastro e do convite: uma senha definida pelo painel não pode ser mais
    # fraca do que a que o próprio usuário conseguiria escolher.
    validar_forca_senha(nova_senha, usuario.get("email"), campo="nova senha")
    
    await db.usuarios.update_one(
        {"id": usuario_id},
        {"$set": {
            "senha_hash": pwd_context.hash(nova_senha),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Senha resetada com sucesso"}


@router.post("/usuarios/{usuario_id}/verificar-email")
async def verificar_email_manualmente(
    usuario_id: str,
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """Verifica o email de um usuário manualmente (ação do admin)"""
    usuario = await db.usuarios.find_one({"id": usuario_id})
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Se já está verificado, informar
    if usuario.get("email_verificado", False):
        return {"message": "Email já estava verificado", "ja_verificado": True}
    
    await db.usuarios.update_one(
        {"id": usuario_id},
        {"$set": {
            "email_verificado": True,
            "email_verification_token": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Email verificado com sucesso", "ja_verificado": False}


# ==================== ASSINATURAS ====================

@router.get("/assinaturas")
async def listar_assinaturas(
    status: Optional[str] = None,
    plano: Optional[str] = None,
    busca: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """Lista todas as assinaturas do sistema (assinaturas_admin + assinaturas)"""
    query = {}
    
    if status:
        query["status"] = status
    if plano:
        # Buscar tanto em "plano" quanto em "plano_id"
        query["$or"] = [{"plano": plano}, {"plano_id": plano}]
    
    # Se tem busca, precisamos fazer um lookup no usuário
    if busca:
        # Primeiro buscar IDs dos usuários que correspondem
        usuarios_match = await db.usuarios.find(
            {"$or": [
                {"nome": {"$regex": re.escape(busca), "$options": "i"}},
                {"email": {"$regex": re.escape(busca), "$options": "i"}}
            ]},
            {"id": 1}
        ).to_list(1000)
        usuario_ids = [u["id"] for u in usuarios_match]
        if "status" in query or ("$or" in query and plano):
            # Já tem outro filtro, adicionar usuario_id no AND
            existing_query = query.copy()
            query = {"$and": [existing_query, {"usuario_id": {"$in": usuario_ids}}]}
        else:
            query["usuario_id"] = {"$in": usuario_ids}
    
    # Buscar de AMBAS as collections
    assinaturas_admin = await db.assinaturas_admin.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    
    assinaturas_checkout = await db.assinaturas.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    
    # Combinar e marcar origem
    for ass in assinaturas_admin:
        ass["origem"] = "admin"
        ass["plano_id"] = ass.get("plano", ass.get("plano_id"))  # Normalizar
        ass["plano"] = ass.get("plano_id") # Garantir campo plano para o frontend
        ass["data_fim"] = ass.get("data_fim", ass.get("data_expiracao")) # Normalizar data
    
    for ass in assinaturas_checkout:
        ass["origem"] = "checkout"
        ass["plano_id"] = ass.get("plano_id", ass.get("plano"))  # Normalizar
        ass["plano"] = ass.get("plano_id") # Garantir campo plano para o frontend
        ass["data_fim"] = ass.get("data_expiracao", ass.get("data_fim")) # Normalizar data
        ass["id"] = ass.get("session_id", ass.get("id")) # Garantir ID consistente
    
    # Unificar
    todas_assinaturas = assinaturas_admin + assinaturas_checkout
    
    # Ordenar por data (mais recente primeiro)
    todas_assinaturas.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # Aplicar paginação
    total = len(todas_assinaturas)
    assinaturas_paginadas = todas_assinaturas[skip:skip+limit]
    
    # Enriquecer com dados do usuário
    for assinatura in assinaturas_paginadas:
        usuario = await db.usuarios.find_one(
            {"id": assinatura["usuario_id"]},
            {"_id": 0, "nome": 1, "email": 1}
        )
        assinatura["usuario"] = usuario if usuario else {"nome": "Não encontrado", "email": "-"}
    
    return {
        "total": total,
        "assinaturas": assinaturas_paginadas
    }


@router.post("/assinaturas")
async def criar_assinatura(
    assinatura: AssinaturaCreate,
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """Cria uma nova assinatura manualmente"""
    # Verificar se usuário existe
    usuario = await db.usuarios.find_one({"id": assinatura.usuario_id})
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    agora = datetime.now(timezone.utc)
    data_fim = (agora + timedelta(days=assinatura.dias_validade)).isoformat()
    
    # Preços dos planos
    precos = {
        "trial": 0,
        "basico": 49.0,
        "profissional": 99.0,
        "enterprise": 199.0
    }
    
    nova_assinatura = {
        "id": str(uuid.uuid4()),
        "usuario_id": assinatura.usuario_id,
        "plano": assinatura.plano,
        "status": "ativa",
        "valor": assinatura.valor if assinatura.valor else precos.get(assinatura.plano, 0),
        "data_inicio": agora.isoformat(),
        "data_fim": data_fim,
        "dias_validade": assinatura.dias_validade,
        "observacoes": assinatura.observacoes,
        "criado_por": current_user.email,
        "created_at": agora.isoformat()
    }
    
    await db.assinaturas_admin.insert_one(nova_assinatura)
    
    # Atualizar plano do usuário
    await db.usuarios.update_one(
        {"id": assinatura.usuario_id},
        {"$set": {
            "plano": assinatura.plano,
            "plano_ativo": True,
            "data_fim_trial": data_fim,
            "updated_at": agora.isoformat()
        }}
    )
    
    del nova_assinatura["_id"]
    return nova_assinatura


@router.get("/assinaturas/{assinatura_id}")
async def obter_assinatura(
    assinatura_id: str,
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """Obtém detalhes de uma assinatura"""
    assinatura = await db.assinaturas_admin.find_one({"id": assinatura_id}, {"_id": 0})
    if not assinatura:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")
    
    # Dados do usuário
    usuario = await db.usuarios.find_one(
        {"id": assinatura["usuario_id"]},
        {"_id": 0, "senha_hash": 0}
    )
    
    return {**assinatura, "usuario": usuario}


@router.put("/assinaturas/{assinatura_id}")
async def atualizar_assinatura(
    assinatura_id: str,
    update: AssinaturaUpdate,
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """
    Atualiza uma assinatura com suporte a:
    - Edição de data de expiração
    - Adição de dias extras
    - Alteração de plano e status
    - Logs de alterações
    """
    assinatura = await db.assinaturas_admin.find_one({"id": assinatura_id})
    if not assinatura:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")
    
    agora = datetime.now(timezone.utc)
    alteracoes = []
    update_data = {}
    
    # Processar data de expiração
    if update.data_expiracao:
        try:
            nova_data = datetime.fromisoformat(update.data_expiracao.replace('Z', '+00:00'))
            data_antiga = assinatura.get("data_expiracao", assinatura.get("data_fim", "N/A"))
            
            update_data["data_expiracao"] = nova_data.isoformat()
            update_data["data_fim"] = nova_data.isoformat()  # Compatibilidade
            
            alteracoes.append({
                "campo": "data_expiracao",
                "valor_anterior": data_antiga,
                "valor_novo": nova_data.isoformat(),
                "descricao": f"Data de expiração alterada para {nova_data.strftime('%d/%m/%Y')}"
            })
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Data inválida: {str(e)}")
    
    # Processar dias extras
    if update.dias_extras and update.dias_extras > 0:
        # Pegar data atual de expiração
        data_atual_str = assinatura.get("data_expiracao", assinatura.get("data_fim"))
        if data_atual_str:
            try:
                data_atual = datetime.fromisoformat(data_atual_str.replace('Z', '+00:00'))
            except Exception:
                data_atual = agora
        else:
            data_atual = agora
        
        # Se a data atual já passou, começar de hoje
        if data_atual < agora:
            data_atual = agora
        
        nova_data = data_atual + timedelta(days=update.dias_extras)
        
        update_data["data_expiracao"] = nova_data.isoformat()
        update_data["data_fim"] = nova_data.isoformat()
        
        alteracoes.append({
            "campo": "dias_extras",
            "valor_anterior": data_atual.isoformat(),
            "valor_novo": nova_data.isoformat(),
            "descricao": f"Adicionados {update.dias_extras} dias. Nova expiração: {nova_data.strftime('%d/%m/%Y')}"
        })
    
    # Processar plano
    if update.plano and update.plano != assinatura.get("plano"):
        alteracoes.append({
            "campo": "plano",
            "valor_anterior": assinatura.get("plano"),
            "valor_novo": update.plano,
            "descricao": f"Plano alterado de {assinatura.get('plano')} para {update.plano}"
        })
        update_data["plano"] = update.plano
    
    # Processar status
    if update.status and update.status != assinatura.get("status"):
        alteracoes.append({
            "campo": "status",
            "valor_anterior": assinatura.get("status"),
            "valor_novo": update.status,
            "descricao": f"Status alterado de {assinatura.get('status')} para {update.status}"
        })
        update_data["status"] = update.status
        
        # Se reativando, garantir plano ativo
        if update.status == "ativa":
            update_data["data_reativacao"] = agora.isoformat()
    
    # Processar valor
    if update.valor is not None and update.valor != assinatura.get("valor"):
        alteracoes.append({
            "campo": "valor",
            "valor_anterior": assinatura.get("valor"),
            "valor_novo": update.valor,
            "descricao": f"Valor alterado de R$ {assinatura.get('valor', 0):.2f} para R$ {update.valor:.2f}"
        })
        update_data["valor"] = update.valor
    
    # Processar observações
    if update.observacoes is not None:
        update_data["observacoes"] = update.observacoes
        if update.observacoes != assinatura.get("observacoes", ""):
            alteracoes.append({
                "campo": "observacoes",
                "valor_anterior": assinatura.get("observacoes", ""),
                "valor_novo": update.observacoes,
                "descricao": "Observações atualizadas"
            })
    
    if not update_data:
        return {"message": "Nenhuma alteração realizada", "alteracoes": []}
    
    # Adicionar metadados
    update_data["updated_at"] = agora.isoformat()
    update_data["updated_by"] = current_user.id
    
    # Registrar log de alteração
    log_alteracao = {
        "id": str(uuid.uuid4()),
        "assinatura_id": assinatura_id,
        "usuario_id": assinatura.get("usuario_id"),
        "admin_id": current_user.id,
        "admin_nome": current_user.nome,
        "admin_email": current_user.email,
        "data_alteracao": agora.isoformat(),
        "alteracoes": alteracoes,
        "tipo": "edicao_assinatura"
    }
    
    # Salvar log
    await db.logs_assinaturas.insert_one(log_alteracao)
    
    # Atualizar assinatura
    await db.assinaturas_admin.update_one(
        {"id": assinatura_id},
        {"$set": update_data}
    )
    
    # Atualizar usuário correspondente
    user_update = {"updated_at": agora.isoformat()}
    
    if "plano" in update_data:
        user_update["plano"] = update_data["plano"]
    
    if "status" in update_data:
        user_update["plano_ativo"] = update_data["status"] == "ativa"
    
    if "data_expiracao" in update_data:
        user_update["data_expiracao_plano"] = update_data["data_expiracao"]
        user_update["data_fim_trial"] = update_data["data_expiracao"]
    
    await db.usuarios.update_one(
        {"id": assinatura["usuario_id"]},
        {"$set": user_update}
    )
    
    return {
        "message": "Assinatura atualizada com sucesso",
        "alteracoes": alteracoes,
        "log_id": log_alteracao["id"]
    }


@router.get("/assinaturas/{assinatura_id}/logs")
async def listar_logs_assinatura(
    assinatura_id: str,
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """Lista o histórico de alterações de uma assinatura"""
    logs = await db.logs_assinaturas.find(
        {"assinatura_id": assinatura_id},
        {"_id": 0}
    ).sort("data_alteracao", -1).to_list(100)
    
    return {"logs": logs}


@router.post("/assinaturas/{assinatura_id}/cancelar")
async def cancelar_assinatura(
    assinatura_id: str,
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """Cancela uma assinatura (Admin ou Checkout)"""
    # Tentar encontrar em ambas as collections
    assinatura = await db.assinaturas_admin.find_one({"id": assinatura_id})
    collection_origem = "assinaturas_admin"
    
    if not assinatura:
        # Tentar na collection de checkout
        assinatura = await db.assinaturas.find_one({"session_id": assinatura_id})
        if assinatura:
            collection_origem = "assinaturas"
        else:
            # Tentar buscar por qualquer campo id
            assinatura = await db.assinaturas.find_one({"$or": [
                {"id": assinatura_id},
                {"session_id": assinatura_id}
            ]})
            if assinatura:
                collection_origem = "assinaturas"
    
    if not assinatura:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")
    
    usuario_id = assinatura.get("usuario_id")
    agora = datetime.now(timezone.utc).isoformat()
    
    if collection_origem == "assinaturas_admin":
        await db.assinaturas_admin.update_one(
            {"id": assinatura_id},
            {"$set": {"status": "cancelada", "data_cancelamento": agora, "updated_at": agora}}
        )
    else:
        # Atualizar no checkout
        await db.assinaturas.update_one(
            {"$or": [{"id": assinatura_id}, {"session_id": assinatura_id}]},
            {"$set": {"status": "cancelada", "data_cancelamento": agora, "updated_at": agora}}
        )
    
    # Rebaixar usuário para trial se não tiver outras assinaturas ativas
    # (Opcional: podemos ser mais agressivos e rebaixar sempre que o admin cancela)
    await db.usuarios.update_one(
        {"id": usuario_id},
        {"$set": {
            "plano": "trial",
            "plano_ativo": False,
            "updated_at": agora
        }}
    )
    
    return {"message": "Assinatura cancelada com sucesso", "origem": collection_origem}


@router.post("/assinaturas/{assinatura_id}/renovar")
async def renovar_assinatura(
    assinatura_id: str,
    dias: int = 30,
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """Renova uma assinatura"""
    assinatura = await db.assinaturas_admin.find_one({"id": assinatura_id})
    if not assinatura:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")
    
    agora = datetime.now(timezone.utc)
    
    # Calcular nova data fim
    data_fim_atual = datetime.fromisoformat(assinatura.get("data_fim", agora.isoformat()).replace("Z", "+00:00"))
    if data_fim_atual < agora:
        nova_data_fim = agora + timedelta(days=dias)
    else:
        nova_data_fim = data_fim_atual + timedelta(days=dias)
    
    await db.assinaturas_admin.update_one(
        {"id": assinatura_id},
        {"$set": {
            "status": "ativa",
            "data_fim": nova_data_fim.isoformat(),
            "updated_at": agora.isoformat()
        }}
    )
    
    # Atualizar usuário
    await db.usuarios.update_one(
        {"id": assinatura["usuario_id"]},
        {"$set": {
            "plano_ativo": True,
            "data_fim_trial": nova_data_fim.isoformat(),
            "updated_at": agora.isoformat()
        }}
    )
    
    return {"message": f"Assinatura renovada por {dias} dias", "nova_data_fim": nova_data_fim.isoformat()}


@router.delete("/assinaturas/{assinatura_id}")
async def deletar_assinatura(
    assinatura_id: str,
    manter_usuario: bool = True,
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """
    Deleta uma assinatura específica (sem deletar o usuário)
    
    Args:
        assinatura_id: ID da assinatura a ser deletada
        manter_usuario: Se True (padrão), mantém o usuário e apenas remove a assinatura
                       Se False, deleta o usuário também (use com cuidado!)
    """
    # Tentar encontrar em ambas as collections
    assinatura = await db.assinaturas_admin.find_one({"id": assinatura_id})
    collection_origem = "assinaturas_admin"
    
    if not assinatura:
        # Tentar na collection de checkout
        assinatura = await db.assinaturas.find_one({"session_id": assinatura_id})
        if assinatura:
            collection_origem = "assinaturas"
            assinatura_id = assinatura.get("session_id")  # Use session_id como ID
        else:
            # Tentar buscar por qualquer campo id
            assinatura = await db.assinaturas.find_one({"$or": [
                {"id": assinatura_id},
                {"session_id": assinatura_id}
            ]})
            if assinatura:
                collection_origem = "assinaturas"
    
    if not assinatura:
        raise HTTPException(status_code=404, detail="Assinatura não encontrada")
    
    usuario_id = assinatura.get("usuario_id")
    plano_deletado = assinatura.get("plano") or assinatura.get("plano_id")
    
    # Deletar assinatura
    if collection_origem == "assinaturas_admin":
        resultado = await db.assinaturas_admin.delete_one({"id": assinatura_id})
    else:
        # Usar $or para cobrir diferentes formatos de ID
        resultado = await db.assinaturas.delete_one({"$or": [
            {"id": assinatura_id},
            {"session_id": assinatura_id}
        ]})
    
    if resultado.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Erro ao deletar assinatura")
    
    if manter_usuario:
        # Verificar se usuário tem outras assinaturas ativas
        outras_admin = await db.assinaturas_admin.count_documents({
            "usuario_id": usuario_id,
            "status": "ativa"
        })
        outras_checkout = await db.assinaturas.count_documents({
            "usuario_id": usuario_id,
            "status": "ativa"
        })
        
        total_ativas = outras_admin + outras_checkout
        
        if total_ativas == 0:
            # Não tem mais assinaturas ativas - rebaixar para trial
            await db.usuarios.update_one(
                {"id": usuario_id},
                {"$set": {
                    "plano": "trial",
                    "plano_ativo": False,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            mensagem_usuario = "Usuário rebaixado para plano trial (sem assinaturas ativas)"
        else:
            mensagem_usuario = f"Usuário mantém {total_ativas} assinatura(s) ativa(s)"
        
        return {
            "message": "Assinatura deletada com sucesso",
            "plano_deletado": plano_deletado,
            "usuario_status": mensagem_usuario,
            "assinaturas_ativas_restantes": total_ativas
        }
    else:
        # Deletar usuário também (use com MUITO cuidado!)
        usuario = await db.usuarios.find_one({"id": usuario_id})
        if usuario:
            # Deletar tudo do usuário
            await db.usuarios.delete_one({"id": usuario_id})
            await db.clientes.delete_many({"usuario_id": usuario_id})
            await db.emprestimos.delete_many({"usuario_id": usuario_id})
            await db.parcelas.delete_many({"usuario_id": usuario_id})
            await db.pagamentos.delete_many({"usuario_id": usuario_id})
            await db.notificacoes.delete_many({"usuario_id": usuario_id})
            
            # Deletar TODAS as outras assinaturas do usuário
            await db.assinaturas_admin.delete_many({"usuario_id": usuario_id})
            await db.assinaturas.delete_many({"usuario_id": usuario_id})
            
            return {
                "message": "Assinatura e usuário deletados permanentemente",
                "usuario_deletado": usuario.get("email")
            }
        
        return {"message": "Assinatura deletada (usuário não encontrado)"}


# ==================== ESTATÍSTICAS ====================

@router.get("/estatisticas/receita")
async def estatisticas_receita(
    meses: int = 6,
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """Retorna estatísticas de receita"""
    precos = {"basico": 49.0, "profissional": 99.0, "enterprise": 199.0}
    
    resultado = []
    agora = datetime.now(timezone.utc)
    
    for i in range(meses):
        data = agora - timedelta(days=30*i)
        mes_inicio = data.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if data.month == 12:
            mes_fim = mes_inicio.replace(year=data.year+1, month=1)
        else:
            mes_fim = mes_inicio.replace(month=data.month+1)
        
        # Contar assinaturas ativas no mês
        assinaturas = await db.assinaturas_admin.find({
            "created_at": {"$gte": mes_inicio.isoformat(), "$lt": mes_fim.isoformat()},
            "status": {"$in": ["ativa", "cancelada"]}
        }).to_list(1000)
        
        receita = sum(a.get("valor", 0) for a in assinaturas)
        
        resultado.append({
            "mes": mes_inicio.strftime("%b/%Y"),
            "receita": receita,
            "assinaturas": len(assinaturas)
        })
    
    return {"dados": list(reversed(resultado))}


@router.get("/estatisticas/usuarios")
async def estatisticas_usuarios(
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """Retorna estatísticas de usuários"""
    
    # Por plano
    por_plano = await db.usuarios.aggregate([
        {"$group": {"_id": "$plano", "count": {"$sum": 1}}}
    ]).to_list(10)
    
    # Por perfil
    por_perfil = await db.usuarios.aggregate([
        {"$group": {"_id": "$perfil", "count": {"$sum": 1}}}
    ]).to_list(10)
    
    # Ativos vs Inativos
    ativos = await db.usuarios.count_documents({"ativo": True})
    inativos = await db.usuarios.count_documents({"ativo": False})
    
    return {
        "por_plano": {p["_id"]: p["count"] for p in por_plano},
        "por_perfil": {p["_id"]: p["count"] for p in por_perfil},
        "ativos": ativos,
        "inativos": inativos
    }


# ==================== CONFIGURAÇÕES DE EMAIL ====================

class EmailConfigUpdate(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    smtp_from_name: Optional[str] = None
    smtp_use_tls: Optional[bool] = True
    smtp_provider: Optional[str] = None  # gmail, hostinger, custom


@router.get("/configuracoes/email")
async def obter_config_email(
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """Obtém as configurações de email SMTP"""
    config = await db.configuracoes_sistema.find_one({"tipo": "email"})
    
    if not config:
        # Retornar valores padrão
        return {
            "smtp_host": "",
            "smtp_port": 587,
            "smtp_user": "",
            "smtp_password": "",
            "smtp_from_email": "",
            "smtp_from_name": "Kredor",
            "smtp_use_tls": True,
            "smtp_provider": "gmail"
        }
    
    # Remover campos internos
    config.pop("_id", None)
    config.pop("tipo", None)
    
    # Mascarar senha se existir
    if config.get("smtp_password"):
        config["smtp_password_set"] = True
        config["smtp_password"] = ""  # Não retornar a senha real
    else:
        config["smtp_password_set"] = False
    
    return config


@router.put("/configuracoes/email")
async def atualizar_config_email(
    config: EmailConfigUpdate,
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """Atualiza as configurações de email SMTP"""
    
    # Buscar config atual
    config_atual = await db.configuracoes_sistema.find_one({"tipo": "email"})
    
    update_data = config.model_dump(exclude_unset=True)
    
    # Se a senha veio vazia e já existe uma, manter a atual
    if not update_data.get("smtp_password") and config_atual and config_atual.get("smtp_password"):
        update_data.pop("smtp_password", None)
    
    update_data["tipo"] = "email"
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["updated_by"] = current_user.id
    
    await db.configuracoes_sistema.update_one(
        {"tipo": "email"},
        {"$set": update_data},
        upsert=True
    )
    
    return {"message": "Configurações de email atualizadas com sucesso"}


@router.post("/configuracoes/email/testar")
async def testar_config_email(
    email_destino: str,
    current_user: Usuario = Depends(require_operador_plataforma)
):
    """Envia um email de teste para verificar as configurações SMTP"""
    
    logs = []
    def log(msg):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_msg = f"[{timestamp}] {msg}"
        logs.append(log_msg)
        logger.info(log_msg)
    
    log("=" * 60)
    log("📧 INICIANDO TESTE DE EMAIL (MODO ROBUSTO)")
    log("=" * 60)
    
    # Buscar configurações
    log("🔍 Buscando configurações de email no banco...")
    config = await db.configuracoes_sistema.find_one({"tipo": "email"})
    
    if not config:
        log("❌ ERRO: Configurações de email não encontradas no banco!")
        raise HTTPException(status_code=400, detail="Configurações de email não definidas")
    
    log(f"✅ Configurações encontradas!")
    
    smtp_host = config.get("smtp_host")
    smtp_port = config.get("smtp_port", 587)
    smtp_user = config.get("smtp_user")
    smtp_password = config.get("smtp_password")
    smtp_from_email = config.get("smtp_from_email", smtp_user)
    smtp_from_name = config.get("smtp_from_name", "Kredor")
    smtp_use_tls = config.get("smtp_use_tls", True)
    
    log(f"📋 Configurações SMTP:")
    log(f"   Host: {smtp_host}")
    log(f"   Porta: {smtp_port}")
    log(f"   Usuário: {smtp_user}")
    log(f"   Senha: {'*' * len(smtp_password) if smtp_password else 'NÃO DEFINIDA'}")
    log(f"   Email remetente: {smtp_from_email}")
    log(f"   Nome remetente: {smtp_from_name}")
    log(f"   TLS/STARTTLS: {smtp_use_tls}")
    log(f"   Email destino: {email_destino}")
    
    # Auto-Discovery de Porta (Similar ao PHPMailer)
    if smtp_port == 465:
        protocolo = "SMTPS (SSL Implícito)"
        use_ssl = True
        use_starttls = False
    elif smtp_port == 587:
        protocolo = "SMTP + STARTTLS"
        use_ssl = False
        use_starttls = True
    else:
        protocolo = "SMTP Padrão (pode usar STARTTLS se disponível)"
        use_ssl = False
        use_starttls = smtp_use_tls

    log(f"   Protocolo detectado: {protocolo}")

    if not all([smtp_host, smtp_user, smtp_password]):
        missing = []
        if not smtp_host: missing.append("host")
        if not smtp_user: missing.append("usuário")
        if not smtp_password: missing.append("senha")
        log(f"❌ ERRO: Configurações SMTP incompletas! Faltando: {', '.join(missing)}")
        raise HTTPException(status_code=400, detail=f"Configurações SMTP incompletas. Faltando: {', '.join(missing)}")
    
    try:
        # Criar mensagem usando EmailMessage (Moderno e Robusto)
        log("📝 Criando mensagem de email (MIME Moderno)...")
        msg = EmailMessage()
        
        # 1. Encoding Robusto (EmailMessage lida com UTF-8 automaticamente)
        final_from_email = smtp_from_email if smtp_from_email else smtp_user
        
        # Formatar endereço "Nome <email>"
        # Com EmailMessage, podemos passar strings normais e ele cuida do encoding
        msg['From'] = f"{smtp_from_name} <{final_from_email}>"
        msg['To'] = email_destino
        msg['Subject'] = f'Teste de Configuração - {smtp_from_name}'
        msg['Reply-To'] = final_from_email
        
        # 2. Headers de Rastreabilidade RFC-Compliant
        # Tentar extrair domínio base de forma segura
        domain = 'kredor.com.br'
        if smtp_host and '.' in smtp_host:
            parts = smtp_host.split('.')
            if len(parts) >= 2:
                domain = f"{parts[-2]}.{parts[-1]}"
        
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid(domain=domain)
        msg['X-Mailer'] = 'Kredor Mailer (Python/3.10)'
        msg['X-Priority'] = '3'
        msg['MIME-Version'] = '1.0'
        
        # 3. Conteúdo Multipart (Texto + HTML)
        corpo_texto = f"""Prezado(a),

Este email foi enviado para verificar as configurações de email do sistema {smtp_from_name}.

Se você recebeu este email, as configurações estão funcionando corretamente.

Detalhes técnicos:
- Servidor: {smtp_host}
- Porta: {smtp_port}
- Remetente: {final_from_email}
- Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

Este é um email automático de teste. Por favor, não responda.

Atenciosamente,
Equipe {smtp_from_name}
"""
        
        corpo_html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h2 style="color: #2c3e50; margin-top: 0; border-bottom: 2px solid #3498db; padding-bottom: 10px;">Verificação de Email</h2>
        
        <p>Prezado(a),</p>
        
        <p>Este email foi enviado para verificar as configurações de email do sistema <strong>{smtp_from_name}</strong>.</p>
        
        <div style="background-color: #e8f6f3; padding: 15px; border-radius: 4px; margin: 20px 0; border-left: 4px solid #2ecc71;">
            <p style="margin: 0; color: #27ae60; font-weight: bold;">✅ Sucesso! O recebimento deste email confirma que o envio está operante.</p>
        </div>

        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin: 20px 0; font-size: 13px; border: 1px solid #e9ecef;">
            <p style="margin: 5px 0; color: #6c757d; text-transform: uppercase; font-size: 11px; font-weight: bold;">Detalhes Técnicos</p>
            <p style="margin: 5px 0;"><strong>Servidor:</strong> {smtp_host}</p>
            <p style="margin: 5px 0;"><strong>Porta:</strong> {smtp_port}</p>
            <p style="margin: 5px 0;"><strong>Remetente:</strong> {final_from_email}</p>
            <p style="margin: 5px 0;"><strong>Data:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        </div>
        
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        
        <p style="color: #999; font-size: 12px; text-align: center;">
            Este é um email automático de teste enviado pelo sistema Kredor.<br>
            Por favor, não responda a este email.
        </p>
    </div>
</body>
</html>
"""
        
        msg.set_content(corpo_texto)
        msg.add_alternative(corpo_html, subtype='html')
        
        log("✅ Mensagem criada com sucesso!")
        
        # Conectar e enviar
        max_retries = 2
        last_error = None
        smtp_response = None
        
        for attempt in range(max_retries):
            try:
                log(f"🔄 Tentativa {attempt + 1} de {max_retries}...")
                
                server = None
                try:
                    if use_ssl:
                        # SMTPS (Porta 465)
                        log(f"🔐 Conectando via SSL Implícito em {smtp_host}:{smtp_port}...")
                        context = ssl.create_default_context()
                        server = smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=30)
                    else:
                        # SMTP (Porta 587 ou 25)
                        log(f"� Conectando em {smtp_host}:{smtp_port}...")
                        server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
                        
                        if use_starttls:
                            log("� Iniciando STARTTLS...")
                            server.ehlo()
                            if server.has_extn("STARTTLS"):
                                context = ssl.create_default_context()
                                server.starttls(context=context)
                                server.ehlo() # Re-identify após TLS
                                log("   STARTTLS estabelecido com sucesso.")
                            else:
                                log("⚠️ ALERTA: Servidor não suporta STARTTLS, mas foi solicitado. Continuando sem criptografia (risco).")

                    # Autenticação
                    log(f"🔑 Autenticando como {smtp_user}...")
                    server.login(smtp_user, smtp_password)
                    log(f"   Autenticação OK")
                    
                    # Envio
                    log(f"📤 Enviando mensagem...")
                    failed = server.send_message(msg)
                    
                    if failed:
                        log(f"⚠️ Falha ao entregar para alguns destinatários: {failed}")
                    else:
                        log(f"✅ Mensagem aceita pelo servidor SMTP!")
                    
                    smtp_response = "Mensagem aceita"
                    break # Sucesso, sair do loop de retry

                finally:
                    if server:
                        try:
                            server.quit()
                        except Exception:
                            pass # Ignorar erros ao fechar conexão
                        
            except (smtplib.SMTPServerDisconnected, TimeoutError, ConnectionResetError, OSError) as e:
                last_error = e
                log(f"⚠️ Erro de Conexão na tentativa {attempt + 1}: {type(e).__name__}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    log(f"❌ FALHA FATAL: Não foi possível conectar após {max_retries} tentativas.")
                    raise HTTPException(status_code=500, detail=f"Erro de conexão SMTP: {str(e)}")
            
            except smtplib.SMTPAuthenticationError as e:
                log(f"❌ ERRO DE AUTENTICAÇÃO: Usuário ou senha inválidos.")
                raise HTTPException(status_code=400, detail=f"Erro de autenticação: {e.smtp_error.decode('utf-8', errors='ignore')}")
                
            except smtplib.SMTPException as e:
                log(f"❌ ERRO SMTP: {e}")
                raise HTTPException(status_code=400, detail=f"Erro SMTP: {str(e)}")

        log("=" * 60)
        log("📧 PROCESSO FINALIZADO")
        log("=" * 60)
        
        return {
            "success": True,
            "message": f"Email de teste enviado com sucesso para {email_destino}",
            "details": {
                "host": smtp_host,
                "port": smtp_port,
                "protocol": protocolo,
                "from": final_from_email,
                "to": email_destino
            },
            "logs": logs
        }
        
    except Exception as e:
        log(f"❌ ERRO GERAL NÃO TRATADO: {type(e).__name__}: {e}")
        log(f"   Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Erro interno ao enviar email: {str(e)}")
