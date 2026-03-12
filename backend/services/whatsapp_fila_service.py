"""
Sistema de Fila de Mensagens WhatsApp
Processa mensagens gradualmente respeitando rate limits
"""

import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase

from services.whatsapp_anti_spam_service import WhatsAppAntiSpamService
from services.whatsapp_service import enviar_mensagem_whatsapp


class WhatsAppFilaService:
    """Gerencia fila de mensagens WhatsApp"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.anti_spam = WhatsAppAntiSpamService(db)
    
    async def adicionar_na_fila(
        self,
        usuario_id: str,
        numero_destino: str,
        mensagem: str,
        cliente_id: Optional[str] = None,
        emprestimo_id: Optional[str] = None,
        parcela_id: Optional[str] = None,
        tipo: str = "cobranca",
        prioridade: int = 5
    ) -> str:
        """
        Adiciona mensagem na fila
        Prioridade: 1 (maior) a 10 (menor)
        """
        fila_item = {
            "usuario_id": usuario_id,
            "numero_destino": numero_destino,
            "mensagem": mensagem,
            "cliente_id": cliente_id,
            "emprestimo_id": emprestimo_id,
            "parcela_id": parcela_id,
            "tipo": tipo,
            "prioridade": prioridade,
            "status": "pendente",
            "tentativas": 0,
            "max_tentativas": 3,
            "erro": None,
            "message_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "scheduled_at": None,
            "processed_at": None
        }
        
        result = await self.db.whatsapp_fila.insert_one(fila_item)
        return str(result.inserted_id)
    
    async def processar_fila(self, usuario_id: str, limite: int = 100) -> Dict[str, Any]:
        """
        Processa fila de mensagens de um usuário
        Retorna estatísticas do processamento
        """
        stats = {
            "processadas": 0,
            "sucesso": 0,
            "erro": 0,
            "aguardando": 0,
            "tempo_total": 0
        }
        
        inicio = datetime.now(timezone.utc)
        
        # Buscar mensagens pendentes ordenadas por prioridade
        mensagens = await self.db.whatsapp_fila.find({
            "usuario_id": usuario_id,
            "status": "pendente"
        }).sort([("prioridade", 1), ("created_at", 1)]).limit(limite).to_list(limite)
        
        for msg in mensagens:
            # Verificar se pode enviar
            pode = await self.anti_spam.pode_enviar(usuario_id)
            
            if not pode["pode_enviar"]:
                # Não pode enviar agora
                stats["aguardando"] += 1
                
                # Se tem próximo disponível, agendar
                if pode.get("proximo_disponivel"):
                    await self.db.whatsapp_fila.update_one(
                        {"_id": msg["_id"]},
                        {"$set": {
                            "scheduled_at": pode["proximo_disponivel"].isoformat(),
                            "status": "agendado",
                            "razao_agendamento": pode["razao"]
                        }}
                    )
                
                # Se tem delay recomendado, esperar
                if pode.get("delay_recomendado", 0) > 0:
                    await asyncio.sleep(pode["delay_recomendado"])
                    continue
                else:
                    # Parar processamento se não pode enviar
                    break
            
            # Tentar enviar
            try:
                resultado = await enviar_mensagem_whatsapp(
                    usuario_id=usuario_id,
                    numero_destino=msg["numero_destino"],
                    mensagem=msg["mensagem"]
                )
                
                if resultado.get("success"):
                    # Sucesso!
                    await self.db.whatsapp_fila.update_one(
                        {"_id": msg["_id"]},
                        {"$set": {
                            "status": "enviado",
                            "processed_at": datetime.now(timezone.utc).isoformat(),
                            "message_id": resultado.get("message_id")
                        }}
                    )
                    
                    await self.anti_spam.registrar_envio(usuario_id, sucesso=True)
                    stats["sucesso"] += 1
                    
                else:
                    # Falha
                    raise Exception(resultado.get("message", "Erro desconhecido"))
                
            except Exception as e:
                # Erro ao enviar
                tentativas = msg.get("tentativas", 0) + 1
                max_tentativas = msg.get("max_tentativas", 3)
                
                if tentativas >= max_tentativas:
                    # Atingiu máximo de tentativas
                    await self.db.whatsapp_fila.update_one(
                        {"_id": msg["_id"]},
                        {"$set": {
                            "status": "falhou",
                            "tentativas": tentativas,
                            "erro": str(e),
                            "processed_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                else:
                    # Tentar novamente depois
                    await self.db.whatsapp_fila.update_one(
                        {"_id": msg["_id"]},
                        {"$set": {
                            "tentativas": tentativas,
                            "erro": str(e),
                            "status": "aguardando_retry"
                        }}
                    )
                
                stats["erro"] += 1
            
            stats["processadas"] += 1
            
            # Aguardar delay recomendado
            delay = pode.get("delay_recomendado", 30)
            await asyncio.sleep(delay)
        
        fim = datetime.now(timezone.utc)
        stats["tempo_total"] = (fim - inicio).total_seconds()
        
        return stats
    
    async def limpar_fila_antiga(self, dias: int = 7):
        """Remove itens processados há mais de X dias"""
        data_limite = datetime.now(timezone.utc) - timedelta(days=dias)
        
        result = await self.db.whatsapp_fila.delete_many({
            "status": {"$in": ["enviado", "falhou"]},
            "processed_at": {"$lt": data_limite.isoformat()}
        })
        
        return result.deleted_count
    
    async def obter_estatisticas_fila(self, usuario_id: str) -> Dict[str, Any]:
        """Retorna estatísticas da fila do usuário"""
        pipeline = [
            {"$match": {"usuario_id": usuario_id}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        
        resultado = await self.db.whatsapp_fila.aggregate(pipeline).to_list(100)
        
        stats = {
            "pendente": 0,
            "agendado": 0,
            "enviado": 0,
            "falhou": 0,
            "aguardando_retry": 0,
            "total": 0
        }
        
        for item in resultado:
            status = item["_id"]
            count = item["count"]
            if status in stats:
                stats[status] = count
            stats["total"] += count
        
        return stats
    
    async def cancelar_mensagem(self, fila_id: str, usuario_id: str):
        """Cancela uma mensagem na fila"""
        result = await self.db.whatsapp_fila.update_one(
            {"_id": fila_id, "usuario_id": usuario_id, "status": {"$in": ["pendente", "agendado"]}},
            {"$set": {
                "status": "cancelado",
                "processed_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return result.modified_count > 0
    
    async def reprocessar_falhadas(self, usuario_id: str):
        """Recoloca mensagens falhadas na fila"""
        result = await self.db.whatsapp_fila.update_many(
            {"usuario_id": usuario_id, "status": "falhou"},
            {"$set": {
                "status": "pendente",
                "tentativas": 0,
                "erro": None
            }}
        )
        
        return result.modified_count
