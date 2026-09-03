import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import ErrorMessage from '../components/ErrorMessage';
import { emprestimosAPI } from '../api/api';
import { formatarMoeda, formatarData } from '../utils/formatters';
import { RefreshCw, TrendingUp, Wallet, AlertTriangle, CircleDollarSign, CalendarClock, ChevronRight } from 'lucide-react';

const StatBox = ({ icon: Icon, label, valor, cor, testId }) => (
  <div
    data-testid={testId}
    className="flex items-center gap-4 rounded-2xl border border-white/10 bg-slate-900/60 p-5 backdrop-blur"
  >
    <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${cor}`}>
      <Icon className="h-6 w-6" />
    </div>
    <div className="min-w-0">
      <p className="text-xs uppercase tracking-wider text-slate-400">{label}</p>
      <p className="truncate text-xl font-semibold text-white">{valor}</p>
    </div>
  </div>
);

const EmprestimosAbertos = () => {
  const [dados, setDados] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const carregar = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await emprestimosAPI.resumoAbertos();
      setDados(data);
    } catch (e) {
      setError('Não foi possível carregar o resumo dos empréstimos abertos.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    carregar();
  }, []);

  if (loading) return <Layout><Loading /></Layout>;

  const totais = dados?.totais || {};
  const itens = dados?.itens || [];

  return (
    <Layout>
      <div className="space-y-8" data-testid="emprestimos-abertos-page">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="flex items-center gap-3 text-2xl font-bold text-white">
              <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-400">
                <Wallet className="h-5 w-5" />
              </span>
              Empréstimos Abertos
            </h1>
            <p className="mt-1 text-sm text-slate-400">
              Empréstimos sem prazo (apenas juros) — juros acumulado e próxima parcela em aberto.
            </p>
          </div>
          <button
            data-testid="btn-atualizar-abertos"
            onClick={carregar}
            className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-slate-900/60 px-4 py-2 text-sm font-medium text-slate-200 transition-colors hover:bg-slate-800"
          >
            <RefreshCw className="h-4 w-4" /> Atualizar
          </button>
        </div>

        {error && <ErrorMessage message={error} />}

        {/* Totais */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatBox
            testId="total-emprestimos-abertos"
            icon={Wallet}
            label="Empréstimos abertos"
            valor={dados?.total_emprestimos ?? 0}
            cor="bg-sky-500/15 text-sky-400"
          />
          <StatBox
            testId="total-juros-gerado"
            icon={TrendingUp}
            label="Juros gerado (total)"
            valor={formatarMoeda(totais.juros_gerado || 0)}
            cor="bg-emerald-500/15 text-emerald-400"
          />
          <StatBox
            testId="total-juros-recebido"
            icon={CircleDollarSign}
            label="Juros recebido"
            valor={formatarMoeda(totais.juros_recebido || 0)}
            cor="bg-violet-500/15 text-violet-400"
          />
          <StatBox
            testId="total-juros-aberto"
            icon={AlertTriangle}
            label="Juros em aberto"
            valor={formatarMoeda(totais.juros_em_aberto || 0)}
            cor="bg-amber-500/15 text-amber-400"
          />
        </div>

        {/* Lista */}
        {itens.length === 0 ? (
          <div
            data-testid="empty-abertos"
            className="rounded-2xl border border-dashed border-white/10 bg-slate-900/40 p-12 text-center text-slate-400"
          >
            Nenhum empréstimo aberto no momento.
          </div>
        ) : (
          <div className="space-y-3">
            {itens.map((it, idx) => {
              const proxima = it.proxima_parcela;
              const emAtraso = proxima && proxima.dias_atraso > 0;
              return (
                <motion.div
                  key={it.emprestimo_id}
                  data-testid={`aberto-card-${it.emprestimo_id}`}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: Math.min(idx * 0.03, 0.3) }}
                  onClick={() => navigate(`/emprestimos/${it.emprestimo_id}`)}
                  className="group cursor-pointer rounded-2xl border border-white/10 bg-slate-900/60 p-5 transition-all hover:border-emerald-500/40 hover:bg-slate-900"
                >
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    {/* Cliente + status */}
                    <div className="min-w-[180px]">
                      <div className="flex items-center gap-2">
                        <p className="font-semibold text-white">{it.cliente_nome}</p>
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${
                            it.status === 'inadimplente'
                              ? 'bg-red-500/15 text-red-400'
                              : 'bg-emerald-500/15 text-emerald-400'
                          }`}
                        >
                          {it.status}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-slate-400">
                        Principal {formatarMoeda(it.valor_principal)} · {it.taxa_juros}%{' '}
                        {it.periodicidade === 'semanal' ? '/semana' : '/mês'}
                      </p>
                    </div>

                    {/* Juros */}
                    <div className="flex flex-wrap items-center gap-6">
                      <div className="text-right">
                        <p className="text-[10px] uppercase tracking-wider text-slate-500">Juros recebido</p>
                        <p className="font-semibold text-violet-300">{formatarMoeda(it.juros_recebido)}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-[10px] uppercase tracking-wider text-slate-500">Em aberto</p>
                        <p className="font-semibold text-amber-300">{formatarMoeda(it.juros_em_aberto)}</p>
                      </div>

                      {/* Próxima parcela */}
                      <div className="min-w-[190px] rounded-xl border border-white/10 bg-slate-950/40 px-3 py-2">
                        <p className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-slate-500">
                          <CalendarClock className="h-3 w-3" /> Próxima parcela
                        </p>
                        {proxima ? (
                          <div className="mt-0.5 flex items-center gap-2">
                            <span className="text-sm font-semibold text-white">
                              #{proxima.numero_parcela} · {formatarMoeda(proxima.valor)}
                            </span>
                            <span
                              className={`text-xs ${emAtraso ? 'text-red-400' : 'text-slate-400'}`}
                            >
                              {formatarData(proxima.data_vencimento)}
                              {emAtraso ? ` · ${proxima.dias_atraso}d atraso` : ''}
                            </span>
                          </div>
                        ) : (
                          <span className="text-sm text-slate-400">—</span>
                        )}
                      </div>

                      <ChevronRight className="h-5 w-5 text-slate-600 transition-colors group-hover:text-emerald-400" />
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>
    </Layout>
  );
};

export default EmprestimosAbertos;
