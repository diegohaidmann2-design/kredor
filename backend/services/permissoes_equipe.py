"""Permissões de membros de equipe.

Um membro (``usuario.owner_id`` preenchido) alcança apenas o que o dono marcou na tela
*Minha Equipe*. O dono da conta e o operador da plataforma passam sempre — quem paga pela
conta não se restringe a si mesmo.

Por que uma tabela central e não um decorator em cada rota
----------------------------------------------------------
São ~110 endpoints de inquilino. Com decorator por rota, a rota nova nasce **aberta**: quem
esquecer o decorator entrega a carteira inteira ao membro, e o esquecimento não aparece em
nenhum lugar. Aqui a rota nova nasce **fechada** — o que não está catalogado é negado ao
membro (`_negar_por_omissao`) — e a decisão de abrir fica registrada numa linha só, revisável
em diff. O dono nunca é afetado por uma omissão, então a falha fechada não derruba a conta.

A tabela é consultada por `resolver()`, função pura e testável: caminho (já sem o prefixo
`/api`) + método HTTP → requisito.
"""
import re
from typing import Iterable, List, Optional, Tuple

# --- catálogo ---------------------------------------------------------------------------

VER_CLIENTES = "ver_clientes"
GERIR_CLIENTES = "gerir_clientes"
VER_EMPRESTIMOS = "ver_emprestimos"
GERIR_EMPRESTIMOS = "gerir_emprestimos"
VER_FINANCEIRO = "ver_financeiro"
GERIR_EQUIPE = "gerir_equipe"
USAR_CONSULTAS = "usar_consultas"

PERMISSOES_VALIDAS = frozenset({
    VER_CLIENTES,
    GERIR_CLIENTES,
    VER_EMPRESTIMOS,
    GERIR_EMPRESTIMOS,
    VER_FINANCEIRO,
    GERIR_EQUIPE,
    USAR_CONSULTAS,
})

# Rótulos que a tela mostra. Ficam aqui para tela e servidor não divergirem.
ROTULOS = {
    VER_CLIENTES: "Ver clientes",
    GERIR_CLIENTES: "Criar, editar e excluir clientes",
    VER_EMPRESTIMOS: "Ver empréstimos e parcelas",
    GERIR_EMPRESTIMOS: "Criar, editar e cobrar empréstimos",
    VER_FINANCEIRO: "Ver dashboard, pagamentos e relatórios",
    USAR_CONSULTAS: "Consultar CPF/CNPJ (consome saldo da carteira)",
    GERIR_EQUIPE: "Gerir a equipe",
}

# Quem pode gerir, pode ver. Evita o membro com "gerir_clientes" tomar 403 num GET.
IMPLICACOES = {
    GERIR_CLIENTES: frozenset({VER_CLIENTES}),
    GERIR_EMPRESTIMOS: frozenset({VER_EMPRESTIMOS}),
}

# Permissão que um membro nunca concede a outro: quem pode gerir a equipe não pode fabricar
# um colega mais poderoso que si mesmo nem promover a si próprio (escalação de privilégio).
NAO_DELEGAVEIS = frozenset({GERIR_EQUIPE})

# --- requisitos especiais ---------------------------------------------------------------

LIVRE = "__livre__"            # qualquer membro autenticado; inclui as rotas públicas
SOMENTE_DONO = "__dono__"      # nunca um membro, nem com permissões

TODOS_OS_METODOS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})
LEITURA = frozenset({"GET", "HEAD", "OPTIONS"})
ESCRITA = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def expandir(permissoes: Iterable[str]) -> frozenset:
    """Aplica as implicações: {'gerir_clientes'} → {'gerir_clientes', 'ver_clientes'}."""
    efetivas = set()
    for p in permissoes or ():
        efetivas.add(p)
        efetivas |= IMPLICACOES.get(p, frozenset())
    return frozenset(efetivas)


# --- tabela -----------------------------------------------------------------------------
# (padrão do caminho, métodos, requisito). Primeira linha que casar decide, então o
# específico vem antes do genérico. `$` fecha o padrão: sem ele, "/clientes" casaria
# "/clientes/{id}/excluir".

_ID = r"[^/]+"

REGRAS: List[Tuple[str, frozenset, str]] = [
    # ---- público e app shell: sem isto a tela do membro não abre ----
    (r"/?$", TODOS_OS_METODOS, LIVRE),
    (r"/timezone-info$", TODOS_OS_METODOS, LIVRE),
    (r"/auth/.*", TODOS_OS_METODOS, LIVRE),
    (r"/onboarding(/.*)?$", TODOS_OS_METODOS, LIVRE),
    (r"/portal(/.*)?$", TODOS_OS_METODOS, LIVRE),
    (r"/blog(/.*)?$", TODOS_OS_METODOS, LIVRE),
    (r"/sitemap.*", TODOS_OS_METODOS, LIVRE),
    (r"/robots.*", TODOS_OS_METODOS, LIVRE),
    (r"/upload(/.*)?$", TODOS_OS_METODOS, LIVRE),          # anexo de ticket de suporte
    (r"/suporte/admin(/.*)?$", TODOS_OS_METODOS, SOMENTE_DONO),
    (r"/suporte(/.*)?$", TODOS_OS_METODOS, LIVRE),         # membro abre o próprio ticket

    # ---- equipe ----
    (r"/equipe/aceitar-convite$", TODOS_OS_METODOS, LIVRE),  # público: quem aceita não tem login
    (r"/equipe(/.*)?$", TODOS_OS_METODOS, GERIR_EQUIPE),

    # ---- assinatura: ver é livre (o AssinaturaWrapper roda em toda tela), comprar é do dono ----
    (r"/assinaturas/webhook-.*", TODOS_OS_METODOS, LIVRE),
    (r"/assinaturas/(planos|social-proof|minha|status|historico)$", LEITURA, LIVRE),
    (r"/assinaturas(/.*)?$", TODOS_OS_METODOS, SOMENTE_DONO),

    # ---- notificações: são do próprio membro ----
    (r"/notificacoes/admin(/.*)?$", TODOS_OS_METODOS, SOMENTE_DONO),
    (r"/notificacoes/verificar-vencimentos$", TODOS_OS_METODOS, GERIR_EMPRESTIMOS),
    (r"/notificacoes(/.*)?$", TODOS_OS_METODOS, LIVRE),

    # ---- clientes ----
    (r"/clientes/lixeira$", LEITURA, GERIR_CLIENTES),
    (r"/clientes$", LEITURA, VER_CLIENTES),
    (rf"/clientes/{_ID}$", LEITURA, VER_CLIENTES),
    (r"/clientes(/.*)?$", ESCRITA, GERIR_CLIENTES),
    (r"/cadastro-publico/(solicitar|info)(/.*)?$", TODOS_OS_METODOS, LIVRE),  # formulário público
    (r"/cadastro-publico(/.*)?$", TODOS_OS_METODOS, GERIR_CLIENTES),
    (r"/analise/recalcular.*", TODOS_OS_METODOS, GERIR_CLIENTES),
    (r"/analise(/.*)?$", LEITURA, VER_CLIENTES),

    # ---- empréstimos e parcelas ----
    (r"/emprestimos/simular(-publico)?$", TODOS_OS_METODOS, VER_EMPRESTIMOS),
    (r"/emprestimos(/.*)?$", LEITURA, VER_EMPRESTIMOS),
    (r"/emprestimos(/.*)?$", ESCRITA, GERIR_EMPRESTIMOS),
    (r"/parcelas/resumo-juros-mora$", LEITURA, VER_FINANCEIRO),
    (r"/parcelas/pendentes$", LEITURA, VER_EMPRESTIMOS),
    (r"/parcelas/cobrar-em-massa$", TODOS_OS_METODOS, SOMENTE_DONO),
    (r"/parcelas(/.*)?$", ESCRITA, GERIR_EMPRESTIMOS),
    (r"/parcelas(/.*)?$", LEITURA, VER_EMPRESTIMOS),
    (r"/contratos/gerar$", TODOS_OS_METODOS, SOMENTE_DONO),
    (r"/contratos(/.*)?$", LEITURA, VER_EMPRESTIMOS),
    (r"/aceite-emprestimo/(info|confirmar)(/.*)?$", TODOS_OS_METODOS, LIVRE),  # tela pública de aceite
    (r"/aceite-emprestimo(/.*)?$", TODOS_OS_METODOS, GERIR_EMPRESTIMOS),

    # ---- financeiro ----
    (r"/pagamentos(/.*)?$", TODOS_OS_METODOS, SOMENTE_DONO),   # já era: is_owner em todas
    (r"/dashboard(/.*)?$", LEITURA, VER_FINANCEIRO),
    (r"/relatorios(/.*)?$", TODOS_OS_METODOS, VER_FINANCEIRO),
    (r"/assistente(/.*)?$", TODOS_OS_METODOS, VER_FINANCEIRO),  # a IA enxerga a carteira toda
    (r"/exportacao(/.*)?$", TODOS_OS_METODOS, SOMENTE_DONO),    # extração em massa

    # ---- carteira de saldo: ver é financeiro, gastar é do dono ----
    (r"/carteira/(recarga|alerta-saldo)(/.*)?$", TODOS_OS_METODOS, SOMENTE_DONO),
    (r"/carteira(/.*)?$", LEITURA, VER_FINANCEIRO),

    # ---- consultas cobradas ----
    (r"/consultas(/.*)?$", TODOS_OS_METODOS, USAR_CONSULTAS),

    # ---- WhatsApp: mandar cobrança é operação, configurar é do dono ----
    (r"/whatsapp/(config|conexoes|anti-spam|fila)(/.*)?$", TODOS_OS_METODOS, SOMENTE_DONO),
    (r"/whatsapp/regua/historico$", LEITURA, VER_EMPRESTIMOS),
    (r"/whatsapp/regua(/.*)?$", TODOS_OS_METODOS, SOMENTE_DONO),
    (r"/whatsapp/templates(/.*)?$", LEITURA, VER_EMPRESTIMOS),
    (r"/whatsapp/templates(/.*)?$", ESCRITA, SOMENTE_DONO),
    (r"/whatsapp/enviar-.*", TODOS_OS_METODOS, GERIR_EMPRESTIMOS),
    (r"/whatsapp/mensagens/enviar$", TODOS_OS_METODOS, GERIR_EMPRESTIMOS),
    (r"/whatsapp(/.*)?$", LEITURA, VER_EMPRESTIMOS),

    # ---- configuração da conta e painéis de plataforma ----
    (r"/configuracoes/landing$", LEITURA, LIVRE),               # a landing é pública
    (r"/configuracoes(/.*)?$", TODOS_OS_METODOS, SOMENTE_DONO),
    (r"/auditoria(/.*)?$", TODOS_OS_METODOS, SOMENTE_DONO),
    (r"/backup(/.*)?$", TODOS_OS_METODOS, SOMENTE_DONO),
    (r"/asaas(/.*)?$", TODOS_OS_METODOS, SOMENTE_DONO),
    (r"/superadmin(/.*)?$", TODOS_OS_METODOS, SOMENTE_DONO),
    (r"/admin(/.*)?$", TODOS_OS_METODOS, SOMENTE_DONO),
    (r"/seguranca(/.*)?$", TODOS_OS_METODOS, SOMENTE_DONO),
]

_REGRAS_COMPILADAS = [(re.compile(f"^{padrao}$" if not padrao.endswith("$") else f"^{padrao}"),
                       metodos, requisito)
                      for padrao, metodos, requisito in REGRAS]


def normalizar_caminho(caminho: str) -> str:
    """Remove o prefixo /api e a barra final, para o padrão da tabela casar."""
    if caminho.startswith("/api"):
        caminho = caminho[len("/api"):]
    if len(caminho) > 1 and caminho.endswith("/"):
        caminho = caminho.rstrip("/")
    return caminho or "/"


def resolver(caminho: str, metodo: str) -> Optional[str]:
    """Requisito da rota: uma permissão, LIVRE, SOMENTE_DONO — ou None se não catalogada."""
    caminho = normalizar_caminho(caminho)
    metodo = (metodo or "GET").upper()
    for regex, metodos, requisito in _REGRAS_COMPILADAS:
        if metodo in metodos and regex.match(caminho):
            return requisito
    return None


def membro_pode(permissoes: Iterable[str], caminho: str, metodo: str) -> Tuple[bool, str]:
    """Decide o acesso de um MEMBRO. Dono e operador da plataforma não passam por aqui.

    Retorna (pode, motivo). O motivo vira o `detail` do 403, então fala com o membro.
    """
    requisito = resolver(caminho, metodo)

    if requisito is None:
        # Falha fechada: rota nova, ou rota de plataforma que ninguém catalogou.
        return False, "Esta área é restrita ao dono da conta."
    if requisito == LIVRE:
        return True, ""
    if requisito == SOMENTE_DONO:
        return False, "Esta área é restrita ao dono da conta."

    if requisito in expandir(permissoes):
        return True, ""

    rotulo = ROTULOS.get(requisito, requisito)
    return False, f"Você não tem a permissão \"{rotulo}\". Peça ao dono da conta."


def validar_permissoes(permissoes: Iterable[str]) -> List[str]:
    """Normaliza a lista vinda da tela: descarta o que não existe, remove repetição, ordena.

    Aceitar string livre aqui deixaria o banco com permissões que nada honra — e daria a
    impressão de que um vínculo foi concedido.
    """
    limpas = {p for p in (permissoes or ()) if p in PERMISSOES_VALIDAS}
    return sorted(limpas)
