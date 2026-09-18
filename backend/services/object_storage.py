"""
Serviço de armazenamento de objetos: anexos do chat de suporte e backups importados.

Com EMERGENT_LLM_KEY configurada, usa o Emergent Object Storage. Sem ela — instalação própria,
fora da plataforma Emergent —, grava em disco, em OBJECT_STORAGE_DIR (padrão /app/storage), que
precisa ser um volume persistente. A interface é a mesma nos dois casos.
"""
import mimetypes
import os
from pathlib import Path

import requests

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "gestorcred"

ARMAZENAMENTO_LOCAL = not EMERGENT_KEY
DIRETORIO_LOCAL = Path(os.environ.get("OBJECT_STORAGE_DIR", "/app/storage"))

_storage_key = None


def _caminho_local(path: str) -> Path:
    """Arquivo do objeto dentro de DIRETORIO_LOCAL. Recusa caminho que saia dele (path traversal)."""
    raiz = DIRETORIO_LOCAL.resolve()
    destino = (raiz / path).resolve()
    if raiz not in destino.parents:
        raise ValueError(f"Caminho de objeto inválido: {path}")
    return destino


def init_storage(force: bool = False):
    """Inicializa (uma vez) a chave de sessão do storage."""
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    """Envia bytes para o storage. Retorna {"path","size","etag"}."""
    if ARMAZENAMENTO_LOCAL:
        destino = _caminho_local(path)
        destino.parent.mkdir(parents=True, exist_ok=True)
        # Grava ao lado e renomeia: um backup grande nunca fica pela metade se o processo cair.
        parcial = destino.with_name(destino.name + ".parcial")
        parcial.write_bytes(data)
        parcial.replace(destino)
        return {"path": path, "size": len(data), "etag": None}

    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120
    )
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data, timeout=120
        )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    """Baixa um objeto. Retorna (bytes, content_type)."""
    if ARMAZENAMENTO_LOCAL:
        origem = _caminho_local(path)
        if not origem.is_file():
            raise FileNotFoundError(f"Objeto não encontrado: {path}")
        return origem.read_bytes(), mimetypes.guess_type(origem.name)[0] or "application/octet-stream"

    key = init_storage()
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key}, timeout=60
    )
    if resp.status_code == 404:
        key = init_storage(force=True)
        resp = requests.get(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key}, timeout=60
        )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


def delete_object(path: str) -> bool:
    """Remove um objeto do storage. Retorna True se removido.

    Em disco (instalação self-hosted) apaga o arquivo. No Emergent Object Storage
    não existe API de exclusão — a fonte da verdade é o banco, e remover a referência
    já revoga o acesso; aqui tentamos por compatibilidade e seguimos se não suportado.
    """
    if ARMAZENAMENTO_LOCAL:
        try:
            origem = _caminho_local(path)
        except ValueError:
            return False
        if origem.is_file():
            origem.unlink()
            return True
        return False

    try:
        key = init_storage()
        resp = requests.delete(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key}, timeout=60
        )
        return resp.status_code in (200, 204)
    except Exception:
        return False


MIME_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp", "pdf": "application/pdf",
}
