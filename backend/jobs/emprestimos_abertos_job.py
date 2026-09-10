"""
Job para gerar parcelas automaticamente para empréstimos sem prazo
Executa diariamente às 00:10
"""
from services.logging_service import get_logger
logger = get_logger("gestorcred.emprestimos_abertos_job")

from datetime import datetime, timezone
from config import db
from services.calculos import calcular_data_vencimento
from services.parcela_service import inserir_parcela_juros_aberto
from utils.dinheiro import formatar_reais, arredondar_centavos


async def job_gerar_parcelas_emprestimos_abertos():
    """
    Gera próxima(s) parcela(s) para empréstimos sem prazo (abertos)
    
    REGRAS:
    1. Ao criar empréstimo: gera primeira parcela (já feito no endpoint)
    2. Parcela paga: gera próxima parcela imediatamente
    3. Parcela vencida e não paga: marcar atrasada + gerar próximas parcelas até cobrir hoje + 1 período
    4. Empréstimo quitado: NÃO gera mais parcelas
    """
    logger.info("=" * 80)
    logger.info(f"🔄 [Job] Gerar Parcelas Empréstimos Abertos - {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 80)
    
    try:
        hoje = datetime.now(timezone.utc)
        
        # Buscar empréstimos sem prazo ainda em aberto.
        # IMPORTANTE: inclui "inadimplente". Um empréstimo aberto (apenas juros)
        # atrasado continua gerando parcelas de juros semanalmente. Só empréstimos
        # "quitado"/"cancelado" param de gerar parcelas.
        emprestimos_abertos = await db.emprestimos.find({
            "sem_prazo": True,
            "status": {"$in": ["ativo", "inadimplente"]},
            "deleted": {"$ne": True}
        }, {"_id": 0}).to_list(1000)
        
        if not emprestimos_abertos:
            logger.info("   ℹ️ Nenhum empréstimo aberto encontrado")
            return
        
        logger.info(f"   📋 Encontrados {len(emprestimos_abertos)} empréstimo(s) aberto(s)")
        
        parcelas_geradas = 0
        
        for emprestimo in emprestimos_abertos:
            emprestimo_id = emprestimo.get("id")
            data_inicio_raw = emprestimo.get("data_inicio")
            if not emprestimo_id or not data_inicio_raw:
                logger.warning(f"   ⚠️ Empréstimo ignorado (id/data_inicio ausente): {emprestimo.get('id')}")
                continue
            periodicidade = emprestimo.get("periodicidade", "mensal")
            try:
                data_inicio = datetime.fromisoformat(data_inicio_raw)
            except (ValueError, TypeError) as e:
                logger.warning(f"   ⚠️ Empréstimo {emprestimo_id[:8]}... com data_inicio inválida ({data_inicio_raw}): {e}")
                continue

            # Marcar parcelas vencidas como atrasadas
            await db.parcelas.update_many(
                {
                    "emprestimo_id": emprestimo_id,
                    "status": "pendente",
                    "data_vencimento": {"$lt": hoje.isoformat()}
                },
                {"$set": {"status": "atrasado", "updated_at": hoje.isoformat()}}
            )
            
            # Buscar última parcela gerada (mesmo que excluída, para saber o próximo número)
            ultima_parcela = await db.parcelas.find_one(
                {"emprestimo_id": emprestimo_id},
                {"_id": 0},
                sort=[("numero_parcela", -1)]
            )
            
            if not ultima_parcela:
                # Se não há nenhuma parcela, começamos do 1
                proximo_numero = 1
            else:
                proximo_numero = ultima_parcela["numero_parcela"] + 1
            max_iteracoes = 100  # Segurança contra loop infinito
            
            for _ in range(max_iteracoes):
                data_vencimento_nova = calcular_data_vencimento(
                    data_inicio,
                    proximo_numero,
                    emprestimo.get("dia_vencimento"),
                    periodicidade
                )
                
                # Parar se a próxima parcela vence DEPOIS de hoje + 1 período
                # (queremos ter sempre 1 parcela futura pendente)
                if data_vencimento_nova > hoje:
                    # Verificar se já existe uma parcela futura pendente
                    parcela_futura = await db.parcelas.find_one({
                        "emprestimo_id": emprestimo_id,
                        "status": "pendente",
                        "data_vencimento": {"$gt": hoje.isoformat()}
                    })
                    if parcela_futura:
                        break  # Já tem parcela futura, não precisa gerar mais
                
                # Verificar se parcela já existe (não-deletada)
                parcela_existente = await db.parcelas.find_one({
                    "emprestimo_id": emprestimo_id,
                    "numero_parcela": proximo_numero,
                    "deleted": {"$ne": True}
                })
                
                if parcela_existente:
                    proximo_numero += 1
                    continue
                
                # Gerar nova parcela via serviço compartilhado
                resultado = await inserir_parcela_juros_aberto(emprestimo, proximo_numero)
                if resultado["inserida"]:
                    parcelas_geradas += 1
                    logger.info(f"   ✅ Parcela #{proximo_numero} gerada ({resultado['status']}) - {emprestimo_id[:8]}... R$ {formatar_reais(resultado['valor_juros_centavos'])} - Venc: {data_vencimento_nova.strftime('%d/%m/%Y')}")
                else:
                    logger.info(f"   ⏭️  Parcela #{proximo_numero} já gerada por outra instância (race evitada)")
                
                proximo_numero += 1
                
                # Se acabamos de gerar uma parcela futura, parar
                if data_vencimento_nova > hoje:
                    break
        
        logger.info("=" * 80)
        logger.info(f"✅ Job concluído: {parcelas_geradas} parcela(s) gerada(s)")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar parcelas: {e}")
        import traceback
        logger.error("Traceback do erro", exc_info=True)


# Para testes manuais
if __name__ == "__main__":
    import asyncio
    logger.info("🧪 Testando job de geração de parcelas para empréstimos abertos...")
    asyncio.run(job_gerar_parcelas_emprestimos_abertos())
