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

# Configurações do banco de dados
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'sgej_database')

# Configurações de Ambiente e CORS
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
CORS_ORIGINS = [origin.strip() for origin in os.environ.get("CORS_ORIGINS", "").split(",")] if os.environ.get("CORS_ORIGINS") else [
    "https://cred-manager-28.preview.emergentagent.com",
    "http://localhost:3000",
    "http://localhost:3001",
    "*"
]
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8001")
APP_URL = os.environ.get("APP_URL", "http://localhost:3000")

# Configurações JWT
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'sgej-secret-key')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Configurações SMTP
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SMTP_FROM_EMAIL = os.environ.get('SMTP_FROM_EMAIL', 'noreply@gestorcred.com.br')
SMTP_FROM_NAME = os.environ.get('SMTP_FROM_NAME', 'Gestor Cred')
SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'

# Configurações LLM
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# Cliente MongoDB
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
