"""
Seeder de Usuários - Cria usuários de teste do sistema
Execute: python -m seeds.usuarios_seeder
"""
import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
import uuid

# Adicionar o diretório backend ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

# Configuração de senha
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

# Configurações
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')


# ==================== DADOS DOS USUÁRIOS ====================
USUARIOS_SEED = [
    {
        'nome': 'Diego Haidmann',
        'email': 'diego.haidmann@gmail.com',
        'senha': 'muda2025',
        'perfil': 'admin',
        'plano': 'enterprise',
        'descricao': 'Administrador Principal'
    },
    {
        'nome': 'Admin Kredor',
        'email': 'admin@gestorcerd.com',
        'senha': 'admin123',
        'perfil': 'admin',
        'plano': 'enterprise',
        'descricao': 'Administrador do Sistema'
    },
    {
        'nome': 'Usuário Teste',
        'email': 'usuario@teste.com',
        'senha': 'senha123',
        'perfil': 'usuario',
        'plano': 'profissional',
        'descricao': 'Usuário comum para testes'
    }
]


def get_trial_days(plano: str) -> int:
    """Retorna dias de trial baseado no plano"""
    if plano == 'enterprise':
        return 365  # Admin tem 1 ano
    elif plano == 'profissional':
        return 30  # 30 dias
    elif plano == 'basico':
        return 30  # 30 dias
    else:
        return 7  # Trial padrão


async def criar_usuarios(db):
    """Cria usuários de teste do sistema"""
    print("\n📦 Criando usuários...")
    
    for user_data in USUARIOS_SEED:
        # Verificar se usuário já existe
        existing = await db.usuarios.find_one({"email": user_data['email']})
        
        if existing:
            print(f"   ⏭️  Usuário '{user_data['email']}' já existe, pulando...")
            continue
        
        # Calcular datas de trial
        trial_days = get_trial_days(user_data['plano'])
        data_inicio = datetime.now(timezone.utc)
        data_fim = data_inicio + timedelta(days=trial_days)
        
        # Criar usuário
        usuario = {
            'id': str(uuid.uuid4()),
            'nome': user_data['nome'],
            'email': user_data['email'],
            'senha_hash': pwd_context.hash(user_data['senha']),
            'perfil': user_data['perfil'],
            'plano': user_data['plano'],
            'plano_ativo': True,
            'ativo': True,
            'email_verificado': True,
            'created_at': data_inicio.isoformat(),
            'updated_at': data_inicio.isoformat(),
            'data_inicio_trial': data_inicio.isoformat(),
            'data_fim_trial': data_fim.isoformat(),
            # Contadores de uso
            'contadores': {
                'clientes': 0,
                'emprestimos': 0,
                'emprestimos_mes': 0,
                'ultimo_reset_mensal': data_inicio.isoformat()
            }
        }
        
        await db.usuarios.insert_one(usuario)
        print(f"   ✅ Usuário '{user_data['email']}' criado!")
        print(f"      📧 Email: {user_data['email']}")
        print(f"      🔑 Senha: {user_data['senha']}")
        print(f"      👤 Perfil: {user_data['perfil']}")
        print(f"      📊 Plano: {user_data['plano'].upper()}")


async def criar_indices_usuarios(db):
    """Cria índices para usuários"""
    print("\n📦 Criando índices de usuários...")
    
    try:
        await db.usuarios.create_index("email", unique=True, background=True)
        await db.usuarios.create_index("id", unique=True, background=True)
        await db.usuarios.create_index("plano", background=True)
        await db.usuarios.create_index("perfil", background=True)
        print("   ✅ Índices de usuários criados")
    except Exception as e:
        print(f"   ⏭️  Índices já existem")


async def run_usuarios_seeder():
    """Executa o seeder de usuários"""
    print("=" * 60)
    print("🌱 Kredor - Seeder de Usuários")
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
        await criar_indices_usuarios(db)
        await criar_usuarios(db)
        
        print("\n" + "=" * 60)
        print("🎉 Seeder de Usuários concluído com sucesso!")
        print("=" * 60)
        
        # Listar credenciais
        print("\n📋 Credenciais de acesso:")
        print("-" * 50)
        for user in USUARIOS_SEED:
            plano_emoji = {
                'enterprise': '🏢',
                'profissional': '⭐',
                'basico': '📦',
                'trial': '🕐'
            }.get(user['plano'], '📦')
            print(f"   {plano_emoji} {user['descricao']}")
            print(f"      Email: {user['email']}")
            print(f"      Senha: {user['senha']}")
            print(f"      Plano: {user['plano'].upper()}")
            print()
        
        client.close()
        
    except Exception as e:
        print(f"\n❌ Erro ao executar seeder: {e}")
        raise e


if __name__ == "__main__":
    asyncio.run(run_usuarios_seeder())
