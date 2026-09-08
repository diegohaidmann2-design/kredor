"""
Serviço de Anti-Spam para WhatsApp
Implementa rate limiting, warming up, e melhores práticas de 2026
"""

import asyncio
import random
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.whatsapp_anti_spam import TIERS_WHATSAPP, WARMING_UP_LIMITS


class WhatsAppAntiSpamService:
    """Gerencia anti-spam e rate limiting para WhatsApp"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def get_config(self, usuario_id: str) -> Dict[str, Any]:
        """Busca ou cria configuração anti-spam do usuário"""
        config = await self.db.configuracoes.find_one({
            "tipo": "whatsapp_anti_spam",
            "usuario_id": usuario_id
        })
        
        if not config:
            # Criar configuração padrão
            config = {
                "tipo": "whatsapp_anti_spam",
                "usuario_id": usuario_id,
                "tier_atual": 1,
                "limite_diario": 1000,
                "limite_por_hora": 100,
                "limite_por_minuto": 20,
                "delay_minimo": 30,
                "delay_maximo": 90,
                "delay_entre_lotes": 300,
                "tamanho_lote": 50,
                "warming_up_ativo": False,
                "warming_up_dia": 0,
                "warming_up_inicio": None,
                "horario_inicio": "08:00",
                "horario_fim": "20:00",
                "enviar_fora_horario": False,
                "dias_permitidos": [1, 2, 3, 4, 5],
                "max_mensagens_identicas": 0,
                "exigir_variacao_template": True,
                "contador_hoje": 0,
                "contador_hora": 0,
                "contador_minuto": 0,
                "ultima_mensagem": None,
                "ultima_reset_dia": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "total_enviadas": 0,
                "total_bloqueios": 0,
                "total_opt_outs": 0,
                "taxa_qualidade": 100.0,
                "fila_ativa": True,
                "processar_fila_automatico": True,
                "status": "ativo",
                "razao_bloqueio": None,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await self.db.configuracoes.insert_one(config)
        
        return config
    
    async def pode_enviar(self, usuario_id: str) -> Dict[str, Any]:
        """
        Verifica se pode enviar mensagem agora
        Retorna: {
            "pode_enviar": bool,
            "razao": str,
            "proximo_disponivel": datetime (opcional),
            "delay_recomendado": int (segundos)
        }
        """
        config = await self.get_config(usuario_id)
        agora = datetime.now(timezone.utc)
        
        # 1. Verificar se está bloqueado
        if config.get("status") == "bloqueado":
            return {
                "pode_enviar": False,
                "razao": f"Conta bloqueada: {config.get('razao_bloqueio')}",
                "proximo_disponivel": None,
                "delay_recomendado": 0
            }
        
        # 2. Verificar se está pausado
        if config.get("status") == "pausado":
            return {
                "pode_enviar": False,
                "razao": "Sistema pausado manualmente",
                "proximo_disponivel": None,
                "delay_recomendado": 0
            }
        
        # 3. Reset de contadores se mudou o dia
        await self._reset_contadores_se_necessario(usuario_id, config, agora)
        
        # 4. Verificar warming up
        if config.get("warming_up_ativo"):
            limite_warming = self._get_limite_warming_up(config.get("warming_up_dia", 0))
            if config.get("contador_hoje", 0) >= limite_warming:
                return {
                    "pode_enviar": False,
                    "razao": f"Limite de warming up atingido ({limite_warming}/dia). Dia {config.get('warming_up_dia')}",
                    "proximo_disponivel": self._get_proximo_reset_diario(),
                    "delay_recomendado": 0
                }
        
        # 5. Verificar limite diário
        limite_diario = config.get("limite_diario", 1000)
        if config.get("contador_hoje", 0) >= limite_diario:
            return {
                "pode_enviar": False,
                "razao": f"Limite diário atingido ({limite_diario} mensagens)",
                "proximo_disponivel": self._get_proximo_reset_diario(),
                "delay_recomendado": 0
            }
        
        # 6. Verificar limite por hora
        if config.get("contador_hora", 0) >= config.get("limite_por_hora", 100):
            return {
                "pode_enviar": False,
                "razao": f"Limite por hora atingido ({config.get('limite_por_hora')} msgs/hora)",
                "proximo_disponivel": self._get_proximo_reset_hora(),
                "delay_recomendado": 60
            }
        
        # 7. Verificar limite por minuto
        if config.get("contador_minuto", 0) >= config.get("limite_por_minuto", 20):
            return {
                "pode_enviar": False,
                "razao": f"Limite por minuto atingido ({config.get('limite_por_minuto')} msgs/min)",
                "proximo_disponivel": self._get_proximo_reset_minuto(),
                "delay_recomendado": 10
            }
        
        # 8. Verificar horário comercial (avaliado no fuso local do usuário)
        agora_local = self._agora_local(config, agora)
        if not config.get("enviar_fora_horario", False):
            if not self._esta_em_horario_comercial(config, agora_local):
                return {
                    "pode_enviar": False,
                    "razao": f"Fora do horário comercial ({config.get('horario_inicio')}-{config.get('horario_fim')})",
                    "proximo_disponivel": self._get_proximo_horario_comercial(config),
                    "delay_recomendado": 0
                }
        
        # 9. Verificar dia da semana
        dia_semana = agora_local.weekday()  # 0=Segunda
        if dia_semana not in config.get("dias_permitidos", [1,2,3,4,5]):
            return {
                "pode_enviar": False,
                "razao": f"Dia da semana não permitido (hoje: {dia_semana})",
                "proximo_disponivel": self._get_proximo_dia_permitido(config),
                "delay_recomendado": 0
            }
        
        # 10. Verificar delay mínimo desde última mensagem
        ultima_msg = config.get("ultima_mensagem")
        if ultima_msg:
            ultima_dt = datetime.fromisoformat(ultima_msg.replace('Z', '+00:00'))
            tempo_decorrido = (agora - ultima_dt).total_seconds()
            delay_minimo = config.get("delay_minimo", 30)
            
            if tempo_decorrido < delay_minimo:
                tempo_espera = int(delay_minimo - tempo_decorrido)
                return {
                    "pode_enviar": False,
                    "razao": f"Aguardando delay mínimo ({delay_minimo}s)",
                    "proximo_disponivel": ultima_dt + timedelta(seconds=delay_minimo),
                    "delay_recomendado": tempo_espera
                }
        
        # ✅ PODE ENVIAR!
        delay_recomendado = random.randint(
            config.get("delay_minimo", 30),
            config.get("delay_maximo", 90)
        )
        
        return {
            "pode_enviar": True,
            "razao": "OK",
            "proximo_disponivel": None,
            "delay_recomendado": delay_recomendado
        }
    
    async def registrar_envio(self, usuario_id: str, sucesso: bool = True, bloqueado: bool = False):
        """Registra envio de mensagem e atualiza contadores"""
        config = await self.get_config(usuario_id)
        agora = datetime.now(timezone.utc)
        
        updates = {
            "ultima_mensagem": agora.isoformat(),
            "contador_hoje": config.get("contador_hoje", 0) + 1,
            "contador_hora": config.get("contador_hora", 0) + 1,
            "contador_minuto": config.get("contador_minuto", 0) + 1,
            "total_enviadas": config.get("total_enviadas", 0) + 1
        }
        
        if bloqueado:
            updates["total_bloqueios"] = config.get("total_bloqueios", 0) + 1
            # Recalcular taxa de qualidade
            total = config.get("total_enviadas", 0) + 1
            bloqueios = updates["total_bloqueios"]
            taxa = ((total - bloqueios) / total) * 100 if total > 0 else 100
            updates["taxa_qualidade"] = round(taxa, 2)
            
            # Se taxa de qualidade cair muito, pausar
            if taxa < 70:
                updates["status"] = "pausado"
                updates["razao_bloqueio"] = f"Taxa de qualidade baixa ({taxa:.1f}%). Revise suas mensagens."
        
        await self.db.configuracoes.update_one(
            {"tipo": "whatsapp_anti_spam", "usuario_id": usuario_id},
            {"$set": updates}
        )
    
    async def registrar_opt_out(self, usuario_id: str):
        """Registra opt-out (cliente pediu para parar)"""
        config = await self.get_config(usuario_id)
        
        total_opt_outs = config.get("total_opt_outs", 0) + 1
        total = config.get("total_enviadas", 0)
        
        # Recalcular taxa de qualidade
        problemas = config.get("total_bloqueios", 0) + total_opt_outs
        taxa = ((total - problemas) / total) * 100 if total > 0 else 100
        
        await self.db.configuracoes.update_one(
            {"tipo": "whatsapp_anti_spam", "usuario_id": usuario_id},
            {"$set": {
                "total_opt_outs": total_opt_outs,
                "taxa_qualidade": round(taxa, 2)
            }}
        )
    
    async def ativar_warming_up(self, usuario_id: str):
        """Ativa modo warming up (aquecimento gradual)"""
        await self.db.configuracoes.update_one(
            {"tipo": "whatsapp_anti_spam", "usuario_id": usuario_id},
            {"$set": {
                "warming_up_ativo": True,
                "warming_up_dia": 1,
                "warming_up_inicio": datetime.now(timezone.utc).isoformat(),
                "contador_hoje": 0
            }}
        )
    
    async def desativar_warming_up(self, usuario_id: str):
        """Desativa modo warming up"""
        await self.db.configuracoes.update_one(
            {"tipo": "whatsapp_anti_spam", "usuario_id": usuario_id},
            {"$set": {
                "warming_up_ativo": False
            }}
        )
    
    async def atualizar_tier(self, usuario_id: str, novo_tier: int):
        """Atualiza tier do usuário"""
        if novo_tier not in TIERS_WHATSAPP:
            raise ValueError(f"Tier inválido: {novo_tier}")
        
        tier_config = TIERS_WHATSAPP[novo_tier]
        
        await self.db.configuracoes.update_one(
            {"tipo": "whatsapp_anti_spam", "usuario_id": usuario_id},
            {"$set": {
                "tier_atual": novo_tier,
                "limite_diario": tier_config.limite_diario,
                "limite_por_minuto": tier_config.limite_por_segundo
            }}
        )
    
    # Métodos auxiliares privados
    
    async def _reset_contadores_se_necessario(self, usuario_id: str, config: dict, agora: datetime):
        """Reset contadores de dia/hora/minuto se necessário"""
        updates = {}
        
        # Reset diário
        ultimo_reset = config.get("ultima_reset_dia")
        if ultimo_reset:
            ultimo_reset_dt = datetime.fromisoformat(ultimo_reset + "T00:00:00+00:00")
            if agora.date() > ultimo_reset_dt.date():
                updates["contador_hoje"] = 0
                updates["ultima_reset_dia"] = agora.strftime("%Y-%m-%d")
                
                # Avançar dia de warming up se ativo
                if config.get("warming_up_ativo"):
                    warming_inicio = config.get("warming_up_inicio")
                    if warming_inicio:
                        inicio_dt = datetime.fromisoformat(warming_inicio.replace('Z', '+00:00'))
                        dias_passados = (agora - inicio_dt).days + 1
                        updates["warming_up_dia"] = min(dias_passados, 15)
        
        # Reset horário (simplificado - reseta a cada hora cheia)
        ultima_msg = config.get("ultima_mensagem")
        if ultima_msg:
            ultima_dt = datetime.fromisoformat(ultima_msg.replace('Z', '+00:00'))
            if agora.hour != ultima_dt.hour:
                updates["contador_hora"] = 0
        
        # Reset minuto
        if ultima_msg:
            ultima_dt = datetime.fromisoformat(ultima_msg.replace('Z', '+00:00'))
            if agora.minute != ultima_dt.minute:
                updates["contador_minuto"] = 0
        
        if updates:
            await self.db.configuracoes.update_one(
                {"tipo": "whatsapp_anti_spam", "usuario_id": usuario_id},
                {"$set": updates}
            )
    
    def _get_limite_warming_up(self, dia: int) -> int:
        """Retorna limite diário baseado no dia de warming up"""
        if dia <= 2:
            return WARMING_UP_LIMITS[1]["diario"]
        elif dia <= 4:
            return WARMING_UP_LIMITS[2]["diario"]
        elif dia <= 6:
            return WARMING_UP_LIMITS[3]["diario"]
        elif dia <= 9:
            return WARMING_UP_LIMITS[4]["diario"]
        elif dia <= 12:
            return WARMING_UP_LIMITS[5]["diario"]
        elif dia <= 14:
            return WARMING_UP_LIMITS[6]["diario"]
        else:
            return WARMING_UP_LIMITS[7]["diario"]
    
    def _agora_local(self, config: dict, agora: datetime = None) -> datetime:
        """Converte o horário atual (UTC) para o fuso local do usuário.

        Padrão: America/Sao_Paulo. Usado para avaliar horário comercial e
        dia da semana no fuso correto (o app é brasileiro).
        """
        agora = agora or datetime.now(timezone.utc)
        tz_nome = config.get("timezone") or "America/Sao_Paulo"
        try:
            return agora.astimezone(ZoneInfo(tz_nome))
        except Exception:
            return agora.astimezone(ZoneInfo("America/Sao_Paulo"))

    def _esta_em_horario_comercial(self, config: dict, agora: datetime) -> bool:
        """Verifica se está dentro do horário comercial"""
        hora_inicio = config.get("horario_inicio", "08:00")
        hora_fim = config.get("horario_fim", "20:00")
        
        hora_atual = agora.strftime("%H:%M")
        return hora_inicio <= hora_atual <= hora_fim
    
    def _get_proximo_reset_diario(self) -> datetime:
        """Retorna próximo reset diário (meia-noite)"""
        agora = datetime.now(timezone.utc)
        amanha = agora + timedelta(days=1)
        return datetime(amanha.year, amanha.month, amanha.day, 0, 0, 0, tzinfo=timezone.utc)
    
    def _get_proximo_reset_hora(self) -> datetime:
        """Retorna próximo reset de hora"""
        agora = datetime.now(timezone.utc)
        proxima_hora = agora.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        return proxima_hora
    
    def _get_proximo_reset_minuto(self) -> datetime:
        """Retorna próximo reset de minuto"""
        agora = datetime.now(timezone.utc)
        proximo_minuto = agora.replace(second=0, microsecond=0) + timedelta(minutes=1)
        return proximo_minuto
    
    def _get_proximo_horario_comercial(self, config: dict) -> datetime:
        """Retorna próximo horário comercial"""
        agora = datetime.now(timezone.utc)
        hora_inicio = config.get("horario_inicio", "08:00")
        hora, minuto = map(int, hora_inicio.split(":"))
        
        proximo = agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
        if proximo <= agora:
            proximo += timedelta(days=1)
        
        return proximo
    
    def _get_proximo_dia_permitido(self, config: dict) -> datetime:
        """Retorna próximo dia da semana permitido"""
        agora = datetime.now(timezone.utc)
        dias_permitidos = config.get("dias_permitidos", [1,2,3,4,5])
        
        for i in range(1, 8):
            proximo = agora + timedelta(days=i)
            if proximo.weekday() in dias_permitidos:
                return proximo.replace(hour=8, minute=0, second=0, microsecond=0)
        
        return agora + timedelta(days=1)
