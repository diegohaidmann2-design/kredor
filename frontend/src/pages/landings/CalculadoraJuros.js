import React, { useMemo, useState } from 'react';
import { Calculator } from 'lucide-react';
import CommercialLanding from '../../components/CommercialLanding';

const brl = (v) =>
  (Number.isFinite(v) ? v : 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const METODOS = [
  { id: 'price', label: 'Price (parcela fixa)' },
  { id: 'sac', label: 'SAC (decrescente)' },
  { id: 'simples', label: 'Juros simples' },
  { id: 'composto', label: 'Juros compostos' },
];

function calcular(metodo, P, iPct, n) {
  const i = iPct / 100;
  if (!(P > 0) || !(n > 0) || i < 0) return null;

  if (metodo === 'simples') {
    const juros = P * i * n;
    const total = P + juros;
    return { total, juros, parcela: total / n, parcelas: null };
  }
  if (metodo === 'composto') {
    const total = P * Math.pow(1 + i, n);
    const juros = total - P;
    return { total, juros, parcela: total / n, parcelas: null };
  }
  if (metodo === 'price') {
    const pmt = i === 0 ? P / n : (P * i) / (1 - Math.pow(1 + i, -n));
    const total = pmt * n;
    const linhas = [];
    let saldo = P;
    for (let k = 1; k <= n; k++) {
      const jurosMes = saldo * i;
      const amort = pmt - jurosMes;
      saldo = Math.max(0, saldo - amort);
      linhas.push({ k, parcela: pmt, juros: jurosMes, amort, saldo });
    }
    return { total, juros: total - P, parcela: pmt, parcelas: linhas };
  }
  // SAC
  const amort = P / n;
  const linhas = [];
  let saldo = P;
  let total = 0;
  for (let k = 1; k <= n; k++) {
    const jurosMes = saldo * i;
    const parcela = amort + jurosMes;
    total += parcela;
    saldo = Math.max(0, saldo - amort);
    linhas.push({ k, parcela, juros: jurosMes, amort, saldo });
  }
  return { total, juros: total - P, parcela: linhas[0].parcela, parcelas: linhas };
}

const CalculadoraWidget = ({ isDark }) => {
  const [metodo, setMetodo] = useState('price');
  const [valor, setValor] = useState('1000');
  const [taxa, setTaxa] = useState('5');
  const [prazo, setPrazo] = useState('6');

  const res = useMemo(
    () => calcular(metodo, parseFloat(valor), parseFloat(taxa), parseInt(prazo, 10)),
    [metodo, valor, taxa, prazo]
  );

  const field = isDark
    ? 'bg-slate-900 border-slate-700 text-white'
    : 'bg-white border-slate-300 text-slate-900';
  const cardBg = isDark ? 'bg-slate-800/50 border-slate-700' : 'bg-white border-slate-200';

  return (
    <div className={`rounded-2xl border p-6 md:p-8 ${cardBg}`} data-testid="calculadora">
      <div className="flex items-center gap-2 mb-6">
        <Calculator className="w-5 h-5 text-primary" />
        <h2 className="text-lg font-display font-semibold">Calculadora de juros</h2>
      </div>

      <div className="flex flex-wrap gap-2 mb-6">
        {METODOS.map((m) => (
          <button
            key={m.id}
            onClick={() => setMetodo(m.id)}
            data-testid={`metodo-${m.id}`}
            className={`px-4 py-2 rounded-full text-sm font-medium border transition ${
              metodo === m.id
                ? 'bg-primary text-white border-primary'
                : isDark
                ? 'border-slate-700 text-slate-300 hover:border-primary'
                : 'border-slate-300 text-slate-700 hover:border-primary'
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      <div className="grid sm:grid-cols-3 gap-4 mb-6">
        <label className="block">
          <span className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>Valor emprestado (R$)</span>
          <input type="number" min="0" value={valor} onChange={(e) => setValor(e.target.value)} data-testid="input-valor"
            className={`mt-1 w-full rounded-lg border px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary/30 ${field}`} />
        </label>
        <label className="block">
          <span className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>Taxa de juros (% ao mês)</span>
          <input type="number" min="0" step="0.1" value={taxa} onChange={(e) => setTaxa(e.target.value)} data-testid="input-taxa"
            className={`mt-1 w-full rounded-lg border px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary/30 ${field}`} />
        </label>
        <label className="block">
          <span className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>Prazo (meses)</span>
          <input type="number" min="1" value={prazo} onChange={(e) => setPrazo(e.target.value)} data-testid="input-prazo"
            className={`mt-1 w-full rounded-lg border px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary/30 ${field}`} />
        </label>
      </div>

      {res && (
        <>
          <div className="grid grid-cols-3 gap-4 mb-6" data-testid="calc-resultado">
            <div className={`rounded-xl p-4 ${isDark ? 'bg-slate-900/60' : 'bg-slate-50'}`}>
              <p className={`text-xs ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>{res.parcelas ? '1ª parcela' : 'Parcela'}</p>
              <p className="text-xl md:text-2xl font-display font-bold text-primary">{brl(res.parcela)}</p>
            </div>
            <div className={`rounded-xl p-4 ${isDark ? 'bg-slate-900/60' : 'bg-slate-50'}`}>
              <p className={`text-xs ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>Total de juros</p>
              <p className="text-xl md:text-2xl font-display font-bold">{brl(res.juros)}</p>
            </div>
            <div className={`rounded-xl p-4 ${isDark ? 'bg-slate-900/60' : 'bg-slate-50'}`}>
              <p className={`text-xs ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>Total a receber</p>
              <p className="text-xl md:text-2xl font-display font-bold">{brl(res.total)}</p>
            </div>
          </div>

          {res.parcelas && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className={isDark ? 'text-slate-400' : 'text-slate-500'}>
                    <th className="text-left py-2 pr-4">#</th>
                    <th className="text-right py-2 pr-4">Parcela</th>
                    <th className="text-right py-2 pr-4">Juros</th>
                    <th className="text-right py-2 pr-4">Amortização</th>
                    <th className="text-right py-2">Saldo</th>
                  </tr>
                </thead>
                <tbody>
                  {res.parcelas.map((l) => (
                    <tr key={l.k} className={`border-t ${isDark ? 'border-slate-800' : 'border-slate-200'}`}>
                      <td className="py-2 pr-4">{l.k}</td>
                      <td className="text-right py-2 pr-4">{brl(l.parcela)}</td>
                      <td className="text-right py-2 pr-4">{brl(l.juros)}</td>
                      <td className="text-right py-2 pr-4">{brl(l.amort)}</td>
                      <td className="text-right py-2">{brl(l.saldo)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
      <p className={`text-xs mt-6 ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>
        Resultado estimado para fins de simulação. Confira sempre a legislação aplicável às suas operações.
      </p>
    </div>
  );
};

const CalculadoraJuros = () => (
  <CommercialLanding
    seo={{
      title: 'Calculadora de juros de empréstimo (Price, SAC, simples e composto) | Kredor',
      description: 'Calculadora de juros gratuita: simule parcela, total e juros por Tabela Price, SAC, juros simples e compostos. Ideal para credores e empréstimos particulares.',
      path: '/calculadora-de-juros',
      image: '/og-controle-de-parcelas-e-juros.jpg',
    }}
    eyebrow="Ferramenta grátis"
    h1="Calculadora de juros de empréstimo"
    subtitle="Simule parcelas, total e juros em Tabela Price, SAC, juros simples e compostos. Grátis, sem cadastro — e integrado ao Kredor quando você quiser automatizar."
    heroBullets={[
      'Compare Price, SAC, simples e composto',
      'Veja parcela, total e juros na hora',
      'Tabela de amortização parcela a parcela',
      'Sem cadastro para calcular',
    ]}
    differentials={[
      { title: 'Do cálculo à operação', text: 'Gostou do resultado? No Kredor você cadastra o empréstimo e as parcelas são geradas automaticamente com esse mesmo cálculo.' },
      { title: 'Encargos automáticos', text: 'Multa e juros de mora aplicados sozinhos em atrasos, sem você refazer contas.' },
      { title: 'Cobrança integrada', text: 'Cada parcela vira uma cobrança por PIX e WhatsApp com baixa automática.' },
      { title: 'Contratos e recibos', text: 'Formalize a operação com CCB e recibos em PDF gerados a partir do empréstimo.' },
    ]}
    faq={[
      { q: 'Qual a diferença entre Price e SAC?', a: 'Na Price a parcela é fixa do início ao fim. No SAC a amortização é constante e a parcela começa mais alta e diminui, resultando em menos juros no total.' },
      { q: 'A taxa é ao mês ou ao ano?', a: 'A calculadora usa a taxa ao mês. Se você tem a taxa anual, converta antes de simular.' },
      { q: 'O cálculo serve para empréstimo particular?', a: 'Sim. Os quatro métodos cobrem os cenários mais comuns de empréstimos particulares e microcrédito.' },
      { q: 'Preciso me cadastrar para usar?', a: 'Não. A calculadora é gratuita e não exige cadastro. O cadastro só é necessário para gerenciar os empréstimos no Kredor.' },
    ]}
    related={[
      { to: '/controle-de-parcelas-e-juros', label: 'Controle de parcelas e juros' },
      { to: '/blog/como-calcular-juros-de-emprestimo-particular', label: 'Como calcular juros (guia)' },
      { to: '/sistema-gestao-emprestimos', label: 'Sistema de gestão de empréstimos' },
      { to: '/precos', label: 'Ver preços' },
    ]}
  >
    {({ isDark }) => <CalculadoraWidget isDark={isDark} />}
  </CommercialLanding>
);

export default CalculadoraJuros;
