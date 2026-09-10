import React, { useEffect, useState } from 'react';
import { Calculator, Loader2 } from 'lucide-react';
import { emprestimosAPI } from '../api/api';

const metodos = [
  { id: 'juros_simples', label: 'Juros Simples', parcelaLabel: 'Parcela fixa' },
  { id: 'juros_compostos', label: 'Juros Compostos', parcelaLabel: 'Parcela' },
  { id: 'tabela_price', label: 'Tabela Price', parcelaLabel: 'Parcela fixa (PMT)' },
  { id: 'sac', label: 'SAC', parcelaLabel: '1ª parcela (decrescente)' },
];

const money = (v) =>
  `R$ ${Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/**
 * Calculadora de juros e parcelas (simples, composto, Price, SAC).
 * Toda a aritmética de dinheiro vem do backend (POST /api/emprestimos/simular-publico),
 * a mesma fonte que gera o contrato — a tela nunca diverge do valor assinado.
 */
const JurosCalculator = ({ isDark = true }) => {
  const [valor, setValor] = useState(1000);
  const [taxa, setTaxa] = useState(5);
  const [prazo, setPrazo] = useState(6);
  const [metodo, setMetodo] = useState('tabela_price');

  const [resultado, setResultado] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    const P = Number(valor) || 0;
    const n = Math.max(1, Math.floor(Number(prazo) || 1));
    const t = Number(taxa) || 0;

    if (P <= 0) {
      setResultado(null);
      setErro(null);
      setCarregando(false);
      return;
    }

    let ativo = true;
    setCarregando(true);
    setErro(null);

    // Debounce: espera o usuário parar de digitar antes de chamar a rede.
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
        const primeira = parcelas[0]?.valor_total ?? 0;
        const ultima = parcelas.length ? parcelas[parcelas.length - 1].valor_total : 0;
        setResultado({
          parcela: primeira,
          ultima: metodo === 'sac' ? ultima : null,
          total: data.valor_total_com_juros,
          juros: data.valor_total_juros,
        });
        setErro(null);
      } catch (e) {
        if (!ativo) return;
        const detail = e?.response?.data?.detail;
        setErro(typeof detail === 'string' ? detail : 'Não foi possível calcular agora. Tente novamente.');
        setResultado(null);
      } finally {
        if (ativo) setCarregando(false);
      }
    }, 450);

    return () => {
      ativo = false;
      clearTimeout(timer);
    };
  }, [valor, taxa, prazo, metodo]);

  const metodoAtual = metodos.find((m) => m.id === metodo);

  const inputCls = `w-full rounded-lg border px-3 py-2 text-sm ${
    isDark ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-300 text-slate-900'
  } focus:outline-none focus:ring-2 focus:ring-primary`;
  const cardCls = `rounded-xl border p-6 ${isDark ? 'bg-slate-800/50 border-slate-700' : 'bg-white border-slate-200'}`;

  return (
    <div className={cardCls} data-testid="juros-calculator">
      <div className="flex items-center gap-2 mb-4">
        <Calculator className="w-5 h-5 text-primary" />
        <h2 className="text-lg font-display font-semibold">Calculadora de juros e parcelas</h2>
        {carregando && <Loader2 className="w-4 h-4 text-primary animate-spin ml-1" data-testid="calc-loading" />}
      </div>

      <div className="grid sm:grid-cols-3 gap-4 mb-4">
        <label className="block">
          <span className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>Valor principal (R$)</span>
          <input type="number" min="0" value={valor} onChange={(e) => setValor(e.target.value)} className={inputCls} data-testid="calc-valor" />
        </label>
        <label className="block">
          <span className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>Taxa ao mês (%)</span>
          <input type="number" min="0" step="0.1" value={taxa} onChange={(e) => setTaxa(e.target.value)} className={inputCls} data-testid="calc-taxa" />
        </label>
        <label className="block">
          <span className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>Prazo (meses)</span>
          <input type="number" min="1" value={prazo} onChange={(e) => setPrazo(e.target.value)} className={inputCls} data-testid="calc-prazo" />
        </label>
      </div>

      <div className="flex flex-wrap gap-2 mb-5">
        {metodos.map((m) => (
          <button
            key={m.id}
            onClick={() => setMetodo(m.id)}
            data-testid={`calc-metodo-${m.id}`}
            className={`text-sm rounded-full px-4 py-1.5 border transition ${
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

      {erro && (
        <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-400" data-testid="calc-erro">
          {erro}
        </div>
      )}

      {resultado && !erro && (
        <div className={`grid sm:grid-cols-3 gap-4 transition-opacity ${carregando ? 'opacity-50' : 'opacity-100'}`} data-testid="calc-resultado">
          <div className={`rounded-lg p-4 ${isDark ? 'bg-slate-900' : 'bg-slate-50'}`}>
            <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>{metodoAtual?.parcelaLabel}</p>
            <p className="text-xl font-bold text-primary" data-testid="calc-parcela">{money(resultado.parcela)}</p>
            {resultado.ultima != null && (
              <p className={`text-xs mt-1 ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>última: {money(resultado.ultima)}</p>
            )}
          </div>
          <div className={`rounded-lg p-4 ${isDark ? 'bg-slate-900' : 'bg-slate-50'}`}>
            <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>Total de juros</p>
            <p className="text-xl font-bold" data-testid="calc-juros">{money(resultado.juros)}</p>
          </div>
          <div className={`rounded-lg p-4 ${isDark ? 'bg-slate-900' : 'bg-slate-50'}`}>
            <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>Total a receber</p>
            <p className="text-xl font-bold" data-testid="calc-total">{money(resultado.total)}</p>
          </div>
        </div>
      )}
      <p className={`text-xs mt-4 ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>
        Simulação educativa calculada pelo mesmo motor do Kredor. No sistema o cálculo é automático e já gera todas as parcelas, com multa e juros de mora em atrasos.
      </p>
    </div>
  );
};

export default JurosCalculator;
