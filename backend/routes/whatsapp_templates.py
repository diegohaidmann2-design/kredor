"""
Rotas para gerenciar Templates de Mensagens WhatsApp
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from config import db
from models.usuario import Usuario
from models.whatsapp_template import WhatsAppTemplate, TEMPLATES_PADRAO
from services.auth import get_current_user

router = APIRouter()


@router.get("/templates")
async def listar_templates(
    tipo: Optional[str] = None,
    incluir_padrao: bool = True,
    current_user: Usuario = Depends(get_current_user)
):
    """Lista todos os templates do usuário"""
    filtro = {"usuario_id": current_user.id}
    
    if tipo:
        filtro["tipo"] = tipo
    
    templates = await db.whatsapp_templates.find(filtro).to_list(100)
    
    # Converter ObjectId para string
    for template in templates:
        if "_id" in template:
            template["_id"] = str(template["_id"])
    
    # Se incluir padrão e usuário não tem templates, criar os padrão
    if incluir_padrao and len(templates) == 0:
        await _criar_templates_padrao(current_user.id)
        templates = await db.whatsapp_templates.find(filtro).to_list(100)
        for template in templates:
            if "_id" in template:
                template["_id"] = str(template["_id"])
    
    return {
        "templates": templates,
        "total": len(templates)
    }


@router.get("/templates/{template_id}")
async def obter_template(
    template_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Obtém um template específico"""
    template = await db.whatsapp_templates.find_one({
        "id": template_id,
        "usuario_id": current_user.id
    })
    
    if not template:
        raise HTTPException(404, "Template não encontrado")
    
    if "_id" in template:
        template["_id"] = str(template["_id"])
    
    return template


@router.post("/templates")
async def criar_template(
    nome: str,
    tipo: str,
    mensagem: str,
    descricao: Optional[str] = None,
    ativo: bool = True,
    current_user: Usuario = Depends(get_current_user)
):
    """Cria um novo template"""
    template = {
        "id": str(uuid.uuid4()),
        "usuario_id": current_user.id,
        "nome": nome,
        "tipo": tipo,
        "mensagem": mensagem,
        "descricao": descricao,
        "variaveis_disponiveis": [
            "{cliente_nome}",
            "{numero_parcela}",
            "{total_parcelas}",
            "{valor}",
            "{data_vencimento}",
            "{dias}"
        ],
        "ativo": ativo,
        "padrao": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = await db.whatsapp_templates.insert_one(template)
    template["_id"] = str(result.inserted_id)
    
    return {
        "success": True,
        "message": "Template criado com sucesso",
        "template": template
    }


@router.put("/templates/{template_id}")
async def atualizar_template(
    template_id: str,
    nome: Optional[str] = None,
    tipo: Optional[str] = None,
    mensagem: Optional[str] = None,
    descricao: Optional[str] = None,
    ativo: Optional[bool] = None,
    current_user: Usuario = Depends(get_current_user)
):
    """Atualiza um template existente"""
    # Verificar se template existe e pertence ao usuário
    template = await db.whatsapp_templates.find_one({
        "id": template_id,
        "usuario_id": current_user.id
    })
    
    if not template:
        raise HTTPException(404, "Template não encontrado")
    
    # Não permitir editar templates padrão do sistema (apenas ativar/desativar)
    if template.get("padrao") and (nome or tipo or mensagem or descricao):
        raise HTTPException(400, "Não é possível editar templates padrão. Crie uma cópia para personalizar.")
    
    updates = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if nome is not None:
        updates["nome"] = nome
    if tipo is not None:
        updates["tipo"] = tipo
    if mensagem is not None:
        updates["mensagem"] = mensagem
    if descricao is not None:
        updates["descricao"] = descricao
    if ativo is not None:
        updates["ativo"] = ativo
    
    await db.whatsapp_templates.update_one(
        {"id": template_id, "usuario_id": current_user.id},
        {"$set": updates}
    )
    
    return {
        "success": True,
        "message": "Template atualizado com sucesso"
    }


@router.delete("/templates/{template_id}")
async def excluir_template(
    template_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Exclui um template"""
    # Verificar se template existe
    template = await db.whatsapp_templates.find_one({
        "id": template_id,
        "usuario_id": current_user.id
    })
    
    if not template:
        raise HTTPException(404, "Template não encontrado")
    
    # Não permitir excluir templates padrão
    if template.get("padrao"):
        raise HTTPException(400, "Não é possível excluir templates padrão")
    
    result = await db.whatsapp_templates.delete_one({
        "id": template_id,
        "usuario_id": current_user.id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(404, "Template não encontrado")
    
    return {
        "success": True,
        "message": "Template excluído com sucesso"
    }


@router.post("/templates/{template_id}/duplicar")
async def duplicar_template(
    template_id: str,
    novo_nome: Optional[str] = None,
    current_user: Usuario = Depends(get_current_user)
):
    """Duplica um template (útil para personalizar templates padrão)"""
    # Buscar template original
    template_original = await db.whatsapp_templates.find_one({
        "id": template_id,
        "usuario_id": current_user.id
    })
    
    if not template_original:
        raise HTTPException(404, "Template não encontrado")
    
    # Criar cópia
    novo_template = {
        "id": str(uuid.uuid4()),
        "usuario_id": current_user.id,
        "nome": novo_nome or f"{template_original['nome']} (Cópia)",
        "tipo": template_original["tipo"],
        "mensagem": template_original["mensagem"],
        "descricao": template_original.get("descricao"),
        "variaveis_disponiveis": template_original.get("variaveis_disponiveis", []),
        "ativo": True,
        "padrao": False,  # Cópias nunca são padrão
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    result = await db.whatsapp_templates.insert_one(novo_template)
    novo_template["_id"] = str(result.inserted_id)
    
    return {
        "success": True,
        "message": "Template duplicado com sucesso",
        "template": novo_template
    }


@router.post("/templates/preview")
async def preview_template(
    mensagem: str,
    dados_exemplo: Optional[dict] = None,
    current_user: Usuario = Depends(get_current_user)
):
    """Gera preview do template com dados de exemplo"""
    from services.whatsapp_service import formatar_template_mensagem
    
    # Dados exemplo padrão
    if not dados_exemplo:
        dados_exemplo = {
            "cliente_nome": "João Silva",
            "numero_parcela": "3",
            "total_parcelas": "12",
            "valor": "850,00",
            "data_vencimento": "15/01/2026",
            "dias": "5"
        }
    
    preview = formatar_template_mensagem(mensagem, dados_exemplo)
    
    return {
        "preview": preview,
        "dados_utilizados": dados_exemplo
    }


@router.post("/templates/restaurar-padrao")
async def restaurar_templates_padrao(current_user: Usuario = Depends(get_current_user)):
    """Restaura os templates padrão do sistema"""
    count = await _criar_templates_padrao(current_user.id, force=True)
    
    return {
        "success": True,
        "message": f"{count} templates padrão restaurados",
        "count": count
    }


# Funções auxiliares

async def _criar_templates_padrao(usuario_id: str, force: bool = False):
    """Cria templates padrão para o usuário"""
    count = 0
    
    for template_padrao in TEMPLATES_PADRAO:
        # Verificar se já existe (só se não for force)
        if not force:
            existe = await db.whatsapp_templates.find_one({
                "usuario_id": usuario_id,
                "nome": template_padrao["nome"],
                "padrao": True
            })
            if existe:
                continue
        
        template = {
            "id": str(uuid.uuid4()),
            "usuario_id": usuario_id,
            **template_padrao,
            "variaveis_disponiveis": [
                "{cliente_nome}",
                "{numero_parcela}",
                "{total_parcelas}",
                "{valor}",
                "{data_vencimento}",
                "{dias}"
            ],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.whatsapp_templates.insert_one(template)
        count += 1
    
    return count
