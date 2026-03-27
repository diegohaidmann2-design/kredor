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
    Gera próxima parcela para empréstimos sem prazo (abertos)
    - Busca empréstimos com sem_prazo=True e status=ativo
    - Verifica se já existe parcela para o mês atual
    - Gera nova parcela se necessário
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
            "deleted_at": {"$exists": False}
        }, {"_id": 0}).to_list(1000)
        
        if not emprestimos_abertos:
            print("   ℹ️ Nenhum empréstimo aberto encontrado")
            return
        
        print(f"   📋 Encontrados {len(emprestimos_abertos)} empréstimo(s) aberto(s)")
        
        parcelas_geradas = 0
        
        for emprestimo in emprestimos_abertos:
            emprestimo_id = emprestimo["id"]
            
            # Buscar última parcela gerada
            ultima_parcela = await db.parcelas.find_one(
                {"emprestimo_id": emprestimo_id},
                {"_id": 0},
                sort=[("numero_parcela", -1)]
            )
            
            if not ultima_parcela:
                print(f"   ⚠️ Empréstimo {emprestimo_id[:8]}... sem parcelas (ignorando)")
                continue
            
            # Verificar se a última parcela já venceu há mais de 1 mês
            data_vencimento_ultima = datetime.fromisoformat(ultima_parcela["data_vencimento"])
            
            # Calcular diferença em meses
            diff_meses = relativedelta(hoje, data_vencimento_ultima).months
            diff_meses += relativedelta(hoje, data_vencimento_ultima).years * 12
            
            if diff_meses < 1:
                # Ainda não é hora de gerar nova parcela
                continue
            
            # Verificar se já existe parcela para o próximo mês
            proximo_numero = ultima_parcela["numero_parcela"] + 1
            parcela_existente = await db.parcelas.find_one({
                "emprestimo_id": emprestimo_id,
                "numero_parcela": proximo_numero
            })
            
            if parcela_existente:
                # Parcela já foi gerada
                continue
            
            # Gerar nova parcela (apenas juros)
            juros_mensal = emprestimo["valor_principal"] * (emprestimo["taxa_juros_mensal"] / 100)
            
            data_inicio = datetime.fromisoformat(emprestimo["data_inicio"])
            data_vencimento_nova = calcular_data_vencimento(
                data_inicio,
                proximo_numero,
                emprestimo.get("dia_vencimento"),
                emprestimo.get("periodicidade", "mensal")
            )
            
            nova_parcela = Parcela(
                emprestimo_id=emprestimo_id,
                numero_parcela=proximo_numero,
                data_vencimento=data_vencimento_nova,
                valor_principal=0.0,  # Apenas juros
                valor_juros=round(juros_mensal, 2),
                valor_total=round(juros_mensal, 2),
                saldo_devedor=emprestimo["valor_principal"],
                total_parcelas=None  # Indeterminado
            )
            
            parcela_doc = nova_parcela.model_dump()
            parcela_doc["data_vencimento"] = parcela_doc["data_vencimento"].isoformat()
            parcela_doc["created_at"] = parcela_doc["created_at"].isoformat()
            parcela_doc["usuario_id"] = emprestimo["usuario_id"]
            
            await db.parcelas.insert_one(parcela_doc)
            
            parcelas_geradas += 1
            print(f"   ✅ Parcela #{proximo_numero} gerada para empréstimo {emprestimo_id[:8]}... (R$ {juros_mensal:.2f})")
        
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
