"""
Seeder de Planos - Cria os planos padrão do sistema
Execute: python -m seeds.planos_seeder
"""
import asyncio
import sys
import os
from datetime import datetime, timezone
import uuid

# Adicionar o diretório backend ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from models.plano import PLANOS_PADRAO, PlanoLimites

# Configurações
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')


async def criar_planos(db):
    """Cria os planos padrão do sistema"""
    print("\n📦 Criando planos...")
    
    for slug, plano_data in PLANOS_PADRAO.items():
        # Verificar se plano já existe
        existing = await db.planos.find_one({"slug": slug})
        
        if existing:
            print(f"   ⏭️  Plano '{plano_data['nome']}' já existe, atualizando...")
            # Atualizar plano existente
            limites_dict = plano_data['limites'].model_dump() if hasattr(plano_data['limites'], 'model_dump') else plano_data['limites'].__dict__
            await db.planos.update_one(
                {"slug": slug},
                {"$set": {
                    "nome": plano_data['nome'],
                    "preco_mensal": plano_data['preco_mensal'],
                    "preco_anual": plano_data.get('preco_anual'),
                    "descricao": plano_data['descricao'],
                    "recursos": plano_data['recursos'],
                    "limites": limites_dict,
                    "destaque": plano_data['destaque'],
                    "ordem": plano_data['ordem'],
                    "cor": plano_data['cor'],
                    "icone": plano_data['icone'],
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            print(f"   ✅ Plano '{plano_data['nome']}' atualizado!")
        else:
            # Criar novo plano
            limites_dict = plano_data['limites'].model_dump() if hasattr(plano_data['limites'], 'model_dump') else plano_data['limites'].__dict__
            plano = {
                'id': str(uuid.uuid4()),
                'nome': plano_data['nome'],
                'slug': slug,
                'preco_mensal': plano_data['preco_mensal'],
                'preco_anual': plano_data.get('preco_anual'),
                'descricao': plano_data['descricao'],
                'recursos': plano_data['recursos'],
                'limites': limites_dict,
                'destaque': plano_data['destaque'],
                'ativo': True,
                'ordem': plano_data['ordem'],
                'cor': plano_data['cor'],
                'icone': plano_data['icone'],
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            await db.planos.insert_one(plano)
            print(f"   ✅ Plano '{plano_data['nome']}' criado!")
            print(f"      💰 Preço: R$ {plano_data['preco_mensal']:.2f}/mês")
            print(f"      👥 Limite de clientes: {limites_dict['max_clientes'] if limites_dict['max_clientes'] != -1 else 'Ilimitado'}")
            print(f"      📋 Limite de empréstimos: {limites_dict['max_emprestimos'] if limites_dict['max_emprestimos'] != -1 else 'Ilimitado'}")


async def criar_indice_planos(db):
    """Cria índices para a coleção de planos"""
    print("\n📦 Criando índices de planos...")
    
    try:
        await db.planos.create_index("slug", unique=True, background=True)
        await db.planos.create_index("ordem", background=True)
        print("   ✅ Índices de planos criados")
    except Exception as e:
        print(f"   ⏭️  Índices já existem")


async def run_planos_seeder():
    """Executa o seeder de planos"""
    print("=" * 60)
    print("🌱 Gestor Cred - Seeder de Planos")
    print("=" * 60)
    print(f"\n📌 Conectando ao MongoDB: {MONGO_URL}")
    print(f"📌 Banco de dados: {DB_NAME}")
    
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Testar conexão
        await client.admin.command('ping')
        print("✅ Conexão com MongoDB estabelecida!\n")
        
        # Executar seeds
        await criar_indice_planos(db)
        await criar_planos(db)
        
        print("\n" + "=" * 60)
        print("🎉 Seeder de Planos concluído com sucesso!")
        print("=" * 60)
        
        # Listar planos criados
        print("\n📋 Planos disponíveis:")
        print("-" * 50)
        planos = await db.planos.find({}).sort("ordem", 1).to_list(100)
        for plano in planos:
            destaque = " ⭐ POPULAR" if plano.get('destaque') else ""
            preco = f"R$ {plano['preco_mensal']:.2f}/mês" if plano['preco_mensal'] > 0 else "Grátis (7 dias)"
            print(f"   {plano['nome']}{destaque}")
            print(f"      Preço: {preco}")
            limites = plano.get('limites', {})
            clientes = limites.get('max_clientes', 0)
            emprestimos = limites.get('max_emprestimos', 0)
            print(f"      Clientes: {'Ilimitado' if clientes == -1 else clientes}")
            print(f"      Empréstimos: {'Ilimitado' if emprestimos == -1 else emprestimos}")
            print()
        
        client.close()
        
    except Exception as e:
        print(f"\n❌ Erro ao executar seeder: {e}")
        raise e


if __name__ == "__main__":
    asyncio.run(run_planos_seeder())
