"""
Script de Validação de Integridade de Dados
Executa verificações diárias para detectar problemas antes que afetem usuários
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import sys
import os

sys.path.insert(0, '/app/backend')
from config import MONGO_URL, DB_NAME


class ValidadorIntegridade:
    """Valida integridade dos dados no MongoDB"""
    
    def __init__(self):
        self.client = AsyncIOMotorClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        self.erros = []
        self.avisos = []
    
    async def validar_parcelas(self):
        """Valida integridade das parcelas"""
        print("\n📋 Validando Parcelas...")
        
        # 1. Parcelas sem valor_parcela
        parcelas_sem_valor = await self.db.parcelas.count_documents({
            "$or": [
                {"valor_parcela": None},
                {"valor_parcela": {"$exists": False}}
            ]
        })
        
        if parcelas_sem_valor > 0:
            self.erros.append(f"❌ {parcelas_sem_valor} parcelas sem valor_parcela")
        else:
            print("  ✅ Todas parcelas têm valor_parcela")
        
        # 2. Parcelas órfãs (sem empréstimo)
        parcelas = await self.db.parcelas.find({}).to_list(1000)
        parcelas_orfas = 0
        
        for parcela in parcelas:
            emp_id = parcela.get("emprestimo_id")
            if not emp_id:
                parcelas_orfas += 1
                continue
            
            emprestimo = await self.db.emprestimos.find_one({"id": emp_id})
            if not emprestimo:
                parcelas_orfas += 1
        
        if parcelas_orfas > 0:
            self.erros.append(f"❌ {parcelas_orfas} parcelas órfãs (sem empréstimo válido)")
        else:
            print("  ✅ Todas parcelas têm empréstimo válido")
        
        # 3. Parcelas com valores inconsistentes
        parcelas_inconsistentes = 0
        for parcela in parcelas:
            if parcela.get("valor_total", 0) <= 0:
                parcelas_inconsistentes += 1
        
        if parcelas_inconsistentes > 0:
            self.avisos.append(f"⚠️  {parcelas_inconsistentes} parcelas com valor_total <= 0")
        else:
            print("  ✅ Todas parcelas têm valor_total > 0")
    
    async def validar_emprestimos(self):
        """Valida integridade dos empréstimos"""
        print("\n💰 Validando Empréstimos...")
        
        emprestimos = await self.db.emprestimos.find({}).to_list(1000)
        
        # 1. Empréstimos órfãos (sem cliente)
        emprestimos_orfaos = 0
        
        for emp in emprestimos:
            cliente_id = emp.get("cliente_id")
            if not cliente_id:
                emprestimos_orfaos += 1
                continue
            
            cliente = await self.db.clientes.find_one({"id": cliente_id})
            if not cliente:
                emprestimos_orfaos += 1
        
        if emprestimos_orfaos > 0:
            self.erros.append(f"❌ {emprestimos_orfaos} empréstimos órfãos (sem cliente válido)")
        else:
            print("  ✅ Todos empréstimos têm cliente válido")
        
        # 2. Empréstimos sem parcelas
        emprestimos_sem_parcelas = 0
        
        for emp in emprestimos:
            parcelas_count = await self.db.parcelas.count_documents({"emprestimo_id": emp["id"]})
            if parcelas_count == 0:
                emprestimos_sem_parcelas += 1
        
        if emprestimos_sem_parcelas > 0:
            self.avisos.append(f"⚠️  {emprestimos_sem_parcelas} empréstimos sem parcelas")
        else:
            print("  ✅ Todos empréstimos têm parcelas")
    
    async def validar_clientes(self):
        """Valida integridade dos clientes"""
        print("\n👥 Validando Clientes...")
        
        # 1. Clientes sem telefone
        clientes_sem_telefone = await self.db.clientes.count_documents({
            "$or": [
                {"telefone": None},
                {"telefone": ""},
                {"telefone": {"$exists": False}}
            ]
        })
        
        if clientes_sem_telefone > 0:
            self.avisos.append(f"⚠️  {clientes_sem_telefone} clientes sem telefone")
        else:
            print("  ✅ Todos clientes têm telefone")
        
        # 2. Clientes duplicados (mesmo CPF)
        pipeline = [
            {"$match": {"cpf_cnpj": {"$ne": None, "$ne": ""}}},
            {"$group": {"_id": "$cpf_cnpj", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}}
        ]
        
        duplicados = await self.db.clientes.aggregate(pipeline).to_list(100)
        
        if len(duplicados) > 0:
            self.avisos.append(f"⚠️  {len(duplicados)} CPFs/CNPJs duplicados")
        else:
            print("  ✅ Nenhum cliente duplicado")
    
    async def gerar_relatorio(self):
        """Gera relatório final"""
        print("\n" + "=" * 60)
        print("📊 RELATÓRIO DE VALIDAÇÃO DE INTEGRIDADE")
        print("=" * 60)
        print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        
        if not self.erros and not self.avisos:
            print("✅ ✅ ✅ SISTEMA 100% ÍNTEGRO ✅ ✅ ✅")
            print("\nNenhum problema encontrado!")
            return True
        
        if self.erros:
            print("🔴 ERROS CRÍTICOS:")
            for erro in self.erros:
                print(f"  {erro}")
            print()
        
        if self.avisos:
            print("🟡 AVISOS:")
            for aviso in self.avisos:
                print(f"  {aviso}")
            print()
        
        print("=" * 60)
        
        return len(self.erros) == 0
    
    async def executar(self):
        """Executa todas as validações"""
        print("\n🔍 Iniciando validação de integridade do sistema...")
        
        try:
            await self.validar_parcelas()
            await self.validar_emprestimos()
            await self.validar_clientes()
            
            sucesso = await self.gerar_relatorio()
            
            self.client.close()
            
            return sucesso
        
        except Exception as e:
            print(f"\n❌ Erro durante validação: {e}")
            self.client.close()
            return False


async def main():
    validador = ValidadorIntegridade()
    sucesso = await validador.executar()
    
    # Retornar código de saída
    exit(0 if sucesso else 1)


if __name__ == "__main__":
    asyncio.run(main())
