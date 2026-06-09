"""
Job para gerar parcelas automaticamente para empréstimos sem prazo
Executa diariamente às 00:10
"""
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from config import db
from models.emprestimo import Parcela
from services.calculos import calcular_data_vencimento


async def job_gerar_parcelas_emprestimos_abertos():
    """
    Gera próxima(s) parcela(s) para empréstimos sem prazo (abertos)
    
    REGRAS:
    1. Ao criar empréstimo: gera primeira parcela (já feito no endpoint)
    2. Parcela paga: gera próxima parcela imediatamente
    3. Parcela vencida e não paga: marcar atrasada + gerar próximas parcelas até cobrir hoje + 1 período
    4. Empréstimo quitado: NÃO gera mais parcelas
    """
    print("=" * 80)
    print(f"🔄 [Job] Gerar Parcelas Empréstimos Abertos - {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)
    
    try:
        hoje = datetime.now(timezone.utc)
        
        # Buscar empréstimos sem prazo ativos
        emprestimos_abertos = await db.emprestimos.find({
            "sem_prazo": True,
            "status": "ativo",
            "deleted": {"$ne": True}
        }, {"_id": 0}).to_list(1000)
        
        if not emprestimos_abertos:
            print("   ℹ️ Nenhum empréstimo aberto encontrado")
            return
        
        print(f"   📋 Encontrados {len(emprestimos_abertos)} empréstimo(s) aberto(s)")
        
        parcelas_geradas = 0
        
        for emprestimo in emprestimos_abertos:
            emprestimo_id = emprestimo["id"]
            periodicidade = emprestimo.get("periodicidade", "mensal")
            data_inicio = datetime.fromisoformat(emprestimo["data_inicio"])
            
            if periodicidade == "semanal":
                taxa_juros = emprestimo.get("taxa_juros_semanal", 0)
            else:
                taxa_juros = emprestimo.get("taxa_juros_mensal", 0)
            juros_periodo = emprestimo["valor_principal"] * (taxa_juros / 100)
            
            # Marcar parcelas vencidas como atrasadas
            await db.parcelas.update_many(
                {
                    "emprestimo_id": emprestimo_id,
                    "status": "pendente",
                    "data_vencimento": {"$lt": hoje.isoformat()}
                },
                {"$set": {"status": "atrasado", "updated_at": hoje.isoformat()}}
            )
            
            # Buscar última parcela gerada
            ultima_parcela = await db.parcelas.find_one(
                {"emprestimo_id": emprestimo_id, "deleted": {"$ne": True}},
                {"_id": 0},
                sort=[("numero_parcela", -1)]
            )
            
            if not ultima_parcela:
                print(f"   ⚠️ Empréstimo {emprestimo_id[:8]}... sem parcelas (ignorando)")
                continue
            
            # Gerar TODAS as parcelas faltantes até cobrir hoje + 1 período
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
                
                # Gerar nova parcela
                nova_parcela = Parcela(
                    emprestimo_id=emprestimo_id,
                    numero_parcela=proximo_numero,
                    data_vencimento=data_vencimento_nova,
                    valor_principal=0.0,
                    valor_juros=round(juros_periodo, 2),
                    valor_total=round(juros_periodo, 2),
                    saldo_devedor=emprestimo["valor_principal"],
                    total_parcelas=None
                )
                
                # Se vencimento já passou, marcar como atrasada
                status_parcela = "atrasado" if data_vencimento_nova < hoje else "pendente"
                
                parcela_doc = nova_parcela.model_dump()
                parcela_doc["status"] = status_parcela
                parcela_doc["data_vencimento"] = parcela_doc["data_vencimento"].isoformat()
                parcela_doc["created_at"] = parcela_doc["created_at"].isoformat()
                parcela_doc["usuario_id"] = emprestimo["usuario_id"]
                parcela_doc["deleted"] = False  # garantir match do índice único parcial
                
                # Insert protegido contra race condition pelo índice único
                # (emprestimo_id, numero_parcela) com partialFilterExpression
                # deleted != True. Se outra execução paralela já inseriu, ignorar.
                try:
                    await db.parcelas.insert_one(parcela_doc)
                    parcelas_geradas += 1
                    print(f"   ✅ Parcela #{proximo_numero} gerada ({status_parcela}) - {emprestimo_id[:8]}... R$ {juros_periodo:.2f} - Venc: {data_vencimento_nova.strftime('%d/%m/%Y')}")
                except Exception as dup_err:
                    # Outra instância do scheduler venceu a corrida — ok, seguimos
                    if "duplicate key" in str(dup_err).lower() or "E11000" in str(dup_err):
                        print(f"   ⏭️  Parcela #{proximo_numero} já gerada por outra instância (race evitada)")
                    else:
                        raise
                
                proximo_numero += 1
                
                # Se acabamos de gerar uma parcela futura, parar
                if data_vencimento_nova > hoje:
                    break
        
        print("=" * 80)
        print(f"✅ Job concluído: {parcelas_geradas} parcela(s) gerada(s)")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Erro ao gerar parcelas: {e}")
        import traceback
        traceback.print_exc()


# Para testes manuais
if __name__ == "__main__":
    import asyncio
    print("🧪 Testando job de geração de parcelas para empréstimos abertos...")
    asyncio.run(job_gerar_parcelas_emprestimos_abertos())
