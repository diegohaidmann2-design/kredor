"""
Rotas de Administração de Transações
Monitoramento e gestão de pagamentos
"""
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import re
from config import db
from services.auth import require_admin
from models.transacao import (
    StatusTransacao, 
    MetodoPagamento,
    MotivoRecusa
)

router = APIRouter(prefix="/admin/transacoes", tags=["Admin - Transações"])

@router.get("/", dependencies=[Depends(require_admin)])
async def listar_transacoes(
    status: Optional[str] = None,
    metodo: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    email: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
):
    """
    Lista todas as transações com filtros
    """
    try:
        # Construir query
        query = {}
        
        if status:
            query["status"] = status
        
        if metodo:
            query["metodo_pagamento"] = metodo
        
        if email:
            query["usuario_email"] = {"$regex": re.escape(email), "$options": "i"}
        
        if data_inicio or data_fim:
            query["criado_em"] = {}
            if data_inicio:
                query["criado_em"]["$gte"] = datetime.fromisoformat(data_inicio)
            if data_fim:
                query["criado_em"]["$lte"] = datetime.fromisoformat(data_fim)
        
        # Buscar transações
        cursor = db.transacoes_checkout.find(query, {"_id": 0}).sort("criado_em", -1).skip(skip).limit(limit)
        transacoes = await cursor.to_list(length=limit)
        
        # Contar total
        total = await db.transacoes_checkout.count_documents(query)
        
        return {
            "success": True,
            "transacoes": transacoes,
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pix-pendentes", dependencies=[Depends(require_admin)])
async def listar_pix_pendentes(skip: int = 0, limit: int = 50):
    """
    Lista todos os PIX gerados mas não pagos
    """
    try:
        query = {
            "metodo_pagamento": "pix",
            "status": {"$in": ["pendente", "processando"]},
            "expira_em": {"$gte": datetime.utcnow()}  # Apenas não expirados
        }
        
        cursor = db.transacoes_checkout.find(query, {"_id": 0}).sort("criado_em", -1).skip(skip).limit(limit)
        transacoes = await cursor.to_list(length=limit)
        
        total = await db.transacoes_checkout.count_documents(query)
        
        # Calcular valor total em aberto
        pipeline = [
            {"$match": query},
            {"$group": {"_id": None, "valor_total": {"$sum": "$valor"}}}
        ]
        resultado = await db.transacoes_checkout.aggregate(pipeline).to_list(length=1)
        valor_total = resultado[0]["valor_total"] if resultado else 0
        
        return {
            "success": True,
            "transacoes": transacoes,
            "total": total,
            "valor_total_aberto": valor_total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cartoes-recusados", dependencies=[Depends(require_admin)])
async def listar_cartoes_recusados(skip: int = 0, limit: int = 50):
    """
    Lista todas as tentativas de pagamento por cartão recusadas
    """
    try:
        query = {
            "metodo_pagamento": "cartao_credito",
            "status": "recusado"
        }
        
        cursor = db.transacoes_checkout.find(query, {"_id": 0}).sort("criado_em", -1).skip(skip).limit(limit)
        transacoes = await cursor.to_list(length=limit)
        
        total = await db.transacoes_checkout.count_documents(query)
        
        # Agrupar por motivo de recusa
        pipeline = [
            {"$match": query},
            {"$group": {
                "_id": "$motivo_recusa",
                "count": {"$sum": 1},
                "valor_total": {"$sum": "$valor"}
            }}
        ]
        motivos = await db.transacoes_checkout.aggregate(pipeline).to_list(length=None)
        
        return {
            "success": True,
            "transacoes": transacoes,
            "total": total,
            "motivos_recusa": motivos,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metricas", dependencies=[Depends(require_admin)])
async def obter_metricas():
    """
    Retorna métricas gerais de transações
    """
    try:
        # Período: últimos 30 dias
        data_inicio = datetime.utcnow() - timedelta(days=30)
        
        # Total de transações
        total_transacoes = await db.transacoes_checkout.count_documents(
            {"criado_em": {"$gte": data_inicio}}
        )
        
        # PIX pendentes
        pix_pendentes = await db.transacoes_checkout.count_documents({
            "metodo_pagamento": "pix",
            "status": {"$in": ["pendente", "processando"]},
            "criado_em": {"$gte": data_inicio}
        })
        
        # Cartões recusados
        cartoes_recusados = await db.transacoes_checkout.count_documents({
            "metodo_pagamento": "cartao_credito",
            "status": "recusado",
            "criado_em": {"$gte": data_inicio}
        })
        
        # Transações aprovadas
        aprovadas = await db.transacoes_checkout.count_documents({
            "status": "aprovado",
            "criado_em": {"$gte": data_inicio}
        })
        
        # Valor total perdido
        pipeline_perdido = [
            {
                "$match": {
                    "status": {"$in": ["recusado", "expirado", "cancelado"]},
                    "criado_em": {"$gte": data_inicio}
                }
            },
            {"$group": {"_id": None, "valor_total": {"$sum": "$valor"}}}
        ]
        resultado = await db.transacoes_checkout.aggregate(pipeline_perdido).to_list(length=1)
        valor_perdido = resultado[0]["valor_total"] if resultado else 0
        
        # Valor total aprovado
        pipeline_aprovado = [
            {
                "$match": {
                    "status": "aprovado",
                    "criado_em": {"$gte": data_inicio}
                }
            },
            {"$group": {"_id": None, "valor_total": {"$sum": "$valor"}}}
        ]
        resultado = await db.transacoes_checkout.aggregate(pipeline_aprovado).to_list(length=1)
        valor_aprovado = resultado[0]["valor_total"] if resultado else 0
        
        # Taxa de conversão
        taxa_conversao = (aprovadas / total_transacoes * 100) if total_transacoes > 0 else 0
        
        return {
            "success": True,
            "periodo": "últimos 30 dias",
            "total_transacoes": total_transacoes,
            "transacoes_aprovadas": aprovadas,
            "pix_pendentes": pix_pendentes,
            "cartoes_recusados": cartoes_recusados,
            "valor_perdido": round(valor_perdido, 2),
            "valor_aprovado": round(valor_aprovado, 2),
            "taxa_conversao": round(taxa_conversao, 2)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{transacao_id}/enviar-email", dependencies=[Depends(require_admin)])
async def enviar_email_recuperacao(transacao_id: str, background_tasks: BackgroundTasks):
    """
    Envia email de recuperação para uma transação não concluída
    Com template personalizado baseado no tipo de falha
    """
    try:
        
        # Buscar transação
        transacao = await db.transacoes_checkout.find_one({"id": transacao_id})
        
        if not transacao:
            raise HTTPException(status_code=404, detail="Transação não encontrada")
        
        # Verificar se já tem cupom gerado
        cupom = transacao.get("cupom_gerado")
        desconto = None
        
        if cupom:
            # Buscar desconto do cupom
            cupom_doc = await db.cupons.find_one({"codigo": cupom})
            desconto = cupom_doc["desconto_percentual"] if cupom_doc else None
        
        # Escolher template baseado no status
        nome = transacao["usuario_nome"]
        plano_nome = transacao["plano_nome"]
        valor = transacao["valor"]
        metodo = transacao["metodo_pagamento"]
        status = transacao["status"]
        
        if metodo == "pix" and status in ["pendente", "expirado"]:
            # PIX não pago ou expirado
            html, texto = email_pix_expirado(
                nome, plano_nome, valor, cupom, desconto
            )
            assunto = "Seu PIX expirou - Gere um novo com desconto!"
        
        elif metodo == "cartao_credito" and status == "recusado":
            # Cartão recusado
            motivo = transacao.get("motivo_recusa", "Pagamento não autorizado")
            html, texto = email_cartao_recusado(
                nome, plano_nome, valor, motivo, cupom, desconto
            )
            assunto = "Pagamento não aprovado - Vamos tentar novamente?"
        
        else:
            # Genérico - carrinho abandonado
            html, texto = email_recuperacao_carrinho(
                nome, plano_nome, valor, cupom, desconto
            )
            assunto = "Não desista! Temos uma oferta especial para você"
        
        # Enviar email em background
        background_tasks.add_task(
            enviar_email_async,
            transacao["usuario_email"],
            assunto,
            html,
            texto
        )
        
        # Marcar como enviado antecipadamente (ou poderíamos fazer isso dentro da task, mas aqui é mais simples para o feedback da UI)
        await db.transacoes_checkout.update_one(
            {"id": transacao_id},
            {
                "$set": {
                    "email_enviado": True,
                    "data_email": datetime.utcnow()
                }
            }
        )
        
        return {
            "success": True,
            "message": "Processamento de envio de e-mail de recuperação iniciado."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{transacao_id}/gerar-cupom", dependencies=[Depends(require_admin)])
async def gerar_cupom_desconto(transacao_id: str, desconto_percentual: int = 10):
    """
    Gera um cupom de desconto para recuperação da transação
    """
    try:
        # Buscar transação
        transacao = await db.transacoes_checkout.find_one({"id": transacao_id})
        
        if not transacao:
            raise HTTPException(status_code=404, detail="Transação não encontrada")
        
        # Gerar código do cupom
        cupom_codigo = f"RECOVER{uuid.uuid4().hex[:8].upper()}"
        
        # Salvar cupom
        cupom = {
            "id": str(uuid.uuid4()),
            "codigo": cupom_codigo,
            "desconto_percentual": desconto_percentual,
            "transacao_origem": transacao_id,
            "usuario_email": transacao["usuario_email"],
            "valido_ate": datetime.utcnow() + timedelta(days=7),
            "usado": False,
            "criado_em": datetime.utcnow()
        }
        
        await db.cupons.insert_one(cupom)
        
        # Atualizar transação
        await db.transacoes_checkout.update_one(
            {"id": transacao_id},
            {"$set": {"cupom_gerado": cupom_codigo}}
        )
        
        return {
            "success": True,
            "cupom": cupom_codigo,
            "desconto": desconto_percentual,
            "valido_ate": cupom["valido_ate"].isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/cupom/validar/{codigo}", dependencies=[Depends(require_admin)])
async def validar_cupom(codigo: str, email: Optional[str] = None):
    """
    Valida um cupom de desconto (uso administrativo).
    O checkout público usa /api/assinaturas/cupom/validar/{codigo}.
    """
    try:
        # Buscar cupom
        cupom = await db.cupons.find_one({"codigo": codigo.upper()})
        
        if not cupom:
            return {
                "valido": False,
                "erro": "Cupom não encontrado"
            }
        
        # Verificar se já foi usado
        if cupom.get("usado", False):
            return {
                "valido": False,
                "erro": "Cupom já foi utilizado"
            }
        
        # Verificar validade
        if cupom.get("valido_ate") and cupom["valido_ate"] < datetime.utcnow():
            return {
                "valido": False,
                "erro": "Cupom expirado"
            }
        
        # Verificar se é específico para um email
        if email and cupom.get("usuario_email"):
            if cupom["usuario_email"].lower() != email.lower():
                return {
                    "valido": False,
                    "erro": "Cupom não é válido para este email"
                }
        
        return {
            "valido": True,
            "codigo": cupom["codigo"],
            "desconto_percentual": cupom["desconto_percentual"],
            "valido_ate": cupom["valido_ate"].isoformat() if cupom.get("valido_ate") else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cupom/usar/{codigo}", dependencies=[Depends(require_admin)])
async def usar_cupom(codigo: str, email: str, valor_original: float):
    """
    Marca um cupom como usado e calcula valor com desconto
    """
    try:
        # Validar cupom primeiro
        cupom = await db.cupons.find_one({"codigo": codigo.upper()})
        
        if not cupom or cupom.get("usado") or (cupom.get("valido_ate") and cupom["valido_ate"] < datetime.utcnow()):
            raise HTTPException(status_code=400, detail="Cupom inválido")
        
        # Verificar email se necessário
        if cupom.get("usuario_email") and cupom["usuario_email"].lower() != email.lower():
            raise HTTPException(status_code=403, detail="Cupom não autorizado para este email")
        
        # Calcular desconto
        desconto_percentual = cupom["desconto_percentual"]
        desconto_valor = valor_original * (desconto_percentual / 100)
        valor_final = valor_original - desconto_valor
        
        # Marcar como usado
        await db.cupons.update_one(
            {"codigo": codigo.upper()},
            {
                "$set": {
                    "usado": True,
                    "usado_em": datetime.utcnow(),
                    "usado_por_email": email,
                    "valor_original": valor_original,
                    "valor_desconto": desconto_valor,
                    "valor_final": valor_final
                }
            }
        )
        
        return {
            "success": True,
            "valor_original": valor_original,
            "desconto_percentual": desconto_percentual,
            "desconto_valor": desconto_valor,
            "valor_final": valor_final
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relatorio-semanal/executar", dependencies=[Depends(require_admin)])
async def executar_relatorio_semanal_manual():
    """
    Executa manualmente o job de relatório semanal (para teste ou forçar envio)
    """
    try:
        
        resultado = await gerar_relatorio_semanal()
        
        return resultado
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/relatorio-semanal/historico", dependencies=[Depends(require_admin)])
async def historico_relatorios_semanais(limit: int = 10):
    """
    Lista histórico de execuções do job de relatório semanal
    """
    try:
        cursor = db.jobs_execucoes.find(
            {"job": "relatorio_semanal"},
            {"_id": 0}  # Excluir _id do MongoDB para evitar erro de serialização
        ).sort("executado_em", -1).limit(limit)
        
        historico = await cursor.to_list(length=limit)
        
        return {
            "success": True,
            "historico": historico,
            "total": len(historico)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== FASE 5: EXPORTAÇÃO AVANÇADA ====================

@router.get("/exportar/{formato}", dependencies=[Depends(require_admin)])
async def exportar_transacoes(
    formato: str,  # csv ou excel
    status: Optional[str] = None,
    metodo: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
):
    """
    Exporta transações em formato CSV ou Excel
    FASE 5 - Exportação real de dados
    """
    try:
        
        if formato not in ["csv", "excel"]:
            raise HTTPException(status_code=400, detail="Formato deve ser 'csv' ou 'excel'")
        
        # Construir query
        query = {}
        
        if status:
            query["status"] = status
        
        if metodo:
            query["metodo_pagamento"] = metodo
        
        if data_inicio or data_fim:
            query["criado_em"] = {}
            if data_inicio:
                query["criado_em"]["$gte"] = datetime.fromisoformat(data_inicio)
            if data_fim:
                query["criado_em"]["$lte"] = datetime.fromisoformat(data_fim)
        
        # Buscar transações
        cursor = db.transacoes_checkout.find(query, {"_id": 0}).sort("criado_em", -1)
        transacoes = await cursor.to_list(length=10000)  # Limitar a 10k registros
        
        if not transacoes:
            raise HTTPException(status_code=404, detail="Nenhuma transação encontrada")
        
        if formato == "csv":
            # Gerar CSV
            output = StringIO()
            fieldnames = [
                "id", "usuario_nome", "usuario_email", "plano_nome", "valor",
                "metodo_pagamento", "status", "criado_em", "payment_id",
                "email_enviado", "cupom_gerado", "motivo_recusa"
            ]
            
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            
            for t in transacoes:
                # Converter datetime para string
                if isinstance(t.get("criado_em"), datetime):
                    t["criado_em"] = t["criado_em"].strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow(t)
            
            output.seek(0)
            
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=transacoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                }
            )
        
        else:  # excel
            # Gerar Excel com openpyxl
            try:
                from openpyxl import Workbook
                from openpyxl.styles import Font, PatternFill, Alignment
            except ImportError:
                raise HTTPException(
                    status_code=500, 
                    detail="Biblioteca openpyxl não instalada. Use formato CSV."
                )
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Transações"
            
            # Cabeçalhos com estilo
            headers = [
                "ID", "Nome", "Email", "Plano", "Valor",
                "Método", "Status", "Data", "Payment ID",
                "Email Enviado", "Cupom", "Motivo Recusa"
            ]
            
            header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF")
            
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
            
            # Dados
            for row_idx, t in enumerate(transacoes, 2):
                ws.cell(row=row_idx, column=1, value=t.get("id", ""))
                ws.cell(row=row_idx, column=2, value=t.get("usuario_nome", ""))
                ws.cell(row=row_idx, column=3, value=t.get("usuario_email", ""))
                ws.cell(row=row_idx, column=4, value=t.get("plano_nome", ""))
                ws.cell(row=row_idx, column=5, value=t.get("valor", 0))
                ws.cell(row=row_idx, column=6, value=t.get("metodo_pagamento", ""))
                ws.cell(row=row_idx, column=7, value=t.get("status", ""))
                
                data_criacao = t.get("criado_em")
                if isinstance(data_criacao, datetime):
                    ws.cell(row=row_idx, column=8, value=data_criacao.strftime("%Y-%m-%d %H:%M:%S"))
                else:
                    ws.cell(row=row_idx, column=8, value=str(data_criacao) if data_criacao else "")
                
                ws.cell(row=row_idx, column=9, value=t.get("payment_id", ""))
                ws.cell(row=row_idx, column=10, value="Sim" if t.get("email_enviado") else "Não")
                ws.cell(row=row_idx, column=11, value=t.get("cupom_gerado", ""))
                ws.cell(row=row_idx, column=12, value=t.get("motivo_recusa", ""))
            
            # Ajustar largura das colunas
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column].width = adjusted_width
            
            # Salvar em BytesIO
            output = BytesIO()
            wb.save(output)
            output.seek(0)
            
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename=transacoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao exportar: {str(e)}")



# ==================== GESTÃO DE CUPONS ====================

from pydantic import BaseModel
from services.email_service import (
            enviar_email_async, 
            email_recuperacao_carrinho, 
            email_pix_expirado,
            email_cartao_recusado
        )
from jobs.relatorio_semanal import gerar_relatorio_semanal
from io import BytesIO, StringIO
from fastapi.responses import StreamingResponse
import csv

class CriarCupomRequest(BaseModel):
    codigo: Optional[str] = None
    desconto_percentual: int = 10
    valido_ate: Optional[str] = None
    usuario_email: Optional[str] = None
    limite_uso: int = 1
    descricao: Optional[str] = None

@router.post("/cupons/criar", dependencies=[Depends(require_admin)])
async def criar_cupom_manual(request: CriarCupomRequest):
    """
    Cria um cupom de desconto manualmente (interface admin)
    Permite criar cupons genéricos ou específicos para um email
    """
    try:
        # Extrair dados do request
        codigo = request.codigo
        desconto_percentual = request.desconto_percentual
        valido_ate = request.valido_ate
        usuario_email = request.usuario_email
        limite_uso = request.limite_uso
        descricao = request.descricao
        
        # Gerar código se não fornecido
        if not codigo:
            codigo = f"PROMO{uuid.uuid4().hex[:8].upper()}"
        else:
            # Verificar se código já existe
            codigo = codigo.strip().upper()
            existing = await db.cupons.find_one({"codigo": codigo})
            if existing:
                raise HTTPException(status_code=400, detail="Código de cupom já existe")
        
        # Validar desconto
        if desconto_percentual < 1 or desconto_percentual > 100:
            raise HTTPException(status_code=400, detail="Desconto deve estar entre 1% e 100%")
        
        # Data de validade
        valido_ate_dt = None
        if valido_ate:
            try:
                valido_ate_dt = datetime.fromisoformat(valido_ate)
            except Exception:
                raise HTTPException(status_code=400, detail="Data de validade inválida")
        else:
            # Padrão: 30 dias
            valido_ate_dt = datetime.utcnow() + timedelta(days=30)
        
        # Criar cupom
        cupom = {
            "id": str(uuid.uuid4()),
            "codigo": codigo,
            "desconto_percentual": desconto_percentual,
            "usuario_email": usuario_email.lower() if usuario_email else None,
            "valido_ate": valido_ate_dt,
            "limite_uso": limite_uso,
            "usos": 0,
            "usado": False,  # Será True quando atingir limite
            "descricao": descricao,
            "tipo": "manual",  # Para diferenciar de cupons de remarketing
            "criado_em": datetime.utcnow(),
            "criado_por": "admin"
        }
        
        await db.cupons.insert_one(cupom)
        
        return {
            "success": True,
            "cupom": {
                "codigo": codigo,
                "desconto_percentual": desconto_percentual,
                "valido_ate": valido_ate_dt.isoformat(),
                "usuario_email": usuario_email,
                "limite_uso": limite_uso
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cupons", dependencies=[Depends(require_admin)])
async def listar_cupons(
    ativo: Optional[bool] = None,
    tipo: Optional[str] = None,  # manual, remarketing
    skip: int = 0,
    limit: int = 50
):
    """
    Lista todos os cupons criados
    """
    try:
        query = {}
        
        if ativo is not None:
            if ativo:
                query["$and"] = [
                    {"usado": False},
                    {"valido_ate": {"$gte": datetime.utcnow()}}
                ]
            else:
                query["$or"] = [
                    {"usado": True},
                    {"valido_ate": {"$lt": datetime.utcnow()}}
                ]
        
        if tipo:
            query["tipo"] = tipo
        
        cursor = db.cupons.find(query, {"_id": 0}).sort("criado_em", -1).skip(skip).limit(limit)
        cupons = await cursor.to_list(length=limit)
        
        total = await db.cupons.count_documents(query)
        
        # Calcular estatísticas
        ativos = await db.cupons.count_documents({
            "usado": False,
            "valido_ate": {"$gte": datetime.utcnow()}
        })
        
        usados = await db.cupons.count_documents({"usado": True})
        
        expirados = await db.cupons.count_documents({
            "usado": False,
            "valido_ate": {"$lt": datetime.utcnow()}
        })
        
        return {
            "success": True,
            "cupons": cupons,
            "total": total,
            "skip": skip,
            "limit": limit,
            "estatisticas": {
                "ativos": ativos,
                "usados": usados,
                "expirados": expirados
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cupons/{codigo}", dependencies=[Depends(require_admin)])
async def detalhes_cupom(codigo: str):
    """
    Detalhes de um cupom específico
    """
    try:
        cupom = await db.cupons.find_one({"codigo": codigo.upper()}, {"_id": 0})
        
        if not cupom:
            raise HTTPException(status_code=404, detail="Cupom não encontrado")
        
        # Buscar histórico de uso
        historico = []
        if cupom.get("usado_em"):
            historico.append({
                "email": cupom.get("usado_por_email"),
                "data": cupom.get("usado_em"),
                "valor_desconto": cupom.get("valor_desconto", 0)
            })
        
        return {
            "success": True,
            "cupom": cupom,
            "historico_uso": historico
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cupons/{codigo}", dependencies=[Depends(require_admin)])
async def deletar_cupom(codigo: str):
    """
    Deleta um cupom (apenas se não foi usado)
    """
    try:
        cupom = await db.cupons.find_one({"codigo": codigo.upper()})
        
        if not cupom:
            raise HTTPException(status_code=404, detail="Cupom não encontrado")
        
        if cupom.get("usado"):
            raise HTTPException(status_code=400, detail="Não é possível deletar cupom já utilizado")
        
        await db.cupons.delete_one({"codigo": codigo.upper()})
        
        return {
            "success": True,
            "message": "Cupom deletado com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/cupons/{codigo}/desativar", dependencies=[Depends(require_admin)])
async def desativar_cupom(codigo: str):
    """
    Desativa um cupom (marca como expirado)
    """
    try:
        cupom = await db.cupons.find_one({"codigo": codigo.upper()})
        
        if not cupom:
            raise HTTPException(status_code=404, detail="Cupom não encontrado")
        
        # Marcar como expirado (data no passado)
        await db.cupons.update_one(
            {"codigo": codigo.upper()},
            {"$set": {"valido_ate": datetime.utcnow() - timedelta(days=1)}}
        )
        
        return {
            "success": True,
            "message": "Cupom desativado com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/exportar", dependencies=[Depends(require_admin)])
async def exportar_transacoes_json(
    formato: str = "csv",
    status: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
):
    """
    Exporta transações em CSV ou Excel
    """
    try:
        # Construir query
        query = {}
        
        if status:
            query["status"] = status
        
        if data_inicio or data_fim:
            query["criado_em"] = {}
            if data_inicio:
                query["criado_em"]["$gte"] = datetime.fromisoformat(data_inicio)
            if data_fim:
                query["criado_em"]["$lte"] = datetime.fromisoformat(data_fim)
        
        # Buscar todas as transações
        cursor = db.transacoes_checkout.find(query, {"_id": 0}).sort("criado_em", -1)
        transacoes = await cursor.to_list(length=None)
        
        # TODO: Implementar formatação CSV/Excel
        # Por enquanto retorna JSON
        
        return {
            "success": True,
            "formato": formato,
            "total_registros": len(transacoes),
            "dados": transacoes
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
