"""E2E de backup: importar, listar, baixar e restaurar, com mongodump/mongorestore reais.

Cobre o caso que zerou o painel em 11/09/2026: um backup gerado antes da Fase 1 guarda o dinheiro
em reais (float). Depois de restaurado, o empréstimo tem de aparecer em centavos, sem nenhum passo
manual. Usa só bancos descartáveis (kredor_e2e_origem e kredor_e2e_destino) e apaga os dois no fim.

Não é coletado pelo pytest (não começa com test_). Rodar da raiz do repositório:

    docker run --rm --network kredor_network --env-file backend/.env \\
      -e MONGO_URL='mongodb://kredor_mongodb:27017/kredor_e2e_destino?replicaSet=rs0' \\
      -e DB_NAME=kredor_e2e_destino -e OBJECT_STORAGE_DIR=/tmp/st -e PYTHONPATH=/app \\
      --tmpfs /app/static:mode=1777 --tmpfs /app/backups:mode=1777 --tmpfs /tmp/st:mode=1777 \\
      -v "$PWD/backend:/app" -w /app --entrypoint python kredor-backend tests/e2e_backup_restore.py

Sem EMERGENT_LLM_KEY no ambiente, o armazenamento é o disco (OBJECT_STORAGE_DIR).
Sai com código 1 se qualquer verificação falhar.
"""
import asyncio
import io
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import httpx
from motor.motor_asyncio import AsyncIOMotorClient

from config import db
from main import app
from models.usuario import Usuario
from services import object_storage
from services.auth import criar_tokens

URI = "mongodb://kredor_mongodb:27017/?replicaSet=rs0"
FALHAS = []


def conferir(condicao, mensagem):
    print(("  OK    " if condicao else "  FALHA ") + mensagem)
    if not condicao:
        FALHAS.append(mensagem)


def gerar_dump_tar() -> bytes:
    """mongodump do banco de origem, empacotado como o /admin/backup gera."""
    with tempfile.TemporaryDirectory() as tmp:
        saida = Path(tmp) / "backup-origem"
        r = subprocess.run(["mongodump", f"--uri={URI}", "--db=kredor_e2e_origem", f"--out={saida}", "--quiet"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"mongodump falhou: {r.stderr}")
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            tar.add(saida, arcname="backup-origem")
        return buf.getvalue()


async def cenario(c, h, conteudo):
    print("\n[1] Importar")
    r = await c.post("/api/backup/importar", headers=h,
                     files={"arquivo": ("meu-dump.tar.gz", conteudo, "application/gzip")})
    conferir(r.status_code == 200, f"importar -> {r.status_code} {r.text[:160]}")
    if r.status_code != 200:
        return
    nome = r.json()["nome"]
    guardado = object_storage.DIRETORIO_LOCAL / "gestorcred/backups" / nome
    conferir(guardado.is_file() and guardado.read_bytes() == conteudo, "arquivo guardado no disco, bytes iguais")

    print("\n[2] Listar e baixar")
    r = await c.get("/api/backup/listar", headers=h)
    conferir(any(b["nome"] == nome for b in r.json()["backups"]), "aparece na listagem")
    r = await c.get(f"/api/backup/download/{nome}", headers=h)
    conferir(r.status_code == 200 and r.content == conteudo, f"download -> {r.status_code}, bytes iguais")

    print("\n[3] Restaurar um backup em reais")
    r = await c.post(f"/api/backup/restaurar/{nome}", headers=h)
    conferir(r.status_code == 200, f"restaurar -> {r.status_code} {r.text[:200]}")
    corpo = r.json() if r.status_code == 200 else {}
    conferir((corpo.get("convertidos_para_centavos") or {}).get("emprestimos") == 1,
             f"resposta informa a conversão: {corpo.get('convertidos_para_centavos')}")
    emp = await db.emprestimos.find_one({"id": "emp-legado"}, {"_id": 0})
    conferir(emp is not None, "empréstimo restaurado no banco de destino")
    if emp:
        conferir(emp.get("valor_principal_centavos") == 123456, f"valor_principal_centavos = {emp.get('valor_principal_centavos')} (esperado 123456)")
        conferir("valor_principal" not in emp, "campo em reais removido")
    n = await db.clientes.count_documents({"id": {"$in": ["c0", "c1", "c2"]}})
    conferir(n == 3, f"clientes restaurados: {n}")

    print("\n[4] Restaurar de novo não converte duas vezes")
    r = await c.post(f"/api/backup/restaurar/{nome}", headers=h)
    emp = await db.emprestimos.find_one({"id": "emp-legado"}, {"_id": 0})
    conferir(r.status_code == 200 and emp and emp.get("valor_principal_centavos") == 123456,
             f"2ª restauração -> {r.status_code}, valor continua {emp and emp.get('valor_principal_centavos')}")

    print("\n[5] Entradas inválidas")
    r = await c.post("/api/backup/importar", headers=h,
                     files={"arquivo": ("x.tar.gz", b"nao e gzip", "application/gzip")})
    conferir(r.status_code == 400, f"arquivo que não é backup -> {r.status_code}")
    r = await c.get("/api/backup/download/..%2F..%2Fetc%2Fpasswd", headers=h)
    conferir(r.status_code == 404, f"path traversal no download -> {r.status_code}")


async def main():
    cli = AsyncIOMotorClient(URI)
    origem = cli["kredor_e2e_origem"]
    await origem.clientes.insert_many([{"id": f"c{i}", "nome": f"Cliente {i}"} for i in range(3)])
    # Formato anterior à Fase 1: dinheiro em reais, float.
    await origem.emprestimos.insert_one({"id": "emp-legado", "cliente_id": "c0", "status": "ativo",
                                         "valor_principal": 1234.56})
    conteudo = await asyncio.to_thread(gerar_dump_tar)
    print(f"dump: {len(conteudo)} bytes | armazenamento local: {object_storage.ARMAZENAMENTO_LOCAL} "
          f"em {object_storage.DIRETORIO_LOCAL}")

    admin = Usuario(nome="Admin E2E", email="admin@kredor-e2e.com.br", perfil="admin", email_verificado=True)
    doc = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in admin.model_dump().items()}
    doc["senha_hash"] = "sem-login"
    await db.usuarios.insert_one(doc)
    h = {"Authorization": f"Bearer {criar_tokens(admin.id)[0]}"}
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://teste") as c:
            await cenario(c, h, conteudo)
    except Exception as e:  # exceção no meio do cenário também é falha, nunca sucesso silencioso
        conferir(False, f"exceção no cenário: {type(e).__name__}: {e}")
    finally:
        await cli.drop_database("kredor_e2e_origem")
        await cli.drop_database("kredor_e2e_destino")


asyncio.run(main())
# O veredito fica fora de main(): nenhum return antecipado pode pular o código de saída.
print(f"\n{'TUDO OK' if not FALHAS else f'{len(FALHAS)} FALHA(S)'}")
sys.exit(1 if FALHAS else 0)
