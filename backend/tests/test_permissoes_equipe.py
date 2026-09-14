"""Tabela de permissões de equipe: o que cada membro alcança.

A regra de ouro destes testes é a última função: TODO caminho que a tela chama precisa
resolver para algum requisito. Uma rota que a tabela não cataloga é negada ao membro
(falha fechada) — proteção correta, mas se for uma rota que a tela usa, o membro vê a
tela quebrada. Esse teste é o que impede a falha fechada de virar tela morta.
"""
from services.permissoes_equipe import (
    GERIR_CLIENTES,
    GERIR_EMPRESTIMOS,
    GERIR_EQUIPE,
    LIVRE,
    PERMISSOES_VALIDAS,
    ROTULOS,
    SOMENTE_DONO,
    USAR_CONSULTAS,
    VER_CLIENTES,
    VER_EMPRESTIMOS,
    VER_FINANCEIRO,
    expandir,
    membro_pode,
    normalizar_caminho,
    resolver,
    validar_permissoes,
)


def pode(permissoes, caminho, metodo="GET"):
    return membro_pode(permissoes, caminho, metodo)[0]


# --- catálogo -------------------------------------------------------------------------

def test_toda_permissao_tem_rotulo():
    # A tela mostra ROTULOS; uma permissão sem rótulo apareceria como id cru na interface.
    assert set(ROTULOS) == set(PERMISSOES_VALIDAS)


def test_validar_permissoes_descarta_o_que_nao_existe():
    assert validar_permissoes(["ver_clientes", "inventada", "admin", ""]) == ["ver_clientes"]
    assert validar_permissoes(["gerir_clientes", "gerir_clientes"]) == ["gerir_clientes"]
    assert validar_permissoes(None) == []


def test_quem_gere_tambem_ve():
    assert expandir([GERIR_CLIENTES]) == {GERIR_CLIENTES, VER_CLIENTES}
    assert expandir([GERIR_EMPRESTIMOS]) == {GERIR_EMPRESTIMOS, VER_EMPRESTIMOS}
    assert pode([GERIR_CLIENTES], "/api/clientes", "GET")


# --- normalização do caminho ----------------------------------------------------------

def test_normalizar_caminho():
    assert normalizar_caminho("/api/clientes") == "/clientes"
    assert normalizar_caminho("/api/clientes/") == "/clientes"
    assert normalizar_caminho("/clientes") == "/clientes"
    assert normalizar_caminho("/api") == "/"
    assert normalizar_caminho("/api/") == "/"


# --- leitura x escrita ----------------------------------------------------------------

def test_ver_clientes_le_mas_nao_escreve():
    assert pode([VER_CLIENTES], "/api/clientes", "GET")
    assert pode([VER_CLIENTES], "/api/clientes/abc-123", "GET")
    assert not pode([VER_CLIENTES], "/api/clientes", "POST")
    assert not pode([VER_CLIENTES], "/api/clientes/abc-123", "PUT")
    assert not pode([VER_CLIENTES], "/api/clientes/abc-123", "DELETE")


def test_gerir_clientes_escreve():
    assert pode([GERIR_CLIENTES], "/api/clientes", "POST")
    assert pode([GERIR_CLIENTES], "/api/clientes/abc/gerar-codigo-portal", "POST")


def test_ver_emprestimos_nao_cria_emprestimo():
    assert pode([VER_EMPRESTIMOS], "/api/emprestimos", "GET")
    assert pode([VER_EMPRESTIMOS], "/api/emprestimos/xyz/parcelas", "GET")
    assert not pode([VER_EMPRESTIMOS], "/api/emprestimos", "POST")
    assert not pode([VER_EMPRESTIMOS], "/api/emprestimos/xyz/quitar", "POST")
    assert not pode([VER_EMPRESTIMOS], "/api/emprestimos/xyz/amortizar", "POST")


def test_simulacao_e_leitura():
    # Simular não move dinheiro nem cria registro; exigir gerir_emprestimos seria ruído.
    assert pode([VER_EMPRESTIMOS], "/api/emprestimos/simular", "POST")


# --- membro sem nenhuma permissão -----------------------------------------------------

def test_membro_sem_permissao_nao_alcanca_dado_nenhum():
    """Era o furo principal: as permissões eram gravadas e nunca lidas."""
    for caminho, metodo in [
        ("/api/clientes", "GET"),
        ("/api/clientes", "POST"),
        ("/api/clientes/abc", "DELETE"),
        ("/api/emprestimos", "GET"),
        ("/api/emprestimos", "POST"),
        ("/api/dashboard", "GET"),
        ("/api/relatorios/gerar", "POST"),
        ("/api/consultas/cpf", "POST"),
        ("/api/analise/dashboard", "GET"),
        ("/api/carteira/", "GET"),
        ("/api/assistente/chat", "POST"),
        ("/api/whatsapp/enviar-cobranca-parcela/abc", "POST"),
    ]:
        assert not pode([], caminho, metodo), f"membro sem permissão alcançou {metodo} {caminho}"


def test_membro_nunca_alcanca_area_do_dono():
    todas = list(PERMISSOES_VALIDAS)
    for caminho, metodo in [
        ("/api/pagamentos", "POST"),
        ("/api/pagamentos", "GET"),
        ("/api/pagamentos/abc", "DELETE"),
        ("/api/configuracoes/notificacoes", "PUT"),
        ("/api/whatsapp/conexoes", "POST"),
        ("/api/whatsapp/regua/config", "PUT"),
        ("/api/whatsapp/regua/executar", "POST"),
        ("/api/whatsapp/templates", "POST"),
        ("/api/carteira/recarga/asaas", "POST"),
        ("/api/exportacao/exportar", "POST"),
        ("/api/backup/criar", "POST"),
        ("/api/auditoria", "GET"),
        ("/api/superadmin/usuarios", "GET"),
        ("/api/admin/carteiras/dashboard", "GET"),
        ("/api/seguranca/resumo", "GET"),
        ("/api/assinaturas/checkout-asaas", "POST"),
        ("/api/parcelas/cobrar-em-massa", "POST"),
        ("/api/contratos/gerar", "POST"),
    ]:
        assert not pode(todas, caminho, metodo), f"membro com tudo alcançou {metodo} {caminho}"


def test_consultas_cobradas_exigem_permissao_propria():
    # Consulta de CPF consome saldo da carteira do dono: não sai de graça com ver_clientes.
    assert not pode([VER_CLIENTES, VER_FINANCEIRO], "/api/consultas/cpf", "POST")
    assert pode([USAR_CONSULTAS], "/api/consultas/cpf", "POST")


def test_gerir_equipe_abre_a_tela_de_equipe():
    assert pode([GERIR_EQUIPE], "/api/equipe", "GET")
    assert pode([GERIR_EQUIPE], "/api/equipe/convidar", "POST")
    assert not pode([VER_CLIENTES], "/api/equipe", "GET")


# --- falha fechada --------------------------------------------------------------------

def test_rota_desconhecida_e_negada():
    """Rota nova nasce fechada ao membro. É o ponto do desenho: o esquecimento não abre nada."""
    assert resolver("/api/rota-que-ainda-nao-existe", "GET") is None
    assert not pode(list(PERMISSOES_VALIDAS), "/api/rota-que-ainda-nao-existe", "GET")


def test_motivo_do_403_fala_com_o_membro():
    _, motivo = membro_pode([], "/api/clientes", "GET")
    assert ROTULOS[VER_CLIENTES] in motivo
    _, motivo_dono = membro_pode(list(PERMISSOES_VALIDAS), "/api/pagamentos", "GET")
    assert "dono da conta" in motivo_dono


# --- o que todo membro precisa --------------------------------------------------------

def test_app_shell_e_livre():
    """Sem isto o membro loga e não vê tela nenhuma."""
    for caminho, metodo in [
        ("/api/auth/me", "GET"),
        ("/api/auth/permissoes", "GET"),
        ("/api/auth/refresh", "POST"),
        ("/api/auth/alterar-senha", "POST"),
        ("/api/onboarding/status", "GET"),
        ("/api/notificacoes", "GET"),
        ("/api/notificacoes/contagem", "GET"),
        ("/api/notificacoes/marcar-todas-lidas", "POST"),
        ("/api/assinaturas/status", "GET"),
        ("/api/assinaturas/minha", "GET"),
        ("/api/suporte/tickets", "POST"),
        ("/api/", "GET"),
    ]:
        assert pode([], caminho, metodo), f"membro sem permissão foi barrado em {metodo} {caminho}"


def test_rota_publica_do_convite_e_livre():
    # Quem aceita o convite ainda não tem login.
    assert resolver("/api/equipe/aceitar-convite", "POST") == LIVRE


def test_pagamentos_inteiro_e_do_dono():
    for metodo in ("GET", "POST", "DELETE"):
        assert resolver("/api/pagamentos", metodo) == SOMENTE_DONO


# --- a rede de segurança --------------------------------------------------------------

# Todo caminho que o frontend chama (extraído de frontend/src/api e das telas). Mantido à mão
# de propósito: acrescentar rota aqui é o lembrete de catalogá-la na tabela.
CAMINHOS_DO_FRONTEND = [
    ("/api/analise/clientes", "GET"), ("/api/analise/dashboard", "GET"),
    ("/api/analise/recalcular/abc", "POST"), ("/api/analise/recalcular-todos", "POST"),
    ("/api/analise/score/abc", "GET"),
    ("/api/asaas/config", "GET"), ("/api/asaas/status", "GET"),
    ("/api/assinaturas/planos", "GET"), ("/api/assinaturas/minha", "GET"),
    ("/api/assinaturas/historico", "GET"), ("/api/assinaturas/cancelar", "POST"),
    ("/api/assinaturas/checkout-asaas", "POST"), ("/api/assinaturas/gateway/config", "GET"),
    ("/api/assinaturas/cupom/validar/X", "POST"), ("/api/assinaturas/social-proof", "GET"),
    ("/api/assistente/chat", "POST"), ("/api/assistente/historico", "GET"),
    ("/api/auditoria", "GET"), ("/api/auditoria/estatisticas", "GET"),
    ("/api/auth/me", "GET"), ("/api/auth/login", "POST"), ("/api/auth/permissoes", "GET"),
    ("/api/auth/refresh", "POST"), ("/api/auth/alterar-senha", "POST"),
    ("/api/auth/2fa-status", "GET"), ("/api/auth/toggle-2fa", "POST"),
    ("/api/backup/listar", "GET"), ("/api/backup/criar", "POST"),
    ("/api/blog/posts", "GET"), ("/api/blog/posts/slug", "GET"),
    ("/api/cadastro-publico/link", "GET"), ("/api/cadastro-publico/solicitacoes", "GET"),
    ("/api/cadastro-publico/solicitar/token", "POST"), ("/api/cadastro-publico/info/token", "GET"),
    ("/api/carteira/", "GET"), ("/api/carteira/movimentos", "GET"),
    ("/api/carteira/precos", "GET"), ("/api/carteira/gateways", "GET"),
    ("/api/carteira/alerta-saldo", "PUT"), ("/api/carteira/recarga/asaas", "POST"),
    ("/api/clientes", "GET"), ("/api/clientes", "POST"), ("/api/clientes/abc", "GET"),
    ("/api/clientes/abc", "PUT"), ("/api/clientes/abc", "DELETE"),
    ("/api/clientes/lixeira", "GET"), ("/api/clientes/abc/restaurar", "POST"),
    ("/api/configuracoes/ia", "GET"), ("/api/configuracoes/landing", "GET"),
    ("/api/configuracoes/notificacoes", "GET"), ("/api/configuracoes/notificacoes", "PUT"),
    ("/api/consultas/cpf", "POST"), ("/api/consultas/historico", "GET"),
    ("/api/consultas/abc", "GET"), ("/api/consultas/abc", "DELETE"),
    ("/api/contratos/gerar", "POST"), ("/api/contratos/preview/abc", "GET"),
    ("/api/dashboard", "GET"),
    ("/api/emprestimos", "GET"), ("/api/emprestimos", "POST"),
    ("/api/emprestimos/abc", "GET"), ("/api/emprestimos/abc", "PUT"),
    ("/api/emprestimos/abc", "DELETE"), ("/api/emprestimos/abertos/resumo", "GET"),
    ("/api/emprestimos/simular", "POST"), ("/api/emprestimos/simular-publico", "POST"),
    ("/api/equipe", "GET"), ("/api/equipe/convidar", "POST"),
    ("/api/equipe/aceitar-convite", "POST"), ("/api/equipe/abc", "DELETE"),
    ("/api/equipe/abc/permissoes", "PUT"), ("/api/equipe/abc/reativar", "POST"),
    ("/api/equipe/abc/reenviar-convite", "POST"),
    ("/api/exportacao/resumo", "GET"), ("/api/exportacao/exportar", "POST"),
    ("/api/notificacoes", "GET"), ("/api/notificacoes/contagem", "GET"),
    ("/api/notificacoes/abc/marcar-lida", "POST"), ("/api/notificacoes/marcar-todas-lidas", "POST"),
    ("/api/notificacoes/limpar-todas", "DELETE"), ("/api/notificacoes/verificar-vencimentos", "POST"),
    ("/api/onboarding/status", "GET"), ("/api/onboarding/start", "POST"),
    ("/api/onboarding/task/update", "POST"), ("/api/onboarding/tour-steps", "GET"),
    ("/api/pagamentos", "GET"), ("/api/pagamentos", "POST"), ("/api/pagamentos/previa", "POST"),
    ("/api/pagamentos/abc", "DELETE"),
    ("/api/parcelas/pendentes", "GET"), ("/api/parcelas/cobrar-em-massa", "POST"),
    ("/api/parcelas/abc", "DELETE"), ("/api/parcelas/resumo-juros-mora", "GET"),
    ("/api/portal/login", "POST"), ("/api/portal/emprestimos", "GET"),
    ("/api/relatorios/gerar", "POST"),
    ("/api/seguranca/resumo", "GET"), ("/api/superadmin/dashboard", "GET"),
    ("/api/suporte/tickets", "GET"), ("/api/suporte/tickets", "POST"),
    ("/api/suporte/admin/tickets", "GET"),
    ("/api/upload/upload", "POST"),
    ("/api/whatsapp/logs", "GET"), ("/api/whatsapp/mensagens", "GET"),
    ("/api/whatsapp/mensagens/enviar", "POST"), ("/api/whatsapp/conexoes", "GET"),
    ("/api/whatsapp/conexoes", "POST"), ("/api/whatsapp/status-servico", "GET"),
    ("/api/whatsapp/templates", "GET"), ("/api/whatsapp/templates", "POST"),
    ("/api/whatsapp/templates/preview", "POST"),
    ("/api/whatsapp/regua/config", "GET"), ("/api/whatsapp/regua/config", "PUT"),
    ("/api/whatsapp/regua/historico", "GET"), ("/api/whatsapp/regua/executar", "POST"),
    ("/api/whatsapp/anti-spam/config", "GET"), ("/api/whatsapp/fila/estatisticas", "GET"),
    ("/api/whatsapp/enviar-cobranca-parcela/abc", "POST"),
    ("/api/whatsapp/enviar-confirmacao-pagamento/abc", "POST"),
    ("/api/whatsapp/config/evolution", "GET"),
    ("/api/admin/scheduler/status", "GET"), ("/api/admin/transacoes/metricas", "GET"),
    ("/api/admin/carteiras/dashboard", "GET"),
    ("/api/timezone-info", "GET"),
]


def test_toda_rota_da_tela_esta_catalogada():
    orfas = [(c, m) for c, m in CAMINHOS_DO_FRONTEND if resolver(c, m) is None]
    assert not orfas, (
        "rotas que a tela chama e a tabela não cataloga (o membro tomaria 403 numa tela "
        f"legítima): {orfas}"
    )


def test_dono_com_tudo_marcado_opera_o_dia_a_dia():
    """Um 'gerente' com todas as permissões delegáveis consegue trabalhar de fato."""
    gerente = [VER_CLIENTES, GERIR_CLIENTES, VER_EMPRESTIMOS, GERIR_EMPRESTIMOS,
               VER_FINANCEIRO, USAR_CONSULTAS]
    esperado_liberado = [
        ("/api/clientes", "POST"), ("/api/clientes/abc", "PUT"),
        ("/api/emprestimos", "POST"), ("/api/emprestimos/abc/quitar", "POST"),
        ("/api/dashboard", "GET"), ("/api/relatorios/gerar", "POST"),
        ("/api/consultas/cpf", "POST"), ("/api/analise/dashboard", "GET"),
        ("/api/whatsapp/enviar-cobranca-parcela/abc", "POST"),
        ("/api/contratos/preview/abc", "GET"), ("/api/carteira/", "GET"),
    ]
    for caminho, metodo in esperado_liberado:
        assert pode(gerente, caminho, metodo), f"gerente foi barrado em {metodo} {caminho}"
