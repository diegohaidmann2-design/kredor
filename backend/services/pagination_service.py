"""
Serviço de Paginação - Kredor
Implementa paginação padronizada para todos os endpoints de listagem
"""
from typing import Dict, Any, List, Optional, TypeVar, Generic
from pydantic import BaseModel
from math import ceil


class PaginationParams(BaseModel):
    """Parâmetros de paginação padrão"""
    page: int = 1
    limit: int = 50
    
    @property
    def skip(self) -> int:
        """Calcula o offset para MongoDB"""
        return (self.page - 1) * self.limit
    
    def validate(self):
        """Valida e ajusta parâmetros"""
        if self.page < 1:
            self.page = 1
        if self.limit < 1:
            self.limit = 1
        if self.limit > 100:
            self.limit = 100  # Limite máximo para evitar sobrecarga


class PaginatedResponse(BaseModel):
    """Resposta paginada padrão"""
    items: List[Any]
    total: int
    page: int
    limit: int
    pages: int
    has_next: bool
    has_prev: bool
    
    @classmethod
    def create(cls, items: List[Any], total: int, page: int, limit: int) -> "PaginatedResponse":
        """Cria uma resposta paginada"""
        pages = ceil(total / limit) if limit > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )


class PaginationService:
    """
    Serviço centralizado para paginação.
    Fornece métodos utilitários para paginação consistente.
    """
    
    @staticmethod
    def get_pagination_params(page: int = 1, limit: int = 50) -> PaginationParams:
        """
        Cria e valida parâmetros de paginação
        
        Args:
            page: Número da página (começa em 1)
            limit: Itens por página (máximo 100)
        
        Returns:
            PaginationParams validados
        """
        params = PaginationParams(page=page, limit=limit)
        params.validate()
        return params
    
    @staticmethod
    async def paginate_query(
        collection,
        query: Dict[str, Any],
        page: int = 1,
        limit: int = 50,
        sort_field: str = "created_at",
        sort_direction: int = -1,
        projection: Optional[Dict] = None
    ) -> PaginatedResponse:
        """
        Executa uma query paginada no MongoDB
        
        Args:
            collection: Coleção do MongoDB
            query: Filtros da query
            page: Número da página
            limit: Itens por página
            sort_field: Campo para ordenação
            sort_direction: 1 para ASC, -1 para DESC
            projection: Campos a retornar (None para todos)
        
        Returns:
            PaginatedResponse com os resultados
        """
        params = PaginationService.get_pagination_params(page, limit)
        
        # Contar total
        total = await collection.count_documents(query)
        
        # Buscar itens
        cursor = collection.find(query, projection or {"_id": 0})
        cursor = cursor.sort(sort_field, sort_direction)
        cursor = cursor.skip(params.skip).limit(params.limit)
        
        items = await cursor.to_list(params.limit)
        
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=params.page,
            limit=params.limit
        )
    
    @staticmethod
    def create_response(
        items: List[Any],
        total: int,
        page: int,
        limit: int
    ) -> Dict[str, Any]:
        """
        Cria uma resposta paginada em formato dict
        
        Args:
            items: Lista de itens
            total: Total de itens
            page: Página atual
            limit: Itens por página
        
        Returns:
            Dict com metadados de paginação
        """
        pages = ceil(total / limit) if limit > 0 else 0
        
        return {
            "items": items,
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "pages": pages,
                "has_next": page < pages,
                "has_prev": page > 1
            }
        }
    
    @staticmethod
    def get_headers(total: int, page: int, limit: int) -> Dict[str, str]:
        """
        Gera headers HTTP para paginação
        
        Args:
            total: Total de itens
            page: Página atual
            limit: Itens por página
        
        Returns:
            Dict com headers de paginação
        """
        pages = ceil(total / limit) if limit > 0 else 0
        
        return {
            "X-Total-Count": str(total),
            "X-Page": str(page),
            "X-Per-Page": str(limit),
            "X-Total-Pages": str(pages)
        }


# Helper functions para uso direto nos endpoints
def paginate(page: int = 1, limit: int = 50) -> PaginationParams:
    """Helper para obter params de paginação"""
    return PaginationService.get_pagination_params(page, limit)


async def paginated_find(
    collection,
    query: Dict,
    page: int = 1,
    limit: int = 50,
    sort_field: str = "created_at",
    sort_direction: int = -1
) -> Dict[str, Any]:
    """
    Helper para executar query paginada e retornar dict
    
    Uso:
        result = await paginated_find(
            db.clientes,
            {"usuario_id": user_id, "deleted": {"$ne": True}},
            page=1,
            limit=20
        )
        return result  # {"items": [...], "pagination": {...}}
    """
    params = paginate(page, limit)
    
    total = await collection.count_documents(query)
    
    items = await collection.find(
        query, 
        {"_id": 0}
    ).sort(
        sort_field, 
        sort_direction
    ).skip(
        params.skip
    ).limit(
        params.limit
    ).to_list(params.limit)
    
    return PaginationService.create_response(items, total, params.page, params.limit)
