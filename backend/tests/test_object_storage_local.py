"""Armazenamento em disco, usado quando não há EMERGENT_LLM_KEY (instalação própria)."""
import pytest

from services import object_storage


@pytest.fixture
def storage_local(tmp_path, monkeypatch):
    monkeypatch.setattr(object_storage, "ARMAZENAMENTO_LOCAL", True)
    monkeypatch.setattr(object_storage, "DIRETORIO_LOCAL", tmp_path)
    return tmp_path


def test_grava_e_le_o_mesmo_conteudo(storage_local):
    resultado = object_storage.put_object("gestorcred/backups/backup-x.tar.gz", b"\x1f\x8bdados", "application/gzip")

    assert resultado == {"path": "gestorcred/backups/backup-x.tar.gz", "size": 7, "etag": None}
    assert (storage_local / "gestorcred/backups/backup-x.tar.gz").read_bytes() == b"\x1f\x8bdados"
    conteudo, _ = object_storage.get_object("gestorcred/backups/backup-x.tar.gz")
    assert conteudo == b"\x1f\x8bdados"


def test_tipo_do_arquivo_vem_da_extensao(storage_local):
    object_storage.put_object("gestorcred/uploads/u1/a.pdf", b"%PDF", "application/pdf")

    _, tipo = object_storage.get_object("gestorcred/uploads/u1/a.pdf")

    assert tipo == "application/pdf"


def test_nao_deixa_arquivo_parcial(storage_local):
    object_storage.put_object("gestorcred/backups/b.tar.gz", b"abc", "application/gzip")

    assert not list(storage_local.rglob("*.parcial"))


def test_objeto_inexistente_levanta_file_not_found(storage_local):
    with pytest.raises(FileNotFoundError):
        object_storage.get_object("gestorcred/uploads/nao-existe.png")


@pytest.mark.parametrize("caminho", ["../fora.txt", "gestorcred/../../fora.txt", "/etc/passwd"])
def test_recusa_caminho_fora_do_diretorio(storage_local, caminho):
    with pytest.raises(ValueError):
        object_storage.put_object(caminho, b"x", "text/plain")
    with pytest.raises(ValueError):
        object_storage.get_object(caminho)
