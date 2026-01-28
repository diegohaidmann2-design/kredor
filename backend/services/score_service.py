"""
Serviço de Cálculo de Score e Classificação de Clientes
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from config import db


class ScoreService:
    """
    Serviço responsável por calcular o score de crédito dos clientes
    baseado em histórico de pagamentos e comportamento financeiro.
    """
    
    # Pesos dos componentes (total = 100%)
    PESO_PONTUALIDADE = 35
    PESO_ATRASOS = 25
    PESO_VALOR_PAGO = 20
    PESO_TEMPO_RELACIONAMENTO = 10
    PESO_HISTORICO_RECENTE = 10
    
    # Classificações
    CLASSIFICACOES = {
        'A': {'min': 85, 'max': 100, 'label': 'Excelente', 'cor': 'green'},
        'B': {'min': 70, 'max': 84, 'label': 'Bom', 'cor': 'blue'},
        'C': {'min': 50, 'max': 69, 'label': 'Regular', 'cor': 'yellow'},
        'D': {'min': 30, 'max': 49, 'label': 'Risco', 'cor': 'orange'},
        'E': {'min': 0, 'max': 29, 'label': 'Alto Risco', 'cor': 'red'}
    }
    
    @staticmethod
    async def calcular_score_cliente(cliente_id: str, usuario_id: str) -> Dict:
        """
        Calcula o score completo de um cliente
        
        Args:
            cliente_id: ID do cliente
            usuario_id: ID do usuário (isolamento multi-tenant)
        
        Returns:
            Dict com score, classificação e detalhes dos componentes
        """
        # Buscar dados do cliente
        cliente = await db.clientes.find_one({
            "id": cliente_id,
            "usuario_id": usuario_id
        })
        
        if not cliente:
            return None
        
        # Buscar todos os empréstimos do cliente
        emprestimos = await db.emprestimos.find({
            "cliente_id": cliente_id,
            "usuario_id": usuario_id
        }).to_list(1000)
        
        if not emprestimos:
            # Cliente novo sem histórico
            return ScoreService._score_cliente_novo(cliente)
        
        # Buscar todas as parcelas
        emprestimo_ids = [e["id"] for e in emprestimos]
        parcelas = await db.parcelas.find({
            "emprestimo_id": {"$in": emprestimo_ids},
            "usuario_id": usuario_id
        }).to_list(10000)
        
        # Buscar todos os pagamentos
        parcela_ids = [p["id"] for p in parcelas]
        pagamentos = await db.pagamentos.find({
            "parcela_id": {"$in": parcela_ids},
            "usuario_id": usuario_id
        }).to_list(10000)
        
        # Calcular cada componente
        pontos_pontualidade = ScoreService._calcular_pontualidade(parcelas)
        pontos_atrasos = ScoreService._calcular_penalidade_atrasos(parcelas)
        pontos_valor = ScoreService._calcular_valor_pago(emprestimos, pagamentos)
        pontos_tempo = ScoreService._calcular_tempo_relacionamento(emprestimos)
        pontos_recente = ScoreService._calcular_historico_recente(parcelas)
        
        # Verificar bônus por empréstimo ativo em dia
        bonus = ScoreService._verificar_bonus_ativo_em_dia(emprestimos, parcelas)
        
        # Score final
        score_final = (
            pontos_pontualidade +
            pontos_atrasos +
            pontos_valor +
            pontos_tempo +
            pontos_recente +
            bonus
        )
        
        # Limitar entre 0 e 100
        score_final = max(0, min(100, round(score_final, 1)))
        
        # Determinar classificação
        classificacao = ScoreService._determinar_classificacao(
            score_final, 
            emprestimos, 
            parcelas
        )
        
        # Métricas adicionais
        metricas = ScoreService._calcular_metricas(emprestimos, parcelas, pagamentos)
        
        return {
            "cliente_id": cliente_id,
            "score": score_final,
            "classificacao": classificacao,
            "componentes": {
                "pontualidade": {
                    "pontos": pontos_pontualidade,
                    "maximo": ScoreService.PESO_PONTUALIDADE,
                    "percentual": round((pontos_pontualidade / ScoreService.PESO_PONTUALIDADE) * 100, 1)
                },
                "atrasos": {
                    "pontos": pontos_atrasos,
                    "maximo": ScoreService.PESO_ATRASOS,
                    "percentual": round((pontos_atrasos / ScoreService.PESO_ATRASOS) * 100, 1)
                },
                "valor_pago": {
                    "pontos": pontos_valor,
                    "maximo": ScoreService.PESO_VALOR_PAGO,
                    "percentual": round((pontos_valor / ScoreService.PESO_VALOR_PAGO) * 100, 1)
                },
                "tempo_relacionamento": {
                    "pontos": pontos_tempo,
                    "maximo": ScoreService.PESO_TEMPO_RELACIONAMENTO,
                    "percentual": round((pontos_tempo / ScoreService.PESO_TEMPO_RELACIONAMENTO) * 100, 1)
                },
                "historico_recente": {
                    "pontos": pontos_recente,
                    "maximo": ScoreService.PESO_HISTORICO_RECENTE,
                    "percentual": round((pontos_recente / ScoreService.PESO_HISTORICO_RECENTE) * 100, 1)
                }
            },
            "metricas": metricas,
            "bonus": bonus,
            "calculado_em": datetime.now(timezone.utc).isoformat()
        }
    
    @staticmethod
    def _score_cliente_novo(cliente: Dict) -> Dict:
        """Score padrão para cliente sem histórico"""
        return {
            "cliente_id": cliente["id"],
            "score": 60.0,
            "classificacao": "C",
            "componentes": {
                "pontualidade": {"pontos": 0, "maximo": 35, "percentual": 0},
                "atrasos": {"pontos": 0, "maximo": 25, "percentual": 0},
                "valor_pago": {"pontos": 0, "maximo": 20, "percentual": 0},
                "tempo_relacionamento": {"pontos": 0, "maximo": 10, "percentual": 0},
                "historico_recente": {"pontos": 0, "maximo": 10, "percentual": 0}
            },
            "metricas": {
                "total_emprestimos": 0,
                "emprestimos_quitados": 0,
                "parcelas_pagas": 0,
                "parcelas_totais": 0,
                "taxa_pontualidade": 0,
                "media_dias_atraso": 0
            },
            "bonus": 0,
            "cliente_novo": True,
            "calculado_em": datetime.now(timezone.utc).isoformat()
        }
    
    @staticmethod
    def _calcular_pontualidade(parcelas: List[Dict]) -> float:
        """Calcula pontos baseado em parcelas pagas em dia"""
        parcelas_pagas = [p for p in parcelas if p.get("status") == "pago"]
        
        if not parcelas_pagas:
            return 0
        
        # Parcelas pagas sem atraso (dias_atraso = 0 ou não informado)
        parcelas_em_dia = [p for p in parcelas_pagas if p.get("dias_atraso", 0) == 0]
        
        taxa = (len(parcelas_em_dia) / len(parcelas_pagas)) * 100
        pontos = (taxa / 100) * ScoreService.PESO_PONTUALIDADE
        
        return round(pontos, 1)
    
    @staticmethod
    def _calcular_penalidade_atrasos(parcelas: List[Dict]) -> float:
        """Calcula penalidade por atrasos"""
        pontos_base = ScoreService.PESO_ATRASOS
        penalidades = 0
        
        for parcela in parcelas:
            dias_atraso = parcela.get("dias_atraso", 0)
            
            if dias_atraso > 0:
                if dias_atraso <= 7:
                    penalidades += 0.5
                elif dias_atraso <= 30:
                    penalidades += 1
                elif dias_atraso <= 60:
                    penalidades += 2
                else:
                    penalidades += 3
        
        pontos_final = max(0, pontos_base - penalidades)
        return round(pontos_final, 1)
    
    @staticmethod
    def _calcular_valor_pago(emprestimos: List[Dict], pagamentos: List[Dict]) -> float:
        """Calcula pontos baseado em valor pago vs devido"""
        total_devido = sum(e.get("valor_total_com_juros", 0) for e in emprestimos)
        total_pago = sum(p.get("valor_pago", 0) for p in pagamentos)
        
        if total_devido == 0:
            return ScoreService.PESO_VALOR_PAGO
        
        taxa = (total_pago / total_devido) * 100
        pontos = (taxa / 100) * ScoreService.PESO_VALOR_PAGO
        
        return round(min(pontos, ScoreService.PESO_VALOR_PAGO), 1)
    
    @staticmethod
    def _calcular_tempo_relacionamento(emprestimos: List[Dict]) -> float:
        """Calcula pontos por tempo de relacionamento"""
        if not emprestimos:
            return 0
        
        # Primeiro empréstimo
        datas = [datetime.fromisoformat(e["created_at"]) for e in emprestimos]
        primeiro_emprestimo = min(datas)
        
        meses = (datetime.now(timezone.utc) - primeiro_emprestimo).days / 30
        
        if meses < 3:
            return 3
        elif meses < 6:
            return 5
        elif meses < 12:
            return 7
        else:
            return 10
    
    @staticmethod
    def _calcular_historico_recente(parcelas: List[Dict]) -> float:
        """Calcula pontos baseado nos últimos 3 meses"""
        data_limite = datetime.now(timezone.utc) - timedelta(days=90)
        
        parcelas_recentes = [
            p for p in parcelas 
            if datetime.fromisoformat(p["created_at"]) > data_limite
        ]
        
        if not parcelas_recentes:
            return 5  # Neutro
        
        parcelas_pagas_recentes = [
            p for p in parcelas_recentes 
            if p.get("status") == "pago" and p.get("dias_atraso", 0) == 0
        ]
        
        taxa = (len(parcelas_pagas_recentes) / len(parcelas_recentes)) * 100
        pontos = (taxa / 100) * ScoreService.PESO_HISTORICO_RECENTE
        
        return round(pontos, 1)
    
    @staticmethod
    def _verificar_bonus_ativo_em_dia(emprestimos: List[Dict], parcelas: List[Dict]) -> float:
        """Bônus de 5 pontos se tem empréstimo ativo sem atraso"""
        emprestimos_ativos = [e for e in emprestimos if e.get("status") == "ativo"]
        
        if not emprestimos_ativos:
            return 0
        
        # Verificar se há alguma parcela atrasada nos empréstimos ativos
        ids_ativos = [e["id"] for e in emprestimos_ativos]
        parcelas_ativas = [p for p in parcelas if p["emprestimo_id"] in ids_ativos]
        
        tem_atraso = any(p.get("status") == "atrasado" for p in parcelas_ativas)
        
        return 0 if tem_atraso else 5
    
    @staticmethod
    def _determinar_classificacao(score: float, emprestimos: List[Dict], parcelas: List[Dict]) -> str:
        """Determina a classificação baseada no score e regras especiais"""
        # Regra especial: inadimplência ativa = Alto Risco
        tem_inadimplencia = any(e.get("status") == "inadimplente" for e in emprestimos)
        if tem_inadimplencia:
            return "E"
        
        # Classificação por score
        for classe, config in ScoreService.CLASSIFICACOES.items():
            if config['min'] <= score <= config['max']:
                return classe
        
        return "E"
    
    @staticmethod
    def _calcular_metricas(emprestimos: List[Dict], parcelas: List[Dict], pagamentos: List[Dict]) -> Dict:
        """Calcula métricas adicionais"""
        total_emprestimos = len(emprestimos)
        emprestimos_quitados = len([e for e in emprestimos if e.get("status") == "quitado"])
        parcelas_pagas = len([p for p in parcelas if p.get("status") == "pago"])
        parcelas_totais = len(parcelas)
        
        # Taxa de pontualidade
        if parcelas_pagas > 0:
            parcelas_em_dia = len([p for p in parcelas if p.get("status") == "pago" and p.get("dias_atraso", 0) == 0])
            taxa_pontualidade = round((parcelas_em_dia / parcelas_pagas) * 100, 1)
        else:
            taxa_pontualidade = 0
        
        # Média de dias de atraso
        parcelas_com_atraso = [p for p in parcelas if p.get("dias_atraso", 0) > 0]
        if parcelas_com_atraso:
            media_atraso = sum(p.get("dias_atraso", 0) for p in parcelas_com_atraso) / len(parcelas_com_atraso)
        else:
            media_atraso = 0
        
        # Totais financeiros
        total_devido = sum(e.get("valor_total_com_juros", 0) for e in emprestimos)
        total_pago = sum(p.get("valor_pago", 0) for p in pagamentos)
        
        return {
            "total_emprestimos": total_emprestimos,
            "emprestimos_quitados": emprestimos_quitados,
            "parcelas_pagas": parcelas_pagas,
            "parcelas_totais": parcelas_totais,
            "taxa_pontualidade": taxa_pontualidade,
            "media_dias_atraso": round(media_atraso, 1),
            "total_devido": total_devido,
            "total_pago": total_pago
        }
    
    @staticmethod
    async def salvar_historico_score(score_data: Dict, usuario_id: str):
        """Salva o histórico do score no banco"""
        doc = {
            **score_data,
            "usuario_id": usuario_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.scores_historico.insert_one(doc)
    
    @staticmethod
    async def atualizar_score_cliente(cliente_id: str, usuario_id: str) -> Dict:
        """Calcula e atualiza o score no registro do cliente"""
        score_data = await ScoreService.calcular_score_cliente(cliente_id, usuario_id)
        
        if not score_data:
            return None
        
        # Atualizar cliente
        await db.clientes.update_one(
            {"id": cliente_id, "usuario_id": usuario_id},
            {
                "$set": {
                    "score_atual": score_data["score"],
                    "classificacao": score_data["classificacao"],
                    "ultima_atualizacao_score": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        # Salvar histórico
        await ScoreService.salvar_historico_score(score_data, usuario_id)
        
        return score_data
