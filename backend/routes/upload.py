import os
import uuid
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import Response
from config import db
from services.auth import get_current_user
from services.object_storage import put_object, get_object, APP_NAME, MIME_TYPES

router = APIRouter()

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload de arquivos para o chat de suporte (imagens e PDF até 5MB).
    Armazenado no Emergent Object Storage (durável em produção).
    """
    filename = file.filename or "arquivo"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensão não permitida. Use: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Arquivo excede o limite de 5MB")

    user_id = getattr(current_user, "id", None) or "anon"
    storage_path = f"{APP_NAME}/uploads/{user_id}/{uuid.uuid4()}{ext}"
    content_type = MIME_TYPES.get(ext.lstrip("."), file.content_type or "application/octet-stream")

    try:
        result = await asyncio.to_thread(put_object, storage_path, data, content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {str(e)}")

    await db.uploads.insert_one({
        "id": str(uuid.uuid4()),
        "storage_path": result["path"],
        "original_filename": filename,
        "content_type": content_type,
        "size": result.get("size", len(data)),
        "uploaded_by": getattr(current_user, "email", None),
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # URL pública servida pelo backend (usável em <img>/<a> sem header de auth)
    url = f"/api/upload/files/{result['path']}"

    return {
        "success": True,
        "url": url,
        "filename": filename,
        "type": "arquivo" if ext == ".pdf" else "imagem"
    }


@router.get("/files/{path:path}")
async def servir_arquivo(path: str):
    """Serve um arquivo do object storage (paths com UUID, não enumeráveis)."""
    record = await db.uploads.find_one({"storage_path": path, "is_deleted": False})
    if not record:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    try:
        data, content_type = await asyncio.to_thread(get_object, path)
    except Exception:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return Response(content=data, media_type=record.get("content_type", content_type))
