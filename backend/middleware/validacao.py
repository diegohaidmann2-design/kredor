"""
Middleware de Validação e Prevenção de Erros
Valida todos os dados antes de processar
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
import logging

logger = logging.getLogger("jurofacil.validacao")


class ValidacaoMiddleware(BaseHTTPMiddleware):
    """Middleware que valida dados antes de processar"""
    
    async def dispatch(self, request: Request, call_next):
        # Log de todas as requisições
        logger.info(f"[{datetime.now()}] {request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Log de erro
            logger.error(f"Erro em {request.url.path}: {str(e)}")
            raise


async def validar_emprestimo_com_parcelas(db, emprestimo_id: str):
    """
    Valida que empréstimo tem todas as informações necessárias
    Previne: Empréstimo sem parcelas, sem cliente
    """
    emprestimo = await db.emprestimos.find_one({"id": emprestimo_id})
    
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    
    # Validar cliente existe
    cliente_id = emprestimo.get("cliente_id")
    if not cliente_id:
        raise HTTPException(status_code=500, detail="Empréstimo sem cliente associado")
    
    cliente = await db.clientes.find_one({"id": cliente_id})
    if not cliente:
        raise HTTPException(status_code=500, detail=f"Cliente {cliente_id} não encontrado")
    
    # Validar tem parcelas
    parcelas_count = await db.parcelas.count_documents({"emprestimo_id": emprestimo_id})
    if parcelas_count == 0:
        raise HTTPException(status_code=500, detail="Empréstimo sem parcelas geradas")
    
    return emprestimo, cliente


async def validar_parcela_integridade(db, parcela_id: str):
    """
    Valida integridade da parcela
    Previne: Parcela sem valores, sem empréstimo
    """
    parcela = await db.parcelas.find_one({"id": parcela_id})
    
    if not parcela:
        raise HTTPException(status_code=404, detail="Parcela não encontrada")
    
    # Validar valores
    if parcela.get("valor_total") is None or parcela.get("valor_total") <= 0:
        raise HTTPException(status_code=500, detail="Parcela com valor inválido")
    
    if parcela.get("valor_parcela") is None:
        raise HTTPException(status_code=500, detail="Parcela sem valor_parcela definido")
    
    # Validar empréstimo existe
    emprestimo_id = parcela.get("emprestimo_id")
    if not emprestimo_id:
        raise HTTPException(status_code=500, detail="Parcela sem empréstimo associado")
    
    emprestimo = await db.emprestimos.find_one({"id": emprestimo_id})
    if not emprestimo:
        raise HTTPException(status_code=500, detail=f"Empréstimo {emprestimo_id} não encontrado")
    
    return parcela, emprestimo


async def auto_corrigir_parcelas_antigas(db):
    """
    Auto-correção: Corrige parcelas antigas com valor_parcela = None
    Roda automaticamente no startup
    """
    print("🔧 Verificando parcelas antigas...")
    
    result = await db.parcelas.update_many(
        {"$or": [
            {"valor_parcela": {"$exists": False}},
            {"valor_parcela": None}
        ]},
        [{"$set": {"valor_parcela": "$valor_total"}}]
    )
    
    if result.modified_count > 0:
        print(f"✅ {result.modified_count} parcelas corrigidas automaticamente")
    else:
        print("✅ Todas parcelas estão corretas")
