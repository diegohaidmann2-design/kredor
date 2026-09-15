/**
 * Dados que o prerender injeta no HTML antes do React montar.
 *
 * O build grava `window.__PRERENDER__` com a configuração da landing e os planos buscados do
 * site público (scripts/prerender.js). Ler daqui faz o HTML estático já sair com os valores
 * do BANCO em vez dos padrões do código — que são uma cópia desatualizada e foi como /precos
 * chegou a anunciar R$ 197 e R$ 497 depois de os preços serem 100 e 200.
 */

const bruto = () => (typeof window !== 'undefined' && window.__PRERENDER__) || {};

/** Configuração da landing injetada no build, ou null. */
export const configPrerender = () => bruto().landingConfig || null;

/** Planos com ciclos injetados no build, ou null. */
export const planosPrerender = () => bruto().planos || null;
