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

# Configurações JWT
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'sgej-secret-key')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Configurações Stripe
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY', '')

# Configurações LLM
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# Cliente MongoDB
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
