import React, { useEffect, useState } from 'react';
import { Calculator, Loader2 } from 'lucide-react';
import CommercialLanding from '../../components/CommercialLanding';
import { emprestimosAPI } from '../../api/api';

const brl = (v) =>
  (Number.isFinite(v) ? v : 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

// Ids iguais aos que o backend aceita: a tela não traduz nem recalcula nada.
const METODOS = [
  { id: 'tabela_price', label: 'Price (parcela fixa)' },
  { id: 'sac', label: 'SAC (decrescente)' },
  { id: 'juros_simples', label: 'Juros simples' },
  { id: 'juros_compostos', label: 'Juros compostos' },
];

/**
 * Toda a aritmética de dinheiro vem de POST /api/emprestimos/simular-publico — a mesma fonte que
 * gera as parcelas de um empréstimo de verdade. Refazer a conta aqui faria a vitrine divergir do
 * sistema: o backend arredonda em centavos inteiros com Decimal, o JavaScript não.
 */
const CalculadoraWidget = ({ isDark }) => {
  const [metodo, setMetodo] = useState('tabela_price');
  const [valor, setValor] = useState('1000');
  const [taxa, setTaxa] = useState('5');
  const [prazo, setPrazo] = useState('6');

  const [res, setRes] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState(null);
  // O primeiro cálculo é automático e ilustrativo. Se ele falhar antes de o visitante mexer em
  // nada, não há o que avisar — e o prerender do build (que não alcança a API) gravava a mensagem
  // de erro no HTML estático. Depois que ele digita, toda falha é reportada.
  const [interagiu, setInteragiu] = useState(false);

  useEffect(() => {
    const P = parseFloat(valor);
    const n = Math.max(1, Math.floor(parseInt(prazo, 10) || 1));
    const t = parseFloat(taxa) || 0;

    if (!(P > 0)) {
      setRes(null);
      setErro(null);
      setCarregando(false);
      return undefined;
    }

    let ativo = true;
    setCarregando(true);
    setErro(null);

    // Debounce: espera parar de digitar antes de chamar a rede.
    const timer = setTimeout(async () => {
      try {
        const { data } = await emprestimosAPI.simularPublico({
          valor_principal: P,
          taxa_juros_mensal: t,
          prazo_meses: n,
          metodo_calculo: metodo,
          periodicidade: 'mensal',
        });
        if (!ativo) return;
        const parcelas = data.parcelas || [];
        setRes({
          parcela: parcelas[0]?.valor_total ?? 0,
          juros: data.valor_total_juros,
          total: data.valor_total_com_juros,
          // Tabela de amortização só faz sentido quando o saldo cai parcela a parcela.
          parcelas: ['tabela_price', 'sac'].includes(metodo) ? parcelas : null,
        });
      } catch (e) {
        if (!ativo) return;
        const detail = e?.response?.data?.detail;
        setErro(typeof detail === 'string' ? detail : 'Não foi possível calcular agora. Tente novamente.');
        setRes(null);
      } finally {
        if (ativo) setCarregando(false);
      }
    }, 450);

    return () => {
      ativo = false;
      clearTimeout(timer);
    };
  }, [metodo, valor, taxa, prazo]);

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
            onClick={() => { setInteragiu(true); setMetodo(m.id); }}
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
          <input type="number" min="0" value={valor} onChange={(e) => { setInteragiu(true); setValor(e.target.value); }} data-testid="input-valor"
            className={`mt-1 w-full rounded-lg border px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary/30 ${field}`} />
        </label>
        <label className="block">
          <span className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>Taxa de juros (% ao mês)</span>
          <input type="number" min="0" step="0.1" value={taxa} onChange={(e) => { setInteragiu(true); setTaxa(e.target.value); }} data-testid="input-taxa"
            className={`mt-1 w-full rounded-lg border px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary/30 ${field}`} />
        </label>
        <label className="block">
          <span className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>Prazo (meses)</span>
          <input type="number" min="1" value={prazo} onChange={(e) => { setInteragiu(true); setPrazo(e.target.value); }} data-testid="input-prazo"
            className={`mt-1 w-full rounded-lg border px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary/30 ${field}`} />
        </label>
      </div>

      {erro && interagiu && (
        <p className="mb-6 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm" data-testid="calc-erro">
          {erro}
        </p>
      )}

      {carregando && !res && (
        <p className={`mb-6 flex items-center gap-2 text-sm ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
          <Loader2 className="w-4 h-4 animate-spin" /> Calculando...
        </p>
      )}

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
                    <tr key={l.numero_parcela} className={`border-t ${isDark ? 'border-slate-800' : 'border-slate-200'}`}>
                      <td className="py-2 pr-4">{l.numero_parcela}</td>
                      <td className="text-right py-2 pr-4">{brl(l.valor_total)}</td>
                      <td className="text-right py-2 pr-4">{brl(l.valor_juros)}</td>
                      <td className="text-right py-2 pr-4">{brl(l.valor_principal)}</td>
                      <td className="text-right py-2">{brl(l.saldo_devedor)}</td>
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
