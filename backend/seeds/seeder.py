"""
Seeder - Script para criar dados iniciais do sistema Gestor Cred
Execute: python -m seeds.seeder
"""
import asyncio
import sys
import os

# Adicionar o diretório backend ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta
import uuid

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
        'nome': 'Admin GestorCred',
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


# ==================== CONFIGURAÇÕES PADRÃO DA LANDING ====================
LANDING_CONFIG_SEED = {
    "id": "landing_config",
    "hero_titulo": "Sistema de Gestão de",
    "hero_destaque": "Empréstimos",
    "hero_subtitulo": "Gerencie seus empréstimos de forma simples e profissional",
    "hero_badge": "✨ 7 dias grátis",
    "stats": {
        "usuarios": "500+",
        "usuarios_label": "Usuários ativos",
        "gerenciados": "R$ 50M+",
        "gerenciados_label": "Gerenciados",
        "uptime": "99.9%",
        "uptime_label": "Uptime"
    },
    "funcionalidades": [
        {
            "icone": "Users",
            "titulo": "Gestão de Clientes",
            "descricao": "Cadastre e gerencie seus clientes com facilidade"
        },
        {
            "icone": "Calculator",
            "titulo": "Cálculos Automáticos",
            "descricao": "Juros simples, compostos, Price e SAC"
        },
        {
            "icone": "FileText",
            "titulo": "Contratos PDF",
            "descricao": "Gere contratos profissionais automaticamente"
        },
        {
            "icone": "Bell",
            "titulo": "Notificações",
            "descricao": "Alertas de vencimento e pagamentos"
        },
        {
            "icone": "BarChart3",
            "titulo": "Relatórios",
            "descricao": "Relatórios completos em PDF e Excel"
        },
        {
            "icone": "Shield",
            "titulo": "Segurança",
            "descricao": "Dados protegidos com criptografia"
        }
    ],
    "planos": [
        {
            "nome": "Trial",
            "preco": "0",
            "periodo": "7 dias",
            "descricao": "Experimente grátis",
            "recursos": [
                "Até 5 clientes",
                "Até 10 empréstimos",
                "Relatórios básicos",
                "Suporte por email"
            ],
            "destaque": False,
            "botao_texto": "Começar Grátis"
        },
        {
            "nome": "Básico",
            "preco": "49",
            "periodo": "/mês",
            "descricao": "Para pequenos negócios",
            "recursos": [
                "Até 50 clientes",
                "Até 100 empréstimos",
                "Relatórios completos",
                "Contratos PDF",
                "Suporte prioritário"
            ],
            "destaque": False,
            "botao_texto": "Assinar Agora"
        },
        {
            "nome": "Profissional",
            "preco": "99",
            "periodo": "/mês",
            "descricao": "Mais popular",
            "recursos": [
                "Clientes ilimitados",
                "Empréstimos ilimitados",
                "Todos os relatórios",
                "Contratos personalizados",
                "Assistente IA",
                "Suporte 24/7"
            ],
            "destaque": True,
            "botao_texto": "Assinar Agora"
        },
        {
            "nome": "Enterprise",
            "preco": "199",
            "periodo": "/mês",
            "descricao": "Para grandes operações",
            "recursos": [
                "Tudo do Profissional",
                "Multi-usuários",
                "API de integração",
                "Relatórios customizados",
                "Gerente de conta dedicado"
            ],
            "destaque": False,
            "botao_texto": "Falar com Vendas"
        }
    ],
    "whatsapp_numero": "5511999999999",
    "whatsapp_mensagem": "Olá! Gostaria de saber mais sobre o Gestor Cred.",
    "whatsapp_ativo": True,
    "rodape": {
        "empresa": "Gestor Cred",
        "descricao": "Sistema completo para gestão de empréstimos",
        "email": "contato@gestorcred.cloud",
        "telefone": "(11) 99999-9999"
    }
}

# ==================== CONFIGURAÇÕES DE GATEWAY PADRÃO ====================
ASSINATURA_GATEWAY_CONFIG_SEED = {
    "tipo": "assinatura_gateway",
    "dados": {
        "estrategia": "rotacao",
        # Asaas (Gateway Brasileiro - Recomendado)
        "asaas_habilitado": True,
        "asaas_api_key": "",
        "asaas_ambiente": "sandbox",
        "asaas_webhook_url": "",
        # Mercado Pago (Gateway Brasileiro - Alternativa)
        "mercadopago_habilitado": True,
        "mercadopago_access_token": "",
        "mercadopago_public_key": "",
        "mercadopago_modo_sandbox": True,
        "mercadopago_webhook_secret": "",
        "mp_cartao_habilitado": True,
        "mp_pix_habilitado": True,
        "rotacao_contador": 0,
        "gateway_primario": "asaas"
    }
}


async def criar_usuarios(db):
    """Cria usuários padrão do sistema"""
    print("\n📦 Criando usuários...")
    
    for user_data in USUARIOS_SEED:
        # Verificar se usuário já existe
        existing = await db.usuarios.find_one({"email": user_data['email']})
        
        if existing:
            print(f"   ⏭️  Usuário '{user_data['email']}' já existe, pulando...")
            continue
        
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
            'created_at': datetime.now(timezone.utc).isoformat(),
            'data_inicio_trial': datetime.now(timezone.utc).isoformat(),
            'data_fim_trial': (datetime.now(timezone.utc) + timedelta(days=365 if user_data['perfil'] == 'admin' else 7)).isoformat()
        }
        
        await db.usuarios.insert_one(usuario)
        print(f"   ✅ Usuário '{user_data['email']}' criado com sucesso!")
        print(f"      📧 Email: {user_data['email']}")
        print(f"      🔑 Senha: {user_data['senha']}")
        print(f"      👤 Perfil: {user_data['perfil']}")


async def criar_landing_config(db):
    """Cria configurações padrão da landing page"""
    print("\n📦 Criando configurações da landing page...")
    
    existing = await db.configuracoes.find_one({"id": "landing_config"})
    
    if existing:
        print("   ⏭️  Configurações da landing já existem, pulando...")
        return
    
    await db.configuracoes.insert_one(LANDING_CONFIG_SEED)
    print("   ✅ Configurações da landing criadas com sucesso!")


async def criar_gateway_config(db):
    """Cria configurações padrão de gateway de pagamento"""
    print("\n📦 Criando configurações de gateway de pagamento...")
    
    existing = await db.configuracoes.find_one({"tipo": "assinatura_gateway"})
    
    if existing:
        print("   ⏭️  Configurações de gateway já existem, pulando...")
        return
    
    await db.configuracoes.insert_one(ASSINATURA_GATEWAY_CONFIG_SEED)
    print("   ✅ Configurações de gateway criadas com sucesso!")
    print("      ⚠️  Configure as chaves do Asaas/Mercado Pago em /configuracoes")


async def criar_indices(db):
    """Cria índices para melhor performance"""
    print("\n📦 Criando índices do banco de dados...")
    
    try:
        # Índices para usuários
        await db.usuarios.create_index("email", unique=True, background=True)
        await db.usuarios.create_index("id", unique=True, background=True)
        print("   ✅ Índices de usuários criados")
    except Exception as e:
        print(f"   ⏭️  Índices de usuários já existem")
    
    try:
        # Índices para clientes
        await db.clientes.create_index("usuario_id", background=True)
        await db.clientes.create_index([("usuario_id", 1), ("cpf_cnpj", 1)], background=True)
        print("   ✅ Índices de clientes criados")
    except Exception as e:
        print(f"   ⏭️  Índices de clientes já existem")
    
    try:
        # Índices para empréstimos
        await db.emprestimos.create_index("usuario_id", background=True)
        await db.emprestimos.create_index("cliente_id", background=True)
        await db.emprestimos.create_index([("usuario_id", 1), ("status", 1)], background=True)
        print("   ✅ Índices de empréstimos criados")
    except Exception as e:
        print(f"   ⏭️  Índices de empréstimos já existem")
    
    try:
        # Índices para parcelas
        await db.parcelas.create_index("emprestimo_id", background=True)
        await db.parcelas.create_index("usuario_id", background=True)
        await db.parcelas.create_index([("usuario_id", 1), ("data_vencimento", 1)], background=True)
        print("   ✅ Índices de parcelas criados")
    except Exception as e:
        print(f"   ⏭️  Índices de parcelas já existem")
    
    try:
        # Índices para pagamentos
        await db.pagamentos.create_index("usuario_id", background=True)
        await db.pagamentos.create_index("emprestimo_id", background=True)
        print("   ✅ Índices de pagamentos criados")
    except Exception as e:
        print(f"   ⏭️  Índices de pagamentos já existem")
    
    try:
        # Índices para notificações
        await db.notificacoes.create_index("usuario_id", background=True)
        await db.notificacoes.create_index([("usuario_id", 1), ("lida", 1)], background=True)
        print("   ✅ Índices de notificações criados")
    except Exception as e:
        print(f"   ⏭️  Índices de notificações já existem")
    
    try:
        # Índices para auditoria
        await db.auditoria.create_index("usuario_id", background=True)
        await db.auditoria.create_index("created_at", background=True)
        print("   ✅ Índices de auditoria criados")
    except Exception as e:
        print(f"   ⏭️  Índices de auditoria já existem")
    
    try:
        # Índices para códigos 2FA
        await db.two_factor_codes.create_index("usuario_id", background=True)
        await db.two_factor_codes.create_index([("usuario_id", 1), ("usado", 1)], background=True)
        await db.two_factor_codes.create_index("expira_em", background=True)
        # TTL index para deletar códigos expirados automaticamente (após 24h)
        await db.two_factor_codes.create_index("expira_em", expireAfterSeconds=86400, background=True)
        print("   ✅ Índices de 2FA criados")
    except Exception as e:
        print(f"   ⏭️  Índices de 2FA já existem ou erro: {e}")


async def run_seeder():
    """Executa o seeder completo"""
    print("=" * 60)
    print("🌱 Gestor Cred - Seeder de Dados Iniciais")
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
        await criar_indices(db)
        await criar_usuarios(db)
        await criar_landing_config(db)
        await criar_gateway_config(db)
        
        print("\n" + "=" * 60)
        print("🎉 Seeder concluído com sucesso!")
        print("=" * 60)
        print("\n📋 Credenciais de acesso:")
        print("-" * 40)
        for user in USUARIOS_SEED:
            print(f"   👤 {user['descricao']}")
            print(f"      Email: {user['email']}")
            print(f"      Senha: {user['senha']}")
            print(f"      Perfil: {user['perfil']}")
            print()
        
        client.close()
        
    except Exception as e:
        print(f"\n❌ Erro ao executar seeder: {e}")
        raise e


async def reset_database():
    """Remove todos os dados e recria (USE COM CUIDADO!)"""
    print("=" * 60)
    print("⚠️  ATENÇÃO: Reset completo do banco de dados!")
    print("=" * 60)
    
    confirm = input("\nDigite 'CONFIRMAR' para continuar: ")
    if confirm != 'CONFIRMAR':
        print("❌ Operação cancelada.")
        return
    
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Dropar coleções
        collections = ['usuarios', 'clientes', 'emprestimos', 'parcelas', 
                      'pagamentos', 'notificacoes', 'auditoria', 'configuracoes']
        
        for col in collections:
            await db[col].drop()
            print(f"   🗑️  Coleção '{col}' removida")
        
        print("\n✅ Banco de dados limpo!")
        
        # Recriar dados
        await run_seeder()
        
        client.close()
        
    except Exception as e:
        print(f"\n❌ Erro ao resetar banco: {e}")
        raise e


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        asyncio.run(reset_database())
    else:
        asyncio.run(run_seeder())
