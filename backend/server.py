"""
Arquivo de entrada para o Uvicorn.
Importa a aplicação FastAPI do módulo main.
"""
from main import app

# Re-exportar app para o uvicorn
__all__ = ['app']
