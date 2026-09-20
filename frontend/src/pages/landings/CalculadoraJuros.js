import React, { useEffect, useState } from 'react';
import { Calculator, Loader2 } from 'lucide-react';
import CommercialLanding from '../../components/CommercialLanding';
import JsonLd from '../../components/JsonLd';
import { howToSchema } from '../../lib/seoSchema';
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

const HOWTO = howToSchema({
  name: 'Como calcular os juros de um empréstimo',
  description:
    'Passo a passo para calcular a parcela, o total e os juros de um empréstimo em juros simples, compostos, Tabela Price ou SAC.',
  steps: [
    { name: 'Informe o valor emprestado', text: 'Digite quanto será emprestado (o valor principal), por exemplo R$ 1.000,00.' },
    { name: 'Defina a taxa de juros ao mês', text: 'Informe a taxa de juros mensal em porcentagem, por exemplo 5% ao mês. Se você tem a taxa anual, converta antes.' },
    { name: 'Escolha o prazo em meses', text: 'Indique em quantas parcelas mensais o empréstimo será pago, por exemplo 6 meses.' },
    { name: 'Selecione o método de cálculo', text: 'Escolha entre juros simples, juros compostos, Tabela Price ou SAC e veja na hora a parcela, o total de juros e o total a receber.' },
  ],
});

// Cenário-base usado nos exemplos: R$ 1.000, 5% ao mês, 6 meses. Valores ilustrativos
// (a calculadora ao vivo calcula os centavos exatos com Decimal no backend).
const EXEMPLOS = [
  { metodo: 'Juros simples', parcela: 'R$ 216,67', juros: 'R$ 300,00', total: 'R$ 1.300,00', nota: 'Juros só sobre o principal (1.000 × 5% × 6).' },
  { metodo: 'Juros compostos', parcela: '—', juros: 'R$ 340,10', total: 'R$ 1.340,10', nota: 'Montante = 1.000 × (1,05)⁶.' },
  { metodo: 'Tabela Price', parcela: 'R$ 197,02', juros: 'R$ 182,11', total: 'R$ 1.182,11', nota: 'Parcela fixa do início ao fim.' },
  { metodo: 'SAC', parcela: 'R$ 216,67 → R$ 175,00', juros: 'R$ 175,00', total: 'R$ 1.175,00', nota: 'Amortização constante; parcela cai a cada mês.' },
];

const ExemplosCalculadora = ({ isDark }) => {
  const cardBg = isDark ? 'bg-slate-800/50 border-slate-700' : 'bg-white border-slate-200';
  return (
    <div className="mt-10">
      <h2 className="text-xl md:text-2xl font-display font-bold mb-3">
        Exemplos prontos: R$ 1.000 a 5% ao mês em 6 meses
      </h2>
      <p className={`text-sm mb-6 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
        Veja como o mesmo empréstimo de <strong>R$ 1.000,00</strong>, a uma taxa de <strong>5% ao mês</strong> por{' '}
        <strong>6 meses</strong>, resulta em parcela, juros e total diferentes conforme o método de cálculo. Use como
        referência rápida e confira os centavos exatos na calculadora acima.
      </p>
      <div className={`overflow-x-auto rounded-xl border ${cardBg}`}>
        <table className="w-full text-sm">
          <thead>
            <tr className={isDark ? 'text-slate-400' : 'text-slate-500'}>
              <th className="text-left py-3 px-4">Método</th>
              <th className="text-right py-3 px-4">Parcela</th>
              <th className="text-right py-3 px-4">Total de juros</th>
              <th className="text-right py-3 px-4">Total a receber</th>
            </tr>
          </thead>
          <tbody>
            {EXEMPLOS.map((e) => (
              <tr key={e.metodo} className={`border-t ${isDark ? 'border-slate-800' : 'border-slate-200'}`}>
                <td className="py-3 px-4">
                  <div className="font-medium">{e.metodo}</div>
                  <div className={`text-xs ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>{e.nota}</div>
                </td>
                <td className="text-right py-3 px-4 whitespace-nowrap">{e.parcela}</td>
                <td className="text-right py-3 px-4 whitespace-nowrap">{e.juros}</td>
                <td className="text-right py-3 px-4 whitespace-nowrap font-semibold text-primary">{e.total}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 className="text-xl md:text-2xl font-display font-bold mt-10 mb-4">Como calcular os juros em 4 passos</h2>
      <ol className={`space-y-3 text-sm ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
        <li><strong>1. Valor emprestado:</strong> informe o principal, ex.: R$ 1.000,00.</li>
        <li><strong>2. Taxa ao mês:</strong> informe a taxa mensal, ex.: 5% a.m. (converta se a sua taxa for anual).</li>
        <li><strong>3. Prazo:</strong> indique o número de parcelas mensais, ex.: 6 meses.</li>
        <li><strong>4. Método:</strong> escolha juros simples, compostos, Price ou SAC e compare parcela, juros e total.</li>
      </ol>
      <p className={`text-xs mt-6 ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>
        Valores ilustrativos para fins de comparação. A legislação pode limitar taxas e encargos conforme o tipo de
        operação — verifique sempre as regras aplicáveis.
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
    {({ isDark }) => (
      <>
        <JsonLd id="howto-calc-juros" data={HOWTO} />
        <CalculadoraWidget isDark={isDark} />
        <ExemplosCalculadora isDark={isDark} />
      </>
    )}
  </CommercialLanding>
);

export default CalculadoraJuros;
