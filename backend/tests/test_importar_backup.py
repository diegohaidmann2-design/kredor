"""
Teste de regressão do endpoint POST /api/backup/importar.

Valida:
  - Importar um .tar.gz de backup válido -> salvo e listado.
  - Importar com restaurar_agora=true -> restaura o banco.
  - Arquivo inválido -> 400.

Executa contra o servidor backend rodando (localhost:8001) usando token de admin.

Uso:
    python -m tests.test_importar_backup
"""
import asyncio

import httpx

from config import db
from services.auth import criar_tokens
from services.backup_service import criar_backup, deletar_backup, BACKUP_DIR

BASE = "http://localhost:8001"


async def _admin_token():
    u = await db.usuarios.find_one(
        {"perfil": {"$in": ["admin", "superadmin"]}, "deleted": {"$ne": True}},
        {"_id": 0, "id": 1}
    )
    assert u, "Nenhum admin encontrado"
    at, _ = criar_tokens(u["id"])
    return at


async def run():
    token = await _admin_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Gera um backup para usar como arquivo de upload
    info = await criar_backup(iniciado_por="teste")
    origem = BACKUP_DIR / info["nome"]
    conteudo = origem.read_bytes()

    importados = []
    try:
        async with httpx.AsyncClient(base_url=BASE, timeout=120) as client:
            # 1. Importar válido (sem restaurar)
            r = await client.post(
                "/api/backup/importar",
                headers=headers,
                files={"arquivo": ("meu_backup_local.tar.gz", conteudo, "application/gzip")},
            )
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["restaurado"] is False
            importados.append(d["nome"])
            print("1) import válido:", d["nome"])

            # Deve aparecer na listagem
            rl = await client.get("/api/backup/listar", headers=headers)
            nomes = [b["nome"] for b in rl.json()["backups"]]
            assert d["nome"] in nomes, "Backup importado não apareceu na listagem"

            # 2. Importar com restauração imediata
            r2 = await client.post(
                "/api/backup/importar?restaurar_agora=true",
                headers=headers,
                files={"arquivo": ("meu_backup_local.tar.gz", conteudo, "application/gzip")},
            )
            assert r2.status_code == 200, r2.text
            d2 = r2.json()
            assert d2["restaurado"] is True, d2
            importados.append(d2["nome"])
            print("2) import + restore:", d2["mensagem"])

            # 3. Arquivo inválido -> 400
            r3 = await client.post(
                "/api/backup/importar",
                headers=headers,
                files={"arquivo": ("fake.tar.gz", b"isto nao e um backup", "application/gzip")},
            )
            assert r3.status_code == 400, r3.text
            print("3) arquivo inválido rejeitado:", r3.json()["detail"])

        print("✅ TESTE PASSOU: importação de backup funcionando (upload, restore e validação).")
    finally:
        # Cleanup dos arquivos de teste
        for nome in importados + [info["nome"]]:
            try:
                await deletar_backup(nome)
            except Exception:
                pass
        print("🧹 Backups de teste removidos.")


if __name__ == "__main__":
    asyncio.run(run())
