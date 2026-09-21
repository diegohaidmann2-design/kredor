import React, { useState, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Send, Check, Loader2, MessageSquareText, ShieldCheck,
  AlertTriangle, Phone, CheckCheck, FileText, Pencil
} from 'lucide-react';
import { whatsappAPI } from '../../api/api';

// Rótulos e cor por tipo de template (usados no seletor)
const TIPO_META = {
  cobranca:     { label: 'Cobrança',     cls: 'bg-emerald-500/12 text-emerald-500' },
  lembrete:     { label: 'Lembrete',     cls: 'bg-sky-500/12 text-sky-500' },
  atraso:       { label: 'Atraso',       cls: 'bg-red-500/12 text-red-500' },
  confirmacao:  { label: 'Confirmação',  cls: 'bg-teal-500/12 text-teal-500' },
  boas_vindas:  { label: 'Boas-vindas',  cls: 'bg-violet-500/12 text-violet-500' },
  custom:       { label: 'Personalizado',cls: 'bg-amber-500/12 text-amber-500' },
};

const OPCAO_PADRAO = {
  id: null,
  nome: 'Mensagem padrão do sistema',
  tipo: 'cobranca',
  descricao: 'Modelo automático ajustado ao tipo de empréstimo (com ou sem prazo).',
  _padrao: true,
};

function horaAgora() {
  return new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

const CobrancaModal = ({ isOpen, parcela, onClose, onConfirm, enviando = false }) => {
  const [templates, setTemplates] = useState([OPCAO_PADRAO]);
  const [carregandoTemplates, setCarregandoTemplates] = useState(false);
  const [selecionado, setSelecionado] = useState(null); // template_id ou null
  const [preview, setPreview] = useState(null);
  const [carregandoPreview, setCarregandoPreview] = useState(false);
  const [erroPreview, setErroPreview] = useState('');
  const previewReqRef = useRef(0);

  // Carrega templates ao abrir (o backend auto-semeia 6 modelos quando não há nenhum)
  useEffect(() => {
    if (!isOpen) return;
    setSelecionado(null);
    setPreview(null);
    setErroPreview('');
    let ativo = true;
    (async () => {
      setCarregandoTemplates(true);
      try {
        const resp = await whatsappAPI.listarTemplates('cobranca');
        const lista = Array.isArray(resp.data) ? resp.data : (resp.data?.templates || []);
        if (ativo) setTemplates([OPCAO_PADRAO, ...lista]);
      } catch {
        if (ativo) setTemplates([OPCAO_PADRAO]);
      } finally {
        if (ativo) setCarregandoTemplates(false);
      }
    })();
    return () => { ativo = false; };
  }, [isOpen]);

  // Renderiza a mensagem final sempre que a seleção muda
  const carregarPreview = useCallback(async (templateId) => {
    if (!parcela?.id) return;
    const reqId = ++previewReqRef.current;
    setCarregandoPreview(true);
    setErroPreview('');
    try {
      const resp = await whatsappAPI.previewCobrancaParcela(parcela.id, templateId);
      if (reqId === previewReqRef.current) setPreview(resp.data);
    } catch (e) {
      if (reqId === previewReqRef.current) {
        setErroPreview(e.response?.data?.detail || 'Não foi possível gerar a pré-visualização.');
        setPreview(null);
      }
    } finally {
      if (reqId === previewReqRef.current) setCarregandoPreview(false);
    }
  }, [parcela?.id]);

  useEffect(() => {
    if (isOpen && parcela?.id) carregarPreview(selecionado);
  }, [isOpen, parcela?.id, selecionado, carregarPreview]);

  // Fecha no ESC
  useEffect(() => {
    if (!isOpen) return;
    const h = (e) => { if (e.key === 'Escape' && !enviando) onClose(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [isOpen, enviando, onClose]);

  const telefone = preview?.telefone;
  const temTelefone = preview ? preview.tem_telefone : true;
  const clienteNome = preview?.cliente_nome || parcela?.cliente_nome || 'Cliente';

  if (typeof document === 'undefined') return null;

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm z-[120]"
            onClick={() => !enviando && onClose()}
          />
          <div className="fixed inset-0 z-[121] flex items-center justify-center p-3 sm:p-4 pointer-events-none">
            <motion.div
              initial={{ opacity: 0, y: 24, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 24, scale: 0.97 }}
              transition={{ type: 'spring', damping: 26, stiffness: 320 }}
              className="pointer-events-auto w-full max-w-3xl max-h-[92vh] flex flex-col rounded-2xl border border-border bg-card shadow-2xl overflow-hidden"
              data-testid="cobranca-modal"
              role="dialog"
              aria-modal="true"
            >
              {/* Cabeçalho */}
              <div className="relative flex items-start gap-3 p-5 border-b border-border/70 bg-gradient-to-br from-emerald-500/[0.07] to-transparent">
                <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-500">
                  <MessageSquareText className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <h2 className="font-display text-lg font-bold text-foreground leading-tight">
                    Enviar cobrança
                  </h2>
                  <p className="mt-0.5 text-sm text-muted-foreground truncate">
                    Para <span className="font-semibold text-foreground">{clienteNome}</span>
                    {parcela?.numero_parcela && (
                      <> · Parcela {parcela.numero_parcela}/{parcela.total_parcelas || '∞'}</>
                    )}
                  </p>
                </div>
                <button
                  onClick={() => !enviando && onClose()}
                  className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-40"
                  disabled={enviando}
                  data-testid="cobranca-modal-fechar"
                  aria-label="Fechar"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Corpo */}
              <div className="grid flex-1 grid-cols-1 gap-0 overflow-hidden md:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
                {/* Coluna: seleção de modelo */}
                <div className="flex flex-col overflow-hidden border-b border-border/70 md:border-b-0 md:border-r">
                  <div className="flex items-center gap-2 px-5 pt-4 pb-2">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Modelo da mensagem
                    </span>
                  </div>
                  <div className="flex-1 space-y-2 overflow-y-auto px-5 pb-5 max-h-[30vh] md:max-h-[46vh]">
                    {carregandoTemplates ? (
                      <div className="space-y-2">
                        {[0, 1, 2].map((i) => (
                          <div key={i} className="h-16 animate-pulse rounded-xl bg-muted/50" />
                        ))}
                      </div>
                    ) : (
                      templates.map((tpl, idx) => {
                        const ativo = selecionado === tpl.id;
                        const meta = TIPO_META[tpl.tipo] || TIPO_META.custom;
                        return (
                          <motion.button
                            key={tpl.id || 'padrao'}
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: Math.min(idx * 0.03, 0.2) }}
                            onClick={() => setSelecionado(tpl.id)}
                            className={`group flex w-full items-start gap-3 rounded-xl border p-3 text-left transition-all ${
                              ativo
                                ? 'border-emerald-500/70 bg-emerald-500/[0.08] shadow-sm'
                                : 'border-border bg-background hover:border-emerald-500/40 hover:bg-muted/40'
                            }`}
                            data-testid={`cobranca-template-${tpl.id || 'padrao'}`}
                          >
                            <span className={`mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full border-2 transition-colors ${
                              ativo ? 'border-emerald-500 bg-emerald-500' : 'border-muted-foreground/40'
                            }`}>
                              {ativo && <Check className="h-3 w-3 text-white" strokeWidth={3} />}
                            </span>
                            <span className="min-w-0 flex-1">
                              <span className="flex items-center gap-2">
                                <span className="truncate text-sm font-semibold text-foreground">{tpl.nome}</span>
                                {tpl._padrao ? (
                                  <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">Padrão</span>
                                ) : (
                                  <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${meta.cls}`}>{meta.label}</span>
                                )}
                              </span>
                              {tpl.descricao && (
                                <span className="mt-0.5 block truncate text-xs text-muted-foreground">{tpl.descricao}</span>
                              )}
                            </span>
                          </motion.button>
                        );
                      })
                    )}
                  </div>
                </div>

                {/* Coluna: pré-visualização estilo WhatsApp */}
                <div className="flex flex-col overflow-hidden">
                  <div className="flex items-center gap-2 px-5 pt-4 pb-2">
                    <Pencil className="h-4 w-4 text-muted-foreground" />
                    <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Pré-visualização
                    </span>
                  </div>
                  <div className="flex-1 overflow-y-auto px-5 pb-5 max-h-[34vh] md:max-h-[46vh]">
                    {/* Moldura de conversa */}
                    <div className="overflow-hidden rounded-2xl border border-border">
                      {/* Barra do contato */}
                      <div className="flex items-center gap-2.5 bg-[#075E54] px-3.5 py-2.5">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/20 text-sm font-bold text-white">
                          {clienteNome.charAt(0).toUpperCase()}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-sm font-semibold text-white">{clienteNome}</div>
                          <div className="flex items-center gap-1 text-[11px] text-white/70">
                            <Phone className="h-3 w-3" />
                            {telefone || 'Sem telefone'}
                          </div>
                        </div>
                      </div>
                      {/* Área de mensagens (papel de parede WhatsApp) */}
                      <div
                        className="min-h-[180px] space-y-2 p-3.5"
                        style={{ backgroundColor: '#0b141a', backgroundImage: 'radial-gradient(rgba(255,255,255,0.03) 1px, transparent 1px)', backgroundSize: '16px 16px' }}
                      >
                        {carregandoPreview ? (
                          <div className="flex h-full min-h-[160px] items-center justify-center">
                            <Loader2 className="h-6 w-6 animate-spin text-emerald-400" />
                          </div>
                        ) : erroPreview ? (
                          <div className="flex h-full min-h-[160px] items-center justify-center px-4 text-center text-sm text-red-400">
                            {erroPreview}
                          </div>
                        ) : (
                          <motion.div
                            key={selecionado || 'padrao'}
                            initial={{ opacity: 0, y: 6 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="ml-auto max-w-[85%] rounded-lg rounded-tr-sm bg-[#005c4b] px-3 py-2 shadow"
                          >
                            <p className="whitespace-pre-wrap break-words text-[13px] leading-relaxed text-[#e9edef]">
                              {preview?.mensagem}
                            </p>
                            <div className="mt-1 flex items-center justify-end gap-1 text-[10px] text-white/60">
                              {horaAgora()}
                              <CheckCheck className="h-3.5 w-3.5 text-sky-300" />
                            </div>
                          </motion.div>
                        )}
                      </div>
                    </div>

                    {!temTelefone && !carregandoPreview && (
                      <div className="mt-3 flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-500">
                        <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                        Este cliente não possui telefone cadastrado. Adicione um número para enviar a cobrança.
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Rodapé */}
              <div className="flex flex-col gap-3 border-t border-border/70 bg-muted/20 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <ShieldCheck className="h-4 w-4 text-emerald-500" />
                  Envio protegido por controle anti-spam.
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => !enviando && onClose()}
                    disabled={enviando}
                    className="rounded-xl px-4 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-40"
                    data-testid="cobranca-modal-cancelar"
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={() => onConfirm(selecionado)}
                    disabled={enviando || carregandoPreview || !temTelefone}
                    className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 transition-all hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-50"
                    data-testid="cobranca-modal-enviar"
                  >
                    {enviando ? (
                      <><Loader2 className="h-4 w-4 animate-spin" /> Enviando…</>
                    ) : (
                      <><Send className="h-4 w-4" /> Enviar cobrança</>
                    )}
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>,
    document.body
  );
};

export default CobrancaModal;
