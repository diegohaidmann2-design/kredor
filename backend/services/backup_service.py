"""
Serviço de Backup e Restore do MongoDB
Camada 1: Backup automático periódico
Camada 2: Backup manual sob demanda
Camada 3: Restore com 1 clique
"""
import os
import subprocess
import tarfile
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

BACKUP_DIR = Path("/app/backups")
MAX_BACKUPS = 30  # Manter últimos 30 dias


def _get_mongo_config() -> Dict[str, str]:
    return {
        "uri": os.environ.get("MONGO_URL", "mongodb://localhost:27017"),
        "db": os.environ.get("DB_NAME", "test_database"),
    }


def _ensure_backup_dir():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _cleanup_old_backups():
    """Remove backups mais antigos mantendo apenas os últimos MAX_BACKUPS"""
    backups = sorted(
        BACKUP_DIR.glob("backup-*.tar.gz"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )
    for old in backups[MAX_BACKUPS:]:
        old.unlink()
        print(f"   🗑️  Backup antigo removido: {old.name}")


async def criar_backup(iniciado_por: str = "sistema") -> Dict:
    """
    Cria um backup completo do banco de dados
    Retorna informações sobre o backup criado
    """
    _ensure_backup_dir()
    
    config = _get_mongo_config()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_name = f"backup-{timestamp}"
    temp_dir = Path(f"/tmp/{backup_name}")
    archive_path = BACKUP_DIR / f"{backup_name}.tar.gz"

    print(f"📦 Iniciando backup: {backup_name}")
    print(f"   DB: {config['db']} @ {config['uri']}")

    try:
        # 1. mongodump
        temp_dir.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                "mongodump",
                f"--uri={config['uri']}",
                f"--db={config['db']}",
                f"--out={temp_dir}",
                "--quiet"
            ],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            raise RuntimeError(f"mongodump falhou: {result.stderr}")

        # 2. Comprimir em .tar.gz
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(temp_dir, arcname=backup_name)

        # 3. Calcular tamanho
        size_bytes = archive_path.stat().st_size
        size_mb = round(size_bytes / (1024 * 1024), 2)

        # 4. Limpar backups antigos
        _cleanup_old_backups()

        info = {
            "id": str(uuid.uuid4()),
            "nome": f"{backup_name}.tar.gz",
            "timestamp": timestamp,
            "criado_em": datetime.now(timezone.utc).isoformat(),
            "tamanho_bytes": size_bytes,
            "tamanho_mb": size_mb,
            "banco": config["db"],
            "iniciado_por": iniciado_por,
            "status": "sucesso",
        }

        print(f"✅ Backup criado: {archive_path.name} ({size_mb} MB)")
        return info

    except Exception as e:
        print(f"❌ Erro ao criar backup: {e}")
        # Limpar arquivos parciais
        if archive_path.exists():
            archive_path.unlink()
        raise
    finally:
        # Sempre limpar diretório temporário
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def listar_backups() -> List[Dict]:
    """Lista todos os backups disponíveis em /app/backups/"""
    _ensure_backup_dir()

    backups = []
    for f in sorted(BACKUP_DIR.glob("backup-*.tar.gz"), reverse=True):
        stat = f.stat()
        size_bytes = stat.st_size
        size_mb = round(size_bytes / (1024 * 1024), 2)
        
        # Extrair timestamp do nome: backup-YYYYMMDD-HHMMSS.tar.gz
        name = f.stem.replace(".tar", "")  # backup-YYYYMMDD-HHMMSS
        parts = name.split("-", 1)
        timestamp_str = parts[1] if len(parts) > 1 else ""
        
        try:
            dt = datetime.strptime(timestamp_str, "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
            criado_em = dt.isoformat()
            data_formatada = dt.strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            criado_em = ""
            data_formatada = "N/A"

        backups.append({
            "nome": f.name,
            "criado_em": criado_em,
            "data_formatada": data_formatada,
            "tamanho_bytes": size_bytes,
            "tamanho_mb": size_mb,
        })

    return backups


async def restaurar_backup(nome_arquivo: str) -> Dict:
    """
    Restaura o banco de dados a partir de um arquivo de backup
    ATENÇÃO: Isso sobrescreve os dados atuais!
    """
    config = _get_mongo_config()
    archive_path = BACKUP_DIR / nome_arquivo

    # Fix #3: Path Traversal — validar que o arquivo fica dentro de BACKUP_DIR
    resolved = (BACKUP_DIR / nome_arquivo).resolve()
    if not str(resolved).startswith(str(BACKUP_DIR.resolve())):
        raise ValueError("Caminho inválido: acesso negado")

    if not resolved.exists():
        raise FileNotFoundError(f"Arquivo de backup não encontrado: {nome_arquivo}")

    if not nome_arquivo.endswith(".tar.gz"):
        raise ValueError("Arquivo inválido. Esperado: .tar.gz")

    temp_dir = Path(f"/tmp/restore-{uuid.uuid4().hex[:8]}")
    print(f"🔄 Iniciando restore: {nome_arquivo}")

    try:
        # 1. Extrair arquivo
        temp_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(temp_dir)

        # 2. Encontrar diretório com o DB
        # Estrutura: temp_dir/backup-YYYYMMDD-HHMMSS/<DB_NAME>/
        db_dir = None
        for item in temp_dir.rglob(config["db"]):
            if item.is_dir():
                db_dir = item
                break

        # Se não encontrou pelo nome do banco, pegar o primeiro diretório disponível
        if db_dir is None:
            for root_dir in temp_dir.iterdir():
                if root_dir.is_dir():
                    for sub in root_dir.iterdir():
                        if sub.is_dir():
                            db_dir = sub
                            break
                    if db_dir:
                        break

        if db_dir is None:
            raise RuntimeError("Estrutura do backup inválida: diretório do banco não encontrado")

        print(f"   Diretório do banco encontrado: {db_dir}")

        # 3. mongorestore com --drop para substituir dados
        result = subprocess.run(
            [
                "mongorestore",
                f"--uri={config['uri']}",
                f"--db={config['db']}",
                "--drop",
                "--quiet",
                str(db_dir)
            ],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            raise RuntimeError(f"mongorestore falhou: {result.stderr}")

        print(f"✅ Restore concluído: {nome_arquivo}")

        return {
            "status": "sucesso",
            "arquivo": nome_arquivo,
            "banco": config["db"],
            "restaurado_em": datetime.now(timezone.utc).isoformat(),
            "mensagem": f"Banco '{config['db']}' restaurado com sucesso a partir de {nome_arquivo}"
        }

    except Exception as e:
        print(f"❌ Erro ao restaurar backup: {e}")
        raise
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


async def deletar_backup(nome_arquivo: str) -> Dict:
    """Deleta um arquivo de backup específico"""
    # Fix #3: Path Traversal check
    resolved = (BACKUP_DIR / nome_arquivo).resolve()
    if not str(resolved).startswith(str(BACKUP_DIR.resolve())):
        raise ValueError("Caminho inválido: acesso negado")

    if not resolved.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {nome_arquivo}")

    resolved.unlink()
    print(f"🗑️  Backup deletado: {nome_arquivo}")
    
    return {
        "status": "sucesso",
        "arquivo": nome_arquivo,
        "mensagem": f"Backup {nome_arquivo} deletado com sucesso"
    }
