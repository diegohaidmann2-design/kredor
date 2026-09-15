"""Transporte Resend: montagem do payload e a escolha do provedor com reserva no SMTP.

Sem rede: os transportes são substituídos. O envio de verdade é conferido por
tests/e2e_email_resend.py, que fala com a API usando o endereço de teste do Resend.
"""
import pytest

from services import email_service


# --- payload ---------------------------------------------------------------------------

def test_payload_minimo():
    p = email_service.montar_payload_resend(
        "alguem@exemplo.com", "Assunto", "<p>oi</p>", remetente="Kredor <x@kredor.com.br>")
    assert p["from"] == "Kredor <x@kredor.com.br>"
    assert p["to"] == ["alguem@exemplo.com"]        # a API exige lista, não string
    assert p["subject"] == "Assunto"
    assert p["html"] == "<p>oi</p>"
    assert "text" not in p
    assert "reply_to" not in p


def test_payload_com_texto_puro():
    # Sem versão em texto, filtro de spam pontua pior e leitor de tela sofre.
    p = email_service.montar_payload_resend(
        "a@b.com", "S", "<p>oi</p>", corpo_texto="oi", remetente="r@kredor.com.br")
    assert p["text"] == "oi"


def test_payload_reply_to_so_quando_existe():
    com = email_service.montar_payload_resend(
        "a@b.com", "S", "<p>x</p>", remetente="r@kredor.com.br", reply_to="contato@kredor.com.br")
    assert com["reply_to"] == "contato@kredor.com.br"

    # Não há caixa postal em kredor.com.br: mandar reply_to vazio faria a resposta voltar.
    sem = email_service.montar_payload_resend(
        "a@b.com", "S", "<p>x</p>", remetente="r@kredor.com.br", reply_to="")
    assert "reply_to" not in sem


def test_remetente_padrao_e_do_dominio_da_marca():
    p = email_service.montar_payload_resend("a@b.com", "S", "<p>x</p>")
    assert "kredor.com.br" in p["from"], (
        f"remetente padrão saiu de outro domínio: {p['from']!r} — nome de uma marca com "
        "endereço de outra é a assinatura de phishing e é o que esta migração corrige"
    )


# --- escolha do transporte -------------------------------------------------------------

@pytest.fixture
def espiao(monkeypatch):
    """Troca os dois transportes por espiões e devolve o registro das chamadas."""
    chamadas = {"resend": 0, "smtp": 0}
    resultado = {"resend": True, "smtp": True}

    async def falso_resend(*a, **k):
        chamadas["resend"] += 1
        return resultado["resend"]

    async def falso_smtp(*a, **k):
        chamadas["smtp"] += 1
        return resultado["smtp"]

    monkeypatch.setattr(email_service, "_enviar_via_resend", falso_resend)
    monkeypatch.setattr(email_service, "_enviar_via_smtp", falso_smtp)
    return chamadas, resultado


@pytest.mark.asyncio
async def test_resend_sucesso_nao_toca_no_smtp(monkeypatch, espiao):
    chamadas, _ = espiao
    monkeypatch.setattr(email_service, "EMAIL_PROVIDER", "resend")

    assert await email_service.enviar_email_async("a@b.com", "S", "<p>x</p>") is True
    assert chamadas == {"resend": 1, "smtp": 0}, "não deve duplicar o envio"


@pytest.mark.asyncio
async def test_resend_falhando_cai_para_o_smtp(monkeypatch, espiao):
    """2FA, verificação de email e convite passam por aqui: não chegar tranca o acesso."""
    chamadas, resultado = espiao
    monkeypatch.setattr(email_service, "EMAIL_PROVIDER", "resend")
    resultado["resend"] = False

    assert await email_service.enviar_email_async("a@b.com", "S", "<p>x</p>") is True
    assert chamadas == {"resend": 1, "smtp": 1}, "a reserva precisa entrar quando o Resend falha"


@pytest.mark.asyncio
async def test_provedor_smtp_nao_chama_resend(monkeypatch, espiao):
    chamadas, _ = espiao
    monkeypatch.setattr(email_service, "EMAIL_PROVIDER", "smtp")

    assert await email_service.enviar_email_async("a@b.com", "S", "<p>x</p>") is True
    assert chamadas == {"resend": 0, "smtp": 1}


@pytest.mark.asyncio
async def test_os_dois_falhando_devolve_false(monkeypatch, espiao):
    # O contrato é devolver bool, nunca levantar: as rotas dependem disso para avisar a tela.
    chamadas, resultado = espiao
    monkeypatch.setattr(email_service, "EMAIL_PROVIDER", "resend")
    resultado["resend"] = False
    resultado["smtp"] = False

    assert await email_service.enviar_email_async("a@b.com", "S", "<p>x</p>") is False


@pytest.mark.asyncio
async def test_resend_sem_chave_nao_tenta_a_rede(monkeypatch):
    """Sem chave, recusa na hora: falar com a API renderia 401 e um log inútil por email."""
    monkeypatch.setattr(email_service, "RESEND_API_KEY", "")

    def nao_deveria_ser_chamado(*a, **k):
        raise AssertionError("tentou abrir conexão sem chave configurada")

    monkeypatch.setattr(email_service.httpx, "AsyncClient", nao_deveria_ser_chamado)

    assert await email_service._enviar_via_resend("a@b.com", "S", "<p>x</p>") is False
