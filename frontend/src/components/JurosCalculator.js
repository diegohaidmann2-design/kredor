import React, { useMemo, useState } from 'react';
import { Calculator } from 'lucide-react';

const metodos = [
  { id: 'simples', label: 'Juros Simples' },
  { id: 'composto', label: 'Juros Compostos' },
  { id: 'price', label: 'Tabela Price' },
  { id: 'sac', label: 'SAC' },
];

const money = (v) =>
  `R$ ${Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

/**
 * Calculadora de juros e parcelas (simples, composto, Price, SAC).
 * Ferramenta pública/educativa da landing de controle de parcelas.
 */
const JurosCalculator = ({ isDark = true }) => {
  const [valor, setValor] = useState(1000);
  const [taxa, setTaxa] = useState(5);
  const [prazo, setPrazo] = useState(6);
  const [metodo, setMetodo] = useState('price');

  const r = useMemo(() => {
    const P = Number(valor) || 0;
    const i = (Number(taxa) || 0) / 100;
    const n = Math.max(1, Math.floor(Number(prazo) || 1));
    if (P <= 0) return null;

    if (metodo === 'simples') {
      const juros = P * i * n;
      const total = P + juros;
      return { parcela: total / n, total, juros, parcelaLabel: 'Parcela fixa' };
    }
    if (metodo === 'composto') {
      const montante = P * Math.pow(1 + i, n);
      const juros = montante - P;
      return { parcela: montante / n, total: montante, juros, parcelaLabel: 'Parcela (montante ÷ n)' };
    }
    if (metodo === 'price') {
      const pmt = i === 0 ? P / n : (P * i) / (1 - Math.pow(1 + i, -n));
      const total = pmt * n;
      return { parcela: pmt, total, juros: total - P, parcelaLabel: 'Parcela fixa (PMT)' };
    }
    // SAC
    const amort = P / n;
    const primeira = amort + P * i;
    const ultima = amort + amort * i;
    let total = 0;
    let saldo = P;
    for (let k = 0; k < n; k++) {
      total += amort + saldo * i;
      saldo -= amort;
    }
    return { parcela: primeira, ultima, total, juros: total - P, parcelaLabel: '1ª parcela (decrescente)' };
  }, [valor, taxa, prazo, metodo]);

  const inputCls = `w-full rounded-lg border px-3 py-2 text-sm ${
    isDark ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-300 text-slate-900'
  } focus:outline-none focus:ring-2 focus:ring-primary`;
  const cardCls = `rounded-xl border p-6 ${isDark ? 'bg-slate-800/50 border-slate-700' : 'bg-white border-slate-200'}`;

  return (
    <div className={cardCls} data-testid="juros-calculator">
      <div className="flex items-center gap-2 mb-4">
        <Calculator className="w-5 h-5 text-primary" />
        <h2 className="text-lg font-display font-semibold">Calculadora de juros e parcelas</h2>
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

      {r && (
        <div className="grid sm:grid-cols-3 gap-4" data-testid="calc-resultado">
          <div className={`rounded-lg p-4 ${isDark ? 'bg-slate-900' : 'bg-slate-50'}`}>
            <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>{r.parcelaLabel}</p>
            <p className="text-xl font-bold text-primary" data-testid="calc-parcela">{money(r.parcela)}</p>
            {r.ultima != null && (
              <p className={`text-xs mt-1 ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>última: {money(r.ultima)}</p>
            )}
          </div>
          <div className={`rounded-lg p-4 ${isDark ? 'bg-slate-900' : 'bg-slate-50'}`}>
            <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>Total de juros</p>
            <p className="text-xl font-bold" data-testid="calc-juros">{money(r.juros)}</p>
          </div>
          <div className={`rounded-lg p-4 ${isDark ? 'bg-slate-900' : 'bg-slate-50'}`}>
            <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>Total a receber</p>
            <p className="text-xl font-bold" data-testid="calc-total">{money(r.total)}</p>
          </div>
        </div>
      )}
      <p className={`text-xs mt-4 ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>
        Simulação educativa. No Kredor o cálculo é automático e já gera todas as parcelas, com multa e juros de mora em atrasos.
      </p>
    </div>
  );
};

export default JurosCalculator;
