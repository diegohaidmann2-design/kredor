"""
Configurações centralizadas da aplicação
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# 🌍 TIMEZONE - Importar funções de timezone
from utils.timezone_utils import (
    now_sp, now_utc, to_sp, to_utc, 
    format_datetime_br, TIMEZONE_SP
)


def _env_obrigatoria(nome: str) -> str:
    """Lê variável de ambiente. Em produção, ausência (ou valor vazio) é erro fatal."""
    valor = os.environ.get(nome, "")
    if not valor:
        if os.environ.get("ENVIRONMENT") == "production":
            raise RuntimeError(
                f"{nome} não definida. Em produção não existe valor padrão para segredos."
            )
        return f"dev-only-{nome.lower()}"
    return valor


# Configurações do banco de dados
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'sgej_database')

# Configurações de Ambiente e CORS
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
CORS_ORIGINS = [origin.strip() for origin in os.environ.get("CORS_ORIGINS", "").split(",")] if os.environ.get("CORS_ORIGINS") else [
    "https://credito-app-12.preview.emergentagent.com",
    "http://localhost:3000",
    "http://localhost:3001",
]
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8001")
APP_URL = os.environ.get("APP_URL", "http://localhost:3000")

# Configurações JWT
JWT_SECRET_KEY = _env_obrigatoria('JWT_SECRET_KEY')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Configurações SMTP
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SMTP_FROM_EMAIL = os.environ.get('SMTP_FROM_EMAIL', 'noreply@kredor.com.br')
SMTP_FROM_NAME = os.environ.get('SMTP_FROM_NAME', 'Kredor')
SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'

# Duração do teste grátis, em dias.
#
# Fonte única: é esta constante que concede o trial (models/usuario.data_fim_trial) E que a
# landing anuncia (GET /configuracoes/landing sobrescreve o valor guardado com ela). Antes o
# número existia em dois lugares independentes — o código concedia 7 dias e a configuração do
# painel dizia 3 — e a mesma página exibia "3 dias grátis" no topo e "7 dias grátis" em quatro
# outros pontos, porque esses estavam escritos à mão.
TRIAL_DIAS = int(os.environ.get('TRIAL_DIAS', '7'))

# Resend — provedor transacional (HTTP, não SMTP).
#
# Por que sair do SMTP de caixa comum: o remetente autenticava por cobraplus.space, domínio de
# outro produto. Nome "Kredor" com endereço de outro domínio é a assinatura de phishing, e
# 2FA + verificação de email + convite de equipe passam por aí — se o email cai no spam, a
# pessoa não entra na conta. Com o Resend o domínio kredor.com.br envia com DKIM próprio sem
# precisar de caixa postal.
#
# A chave é restrita a envio (least privilege) e vive só no .env, que não vai para o git.
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
RESEND_FROM = os.environ.get('RESEND_FROM', 'Kredor <nao-responda@kredor.com.br>')
# Sem caixa postal em kredor.com.br, resposta a nao-responda@ volta. Preencher quando existir.
RESEND_REPLY_TO = os.environ.get('RESEND_REPLY_TO', '')
RESEND_TIMEOUT = float(os.environ.get('RESEND_TIMEOUT', '20'))

# 'resend' | 'smtp'. Vazio decide pela presença da chave, para o ambiente sem Resend
# continuar funcionando sem precisar declarar nada.
EMAIL_PROVIDER = (os.environ.get('EMAIL_PROVIDER', '') or
                  ('resend' if RESEND_API_KEY else 'smtp')).strip().lower()

# Configurações LLM
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# Cloudflare Turnstile (proteção anti-bot)
TURNSTILE_SECRET_KEY = os.environ.get('TURNSTILE_SECRET_KEY', '')

# Criptografia de campos sensíveis (obrigatória em produção)
FIELD_ENCRYPTION_KEY = _env_obrigatoria('FIELD_ENCRYPTION_KEY')

# Cliente MongoDB
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
