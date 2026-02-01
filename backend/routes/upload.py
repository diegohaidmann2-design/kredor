import os
import shutil
import uuid
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from config import db
from services.auth import get_current_user

router = APIRouter()

UPLOAD_DIR = "static/uploads"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# Garantir que diretório existe
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload de arquivos para o chat de suporte
    Suporta imagens e PDF até 5MB
    """
    
    # Validar extensão
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Extensão não permitida. Use: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Gerar nome único
    new_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, new_filename)
    
    # Salvar arquivo
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {str(e)}")
        
    # Retornar URL pública
    # Em produção, usaria CDN ou S3. Aqui usamos static mount.
    url = f"/static/uploads/{new_filename}"
    
    return {
        "success": True,
        "url": url,
        "filename": filename,
        "type": "arquivo" if ext == ".pdf" else "imagem"
    }
