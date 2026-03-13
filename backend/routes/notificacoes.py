"""
Rotas de Notificações - Sistema Gestor Cred
Endpoints para gerenciar notificações de usuários e admins
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime, timedelta, timezone

from config import db
from models.notificacao import Notificacao
from models.usuario import Usuario
from services.auth import get_current_user
from services.auth_utils import get_user_context
from services.permissao_service import verificar_plano_ativo
from services.notificacao_service import (
    verificar_vencimentos_usuario,
    verificar_assinaturas_expirando,
    criar_resumo_diario_admin,
    criar_notificacao
)

router = APIRouter()


@router.get("")
async def listar_notificacoes(
    apenas_nao_lidas: bool = False,
    tipo: Optional[str] = None,
    limit: int = 50,
    current_user: Usuario = Depends(verificar_plano_ativo)
):
    """Lista notificações do usuário com filtros opcionais"""
    context_id = get_user_context(current_user)
    query = {"usuario_id": context_id}
    
    if apenas_nao_lidas:
        query["lida"] = False
    
    if tipo:
        query["tipo"] = tipo
    
    notificacoes = await db.notificacoes.find(
        query, 
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    # Converter datas para formato correto
    for n in notificacoes:
        if isinstance(n.get("created_at"), str):
            try:
                n["created_at"] = datetime.fromisoformat(n["created_at"].replace('Z', '+00:00'))
            except:
                pass
    
    return notificacoes


@router.get("/contagem")
async def contar_notificacoes(current_user: Usuario = Depends(get_current_user)):
    """Retorna contagem de notificações não lidas e por tipo"""
    context_id = get_user_context(current_user)
    
    # Total não lidas
    nao_lidas = await db.notificacoes.count_documents({
        "usuario_id": context_id,
        "lida": False
    })
    
    # Contar por tipo
    pipeline = [
        {"$match": {"usuario_id": context_id, "lida": False, "deleted": {"$ne": True}}},
        {"$group": {"_id": "$tipo", "count": {"$sum": 1}}}
    ]
    por_tipo = await db.notificacoes.aggregate(pipeline).to_list(20)
    
    tipos_count = {item["_id"]: item["count"] for item in por_tipo}
    
    return {
        "total_nao_lidas": nao_lidas,
        "por_tipo": tipos_count
    }


@router.post("/{notificacao_id}/marcar-lida")
async def marcar_notificacao_lida(
    notificacao_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Marca uma notificação como lida"""
    context_id = get_user_context(current_user)
    result = await db.notificacoes.update_one(
        {"id": notificacao_id, "usuario_id": context_id},
        {"$set": {"lida": True}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    
    return {"message": "Notificação marcada como lida"}


@router.post("/marcar-todas-lidas")
async def marcar_todas_lidas(
    tipo: Optional[str] = None,
    current_user: Usuario = Depends(get_current_user)
):
    """Marca todas as notificações como lidas (opcionalmente por tipo)"""
    context_id = get_user_context(current_user)
    query = {"usuario_id": context_id, "lida": False, "deleted": {"$ne": True}}
    
    if tipo:
        query["tipo"] = tipo
    
    result = await db.notificacoes.update_many(
        query,
        {"$set": {"lida": True}}
    )
    
    return {
        "message": f"{result.modified_count} notificações marcadas como lidas"
    }


@router.post("/verificar-vencimentos")
async def verificar_vencimentos(current_user: Usuario = Depends(get_current_user)):
    """Verifica parcelas próximas do vencimento e em atraso para o usuário logado"""
    context_id = get_user_context(current_user)
    resultado = await verificar_vencimentos_usuario(context_id)
    
    return {
        "message": f"{resultado['notificacoes_criadas']} notificações criadas",
        "notificacoes_criadas": resultado['notificacoes_criadas']
    }


@router.delete("/limpar-lidas")
async def limpar_notificacoes_lidas(current_user: Usuario = Depends(get_current_user)):
    """Remove todas as notificações já lidas"""
    context_id = get_user_context(current_user)
    result = await db.notificacoes.delete_many({
        "usuario_id": context_id,
        "lida": True
    })
    
    return {
        "message": f"{result.deleted_count} notificações removidas"
    }


@router.delete("/limpar-todas")
async def limpar_todas_notificacoes(current_user: Usuario = Depends(get_current_user)):
    """Remove TODAS as notificações do usuário (lidas e não lidas)"""
    context_id = get_user_context(current_user)
    result = await db.notificacoes.delete_many({
        "usuario_id": context_id
    })
    
    return {
        "message": f"{result.deleted_count} notificações removidas"
    }


@router.delete("/{notificacao_id}")
async def deletar_notificacao(
    notificacao_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Marca notificação como deletada (soft delete)
    Evita que seja recriada pelo job de notificações
    """
    context_id = get_user_context(current_user)
    result = await db.notificacoes.update_one(
        {"id": notificacao_id, "usuario_id": context_id},
        {"$set": {
            "deleted": True,
            "deleted_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    
    return {"message": "Notificação excluída"}


# ================== ENDPOINTS ADMIN ==================

@router.get("/admin/todas")
async def listar_todas_notificacoes_admin(
    limit: int = 100,
    tipo: Optional[str] = None,
    current_user: Usuario = Depends(get_current_user)
):
    """[ADMIN] Lista todas as notificações do sistema"""
    if current_user.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    query = {}
    if tipo:
        query["tipo"] = tipo
    
    notificacoes = await db.notificacoes.find(
        query, 
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return notificacoes


@router.post("/admin/verificar-todos")
async def verificar_vencimentos_todos_admin(current_user: Usuario = Depends(get_current_user)):
    """[ADMIN] Executa verificação de vencimentos para todos os usuários"""
    if current_user.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    from jobs.notificacoes_job import job_verificar_vencimentos_todos
    resultado = await job_verificar_vencimentos_todos()
    
    return resultado


@router.post("/admin/verificar-assinaturas")
async def verificar_assinaturas_admin(current_user: Usuario = Depends(get_current_user)):
    """[ADMIN] Verifica assinaturas expirando e cria notificações"""
    if current_user.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    resultado = await verificar_assinaturas_expirando()
    
    return {
        "message": f"{resultado['notificacoes_criadas']} notificações de assinatura criadas",
        **resultado
    }


@router.post("/admin/gerar-resumo")
async def gerar_resumo_diario(current_user: Usuario = Depends(get_current_user)):
    """[ADMIN] Gera resumo diário manualmente"""
    if current_user.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    resultado = await criar_resumo_diario_admin()
    
    return {
        "message": "Resumo diário gerado com sucesso",
        **resultado
    }


@router.post("/admin/enviar-global")
async def enviar_notificacao_global(
    titulo: str,
    mensagem: str,
    tipo: str = "sistema",
    prioridade: str = "normal",
    current_user: Usuario = Depends(get_current_user)
):
    """[ADMIN] Envia notificação para todos os usuários"""
    if current_user.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    # Buscar todos os usuários ativos
    usuarios = await db.usuarios.find({"ativo": True}).to_list(10000)
    
    notificacoes_criadas = 0
    for usuario in usuarios:
        usuario_id = usuario.get("id")
        if usuario_id:
            await criar_notificacao(
                usuario_id=usuario_id,
                tipo=tipo,
                titulo=titulo,
                mensagem=mensagem,
                prioridade=prioridade
            )
            notificacoes_criadas += 1
    
    return {
        "message": f"Notificação enviada para {notificacoes_criadas} usuários",
        "total_usuarios": notificacoes_criadas
    }


@router.get("/admin/estatisticas")
async def estatisticas_notificacoes(current_user: Usuario = Depends(get_current_user)):
    """[ADMIN] Retorna estatísticas gerais de notificações"""
    if current_user.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    # Total de notificações
    total = await db.notificacoes.count_documents({})
    
    # Não lidas
    nao_lidas = await db.notificacoes.count_documents({"lida": False})
    
    # Por tipo
    pipeline = [
        {"$group": {"_id": "$tipo", "count": {"$sum": 1}}}
    ]
    por_tipo = await db.notificacoes.aggregate(pipeline).to_list(50)
    
    # Últimas 24h
    ontem = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    ultimas_24h = await db.notificacoes.count_documents({
        "created_at": {"$gte": ontem}
    })
    
    return {
        "total": total,
        "nao_lidas": nao_lidas,
        "ultimas_24h": ultimas_24h,
        "por_tipo": {item["_id"]: item["count"] for item in por_tipo}
    }
