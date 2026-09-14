/**
 * Permissões de membro de equipe — lado da tela.
 *
 * A autoridade é o servidor (backend/services/permissoes_equipe.py): é lá que o acesso é
 * negado de fato, e é de lá que vem a lista de permissões exibida em Minha Equipe. Aqui
 * ficam apenas os ids e a mesma implicação "quem gere, vê", para a navegação não oferecer
 * uma tela que o membro tomaria 403 ao abrir.
 *
 * Dono da conta (owner_id nulo) e operador da plataforma não passam por nada disto.
 */

export const VER_CLIENTES = 'ver_clientes';
export const GERIR_CLIENTES = 'gerir_clientes';
export const VER_EMPRESTIMOS = 'ver_emprestimos';
export const GERIR_EMPRESTIMOS = 'gerir_emprestimos';
export const VER_FINANCEIRO = 'ver_financeiro';
export const GERIR_EQUIPE = 'gerir_equipe';
export const USAR_CONSULTAS = 'usar_consultas';

// Sentinela: tela que nunca é de membro, com permissão ou sem.
export const SOMENTE_DONO = '__dono__';

const IMPLICACOES = {
  [GERIR_CLIENTES]: [VER_CLIENTES],
  [GERIR_EMPRESTIMOS]: [VER_EMPRESTIMOS],
};

/** Permissões efetivas: gerir_clientes traz ver_clientes junto. */
export const expandir = (permissoes) => {
  const efetivas = new Set();
  (permissoes || []).forEach((p) => {
    efetivas.add(p);
    (IMPLICACOES[p] || []).forEach((i) => efetivas.add(i));
  });
  return efetivas;
};

export const ehMembro = (user) => !!user?.owner_id;

/**
 * O usuário alcança o que esta tela exige?
 * @param requisito id de permissão, SOMENTE_DONO, ou nada (tela livre)
 */
export const podeAcessar = (user, requisito) => {
  if (!requisito) return true;
  if (!ehMembro(user)) return true;              // dono e operador da plataforma
  if (requisito === SOMENTE_DONO) return false;
  return expandir(user?.permissoes).has(requisito);
};

// Telas candidatas a primeira tela, na ordem em que fazem sentido como "início".
const CANDIDATAS_INICIO = [
  ['/dashboard', VER_FINANCEIRO],
  ['/clientes', VER_CLIENTES],
  ['/emprestimos', VER_EMPRESTIMOS],
  ['/consultas', USAR_CONSULTAS],
  ['/equipe', GERIR_EQUIPE],
  ['/notificacoes', null],          // livre: sempre existe uma saída
];

/**
 * Primeira tela que este usuário consegue abrir de fato.
 *
 * O login manda todo mundo para /dashboard, que exige ver_financeiro. Sem isto, o membro sem
 * essa permissão entra e cai direto no aviso de acesso não liberado — com a conta certa, a
 * senha certa e as permissões que o dono quis dar.
 */
export const rotaInicial = (user) => {
  if (!ehMembro(user)) return '/dashboard';
  const achada = CANDIDATAS_INICIO.find(([, req]) => podeAcessar(user, req));
  return achada ? achada[0] : '/notificacoes';
};
