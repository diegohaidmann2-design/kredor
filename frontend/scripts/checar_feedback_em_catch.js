#!/usr/bin/env node
/**
 * Conta blocos `catch` que falham em avisar o usuário — e os que avisam duas vezes.
 *
 * Por que não dá para usar grep: `grep -A1 catch | grep -c console.error` olha uma linha e não
 * enxerga se o bloco já dá retorno ao usuário. Foi essa métrica que levou a inserir um toast em
 * blocos que já mostravam modal/alerta/erro na tela, criando mensagem dupla. Aqui o bloco é lido
 * inteiro, casando as chaves a partir da que abre depois do `catch (...)`.
 *
 * Dois defeitos entram no gate, medidos separado porque o conserto de um não pode criar o outro:
 *   sem_aviso  — registra no console/logger mas não diz nada ao usuário
 *   duplicado  — dois canais DIFERENTES para a mesma falha (ex.: toast + modal bloqueante)
 *
 * `engolido` (nem avisa nem registra) é só informativo e NÃO reprova: a maioria é silêncio
 * legítimo — parser de token que devolve `null`, decodificador que preserva o erro original.
 * Exigir aviso nesses seria o mesmo anti-padrão que se quer evitar.
 *
 * O gate vale só para `pages/` e `components/`, onde existe a operação que o usuário disparou.
 * Em `utils/`, `hooks/`, `context/` e `api/` a função não tem como avisar ninguém — ela devolve
 * um valor e quem chamou decide o que dizer; essas ocorrências saem listadas como `fora_do_gate`.
 *
 * Dois `setError` em ramos distintos do mesmo `if/else` não são duplicidade: só um roda. Por isso
 * a contagem é de canais distintos, não de chamadas.
 *
 * Há bloco que deve ficar calado (recurso opcional que falhou, prévia que só deixa de aparecer,
 * limpeza em `finally`). Para esses, escreva no bloco um comentário `// silencioso: <motivo>` —
 * o medidor passa a ignorá-lo, e o motivo fica no código para quem for ler depois.
 *
 * Uso:  node scripts/checar_feedback_em_catch.js [caminho] [-v] [--json]
 * Sai com 1 se houver qualquer ocorrência dos dois tipos.
 */
const fs = require('fs');
const path = require('path');

// Cada canal é uma superfície de UI diferente vista pelo usuário.
const CANAIS = {
  toast: /\btoast\s*\(/,
  modal: /\bmodal\.(?:error|success|warning|info)\s*\(|\bshowModal\s*\(/,
  alerta: /\balert\s*\(/,
  inline: /\bset(?:Error|Erro|PayError|Mensagem|Snack|StatusMsg)\w*\s*\(/,
};

const CATCH = /\bcatch\s*\([^)]*\)\s*\{|\bcatch\s*\{/g;
const LOG = /console\.(?:error|warn)\s*\(|logger\.\w+\s*\(|Sentry\./;
const SILENCIO_PROPOSITAL = /\/\/\s*silencioso:/;

function arquivosJs(raiz) {
  const saida = [];
  (function andar(dir) {
    for (const item of fs.readdirSync(dir, { withFileTypes: true })) {
      if (item.name === 'node_modules' || item.name.startsWith('.')) continue;
      const cheio = path.join(dir, item.name);
      if (item.isDirectory()) andar(cheio);
      else if (/\.jsx?$/.test(item.name)) saida.push(cheio);
    }
  })(raiz);
  return saida.sort();
}

/** Corpo do bloco que começa na chave em `inicio` (índice do `{`). */
function corpoDoBloco(fonte, inicio) {
  let nivel = 0;
  for (let i = inicio; i < fonte.length; i += 1) {
    if (fonte[i] === '{') nivel += 1;
    else if (fonte[i] === '}') {
      nivel -= 1;
      if (nivel === 0) return fonte.slice(inicio + 1, i);
    }
  }
  return fonte.slice(inicio + 1); // arquivo malformado: conta o que sobrou
}

const raiz = process.argv.find((a) => !a.startsWith('-') && a !== process.argv[0] && a !== process.argv[1]) || 'src';
// Onde o usuário disparou a ação e há tela para avisá-lo.
const NO_GATE = /(?:^|\/)(?:pages|components)\//;

const engolido = [];
const semAviso = [];
const duplicado = [];
const foraDoGate = [];

for (const arquivo of arquivosJs(raiz)) {
  const fonte = fs.readFileSync(arquivo, 'utf8');
  const linhaDe = (indice) => fonte.slice(0, indice).split('\n').length;
  CATCH.lastIndex = 0;
  let m;
  while ((m = CATCH.exec(fonte)) !== null) {
    const corpo = corpoDoBloco(fonte, m.index + m[0].length - 1);
    const canais = Object.keys(CANAIS).filter((c) => CANAIS[c].test(corpo));
    const onde = `${arquivo}:${linhaDe(m.index)}`;
    if (SILENCIO_PROPOSITAL.test(corpo)) continue;
    const dentroDoGate = NO_GATE.test(arquivo);
    if (canais.length === 0) {
      // Sem canal de aviso: distingue o que ao menos deixa rastro do que não deixa nada.
      if (!dentroDoGate) foraDoGate.push(onde);
      else (LOG.test(corpo) ? semAviso : engolido).push(onde);
    } else if (canais.length >= 2) {
      (dentroDoGate ? duplicado : foraDoGate).push(`${onde} (${canais.join(' + ')})`);
    }
  }
}

if (process.argv.includes('--json')) {
  console.log(JSON.stringify({ sem_aviso: semAviso, duplicado, engolido, fora_do_gate: foraDoGate }, null, 2));
} else {
  console.log(`sem_aviso (registra, não avisa):    ${semAviso.length}   <- gate`);
  console.log(`duplicado (dois canais na falha):   ${duplicado.length}   <- gate`);
  console.log(`engolido  (nem avisa nem registra): ${engolido.length}   (informativo)`);
  console.log(`fora do gate (utils/hooks/context/api): ${foraDoGate.length}   (informativo)`);
  if (process.argv.includes('-v')) {
    if (engolido.length) console.log('\n-- engolido --\n' + engolido.join('\n'));
    if (foraDoGate.length) console.log('\n-- fora do gate --\n' + foraDoGate.join('\n'));
    if (semAviso.length) console.log('\n-- sem aviso --\n' + semAviso.join('\n'));
    if (duplicado.length) console.log('\n-- duplicado --\n' + duplicado.join('\n'));
  }
}

process.exit(semAviso.length + duplicado.length > 0 ? 1 : 0);
