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
    
    REGRAS:
    1. Ao criar empréstimo: gera primeira parcela (já feito no endpoint)
    2. Parcela paga: gera próxima parcela imediatamente
    3. Parcela vencida e não paga: gera próxima parcela
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
            
            # Buscar última parcela gerada
            ultima_parcela = await db.parcelas.find_one(
                {"emprestimo_id": emprestimo_id},
                {"_id": 0},
                sort=[("numero_parcela", -1)]
            )
            
            if not ultima_parcela:
                print(f"   ⚠️ Empréstimo {emprestimo_id[:8]}... sem parcelas (ignorando)")
                continue
            
            # VERIFICAR SE DEVE GERAR NOVA PARCELA
            status_ultima = ultima_parcela.get("status")
            data_vencimento = datetime.fromisoformat(ultima_parcela["data_vencimento"])
            
            deve_gerar = False
            motivo = ""
            
            # Regra 1: Parcela foi paga → gera próxima
            if status_ultima == "pago":
                deve_gerar = True
                motivo = "parcela paga"
            
            # Regra 2: Parcela venceu e não foi paga → marcar atrasada + gerar próxima
            elif status_ultima in ["pendente", "parcial", "atrasado"] and data_vencimento < hoje:
                dias_apos_vencimento = (hoje - data_vencimento).days
                if dias_apos_vencimento >= 1:
                    deve_gerar = True
                    motivo = f"vencida há {dias_apos_vencimento} dia(s)"
                    
                    # Marcar parcela vencida como "atrasado" se ainda não estiver
                    if status_ultima != "atrasado":
                        await db.parcelas.update_one(
                            {"id": ultima_parcela["id"]},
                            {"$set": {"status": "atrasado", "updated_at": hoje.isoformat()}}
                        )
                        print(f"   ⚠️ Parcela #{ultima_parcela['numero_parcela']} marcada como atrasada")
            
            if not deve_gerar:
                continue
            
            # Verificar se próxima parcela já existe
            proximo_numero = ultima_parcela["numero_parcela"] + 1
            parcela_existente = await db.parcelas.find_one({
                "emprestimo_id": emprestimo_id,
                "numero_parcela": proximo_numero
            })
            
            if parcela_existente:
                continue
            
            # Gerar nova parcela (apenas juros) — respeitar periodicidade
            periodicidade = emprestimo.get("periodicidade", "mensal")
            if periodicidade == "semanal":
                taxa_juros = emprestimo.get("taxa_juros_semanal", 0)
            else:
                taxa_juros = emprestimo.get("taxa_juros_mensal", 0)
            juros_periodo = emprestimo["valor_principal"] * (taxa_juros / 100)
            
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
                valor_principal=0.0,
                valor_juros=round(juros_periodo, 2),
                valor_total=round(juros_periodo, 2),
                saldo_devedor=emprestimo["valor_principal"],
                total_parcelas=None
            )
            
            parcela_doc = nova_parcela.model_dump()
            parcela_doc["data_vencimento"] = parcela_doc["data_vencimento"].isoformat()
            parcela_doc["created_at"] = parcela_doc["created_at"].isoformat()
            parcela_doc["usuario_id"] = emprestimo["usuario_id"]
            
            await db.parcelas.insert_one(parcela_doc)
            
            parcelas_geradas += 1
            print(f"   ✅ Parcela #{proximo_numero} gerada para empréstimo {emprestimo_id[:8]}... (R$ {juros_periodo:.2f}) - Motivo: {motivo}")
        
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
