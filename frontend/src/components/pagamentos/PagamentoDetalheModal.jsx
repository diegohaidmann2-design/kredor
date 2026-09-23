import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { X, Calendar, Wallet, StickyNote, ArrowRight, Landmark, MessageCircle, History, Receipt, ChevronDown } from 'lucide-react';
import Button from '../Button';
import RestanteDoPagamento from './RestanteDoPagamento';
import { formatarMoeda, formatarData, hojeISO } from '../../utils/formatters';

/**
 * Modal de detalhe da parcela — estilo Rocket Money adaptado ao tema escuro Kredor.
 * Esquerda: informação clara com valor em destaque. Direita: AÇÕES (registrar pagamento).
 */
const METODOS = [
  { value: 'pix', label: 'PIX' },
  { value: 'transferencia', label: 'Transferência' },
  { value: 'dinheiro', label: 'Dinheiro' },
  { value: 'cartao', label: 'Cartão' },
  { value: 'boleto', label: 'Boleto' },
];

const STATUS = {
  atrasado: { label: 'Atrasado', dot: 'bg-red-500', text: 'text-red-400' },
  parcial: { label: 'Pagamento parcial', dot: 'bg-violet-500', text: 'text-violet-300' },
  pendente: { label: 'Pendente', dot: 'bg-slate-400', text: 'text-slate-300' },
};

const PagamentoDetalheModal = ({ parcela, form, setForm, onSubmit, onClose, onCobrar, historico = [], onRecibo }) => {
  const [showHist, setShowHist] = useState(false);
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  if (!parcela) return null;

  const valorDevido =
    parcela.valor_total - parcela.valor_pago + (parcela.valor_multa || 0) + (parcela.valor_juros_mora || 0);
  const temMulta = (parcela.valor_multa || 0) > 0;
  const temMora = (parcela.valor_juros_mora || 0) > 0;
  const ref = (parcela.emprestimo_id || '').slice(-6).toUpperCase();
  const totalParc = parcela.total_parcelas || '∞';
  const st = STATUS[parcela.status] || STATUS.pendente;

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-[#050807]/80 backdrop-blur-md animate-fade-in font-satoshi"
      data-testid="pagamento-modal"
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <button
        onClick={onClose}
        className="absolute top-5 right-5 sm:top-7 sm:right-7 z-[10001] h-11 w-11 rounded-full bg-white/5 ring-1 ring-white/10 text-white/80 flex items-center justify-center hover:bg-white/10 hover:text-white transition-colors"
        data-testid="cancelar-button"
        aria-label="Fechar"
      >
        <X className="w-5 h-5" strokeWidth={1.5} />
      </button>

      <div
        className="relative w-full max-w-4xl bg-card rounded-xl ring-1 ring-white/10 shadow-[0_32px_64px_rgba(0,0,0,0.5)] overflow-hidden animate-scale-in"
        style={{ zIndex: 10000 }}
        role="dialog"
        aria-modal="true"
        aria-label="Detalhe da parcela e registro de pagamento"
      >
        <div className="grid grid-cols-1 md:grid-cols-12">
          {/* ESQUERDA — informação */}
          <div className="md:col-span-7 px-7 sm:px-9 py-8 md:border-r border-white/10 space-y-7">
            <span className="inline-flex items-center gap-2 rounded-full bg-white/[0.03] ring-1 ring-white/10 px-3 py-1.5 text-xs font-medium text-foreground/80">
              <Calendar className="w-3.5 h-3.5 text-muted-foreground" strokeWidth={1.5} />
              <span className="font-mono">Vence {formatarData(parcela.data_vencimento)}</span>
            </span>

            <div>
              <div className="flex items-center gap-2 mb-3">
                <span className={`h-2 w-2 rounded-full ${st.dot}`} />
                <span className={`text-sm font-medium ${st.text}`}>
                  {st.label}{parcela.dias_atraso > 0 ? ` · ${parcela.dias_atraso} dias` : ''}
                </span>
              </div>
              <h2 className="font-cabinet font-extrabold text-2xl text-foreground tracking-tight truncate" data-testid="detalhe-cliente-nome">
                {parcela.cliente_nome || 'Cliente'}
              </h2>
              {parcela.cliente_telefone && (
                <p className="text-sm text-muted-foreground font-mono">{parcela.cliente_telefone}</p>
              )}
            </div>

            <div>
              <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground mb-2">Total a receber</p>
              <p className="font-mono font-semibold text-5xl sm:text-6xl text-foreground leading-none tracking-tight" data-testid="detalhe-valor-devido">
                {formatarMoeda(valorDevido)}
              </p>
            </div>

            <div className="space-y-0 rounded-xl ring-1 ring-white/10 overflow-hidden">
              <Linha rotulo="Valor da parcela" valor={formatarMoeda(parcela.valor_total)} />
              {parcela.valor_pago > 0 && (
                <Linha rotulo="Já pago" valor={`− ${formatarMoeda(parcela.valor_pago)}`} classe="text-emerald-400" />
              )}
              {temMulta && <Linha rotulo="Multa" valor={`+ ${formatarMoeda(parcela.valor_multa)}`} classe="text-red-400" />}
              {temMora && <Linha rotulo="Juros de mora" valor={`+ ${formatarMoeda(parcela.valor_juros_mora)}`} classe="text-orange-400" />}
            </div>

            <p className="font-mono text-[11px] tracking-wide text-muted-foreground uppercase flex items-center gap-1.5">
              <Landmark className="w-3.5 h-3.5" strokeWidth={1.5} />
              Empréstimo #{ref} · Parcela {parcela.numero_parcela}/{totalParc}
            </p>

            {/* AÇÕES — como no Rocket Money */}
            <div className="pt-1 space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Ações</p>
              <button
                type="button"
                onClick={onCobrar}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-md ring-1 ring-white/10 bg-background hover:bg-white/5 transition-colors text-left"
                data-testid="modal-acao-cobrar"
              >
                <span className="flex items-center justify-center w-8 h-8 rounded-md bg-emerald-500/10 text-emerald-400 shrink-0">
                  <MessageCircle className="w-4 h-4" strokeWidth={1.5} />
                </span>
                <span className="flex-1 min-w-0">
                  <span className="block text-sm font-medium text-foreground">Cobrar no WhatsApp</span>
                  <span className="block text-xs text-muted-foreground">Enviar lembrete de cobrança</span>
                </span>
                <ArrowRight className="w-4 h-4 text-muted-foreground shrink-0" strokeWidth={1.5} />
              </button>

              {historico.length > 0 && (
                <button
                  type="button"
                  onClick={() => setShowHist((v) => !v)}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-md ring-1 ring-white/10 bg-background hover:bg-white/5 transition-colors text-left"
                  data-testid="modal-acao-historico"
                  aria-expanded={showHist}
                >
                  <span className="flex items-center justify-center w-8 h-8 rounded-md bg-white/5 text-foreground/70 shrink-0">
                    <History className="w-4 h-4" strokeWidth={1.5} />
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className="block text-sm font-medium text-foreground">Ver histórico</span>
                    <span className="block text-xs text-muted-foreground">{historico.length} pagamento{historico.length === 1 ? '' : 's'} nesta parcela</span>
                  </span>
                  <ChevronDown className={`w-4 h-4 text-muted-foreground shrink-0 transition-transform ${showHist ? 'rotate-180' : ''}`} strokeWidth={1.5} />
                </button>
              )}

              {showHist && historico.length > 0 && (
                <div className="rounded-md ring-1 ring-white/10 divide-y divide-white/5 overflow-hidden" data-testid="modal-historico-lista">
                  {historico.map((h) => (
                    <div key={h.id} className="flex items-center justify-between px-3 py-2.5">
                      <div className="min-w-0">
                        <p className="font-mono text-sm text-foreground">{formatarData(h.data_pagamento)}</p>
                        <p className="text-xs text-muted-foreground uppercase">{(h.metodo_pagamento || '').toUpperCase()}</p>
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        <span className="font-mono text-sm font-semibold text-emerald-400">{formatarMoeda(h.valor_pago)}</span>
                        <button
                          type="button"
                          onClick={() => onRecibo && onRecibo(h.id)}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-foreground/80 hover:bg-white/5 hover:text-foreground transition-colors"
                          data-testid={`modal-recibo-${h.id}`}
                          title="Baixar recibo em PDF"
                        >
                          <Receipt className="w-3.5 h-3.5" strokeWidth={1.5} /> Recibo
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* DIREITA — ações */}
          <div className="md:col-span-5 bg-white/[0.02] px-7 sm:px-8 py-8">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground mb-5">Registrar pagamento</p>

            <form onSubmit={onSubmit} className="space-y-5">
              <div>
                <label className="flex items-center gap-1.5 text-sm font-medium text-foreground mb-2">
                  <Wallet className="w-4 h-4 text-muted-foreground" strokeWidth={1.5} /> Valor recebido (R$)
                </label>
                <input
                  type="number"
                  value={form.valor_pago}
                  onChange={(e) => setForm({ ...form, valor_pago: e.target.value })}
                  required
                  step="0.01"
                  min="0"
                  className="w-full px-3 py-2.5 bg-background rounded-md ring-1 ring-white/10 text-foreground text-lg font-mono font-semibold focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 transition-shadow"
                  data-testid="input-valor-pago"
                />
              </div>

              <div>
                <label className="flex items-center gap-1.5 text-sm font-medium text-foreground mb-2">
                  <Calendar className="w-4 h-4 text-muted-foreground" strokeWidth={1.5} /> Data do pagamento
                </label>
                <input
                  type="date"
                  value={form.data_pagamento}
                  onChange={(e) => setForm({ ...form, data_pagamento: e.target.value })}
                  required
                  max={hojeISO()}
                  className="w-full px-3 py-2.5 bg-background rounded-md ring-1 ring-white/10 text-foreground font-mono focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 transition-shadow"
                  data-testid="input-data-pagamento"
                />
              </div>

              <RestanteDoPagamento
                parcelaId={parcela?.id}
                valorPago={form.valor_pago}
                dataPagamento={form.data_pagamento}
                ignorar={form.quitar_ignorando_restante}
                onChangeIgnorar={(v) => setForm((f) => ({ ...f, quitar_ignorando_restante: v }))}
              />

              <div>
                <label className="text-sm font-medium text-foreground mb-2 block">Método</label>
                <div className="grid grid-cols-3 gap-2" data-testid="select-metodo-pagamento">
                  {METODOS.map((m) => (
                    <button
                      key={m.value}
                      type="button"
                      onClick={() => setForm({ ...form, metodo_pagamento: m.value })}
                      className={`px-2 py-2 rounded-md text-xs font-medium ring-1 transition-colors ${
                        form.metodo_pagamento === m.value
                          ? 'bg-emerald-500/15 ring-emerald-500/60 text-emerald-300'
                          : 'bg-background ring-white/10 text-muted-foreground hover:bg-white/5'
                      }`}
                      data-testid={`metodo-${m.value}`}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="flex items-center gap-1.5 text-sm font-medium text-foreground mb-2">
                  <StickyNote className="w-4 h-4 text-muted-foreground" strokeWidth={1.5} /> Observação
                </label>
                <textarea
                  value={form.observacoes}
                  onChange={(e) => setForm({ ...form, observacoes: e.target.value })}
                  rows="2"
                  className="w-full px-3 py-2 bg-background rounded-md ring-1 ring-white/10 text-foreground placeholder:text-muted-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 resize-none transition-shadow"
                  placeholder="Adicionar uma nota (opcional)…"
                  data-testid="textarea-observacoes"
                />
              </div>

              <Button
                type="submit"
                variant="primary"
                testId="confirmar-pagamento-button"
                className="w-full justify-center gap-2 !py-3 !rounded-md text-base"
              >
                Confirmar pagamento
                <ArrowRight className="w-4 h-4" strokeWidth={1.5} />
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
};

const Linha = ({ rotulo, valor, classe = 'text-foreground' }) => (
  <div className="flex items-center justify-between px-4 py-3 border-b border-white/5 last:border-b-0">
    <span className="text-sm text-muted-foreground">{rotulo}</span>
    <span className={`text-sm font-mono font-semibold ${classe}`}>{valor}</span>
  </div>
);

export default PagamentoDetalheModal;
