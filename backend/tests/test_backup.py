"""
Testes para o sistema de Backup & Restore
Testa todas as rotas: /api/backup/listar, criar, status, logs, restaurar, deletar, download
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Credenciais admin
ADMIN_EMAIL = "admin@gestorcerd.com"
ADMIN_SENHA = "admin123"

@pytest.fixture(scope="module")
def token():
    res = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "senha": ADMIN_SENHA})
    if res.status_code != 200:
        pytest.skip(f"Login falhou: {res.status_code} {res.text}")
    return res.json().get("token") or res.json().get("access_token")

@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestBackupStatus:
    """Testa GET /api/backup/status"""
    def test_status_ok(self, headers):
        res = requests.get(f"{BASE_URL}/api/backup/status", headers=headers)
        assert res.status_code == 200, f"Status esperado 200, obtido {res.status_code}: {res.text}"
        data = res.json()
        assert "total_backups" in data
        assert "max_backups" in data
        assert data["max_backups"] == 30
        print(f"✅ Status: total_backups={data['total_backups']}, max={data['max_backups']}")


class TestBackupListar:
    """Testa GET /api/backup/listar"""
    def test_listar_ok(self, headers):
        res = requests.get(f"{BASE_URL}/api/backup/listar", headers=headers)
        assert res.status_code == 200, f"Status esperado 200: {res.text}"
        data = res.json()
        assert "backups" in data
        assert "total" in data
        assert isinstance(data["backups"], list)
        print(f"✅ Listar: {data['total']} backups encontrados")


class TestBackupLogs:
    """Testa GET /api/backup/logs"""
    def test_logs_ok(self, headers):
        res = requests.get(f"{BASE_URL}/api/backup/logs", headers=headers)
        assert res.status_code == 200, f"Status esperado 200: {res.text}"
        data = res.json()
        assert "logs" in data
        assert isinstance(data["logs"], list)
        print(f"✅ Logs: {data['total']} logs encontrados")


class TestBackupCriar:
    """Testa POST /api/backup/criar"""
    created_backup_name = None

    def test_criar_backup(self, headers):
        res = requests.post(f"{BASE_URL}/api/backup/criar", headers=headers)
        assert res.status_code == 200, f"Falha ao criar backup: {res.text}"
        data = res.json()
        assert data.get("sucesso") is True
        assert "backup" in data
        assert "nome" in data["backup"]
        TestBackupCriar.created_backup_name = data["backup"]["nome"]
        print(f"✅ Backup criado: {TestBackupCriar.created_backup_name}")

    def test_backup_aparece_na_lista(self, headers):
        if not TestBackupCriar.created_backup_name:
            pytest.skip("Backup não foi criado no teste anterior")
        res = requests.get(f"{BASE_URL}/api/backup/listar", headers=headers)
        assert res.status_code == 200
        nomes = [b["nome"] for b in res.json()["backups"]]
        assert TestBackupCriar.created_backup_name in nomes
        print(f"✅ Backup aparece na lista: {TestBackupCriar.created_backup_name}")

    def test_log_criado_apos_backup(self, headers):
        if not TestBackupCriar.created_backup_name:
            pytest.skip("Backup não foi criado")
        res = requests.get(f"{BASE_URL}/api/backup/logs", headers=headers)
        assert res.status_code == 200
        logs = res.json()["logs"]
        manual_logs = [l for l in logs if l.get("tipo") == "manual"]
        assert len(manual_logs) > 0
        print(f"✅ Log manual registrado: {manual_logs[0].get('arquivo')}")


class TestBackupDeletar:
    """Testa DELETE /api/backup/deletar/{nome}"""
    
    def test_deletar_backup_inexistente(self, headers):
        res = requests.delete(f"{BASE_URL}/api/backup/deletar/arquivo-nao-existe.tar.gz", headers=headers)
        assert res.status_code == 404
        print("✅ Retorna 404 para arquivo inexistente")

    def test_criar_e_deletar_backup(self, headers):
        # Criar backup para deletar
        res = requests.post(f"{BASE_URL}/api/backup/criar", headers=headers)
        assert res.status_code == 200
        nome = res.json()["backup"]["nome"]

        # Deletar
        res_del = requests.delete(f"{BASE_URL}/api/backup/deletar/{nome}", headers=headers)
        assert res_del.status_code == 200, f"Falha ao deletar: {res_del.text}"
        data = res_del.json()
        assert data.get("status") == "sucesso"

        # Verificar que não existe mais na lista
        res_list = requests.get(f"{BASE_URL}/api/backup/listar", headers=headers)
        nomes = [b["nome"] for b in res_list.json()["backups"]]
        assert nome not in nomes
        print(f"✅ Backup deletado e removido da lista: {nome}")


class TestBackupDownload:
    """Testa GET /api/backup/download/{nome}"""

    def test_download_inexistente(self, headers):
        res = requests.get(f"{BASE_URL}/api/backup/download/arquivo-nao-existe.tar.gz", headers=headers)
        assert res.status_code == 404
        print("✅ Download retorna 404 para arquivo inexistente")

    def test_download_backup_existente(self, headers):
        # Primeiro verificar se há backups
        res_list = requests.get(f"{BASE_URL}/api/backup/listar", headers=headers)
        backups = res_list.json()["backups"]
        if not backups:
            # Criar um
            res_criar = requests.post(f"{BASE_URL}/api/backup/criar", headers=headers)
            assert res_criar.status_code == 200
            nome = res_criar.json()["backup"]["nome"]
        else:
            nome = backups[0]["nome"]
        
        res = requests.get(f"{BASE_URL}/api/backup/download/{nome}", headers=headers)
        assert res.status_code == 200
        assert len(res.content) > 0
        print(f"✅ Download OK: {nome} ({len(res.content)} bytes)")


class TestBackupScheduler:
    """Testa se job backup_automatico está no scheduler"""
    def test_scheduler_tem_job_backup(self, headers):
        res = requests.get(f"{BASE_URL}/api/admin/scheduler/status", headers=headers)
        assert res.status_code == 200, f"Scheduler endpoint falhou: {res.status_code} {res.text}"
        data = res.json()
        # Procurar pelo job de backup (resposta aninhada em scheduler.jobs)
        jobs = data.get("jobs") or data.get("scheduler", {}).get("jobs", [])
        job_ids = [j.get("id", "") for j in jobs]
        backup_job = any("backup" in j_id.lower() for j_id in job_ids)
        assert backup_job, f"Job de backup não encontrado. Jobs disponíveis: {job_ids}"
        print(f"✅ Job de backup encontrado no scheduler: {[j for j in job_ids if 'backup' in j.lower()]}")
