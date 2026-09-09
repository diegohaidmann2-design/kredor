"""
Serviço de Soft Delete - Kredor
Implementa exclusão lógica para auditoria, recuperação e conformidade com LGPD
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from config import db


class SoftDeleteService:
    """
    Serviço para implementar soft delete em todas as coleções.
    Em vez de remover registros permanentemente, marca-os como deletados.
    """
    
    @staticmethod
    async def soft_delete(
        collection_name: str,
        document_id: str,
        usuario_id: str,
        motivo: Optional[str] = None,
        deleted_by: Optional[str] = None
    ) -> bool:
        """
        Marca um documento como deletado (soft delete)
        
        Args:
            collection_name: Nome da coleção no MongoDB
            document_id: ID do documento a ser deletado
            usuario_id: ID do usuário dono do documento (para isolamento)
            motivo: Motivo da exclusão (opcional)
            deleted_by: Email/ID de quem deletou (opcional)
        
        Returns:
            bool: True se o documento foi marcado como deletado
        """
        collection = db[collection_name]
        
        # Verificar se documento existe e pertence ao usuário
        document = await collection.find_one({
            "id": document_id,
            "usuario_id": usuario_id,
            "deleted": {"$ne": True}  # Não já deletado
        })
        
        if not document:
            return False
        
        # Marcar como deletado
        result = await collection.update_one(
            {"id": document_id, "usuario_id": usuario_id},
            {
                "$set": {
                    "deleted": True,
                    "deleted_at": datetime.now(timezone.utc).isoformat(),
                    "deleted_by": deleted_by,
                    "deleted_reason": motivo
                }
            }
        )
        
        return result.modified_count > 0
    
    @staticmethod
    async def restore(
        collection_name: str,
        document_id: str,
        usuario_id: str
    ) -> bool:
        """
        Restaura um documento previamente deletado
        
        Args:
            collection_name: Nome da coleção no MongoDB
            document_id: ID do documento a ser restaurado
            usuario_id: ID do usuário dono do documento
        
        Returns:
            bool: True se o documento foi restaurado
        """
        collection = db[collection_name]
        
        result = await collection.update_one(
            {
                "id": document_id,
                "usuario_id": usuario_id,
                "deleted": True
            },
            {
                "$set": {"deleted": False},
                "$unset": {
                    "deleted_at": "",
                    "deleted_by": "",
                    "deleted_reason": ""
                }
            }
        )
        
        return result.modified_count > 0
    
    @staticmethod
    async def hard_delete(
        collection_name: str,
        document_id: str,
        usuario_id: str
    ) -> bool:
        """
        Remove permanentemente um documento (usar com cautela!)
        Ideal apenas para dados já em soft delete há muito tempo.
        
        Args:
            collection_name: Nome da coleção no MongoDB
            document_id: ID do documento a ser removido
            usuario_id: ID do usuário dono do documento
        
        Returns:
            bool: True se o documento foi removido permanentemente
        """
        collection = db[collection_name]
        
        result = await collection.delete_one({
            "id": document_id,
            "usuario_id": usuario_id
        })
        
        return result.deleted_count > 0
    
    @staticmethod
    async def list_deleted(
        collection_name: str,
        usuario_id: str,
        skip: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Lista documentos deletados (lixeira)
        
        Args:
            collection_name: Nome da coleção no MongoDB
            usuario_id: ID do usuário
            skip: Pular N documentos (paginação)
            limit: Limite de documentos
        
        Returns:
            Dict com total e lista de documentos deletados
        """
        collection = db[collection_name]
        
        query = {
            "usuario_id": usuario_id,
            "deleted": True
        }
        
        total = await collection.count_documents(query)
        
        documents = await collection.find(
            query,
            {"_id": 0}
        ).sort("deleted_at", -1).skip(skip).limit(limit).to_list(limit)
        
        return {
            "total": total,
            "items": documents
        }
    
    @staticmethod
    def get_active_filter(usuario_id: str, extra_filters: Optional[Dict] = None) -> Dict:
        """
        Retorna um filtro padrão para queries que exclui documentos deletados
        
        Args:
            usuario_id: ID do usuário
            extra_filters: Filtros adicionais a serem combinados
        
        Returns:
            Dict com filtro MongoDB
        """
        base_filter = {
            "usuario_id": usuario_id,
            "deleted": {"$ne": True}
        }
        
        if extra_filters:
            base_filter.update(extra_filters)
        
        return base_filter


# Helper functions para uso direto
async def soft_delete_cliente(cliente_id: str, usuario_id: str, deleted_by: str = None, motivo: str = None) -> bool:
    """Soft delete de cliente"""
    return await SoftDeleteService.soft_delete("clientes", cliente_id, usuario_id, motivo, deleted_by)


async def soft_delete_emprestimo(emprestimo_id: str, usuario_id: str, deleted_by: str = None, motivo: str = None) -> bool:
    """Soft delete de empréstimo e parcelas associadas"""
    # Deletar empréstimo
    result = await SoftDeleteService.soft_delete("emprestimos", emprestimo_id, usuario_id, motivo, deleted_by)
    
    if result:
        # Deletar parcelas associadas
        collection = db["parcelas"]
        await collection.update_many(
            {"emprestimo_id": emprestimo_id, "usuario_id": usuario_id},
            {
                "$set": {
                    "deleted": True,
                    "deleted_at": datetime.now(timezone.utc).isoformat(),
                    "deleted_by": deleted_by,
                    "deleted_reason": f"Empréstimo {emprestimo_id} deletado"
                }
            }
        )
        
        # Deletar pagamentos associados
        pagamentos_collection = db["pagamentos"]
        await pagamentos_collection.update_many(
            {"emprestimo_id": emprestimo_id, "usuario_id": usuario_id},
            {
                "$set": {
                    "deleted": True,
                    "deleted_at": datetime.now(timezone.utc).isoformat(),
                    "deleted_by": deleted_by,
                    "deleted_reason": f"Empréstimo {emprestimo_id} deletado"
                }
            }
        )
    
    return result


async def restore_cliente(cliente_id: str, usuario_id: str) -> bool:
    """Restaura cliente deletado"""
    return await SoftDeleteService.restore("clientes", cliente_id, usuario_id)


async def restore_emprestimo(emprestimo_id: str, usuario_id: str) -> bool:
    """Restaura empréstimo e parcelas deletados — preserva status quitado"""
    # Fix #16: Verificar status original antes de restaurar
    emp = await db.emprestimos.find_one(
        {"id": emprestimo_id, "usuario_id": usuario_id, "deleted": True},
        {"status": 1}
    )

    result = await SoftDeleteService.restore("emprestimos", emprestimo_id, usuario_id)

    if result:
        # Restaurar parcelas
        collection = db["parcelas"]
        await collection.update_many(
            {"emprestimo_id": emprestimo_id, "usuario_id": usuario_id, "deleted": True},
            {
                "$set": {"deleted": False},
                "$unset": {"deleted_at": "", "deleted_by": "", "deleted_reason": ""}
            }
        )

        # Restaurar pagamentos
        pagamentos_collection = db["pagamentos"]
        await pagamentos_collection.update_many(
            {"emprestimo_id": emprestimo_id, "usuario_id": usuario_id, "deleted": True},
            {
                "$set": {"deleted": False},
                "$unset": {"deleted_at": "", "deleted_by": "", "deleted_reason": ""}
            }
        )

        # Fix #16: Se era quitado, preservar o status quitado (não deixar voltar como ativo)
        if emp and emp.get("status") == "quitado":
            await db.emprestimos.update_one(
                {"id": emprestimo_id, "usuario_id": usuario_id},
                {"$set": {"status": "quitado"}}
            )

    return result
