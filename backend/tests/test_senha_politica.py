"""Política única de senha e normalização de email.

Antes havia quatro réguas diferentes na mesma base de usuários: o cadastro exigia 6
caracteres, o convite de membro e o aceite de convite não exigiam nada, e a troca de senha
também não. A conta vale pela porta mais frouxa, então a régua passou a ser uma só.
"""
import pytest
from fastapi import HTTPException

from models.usuario import LoginRequest, UsuarioCreate, normalizar_email
from services.auth import SENHA_MINIMA, validar_forca_senha


def recusa(senha, **kwargs):
    with pytest.raises(HTTPException) as e:
        validar_forca_senha(senha, **kwargs)
    assert e.value.status_code == 422
    return e.value.detail


# --- força da senha -------------------------------------------------------------------

def test_aceita_senha_razoavel():
    validar_forca_senha("Kr3dor-2026x")
    validar_forca_senha("mariana47banco")


def test_recusa_curta():
    assert str(SENHA_MINIMA) in recusa("Ab1c2")


def test_recusa_sem_numero_ou_sem_letra():
    assert "letras e números" in recusa("senhasegura")
    assert "letras e números" in recusa("184920571")


def test_recusa_as_obvias():
    for senha in ("senha123", "password123", "admin123", "qwerty123"):
        assert "muito comum" in recusa(senha)


def test_recusa_pouca_variacao():
    # 8 caracteres, tem letra e número, e não protege nada.
    assert "variação" in recusa("a1a1a1a1")


def test_recusa_senha_que_contem_o_email():
    detalhe = recusa("mariana2026", email="mariana@empresa.com")
    assert "email" in detalhe
    # O local part curto não vira proibição: "ana" apareceria em senha demais.
    validar_forca_senha("anabela2026x", email="ana@empresa.com")


def test_nome_do_campo_aparece_na_mensagem():
    # A tela mostra o detail cru; "a senha do membro" e "a nova senha" precisam se distinguir.
    assert "senha do membro" in recusa("abc", campo="senha do membro")
    assert "nova senha" in recusa("abc", campo="nova senha")


# --- normalização de email ------------------------------------------------------------

def test_normalizar_email():
    assert normalizar_email("  Joao@Empresa.COM ") == "joao@empresa.com"
    assert normalizar_email(None) is None


def test_modelos_normalizam_na_borda():
    """O índice único de usuarios.email é sensível a maiúsculas.

    Sem normalizar na validação, "Joao@x.com" cria uma segunda conta, a checagem de
    duplicado não pega, e quem foi cadastrado com maiúscula não entra digitando minúscula.
    """
    assert UsuarioCreate(nome="J", email="Joao@Empresa.COM", senha="Kr3dor-2026x").email == "joao@empresa.com"
    assert LoginRequest(email=" JOAO@empresa.com ", senha="x").email == "joao@empresa.com"


def test_email_do_membro_normaliza():
    from routes.equipe import ConviteEquipe
    convite = ConviteEquipe(nome="M", email="Membro@Empresa.Com")
    assert convite.email == "membro@empresa.com"
