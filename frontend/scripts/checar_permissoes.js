#!/usr/bin/env node
/**
 * Coerência do modelo de permissões entre servidor e tela.
 *
 * Existem duas cópias dos ids de permissão: a autoridade em
 * backend/services/permissoes_equipe.py e o espelho em frontend/src/lib/permissoes.js, que a
 * navegação usa para não oferecer tela que o membro tomaria 403 ao abrir. Duas cópias
 * divergem em silêncio, e a divergência aparece como "tela em branco para o funcionário".
 *
 * Verifica:
 *   1. os ids são exatamente os mesmos dos dois lados;
 *   2. todo `permissao={X}` em App.js e Sidebar.js é um id que existe;
 *   3. a primeira tela de cada perfil de membro é uma tela que ele ABRE — foi o defeito real:
 *      /dashboard exige ver_financeiro, e era para lá que todo login ia.
 *
 * Rodar de frontend/:  node scripts/checar_permissoes.js
 * Sai com código 1 em qualquer divergência.
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const RAIZ = path.resolve(__dirname, '..');
const MODULO_TELA = path.join(RAIZ, 'src', 'lib', 'permissoes.js');
const APP = path.join(RAIZ, 'src', 'App.js');
const SIDEBAR = path.join(RAIZ, 'src', 'components', 'Sidebar.js');
const MODULO_SERVIDOR = path.resolve(RAIZ, '..', 'backend', 'services', 'permissoes_equipe.py');

// Telas que todo membro deve abrir: são dele mesmo, não da carteira do dono.
const LIVRES_DE_PROPOSITO = new Set([
  '/notificacoes',
  '/suporte',
  '/suporte/:numero_ticket',
  '/perfil',
  '/verificar-email',
]);

const problemas = [];
const falhar = (msg) => problemas.push(msg);

function ler(arquivo) {
  if (!fs.existsSync(arquivo)) {
    console.error(`arquivo não encontrado: ${arquivo}`);
    process.exit(1);
  }
  return fs.readFileSync(arquivo, 'utf8');
}

// --- 1. carrega o módulo da tela num sandbox -------------------------------------------
// O módulo é autocontido (sem imports), então basta remover `export` para rodá-lo como
// script. Se alguém acrescentar um import, isto falha alto — que é o comportamento desejado.
const fonteTela = ler(MODULO_TELA);
if (/^\s*import\s/m.test(fonteTela)) {
  falhar('src/lib/permissoes.js passou a ter import — este checker precisa ser ajustado.');
}
// `const` no topo de um script do vm fica no escopo lexical, não no objeto de contexto — daí
// o epílogo: ele roda no mesmo escopo e publica os nomes exportados.
const nomesExportados = [...fonteTela.matchAll(/^export\s+const\s+([A-Za-z_$][\w$]*)/gm)]
  .map((x) => x[1]);
const script = fonteTela.replace(/^export\s+/gm, '')
  + `\n;__publicar({ ${nomesExportados.join(', ')} });\n`;

const sandbox = {};
sandbox.__publicar = (obj) => Object.assign(sandbox, obj);
try {
  vm.runInNewContext(script, sandbox);
} catch (e) {
  console.error(`não foi possível avaliar src/lib/permissoes.js: ${e.message}`);
  process.exit(1);
}
delete sandbox.__publicar;
const { podeAcessar, rotaInicial, SOMENTE_DONO } = sandbox;
if (typeof podeAcessar !== 'function' || typeof rotaInicial !== 'function') {
  console.error('src/lib/permissoes.js não expõe podeAcessar/rotaInicial.');
  process.exit(1);
}

// ids exportados como constantes de permissão (maiúsculas), menos as sentinelas
const idsTela = new Set(
  Object.entries(sandbox)
    .filter(([nome, valor]) => /^[A-Z_]+$/.test(nome) && typeof valor === 'string'
      && !valor.startsWith('__'))
    .map(([, valor]) => valor)
);

// --- 2. ids do servidor ----------------------------------------------------------------
const fonteServidor = ler(MODULO_SERVIDOR);
const blocoValidas = fonteServidor.match(/PERMISSOES_VALIDAS\s*=\s*frozenset\(\{([\s\S]*?)\}\)/);
if (!blocoValidas) {
  falhar('não achei PERMISSOES_VALIDAS em backend/services/permissoes_equipe.py');
}
const idsServidor = new Set();
if (blocoValidas) {
  // O bloco lista os nomes das constantes; resolve cada nome para o literal.
  for (const nome of blocoValidas[1].split(',').map((x) => x.trim()).filter(Boolean)) {
    const literal = fonteServidor.match(new RegExp(`^${nome}\\s*=\\s*"([^"]+)"`, 'm'));
    if (literal) idsServidor.add(literal[1]);
    else falhar(`constante ${nome} listada em PERMISSOES_VALIDAS sem valor literal`);
  }
}

for (const id of idsServidor) {
  if (!idsTela.has(id)) falhar(`permissão "${id}" existe no servidor e falta em src/lib/permissoes.js`);
}
for (const id of idsTela) {
  if (!idsServidor.has(id)) falhar(`permissão "${id}" existe na tela e o servidor não reconhece`);
}

// --- 3. todo permissao={X} usa um id conhecido -----------------------------------------
const conhecidos = new Set([...idsServidor, SOMENTE_DONO]);
const requisitosPorRota = new Map();

const fonteApp = ler(APP);
// path="/x" ... <ProtectedRoute permissao={CONST}>
// Exige o `element={` entre o path e o ProtectedRoute. Sem essa âncora, um <Route> vizinho
// sem ProtectedRoute (como /timezone-test) casava com o guard da rota SEGUINTE e escondia a
// rota do meio — foi assim que /clientes ficou fora desta conferência.
const reRota = /path="([^"]+)"\s*(?:\r?\n\s*)?element=\{\s*(?:\r?\n\s*)?<ProtectedRoute(?:\s+permissao=\{([A-Z_]+)\})?\s*>/g;
let m;
while ((m = reRota.exec(fonteApp)) !== null) {
  const [, rota, constante] = m;
  if (!constante) {
    requisitosPorRota.set(rota, null);
    if (!LIVRES_DE_PROPOSITO.has(rota)) {
      falhar(`App.js: rota ${rota} está sob ProtectedRoute sem permissao={} — qualquer membro abre. `
        + 'Anote o requisito, ou acrescente a rota em LIVRES_DE_PROPOSITO se ela for mesmo de todos.');
    }
    continue;
  }
  const valor = sandbox[constante];
  if (valor === undefined) {
    falhar(`App.js: rota ${rota} usa permissao={${constante}}, que não existe em lib/permissoes.js`);
    continue;
  }
  if (!conhecidos.has(valor)) {
    falhar(`App.js: rota ${rota} exige "${valor}", que o servidor não reconhece`);
  }
  requisitosPorRota.set(rota, valor);
}

// Nenhuma rota pode escapar desta conferência: se o pareamento perder uma, ela fica invisível
// aqui — que foi justamente como /clientes passou sem ser vista.
const totalProtegidas = (fonteApp.match(/<ProtectedRoute(\s|>)/g) || []).length;
if (totalProtegidas !== requisitosPorRota.size) {
  falhar(
    `App.js tem ${totalProtegidas} <ProtectedRoute> e este checker pareou ${requisitosPorRota.size}: `
    + 'alguma rota não está sendo conferida. Ajuste reRota.'
  );
}

const fonteSidebar = ler(SIDEBAR);
const reMenu = /permissao:\s*([A-Z_]+)/g;
while ((m = reMenu.exec(fonteSidebar)) !== null) {
  const valor = sandbox[m[1]];
  if (valor === undefined) {
    falhar(`Sidebar.js: item usa permissao: ${m[1]}, que não existe em lib/permissoes.js`);
  } else if (!conhecidos.has(valor)) {
    falhar(`Sidebar.js: item exige "${valor}", que o servidor não reconhece`);
  }
}

// --- 4. a primeira tela de cada perfil é uma tela que ele abre -------------------------
const perfis = [
  ['membro sem nenhuma permissão', []],
  ...[...idsServidor].sort().map((id) => [`membro com apenas ${id}`, [id]]),
  ['membro com tudo', [...idsServidor]],
];

for (const [nome, permissoes] of perfis) {
  const user = { owner_id: 'dono-x', permissoes };
  const destino = rotaInicial(user);
  if (!requisitosPorRota.has(destino)) {
    falhar(`${nome}: rotaInicial devolve "${destino}", que não é uma rota protegida conhecida do App.js`);
    continue;
  }
  const requisito = requisitosPorRota.get(destino);
  if (!podeAcessar(user, requisito)) {
    falhar(
      `${nome}: rotaInicial manda para "${destino}", que exige "${requisito}" — ele entra e cai no aviso de acesso não liberado`
    );
  }
}

const dono = { owner_id: null, permissoes: [] };
if (rotaInicial(dono) !== '/dashboard') {
  falhar(`dono da conta deveria cair em /dashboard, e cai em "${rotaInicial(dono)}"`);
}

// --- saída ----------------------------------------------------------------------------
console.log(`permissões conferidas: ${[...idsServidor].sort().join(', ')}`);
console.log(`rotas protegidas com requisito: ${[...requisitosPorRota].filter(([, r]) => r).length}`);
console.log(`perfis de membro testados: ${perfis.length}`);

if (problemas.length) {
  console.error(`\n${problemas.length} problema(s):`);
  problemas.forEach((p) => console.error(`  - ${p}`));
  process.exit(1);
}
console.log('\nOK: servidor e tela concordam, e todo perfil tem uma primeira tela que abre.');
