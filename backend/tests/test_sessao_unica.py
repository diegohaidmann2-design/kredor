"""Uma conta, um acesso por vez.

Pedido de 14/09/2026: não permitir dois acessos simultâneos na mesma conta. Quem precisa de outra
pessoa no sistema cadastra um membro da equipe, que tem usuário e sessão próprios.
"""
from services.auth import MENSAGEM_OUTRA_SESSAO, criar_tokens, jti_do_token, sessao_de_outro_dispositivo


def test_token_da_sessao_atual_e_aceito():
    assert sessao_de_outro_dispositivo({"sessao_jti": "abc"}, "abc") is False


def test_token_de_sessao_anterior_e_recusado():
    assert sessao_de_outro_dispositivo({"sessao_jti": "novo"}, "antigo") is True


def test_conta_sem_sessao_registrada_continua_valendo():
    # Quem já estava logado quando a regra entrou não é desconectado de uma vez:
    # a regra passa a valer no próximo login.
    assert sessao_de_outro_dispositivo({}, "qualquer") is False
    assert sessao_de_outro_dispositivo({"sessao_jti": None}, "qualquer") is False


def test_token_sem_jti_nao_e_barrado_por_esta_regra():
    # Token antigo sem jti não é assunto desta regra (a validade dele é decidida pela expiração).
    assert sessao_de_outro_dispositivo({"sessao_jti": "abc"}, None) is False


def test_cada_login_gera_um_jti_diferente():
    a, _ = criar_tokens("usuario-1")
    b, _ = criar_tokens("usuario-1")
    assert jti_do_token(a) != jti_do_token(b)


def test_access_e_refresh_do_mesmo_login_compartilham_o_jti():
    # É o que permite o refresh continuar a MESMA sessão, sem virar um segundo acesso.
    access, refresh = criar_tokens("usuario-1")
    assert jti_do_token(access) == jti_do_token(refresh)


def test_jti_de_token_invalido_e_none():
    assert jti_do_token("nao-e-um-token") is None


def test_mensagem_diz_o_que_fazer():
    # A mensagem precisa apontar a saída: cadastrar membro da equipe.
    assert "outro dispositivo" in MENSAGEM_OUTRA_SESSAO   # o frontend procura este trecho
    assert "Minha Equipe" in MENSAGEM_OUTRA_SESSAO         # a saída para duas pessoas
    assert len(MENSAGEM_OUTRA_SESSAO) <= 140, "aviso longo demais para caber na tela de login"
