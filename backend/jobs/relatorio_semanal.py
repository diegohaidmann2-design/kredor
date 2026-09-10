"""
Job para envio de relatórios semanais automáticos
Executa toda segunda-feira às 9h via cron ou scheduler
"""
from services.logging_service import get_logger
logger = get_logger("gestorcred.relatorio_semanal")

from datetime import datetime, timedelta
from config import db
from services.email_service import enviar_email, email_relatorio_semanal_admin
import traceback
import asyncio


async def gerar_relatorio_semanal():
    """
    Gera e envia relatório semanal para todos os admins
    """
    try:
        # Calcular período (últimos 7 dias)
        data_fim = datetime.utcnow()
        data_inicio = data_fim - timedelta(days=7)
        periodo_formatado = f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
        
        # Query base para o período
        query_periodo = {
            "criado_em": {
                "$gte": data_inicio,
                "$lte": data_fim
            }
        }
        
        # 1. Total de transações
        total_transacoes = await db.transacoes_checkout.count_documents(query_periodo)
        
        # 2. PIX pendentes
        query_pix = {
            **query_periodo,
            "metodo_pagamento": "pix",
            "status": {"$in": ["pendente", "processando"]}
        }
        pix_pendentes = await db.transacoes_checkout.count_documents(query_pix)
        
        # 3. Cartões recusados
        query_cartoes = {
            **query_periodo,
            "metodo_pagamento": "cartao_credito",
            "status": "recusado"
        }
        cartoes_recusados = await db.transacoes_checkout.count_documents(query_cartoes)
        
        # 4. Taxa de conversão
        aprovadas = await db.transacoes_checkout.count_documents({
            **query_periodo,
            "status": "aprovado"
        })
        taxa_conversao = (aprovadas / total_transacoes * 100) if total_transacoes > 0 else 0
        
        # 5. Valores
        pipeline_valores = [
            {"$match": query_periodo},
            {
                "$group": {
                    "_id": "$status",
                    "total": {"$sum": "$valor"}
                }
            }
        ]
        valores = await db.transacoes_checkout.aggregate(pipeline_valores).to_list(length=10)
        
        valor_aprovado = 0
        valor_perdido = 0
        
        for item in valores:
            if item["_id"] == "aprovado":
                valor_aprovado = item["total"]
            elif item["_id"] in ["recusado", "expirado", "cancelado"]:
                valor_perdido += item["total"]
        
        # 6. Métricas de remarketing
        emails_enviados = await db.transacoes_checkout.count_documents({
            **query_periodo,
            "email_enviado": True
        })
        
        cupons_gerados = await db.cupons.count_documents({
            "criado_em": {
                "$gte": data_inicio,
                "$lte": data_fim
            }
        })
        
        # Recuperações = transações que tinham email enviado e depois foram aprovadas
        pipeline_recuperacoes = [
            {
                "$match": {
                    **query_periodo,
                    "email_enviado": True,
                    "status": "aprovado"
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "valor_total": {"$sum": "$valor"}
                }
            }
        ]
        resultado_recuperacoes = await db.transacoes_checkout.aggregate(pipeline_recuperacoes).to_list(length=1)
        
        recuperacoes = resultado_recuperacoes[0]["total"] if resultado_recuperacoes else 0
        valor_recuperado = resultado_recuperacoes[0]["valor_total"] if resultado_recuperacoes else 0
        
        # 7. Buscar emails dos admins
        admins = await db.usuarios.find({"perfil": "admin", "ativo": True}).to_list(length=100)
        
        if not admins:
            logger.warning("⚠️ Nenhum admin encontrado para enviar relatório")
            return {
                "success": False,
                "message": "Nenhum admin encontrado"
            }
        
        # 8. Gerar e enviar email para cada admin
        emails_enviados_count = 0
        
        for admin in admins:
            try:
                html, texto = email_relatorio_semanal_admin(
                    periodo=periodo_formatado,
                    total_transacoes=total_transacoes,
                    pix_pendentes=pix_pendentes,
                    cartoes_recusados=cartoes_recusados,
                    taxa_conversao=taxa_conversao,
                    valor_perdido=valor_perdido,
                    valor_aprovado=valor_aprovado,
                    emails_enviados=emails_enviados,
                    cupons_gerados=cupons_gerados,
                    recuperacoes=recuperacoes,
                    valor_recuperado=valor_recuperado
                )
                
                sucesso = enviar_email(
                    admin["email"],
                    f"📊 Relatório Semanal de Transações - {periodo_formatado}",
                    html,
                    texto
                )
                
                if sucesso:
                    emails_enviados_count += 1
                    logger.info(f"✅ Relatório enviado para {admin['email']}")
                else:
                    logger.error(f"⚠️ Falha ao enviar para {admin['email']}")
                    
            except Exception as e:
                logger.error(f"❌ Erro ao enviar para {admin['email']}: {e}")
        
        # 9. Registrar execução do job
        await db.jobs_execucoes.insert_one({
            "job": "relatorio_semanal",
            "executado_em": datetime.utcnow(),
            "periodo": periodo_formatado,
            "emails_enviados": emails_enviados_count,
            "status": "sucesso" if emails_enviados_count > 0 else "falha",
            "metricas": {
                "total_transacoes": total_transacoes,
                "taxa_conversao": taxa_conversao,
                "valor_aprovado": valor_aprovado,
                "valor_recuperado": valor_recuperado
            }
        })
        
        return {
            "success": True,
            "emails_enviados": emails_enviados_count,
            "periodo": periodo_formatado,
            "metricas": {
                "total_transacoes": total_transacoes,
                "taxa_conversao": round(taxa_conversao, 2),
                "recuperacoes": recuperacoes
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar relatório semanal: {e}")
        logger.error("Traceback do erro", exc_info=True)
        
        # Registrar erro
        await db.jobs_execucoes.insert_one({
            "job": "relatorio_semanal",
            "executado_em": datetime.utcnow(),
            "status": "erro",
            "erro": str(e)
        })
        
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    """
    Permite executar o job manualmente para teste:
    python -m jobs.relatorio_semanal
    """
    
    async def main():
        logger.info("🚀 Executando job de relatório semanal...")
        resultado = await gerar_relatorio_semanal()
        logger.info(f"✅ Job concluído: {resultado}")
    
    asyncio.run(main())
