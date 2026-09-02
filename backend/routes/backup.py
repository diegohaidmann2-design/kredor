"""
Rotas de Backup e Restore do MongoDB
Camada 2: Backup manual sob demanda
Camada 3: Restore com 1 clique
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import FileResponse
from pathlib import Path

from services.auth import get_current_user, require_admin
from models.usuario import Usuario
from services.backup_service import (
    criar_backup,
    listar_backups,
    restaurar_backup,
    deletar_backup,
    validar_arquivo_backup_tar,
    _nome_seguro_backup,
    _ensure_backup_dir,
    BACKUP_DIR
)
from config import db
from datetime import datetime, timezone
import asyncio
import io
import tarfile
import uuid
from services.object_storage import put_object, get_object, APP_NAME


async def _garantir_backup_local(nome_seguro: str) -> Path:
    """Garante que o backup existe localmente (baixa do object storage se preciso)."""
    _ensure_backup_dir()
    destino = BACKUP_DIR / nome_seguro
    resolved = destino.resolve()
    if not str(resolved).startswith(str(BACKUP_DIR.resolve())):
        raise ValueError("Nome de arquivo inválido")
    if not destino.exists():
        conteudo, _ = await asyncio.to_thread(get_object, f"{APP_NAME}/backups/{nome_seguro}")
        with open(destino, "wb") as f:
            f.write(conteudo)
    return destino


router = APIRouter()


@router.get("/listar")
async def listar(current_user: Usuario = Depends(require_admin)):
    """Lista backups disponíveis (locais + importados no object storage)."""
    backups = list(listar_backups())
    existentes = {b["nome"] for b in backups}

    # Incluir backups registrados em backup_logs (ex.: importados no object storage)
    logs = await db.backup_logs.find(
        {"tipo": {"$in": ["importacao", "manual"]}, "status": "sucesso", "arquivo": {"$exists": True}},
        {"_id": 0}
    ).sort("created_at", -1).to_list(200)

    for log in logs:
        nome = log.get("arquivo")
        if not nome or nome in existentes:
            continue
        existentes.add(nome)
        criado_em = log.get("created_at", "") or ""
        data_formatada = "N/A"
        try:
            data_formatada = datetime.fromisoformat(criado_em).strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            pass
        tamanho_mb = log.get("tamanho_mb", 0) or 0
        backups.append({
            "nome": nome,
            "criado_em": criado_em,
            "data_formatada": data_formatada,
            "tamanho_bytes": int(tamanho_mb * 1024 * 1024),
            "tamanho_mb": tamanho_mb,
        })

    backups.sort(key=lambda b: b.get("criado_em", ""), reverse=True)
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
        await _garantir_backup_local(nome_arquivo)
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
    token: str = None,
    current_user: Usuario = Depends(require_admin)
):
    """Faz download de um arquivo de backup"""
    try:
        arquivo = await _garantir_backup_local(nome_arquivo)
    except Exception:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(
        path=str(arquivo),
        filename=nome_arquivo,
        media_type="application/gzip"
    )


@router.post("/importar")
async def importar(
    arquivo: UploadFile = File(...),
    restaurar_agora: bool = Query(False, description="Se True, restaura o banco imediatamente após o upload"),
    current_user: Usuario = Depends(require_admin)
):
    """
    Importa um arquivo de backup (.tar.gz) enviado pelo usuário.
    Salva na lista de backups e, opcionalmente, restaura imediatamente.
    """
    if not (arquivo.filename or "").endswith(".tar.gz"):
        raise HTTPException(status_code=400, detail="Arquivo inválido. Envie um backup no formato .tar.gz")

    _ensure_backup_dir()

    try:
        nome_seguro = _nome_seguro_backup(arquivo.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Ler o upload em memória e validar sem persistir no disco do pod
    conteudo = await arquivo.read()
    try:
        with tarfile.open(fileobj=io.BytesIO(conteudo), mode="r:gz") as tar:
            nomes = tar.getnames()
        if not any(n.endswith(".bson") for n in nomes):
            raise ValueError("O arquivo não contém dados de backup do MongoDB (.bson)")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Arquivo de backup inválido: {str(e)}")

    # Persistir no Emergent Object Storage (durável em produção)
    try:
        await asyncio.to_thread(put_object, f"{APP_NAME}/backups/{nome_seguro}", conteudo, "application/gzip")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao armazenar backup: {str(e)}")

    tamanho_mb = round(len(conteudo) / (1024 * 1024), 2)

    await db.backup_logs.insert_one({
        "id": str(uuid.uuid4()),
        "tipo": "importacao",
        "iniciado_por": current_user.email,
        "arquivo": nome_seguro,
        "tamanho_mb": tamanho_mb,
        "status": "sucesso",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    resultado = {
        "sucesso": True,
        "nome": nome_seguro,
        "tamanho_mb": tamanho_mb,
        "restaurado": False,
        "mensagem": f"Backup '{nome_seguro}' importado com sucesso. Use 'Restaurar' para aplicá-lo."
    }

    if restaurar_agora:
        try:
            await _garantir_backup_local(nome_seguro)
            restore = await restaurar_backup(nome_seguro)
            resultado["restaurado"] = True
            resultado["mensagem"] = restore.get("mensagem", "Backup importado e restaurado com sucesso")
            await db.backup_logs.insert_one({
                "id": str(uuid.uuid4()),
                "tipo": "restore",
                "iniciado_por": current_user.email,
                "arquivo": nome_seguro,
                "status": "sucesso",
                "created_at": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            await db.backup_logs.insert_one({
                "id": str(uuid.uuid4()),
                "tipo": "restore",
                "iniciado_por": current_user.email,
                "arquivo": nome_seguro,
                "status": "erro",
                "erro": str(e),
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            raise HTTPException(
                status_code=500,
                detail=f"Backup importado, mas falhou ao restaurar: {str(e)}"
            )

    return resultado


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
