"""
Rotas de Exportação em Massa
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Literal, Optional
from datetime import datetime, timezone
import io
import csv
import json

from config import db
from models.usuario import Usuario
from services.auth import get_current_user
from services.permissao_service import verificar_recurso
from services.permissao_service import PermissaoService
import zipfile

router = APIRouter()


def _registros_para_csv_bytes(registros: list) -> bytes:
    """Gera CSV cobrindo TODAS as colunas presentes em qualquer registro.

    O Mongo guarda documentos heterogêneos (campos que surgiram com o tempo),
    então usar só as chaves do 1º registro quebrava o export (ValueError em
    writerows) e/ou omitia colunas. Aqui a lista de colunas é a UNIÃO de todas
    as chaves, na ordem de aparição, e valores dict/list viram JSON.
    """
    output = io.StringIO()
    if registros:
        fieldnames = []
        vistos = set()
        for r in registros:
            for k in r.keys():
                if k not in vistos:
                    vistos.add(k)
                    fieldnames.append(k)
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in registros:
            linha = {}
            for k in fieldnames:
                v = r.get(k, "")
                if isinstance(v, (dict, list)):
                    linha[k] = json.dumps(v, ensure_ascii=False, default=str)
                elif v is None:
                    linha[k] = ""
                else:
                    linha[k] = v
            writer.writerow(linha)
    return output.getvalue().encode("utf-8")


class ExportRequest(BaseModel):
    entidades: List[Literal["clientes", "emprestimos", "pagamentos", "parcelas"]]
    formato: Literal["csv", "json"] = "csv"
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None


@router.post("/exportar")
async def exportar_dados(
    request: ExportRequest,
    current_user: Usuario = Depends(verificar_recurso("exportacao_dados"))
):
    """Exporta dados em massa para CSV ou JSON"""
    user_filter = {"usuario_id": current_user.id}
    
    # Filtro de data
    date_filter = {}
    if request.data_inicio:
        date_filter["$gte"] = request.data_inicio
    if request.data_fim:
        date_filter["$lte"] = request.data_fim
    
    dados_exportados = {}
    
    for entidade in request.entidades:
        query = {**user_filter}
        if date_filter and entidade in ["emprestimos", "pagamentos"]:
            query["created_at"] = date_filter
        
        collection = getattr(db, entidade)
        registros = await collection.find(query, {"_id": 0}).to_list(50000)
        
        # Converter ObjectId e datetime para string
        for r in registros:
            for k, v in r.items():
                if hasattr(v, 'isoformat'):
                    r[k] = v.isoformat()
                elif hasattr(v, '__str__') and not isinstance(v, (str, int, float, bool, list, dict)):
                    r[k] = str(v)
        
        dados_exportados[entidade] = registros
    
    if request.formato == "json":
        # Retornar JSON
        output = io.BytesIO()
        output.write(json.dumps(dados_exportados, ensure_ascii=False, indent=2, default=str).encode('utf-8'))
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=exportacao_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
            }
        )
    else:
        # Retornar CSV (zip com múltiplos arquivos se houver várias entidades)
        
        if len(request.entidades) == 1:
            # Único CSV
            entidade = request.entidades[0]
            registros = dados_exportados[entidade]

            return StreamingResponse(
                io.BytesIO(_registros_para_csv_bytes(registros)),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename={entidade}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
                }
            )
        else:
            # Múltiplos CSVs em ZIP
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for entidade, registros in dados_exportados.items():
                    zip_file.writestr(f"{entidade}.csv", _registros_para_csv_bytes(registros).decode('utf-8'))
            
            zip_buffer.seek(0)
            return StreamingResponse(
                zip_buffer,
                media_type="application/zip",
                headers={
                    "Content-Disposition": f"attachment; filename=exportacao_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.zip"
                }
            )


@router.get("/resumo")
async def resumo_exportacao(current_user: Usuario = Depends(get_current_user)):
    """Retorna resumo dos dados disponíveis para exportação e permissão"""
    permissao_service = PermissaoService()
    
    user_filter = {"usuario_id": current_user.id}
    
    # Verificar se tem permissão de exportação
    pode_exportar, mensagem = await permissao_service.verificar_recurso(current_user, "exportacao_dados")
    
    return {
        "clientes": await db.clientes.count_documents(user_filter),
        "emprestimos": await db.emprestimos.count_documents(user_filter),
        "pagamentos": await db.pagamentos.count_documents(user_filter),
        "parcelas": await db.parcelas.count_documents(user_filter),
        "pode_exportar": pode_exportar,
        "mensagem_permissao": None if pode_exportar else mensagem
    }
