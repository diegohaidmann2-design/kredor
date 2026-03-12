"""
Sistema de Verificação Contínua
Roda a cada 1 hora e valida integridade do sistema
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import sys
import os

sys.path.insert(0, '/app/backend')
from config import MONGO_URL, DB_NAME


class VerificadorContinuo:
    """Verifica continuamente a integridade do sistema"""
    
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        self.problemas_encontrados = []
    
    async def corrigir_parcelas_sem_valor(self):
        """Corrige automaticamente parcelas com valor_parcela = None"""
        print("🔧 Corrigindo parcelas...")
        
        result = await self.db.parcelas.update_many(
            {"$or": [
                {"valor_parcela": {"$exists": False}},
                {"valor_parcela": None}
            ]},
            [{"$set": {"valor_parcela": "$valor_total"}}]
        )
        
        if result.modified_count > 0:
            print(f"✅ {result.modified_count} parcelas corrigidas")
            return result.modified_count
        return 0
    
    async def verificar_relacionamentos(self):
        """Verifica e corrige relacionamentos quebrados"""
        print("🔗 Verificando relacionamentos...")
        
        # Verificar parcelas órfãs
        parcelas = await self.db.parcelas.find({}).to_list(1000)
        parcelas_orfas = []
        
        for parcela in parcelas:
            emp_id = parcela.get("emprestimo_id")
            if emp_id:
                emp = await self.db.emprestimos.find_one({"id": emp_id})
                if not emp:
                    parcelas_orfas.append(parcela["id"])
        
        if parcelas_orfas:
            print(f"⚠️  Encontradas {len(parcelas_orfas)} parcelas órfãs")
            # Marcar como deletadas ao invés de deletar
            await self.db.parcelas.update_many(
                {"id": {"$in": parcelas_orfas}},
                {"$set": {"deleted": True, "deleted_at": datetime.now().isoformat()}}
            )
            print(f"✅ Parcelas órfãs marcadas como deletadas")
        else:
            print("✅ Nenhuma parcela órfã")
    
    async def verificar_valores_zerados(self):
        """Detecta e alerta valores zerados"""
        print("💰 Verificando valores...")
        
        parcelas_zeradas = await self.db.parcelas.count_documents({
            "valor_total": {"$lte": 0}
        })
        
        if parcelas_zeradas > 0:
            print(f"⚠️  {parcelas_zeradas} parcelas com valor <= 0")
            self.problemas_encontrados.append(f"{parcelas_zeradas} parcelas zeradas")
        else:
            print("✅ Todos os valores estão corretos")
    
    async def gerar_relatorio(self):
        """Gera relatório de saúde do sistema"""
        print("\n" + "=" * 60)
        print("🏥 RELATÓRIO DE SAÚDE DO SISTEMA")
        print("=" * 60)
        print(f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        
        # Estatísticas
        total_clientes = await self.db.clientes.count_documents({})
        total_emprestimos = await self.db.emprestimos.count_documents({})
        total_parcelas = await self.db.parcelas.count_documents({})
        
        print(f"📊 Estatísticas:")
        print(f"  Clientes: {total_clientes}")
        print(f"  Empréstimos: {total_emprestimos}")
        print(f"  Parcelas: {total_parcelas}")
        print()
        
        if self.problemas_encontrados:
            print("⚠️  Problemas Encontrados:")
            for problema in self.problemas_encontrados:
                print(f"  - {problema}")
        else:
            print("✅ SISTEMA SAUDÁVEL - Nenhum problema encontrado!")
        
        print("=" * 60)
    
    async def executar_verificacao_completa(self):
        """Executa verificação completa e correções"""
        print("\n🔍 Iniciando verificação contínua...\n")
        
        try:
            # Correções automáticas
            await self.corrigir_parcelas_sem_valor()
            await self.verificar_relacionamentos()
            
            # Verificações
            await self.verificar_valores_zerados()
            
            # Relatório
            await self.gerar_relatorio()
            
            self.client.close()
            return len(self.problemas_encontrados) == 0
        
        except Exception as e:
            print(f"❌ Erro durante verificação: {e}")
            self.client.close()
            return False


async def main():
    """Executa verificação uma vez"""
    verificador = VerificadorContinuo()
    sucesso = await verificador.executar_verificacao_completa()
    exit(0 if sucesso else 1)


if __name__ == "__main__":
    asyncio.run(main())
