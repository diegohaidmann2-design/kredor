import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, CalendarDays, Wallet, StickyNote, ArrowRight, Landmark } from 'lucide-react';
import Button from '../Button';
import RestanteDoPagamento from './RestanteDoPagamento';
import { formatarMoeda, formatarData, hojeISO } from '../../utils/formatters';

/**
 * Modal de detalhe da parcela no estilo Rocket Money (adaptado ao tema escuro Kredor).
 * Coluna esquerda: informações claras da parcela (valor em destaque).
 * Coluna direita: AÇÕES — foco em Registrar pagamento.
 */
const METODOS = [
  { value: 'pix', label: 'PIX' },
  { value: 'transferencia', label: 'Transferência' },
  { value: 'dinheiro', label: 'Dinheiro' },
  { value: 'cartao', label: 'Cartão' },
  { value: 'boleto', label: 'Boleto' },
];

const PagamentoDetalheModal = ({ parcela, form, setForm, onSubmit, onClose }) => {
  // Fecha com ESC e trava o scroll do fundo enquanto aberto
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

  const statusInfo = {
    atrasado: { label: 'Atrasado', cls: 'bg-red-500/15 text-red-400 ring-red-500/30' },
    parcial: { label: 'Pagamento parcial', cls: 'bg-amber-500/15 text-amber-400 ring-amber-500/30' },
    pendente: { label: 'Pendente', cls: 'bg-muted text-muted-foreground ring-border' },
  }[parcela.status] || { label: 'Pendente', cls: 'bg-muted text-muted-foreground ring-border' };

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150"
      data-testid="pagamento-modal"
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      {/* Botão fechar — círculo escuro, como no Rocket Money */}
      <button
        onClick={onClose}
        className="absolute top-5 right-5 sm:top-7 sm:right-7 z-[10001] h-11 w-11 rounded-full bg-neutral-900/90 text-white flex items-center justify-center hover:bg-neutral-800 transition-colors shadow-lg"
        data-testid="cancelar-button"
        aria-label="Fechar"
      >
        <X className="w-5 h-5" />
      </button>

      <div
        className="relative w-full max-w-3xl bg-card rounded-3xl border border-border shadow-2xl overflow-hidden"
        style={{ zIndex: 10000 }}
      >
        {/* Topbar: pill de data de vencimento */}
        <div className="flex items-center justify-between px-6 sm:px-8 pt-6">
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-3.5 py-1.5 text-sm font-medium text-foreground">
            <CalendarDays className="w-4 h-4 text-muted-foreground" />
            Vence {formatarData(parcela.data_vencimento)}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-0">
          {/* ESQUERDA — informações claras */}
          <div className="md:col-span-3 px-6 sm:px-8 py-6 space-y-5">
            <div>
              <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${statusInfo.cls}`}>
                {statusInfo.label}
                {parcela.dias_atraso > 0 && ` · ${parcela.dias_atraso}d`}
              </span>
              <h2 className="mt-3 text-xl font-semibold text-foreground truncate" data-testid="detalhe-cliente-nome">
                {parcela.cliente_nome || 'Cliente'}
              </h2>
              {parcela.cliente_telefone && (
                <p className="text-sm text-muted-foreground">{parcela.cliente_telefone}</p>
              )}
            </div>

            {/* Valor em destaque */}
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Total a receber</p>
              <p className="text-4xl sm:text-5xl font-bold text-foreground leading-none tracking-tight" data-testid="detalhe-valor-devido">
                {formatarMoeda(valorDevido)}
              </p>
            </div>

            {/* Composição do valor */}
            <div className="rounded-2xl border border-border bg-background/60 divide-y divide-border">
              <Linha rotulo="Valor da parcela" valor={formatarMoeda(parcela.valor_total)} />
              {parcela.valor_pago > 0 && (
                <Linha rotulo="Já pago" valor={`- ${formatarMoeda(parcela.valor_pago)}`} classe="text-emerald-400" />
              )}
              {temMulta && <Linha rotulo="Multa" valor={`+ ${formatarMoeda(parcela.valor_multa)}`} classe="text-red-400" />}
              {temMora && <Linha rotulo="Juros de mora" valor={`+ ${formatarMoeda(parcela.valor_juros_mora)}`} classe="text-orange-400" />}
            </div>

            {/* Rodapé estilo "statement" */}
            <div className="pt-2 text-center md:text-left">
              <p className="font-mono text-[11px] tracking-wide text-muted-foreground uppercase flex items-center justify-center md:justify-start gap-1.5">
                <Landmark className="w-3.5 h-3.5" />
                Empréstimo #{ref} · Parcela {parcela.numero_parcela}/{totalParc}
              </p>
            </div>
          </div>

          {/* DIREITA — AÇÕES */}
          <div className="md:col-span-2 bg-background/40 border-t md:border-t-0 md:border-l border-border px-6 sm:px-7 py-6">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">Registrar pagamento</p>

            <form onSubmit={onSubmit} className="space-y-4">
              <div>
                <label className="flex items-center gap-1.5 text-sm font-medium text-foreground mb-1.5">
                  <Wallet className="w-4 h-4 text-muted-foreground" /> Valor recebido (R$)
                </label>
                <input
                  type="number"
                  value={form.valor_pago}
                  onChange={(e) => setForm({ ...form, valor_pago: e.target.value })}
                  required
                  step="0.01"
                  min="0"
                  className="w-full px-3 py-2.5 bg-background border border-border rounded-xl text-foreground text-lg font-semibold focus:outline-none focus:ring-2 focus:ring-primary"
                  data-testid="input-valor-pago"
                />
              </div>

              <div>
                <label className="flex items-center gap-1.5 text-sm font-medium text-foreground mb-1.5">
                  <CalendarDays className="w-4 h-4 text-muted-foreground" /> Data do pagamento
                </label>
                <input
                  type="date"
                  value={form.data_pagamento}
                  onChange={(e) => setForm({ ...form, data_pagamento: e.target.value })}
                  required
                  max={hojeISO()}
                  className="w-full px-3 py-2.5 bg-background border border-border rounded-xl text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
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
                <label className="text-sm font-medium text-foreground mb-1.5 block">Método</label>
                <div className="grid grid-cols-3 gap-2" data-testid="select-metodo-pagamento">
                  {METODOS.map((m) => (
                    <button
                      key={m.value}
                      type="button"
                      onClick={() => setForm({ ...form, metodo_pagamento: m.value })}
                      className={`px-2 py-2 rounded-xl text-xs font-medium border transition-colors ${
                        form.metodo_pagamento === m.value
                          ? 'bg-primary/15 border-primary text-primary'
                          : 'bg-background border-border text-muted-foreground hover:bg-muted'
                      }`}
                      data-testid={`metodo-${m.value}`}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="flex items-center gap-1.5 text-sm font-medium text-foreground mb-1.5">
                  <StickyNote className="w-4 h-4 text-muted-foreground" /> Observação
                </label>
                <textarea
                  value={form.observacoes}
                  onChange={(e) => setForm({ ...form, observacoes: e.target.value })}
                  rows="2"
                  className="w-full px-3 py-2 bg-background border border-border rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                  placeholder="Adicionar uma nota (opcional)…"
                  data-testid="textarea-observacoes"
                />
              </div>

              <Button
                type="submit"
                variant="primary"
                testId="confirmar-pagamento-button"
                className="w-full justify-center gap-2 !py-3 !rounded-xl text-base"
              >
                Confirmar pagamento
                <ArrowRight className="w-4 h-4" />
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
  <div className="flex items-center justify-between px-4 py-2.5">
    <span className="text-sm text-muted-foreground">{rotulo}</span>
    <span className={`text-sm font-semibold ${classe}`}>{valor}</span>
  </div>
);

export default PagamentoDetalheModal;
