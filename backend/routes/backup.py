"""
Rotas de Backup e Restore do MongoDB
Camada 2: Backup manual sob demanda
Camada 3: Restore com 1 clique
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pathlib import Path

from services.auth import get_current_user, require_admin
from models.usuario import Usuario
from services.backup_service import (
    criar_backup,
    listar_backups,
    restaurar_backup,
    deletar_backup,
    BACKUP_DIR
)
from config import db
from datetime import datetime, timezone
import uuid

router = APIRouter()


@router.get("/listar")
async def listar(current_user: Usuario = Depends(require_admin)):
    """Lista todos os backups disponíveis"""
    backups = listar_backups()
    return {
        "backups": backups,
        "total": len(backups),
        "pasta": str(BACKUP_DIR)
    }


@router.post("/criar")
async def criar(current_user: Usuario = Depends(require_admin)):
    """Cria um backup manual agora"""
    try:
        info = await criar_backup(iniciado_por=current_user.email)

        # Registrar no log de backups
        await db.backup_logs.insert_one({
            "id": str(uuid.uuid4()),
            "tipo": "manual",
            "iniciado_por": current_user.email,
            "arquivo": info["nome"],
            "tamanho_mb": info["tamanho_mb"],
            "status": "sucesso",
            "created_at": datetime.now(timezone.utc).isoformat()
        })

        return {
            "sucesso": True,
            "mensagem": f"Backup criado com sucesso: {info['nome']}",
            "backup": info
        }
    except Exception as e:
        await db.backup_logs.insert_one({
            "id": str(uuid.uuid4()),
            "tipo": "manual",
            "iniciado_por": current_user.email,
            "status": "erro",
            "erro": str(e),
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        raise HTTPException(status_code=500, detail=f"Erro ao criar backup: {str(e)}")


@router.post("/restaurar/{nome_arquivo:path}")
async def restaurar(
    nome_arquivo: str,
    current_user: Usuario = Depends(require_admin)
):
    """Restaura o banco a partir de um backup"""
    try:
        resultado = await restaurar_backup(nome_arquivo)

        # Registrar no log
        await db.backup_logs.insert_one({
            "id": str(uuid.uuid4()),
            "tipo": "restore",
            "iniciado_por": current_user.email,
            "arquivo": nome_arquivo,
            "status": "sucesso",
            "created_at": datetime.now(timezone.utc).isoformat()
        })

        return resultado
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.backup_logs.insert_one({
            "id": str(uuid.uuid4()),
            "tipo": "restore",
            "iniciado_por": current_user.email,
            "arquivo": nome_arquivo,
            "status": "erro",
            "erro": str(e),
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        raise HTTPException(status_code=500, detail=f"Erro ao restaurar: {str(e)}")


@router.delete("/deletar/{nome_arquivo:path}")
async def deletar(
    nome_arquivo: str,
    current_user: Usuario = Depends(require_admin)
):
    """Deleta um arquivo de backup"""
    try:
        resultado = await deletar_backup(nome_arquivo)
        return resultado
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao deletar: {str(e)}")


@router.get("/download/{nome_arquivo:path}")
async def download(
    nome_arquivo: str,
    current_user: Usuario = Depends(require_admin)
):
    """Faz download de um arquivo de backup"""
    arquivo = BACKUP_DIR / nome_arquivo
    if not arquivo.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    
    return FileResponse(
        path=str(arquivo),
        filename=nome_arquivo,
        media_type="application/gzip"
    )


@router.get("/logs")
async def listar_logs(
    limit: int = 50,
    current_user: Usuario = Depends(require_admin)
):
    """Lista os logs de backup/restore"""
    logs = await db.backup_logs.find(
        {}, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "logs": logs,
        "total": len(logs)
    }


@router.get("/status")
async def status_backup(current_user: Usuario = Depends(require_admin)):
    """Retorna status geral do sistema de backup"""
    backups = listar_backups()
    
    ultimo_backup = backups[0] if backups else None
    ultimo_log = await db.backup_logs.find_one(
        {"tipo": "automatico", "status": "sucesso"},
        {"_id": 0},
        sort=[("created_at", -1)]
    )

    return {
        "total_backups": len(backups),
        "pasta": str(BACKUP_DIR),
        "ultimo_backup": ultimo_backup,
        "ultimo_backup_automatico": ultimo_log,
        "proximo_backup_automatico": "A cada 6 horas (job agendado)",
        "max_backups": 30
    }
