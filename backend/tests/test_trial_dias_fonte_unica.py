"""Duração do trial: uma fonte só.

O número existia em dois lugares independentes — o código concedia 7 dias
(models/usuario.data_fim_trial) e a configuração do painel dizia 3 — e a landing exibia
"3 dias grátis" no topo com "7 dias grátis" em quatro outros pontos, porque esses estavam
escritos à mão. Estes testes travam a fonte única.
"""
from datetime import datetime, timezone

from config import TRIAL_DIAS
from models.configuracao import LandingConfig
from models.usuario import Usuario


def test_constante_e_plausivel():
    assert isinstance(TRIAL_DIAS, int)
    assert 1 <= TRIAL_DIAS <= 30, f"duração de trial fora do razoável: {TRIAL_DIAS}"


def test_conta_nova_recebe_exatamente_a_constante():
    """É o trial CONCEDIDO — o que a landing anuncia tem de bater com isto."""
    antes = datetime.now(timezone.utc)
    u = Usuario(nome="T", email="t@exemplo.com")
    dias = (u.data_fim_trial - antes).total_seconds() / 86400
    assert abs(dias - TRIAL_DIAS) < 0.01, f"concedeu {dias:.2f} dias, constante diz {TRIAL_DIAS}"


def test_default_da_landing_segue_a_constante():
    assert LandingConfig().plano_trial_dias == TRIAL_DIAS


def test_rota_publica_ignora_o_valor_guardado():
    """A rota sobrescreve o que está no banco: cópia desatualizada não volta a aparecer."""
    import inspect

    from routes import configuracoes

    fonte = inspect.getsource(configuracoes.obter_configuracoes_landing)
    assert 'dados["plano_trial_dias"] = TRIAL_DIAS' in fonte, (
        "GET /configuracoes/landing precisa anunciar o trial concedido, não a cópia guardada "
        "no banco — foi a cópia (3 dias) que contradisse o sistema (7 dias)"
    )
