import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import ErrorMessage from '../components/ErrorMessage';
import { emprestimosAPI, pagamentosAPI, whatsappAPI } from '../api/api';
import { formatarMoeda, formatarData, hojeISO } from '../utils/formatters';
import RestanteDoPagamento from '../components/pagamentos/RestanteDoPagamento';
import { RefreshCw, TrendingUp, Wallet, AlertTriangle, CircleDollarSign, CalendarClock, ChevronRight, DollarSign, X, MessageCircle } from 'lucide-react';

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

  // Estado do modal de pagamento
  const [payItem, setPayItem] = useState(null);
  const [payValor, setPayValor] = useState('');
  const [payMetodo, setPayMetodo] = useState('dinheiro');
  const [payData, setPayData] = useState(hojeISO());
  // Quitar a parcela sem cobrar o que faltou (multa, mora ou juros que o credor não cobrou)
  const [payIgnorarRestante, setPayIgnorarRestante] = useState(false);
  const [paySubmitting, setPaySubmitting] = useState(false);
  const [payError, setPayError] = useState('');
  const [payOk, setPayOk] = useState('');

  // Cobrança via WhatsApp
  const [cobrandoId, setCobrandoId] = useState(null);
  const [toast, setToast] = useState(null); // { tipo: 'ok'|'erro', texto }

  const mostrarToast = (tipo, texto) => {
    setToast({ tipo, texto });
    setTimeout(() => setToast(null), 4000);
  };

  const cobrarWhatsapp = async (item, e) => {
    if (e) e.stopPropagation();
    const parcelaId = item?.proxima_parcela?.parcela_id;
    if (!parcelaId) return;
    setCobrandoId(item.emprestimo_id);
    try {
      // Cobrança MANUAL de 1 parcela => envio IMEDIATO (usar_fila=false)
      const resp = await whatsappAPI.enviarCobrancaParcela(parcelaId, false);
      if (resp.data?.success === false) {
        // Anti-spam bloqueou => cai para a fila
        await whatsappAPI.enviarCobrancaParcela(parcelaId, true);
        const prox = resp.data?.proximo_disponivel;
        let quando = 'nos próximos minutos';
        if (prox) {
          const min = Math.max(1, Math.ceil((new Date(prox).getTime() - Date.now()) / 60000));
          quando = `em ~${min} min`;
        }
        mostrarToast('ok', `Limite anti-spam: cobrança de ${item.cliente_nome} foi para a fila e sai ${quando}.`);
      } else {
        mostrarToast('ok', `Cobrança enviada no WhatsApp de ${item.cliente_nome}.`);
      }
      if (typeof carregar === 'function') carregar({ silencioso: true });
    } catch (err) {
      mostrarToast('erro', err?.response?.data?.detail || 'Não foi possível enviar a cobrança.');
    } finally {
      setCobrandoId(null);
    }
  };

  const abrirPagamento = (item, e) => {
    if (e) e.stopPropagation();
    setPayItem(item);
    setPayValor(item?.proxima_parcela?.valor ? String(item.proxima_parcela.valor) : '');
    setPayMetodo('dinheiro');
    setPayIgnorarRestante(false);
    setPayError('');
    setPayOk('');
  };

  const fecharPagamento = () => {
    if (paySubmitting) return;
    setPayItem(null);
  };

  const submitPagamento = async () => {
    const valor = parseFloat(String(payValor).replace(',', '.'));
    if (!payItem?.proxima_parcela?.parcela_id) {
      setPayError('Parcela inválida.');
      return;
    }
    if (!valor || valor <= 0) {
      setPayError('Informe um valor válido.');
      return;
    }
    setPaySubmitting(true);
    setPayError('');
    try {
      await pagamentosAPI.criar({
        parcela_id: payItem.proxima_parcela.parcela_id,
        valor_pago: valor,
        data_pagamento: payData,
        metodo_pagamento: payMetodo,
        quitar_ignorando_restante: payIgnorarRestante,
      });
      setPayOk('Pagamento registrado!');
      await carregar({ silencioso: true });
      setTimeout(() => setPayItem(null), 700);
    } catch (err) {
      setPayError(err?.response?.data?.detail || 'Erro ao registrar pagamento.');
    } finally {
      setPaySubmitting(false);
    }
  };

  const carregar = async ({ silencioso = false } = {}) => {
    // Silencioso: a tela continua visível enquanto atualiza. Ligar o loading aqui trocava
    // a página inteira pelo "Carregando..." a cada ação concluída.
    if (!silencioso) setLoading(true);
    setError('');
    try {
      const { data } = await emprestimosAPI.resumoAbertos();
      setDados(data);
    } catch (e) {
      setError('Não foi possível carregar o resumo dos empréstimos abertos.');
    } finally {
      if (!silencioso) setLoading(false);
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
      <div className="p-4 sm:p-6 space-y-6 sm:space-y-8 pb-24" data-testid="emprestimos-abertos-page">
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
                        {{ mensal: '/mês', semanal: '/semana', quinzenal: '/quinzena', diario: '/dia' }[it.periodicidade] || '/mês'}
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

                      <button
                        data-testid={`btn-cobrar-${it.emprestimo_id}`}
                        onClick={(e) => cobrarWhatsapp(it, e)}
                        disabled={!proxima || !emAtraso || cobrandoId === it.emprestimo_id}
                        title={emAtraso ? 'Enviar cobrança no WhatsApp do cliente' : 'Sem parcela vencida'}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-green-500/15 px-3 py-2 text-xs font-semibold text-green-300 transition-colors hover:bg-green-500/25 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        <MessageCircle className="h-3.5 w-3.5" />
                        {cobrandoId === it.emprestimo_id ? 'Enviando...' : 'Cobrar'}
                      </button>

                      <button
                        data-testid={`btn-pagar-${it.emprestimo_id}`}
                        onClick={(e) => abrirPagamento(it, e)}
                        disabled={!proxima}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-500/15 px-3 py-2 text-xs font-semibold text-emerald-300 transition-colors hover:bg-emerald-500/25 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        <DollarSign className="h-3.5 w-3.5" /> Pagar
                      </button>

                      <ChevronRight className="h-5 w-5 text-slate-600 transition-colors group-hover:text-emerald-400" />
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>

      {/* Modal de pagamento rápido */}
      {payItem && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
          data-testid="modal-pagamento-aberto"
          onClick={fecharPagamento}
        >
          <div
            className="w-full max-w-md rounded-2xl border border-white/10 bg-slate-900 p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h3 className="text-lg font-bold text-white">Registrar pagamento</h3>
                <p className="text-sm text-slate-400">{payItem.cliente_nome}</p>
              </div>
              <button
                data-testid="btn-fechar-modal-pagamento"
                onClick={fecharPagamento}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {payItem.proxima_parcela && (
              <div className="mb-4 rounded-xl border border-white/10 bg-slate-950/50 p-3 text-sm text-slate-300">
                Parcela #{payItem.proxima_parcela.numero_parcela} · vence{' '}
                {formatarData(payItem.proxima_parcela.data_vencimento)}
                {payItem.proxima_parcela.dias_atraso > 0 && (
                  <span className="text-red-400"> · {payItem.proxima_parcela.dias_atraso}d atraso</span>
                )}
              </div>
            )}

            <label className="mb-1 block text-xs uppercase tracking-wider text-slate-400">Valor pago</label>
            <input
              data-testid="input-valor-pagamento"
              type="number"
              step="0.01"
              value={payValor}
              onChange={(e) => setPayValor(e.target.value)}
              className="mb-4 w-full rounded-xl border border-white/10 bg-slate-950/60 px-4 py-2.5 text-white outline-none focus:border-emerald-500"
              placeholder="0,00"
            />

            <label className="mb-1 block text-xs uppercase tracking-wider text-slate-400">Data do pagamento</label>
            <input
              data-testid="input-data-pagamento"
              type="date"
              value={payData}
              max={hojeISO()}
              onChange={(e) => setPayData(e.target.value)}
              className="mb-1 w-full rounded-xl border border-white/10 bg-slate-950/60 px-4 py-2.5 text-white outline-none focus:border-emerald-500"
            />
            <p className="mb-4 text-xs text-slate-400">Dia em que o cliente pagou. Multa e mora são calculadas por esta data.</p>

            <div className="mb-4">
              <RestanteDoPagamento
                parcelaId={payItem?.proxima_parcela?.parcela_id}
                valorPago={String(payValor).replace(',', '.')}
                dataPagamento={payData}
                ignorar={payIgnorarRestante}
                onChangeIgnorar={setPayIgnorarRestante}
              />
            </div>

            <label className="mb-1 block text-xs uppercase tracking-wider text-slate-400">Forma de pagamento</label>
            <select
              data-testid="select-metodo-pagamento"
              value={payMetodo}
              onChange={(e) => setPayMetodo(e.target.value)}
              className="mb-4 w-full rounded-xl border border-white/10 bg-slate-950/60 px-4 py-2.5 text-white outline-none focus:border-emerald-500"
            >
              <option value="dinheiro">Dinheiro</option>
              <option value="pix">PIX</option>
              <option value="transferencia">Transferência</option>
              <option value="boleto">Boleto</option>
              <option value="cartao">Cartão</option>
            </select>

            {payError && (
              <p className="mb-3 text-sm text-red-400" data-testid="pagamento-erro">{payError}</p>
            )}
            {payOk && (
              <p className="mb-3 text-sm text-emerald-400" data-testid="pagamento-sucesso">{payOk}</p>
            )}

            <button
              data-testid="btn-confirmar-pagamento"
              onClick={submitPagamento}
              disabled={paySubmitting}
              className="w-full rounded-xl bg-emerald-500 px-4 py-3 font-semibold text-slate-950 transition-colors hover:bg-emerald-400 disabled:opacity-50"
            >
              {paySubmitting ? 'Registrando...' : 'Confirmar pagamento'}
            </button>
          </div>
        </div>
      )}
      {/* Toast de feedback da cobrança */}
      {toast && (
        <div
          data-testid="toast-cobranca"
          className={`fixed bottom-6 right-6 z-50 max-w-sm rounded-xl border px-4 py-3 text-sm font-medium shadow-2xl backdrop-blur ${
            toast.tipo === 'ok'
              ? 'border-emerald-500/40 bg-emerald-500/15 text-emerald-200'
              : 'border-red-500/40 bg-red-500/15 text-red-200'
          }`}
        >
          {toast.texto}
        </div>
      )}
    </Layout>
  );
};

export default EmprestimosAbertos;
