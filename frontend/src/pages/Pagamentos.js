import React, { useState, useEffect, useCallback, useMemo } from 'react';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import ErrorMessage from '../components/ErrorMessage';
import Button from '../components/Button';
import { useModal } from '../components/Modal';
import { pagamentosAPI, parcelasAPI, whatsappAPI } from '../api/api';
import { formatarMoeda, formatarData, formatarDataHora, hojeISO } from '../utils/formatters';
import { isToday } from '../utils/timezone';
import { DatePickerBR } from '../components/ui/date-picker-br';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  DollarSign, MessageCircle, Trash2, MoreVertical, Download, RotateCcw, CheckSquare, Square,
  ChevronRight, ChevronDown, ChevronUp, Layers, Repeat, X, Search, Inbox, Calendar,
  ArrowDownRight, ArrowUpRight, Percent, Users, Receipt, RefreshCw, Send, CheckCircle2, Wallet,
} from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../components/ui/dropdown-menu';
import { toast } from '../hooks/use-toast';
import AnimatedNumber from '../components/AnimatedNumber';
import CobrancaModal from '../components/pagamentos/CobrancaModal';
import PagamentoDetalheModal from '../components/pagamentos/PagamentoDetalheModal';

const ICON = 1.5; // stroke-width padrão (lucide)

// Dias até o vencimento (negativo = atrasada)
const diasAteVencimento = (dataVencimento) => {
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);
  const venc = new Date(dataVencimento);
  venc.setHours(0, 0, 0, 0);
  return Math.round((venc - hoje) / (1000 * 60 * 60 * 24));
};

const statusMeta = (s) => ({
  atrasado: { label: 'Atrasado', dot: 'bg-red-500', text: 'text-red-400' },
  parcial: { label: 'Parcial', dot: 'bg-violet-500', text: 'text-violet-300' },
  pendente: { label: 'Pendente', dot: 'bg-slate-400', text: 'text-slate-300' },
}[s] || { label: 'Pendente', dot: 'bg-slate-400', text: 'text-slate-300' });

// Status de entrega (WhatsApp) em texto amigável
const formatarStatusEntrega = (status) => {
  switch ((status || '').toUpperCase()) {
    case 'READ':
    case 'PLAYED':
      return 'lida';
    case 'DELIVERY_ACK':
      return 'entregue no aparelho';
    case 'SERVER_ACK':
      return 'recebida pelo servidor';
    case 'PENDING':
    case '':
      return 'enviada (aguardando confirmação)';
    default:
      return `enviada (${status})`;
  }
};

const formatarEtaFila = (data) => {
  const prox = data?.proximo_disponivel;
  if (prox) {
    const alvo = new Date(prox);
    const diffMs = alvo.getTime() - Date.now();
    const min = Math.max(1, Math.ceil(diffMs / 60000));
    const hora = alvo.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    return `em ~${min} min (por volta de ${hora})`;
  }
  const delay = data?.delay_recomendado;
  if (delay && delay > 0) {
    if (delay >= 60) return `em ~${Math.ceil(delay / 60)} min`;
    return `em ~${Math.round(delay)}s`;
  }
  return 'nos próximos minutos (a fila processa a cada ~2 min)';
};

// ---------- Linha de parcela: lista plana, alinhada, sem badge soup ----------
const ParcelaRow = ({ parcela, handleRegistrarPagamento, handleEnviarWhatsApp, handleExcluirParcela, formatarData, formatarMoeda, selecionavel, selecionada, onToggleSelecionar }) => {
  const valorDevido = parcela.valor_total - parcela.valor_pago + (parcela.valor_multa || 0) + (parcela.valor_juros_mora || 0);
  const temJurosOuMulta = (parcela.valor_multa || 0) > 0 || (parcela.valor_juros_mora || 0) > 0;
  const diasParaVencer = parcela.status !== 'atrasado' ? diasAteVencimento(parcela.data_vencimento) : null;
  const st = statusMeta(parcela.status);

  let ultimaCobrancaTxt = null;
  if (parcela.ultima_cobranca_em) {
    const diff = Math.floor((Date.now() - new Date(parcela.ultima_cobranca_em).getTime()) / (1000 * 60 * 60 * 24));
    ultimaCobrancaTxt = diff <= 0 ? 'Cobrado hoje' : `Cobrado há ${diff}d`;
  }

  return (
    <div
      className="group flex flex-col gap-1 py-3 pl-1 pr-1 border-b border-border last:border-b-0 hover:bg-muted/40 transition-colors cursor-pointer"
      role="button"
      tabIndex={0}
      onClick={() => handleRegistrarPagamento(parcela)}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleRegistrarPagamento(parcela); } }}
      data-testid={`parcela-row-${parcela.id}`}
    >
      <div className="flex items-center gap-3">
        {selecionavel && (
          <button
            onClick={(e) => { e.stopPropagation(); onToggleSelecionar(parcela.id); }}
            className="p-1 rounded-md hover:bg-muted transition-colors shrink-0 focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:outline-none"
            data-testid={`checkbox-parcela-${parcela.id}`}
            aria-label={selecionada ? 'Desselecionar parcela' : 'Selecionar parcela'}
          >
            {selecionada
              ? <CheckSquare className="w-[18px] h-[18px] text-emerald-400" strokeWidth={ICON} />
              : <Square className="w-[18px] h-[18px] text-muted-foreground" strokeWidth={ICON} />}
          </button>
        )}

        <span className="font-mono text-sm text-foreground w-11 shrink-0">{parcela.numero_parcela}/{parcela.total_parcelas || '∞'}</span>
        <span className="font-mono text-xs text-muted-foreground w-24 shrink-0 hidden sm:block">{formatarData(parcela.data_vencimento)}</span>

        <div className="flex items-center gap-2 min-w-0 flex-1">
          <span className={`h-2 w-2 rounded-full shrink-0 ${st.dot}`} />
          <span className={`text-sm font-medium ${st.text}`}>{st.label}</span>
          {parcela.dias_atraso > 0 && (
            <span className="text-xs text-red-400/80 font-mono whitespace-nowrap">{parcela.dias_atraso}d</span>
          )}
          {diasParaVencer !== null && diasParaVencer <= 7 && (
            <span
              className={`text-xs font-medium whitespace-nowrap ${
                diasParaVencer <= 0 ? 'text-orange-400' : diasParaVencer <= 2 ? 'text-amber-400' : 'text-yellow-500/80'
              }`}
              data-testid={`badge-urgencia-${parcela.id}`}
            >
              {diasParaVencer <= 0 ? 'vence hoje' : diasParaVencer === 1 ? 'vence amanhã' : `vence em ${diasParaVencer}d`}
            </span>
          )}
        </div>

        <span className="font-mono text-sm font-semibold text-foreground text-right w-24 sm:w-28 shrink-0">{formatarMoeda(valorDevido)}</span>

        <div className="flex items-center gap-0.5 shrink-0">
          <button
            onClick={(e) => { e.stopPropagation(); handleRegistrarPagamento(parcela); }}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-emerald-300 hover:bg-emerald-500/10 transition-colors focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:outline-none"
            data-testid={`btn-pagar-inline-${parcela.id}`}
            title="Registrar pagamento"
          >
            <Wallet className="w-4 h-4" strokeWidth={ICON} />
            <span className="hidden md:inline">Pagar</span>
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); handleEnviarWhatsApp(parcela); }}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-foreground/70 hover:bg-muted hover:text-foreground transition-colors focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:outline-none"
            data-testid={`btn-cobrar-inline-${parcela.id}`}
            title="Enviar cobrança via WhatsApp"
          >
            <MessageCircle className="w-4 h-4" strokeWidth={ICON} />
            <span className="hidden md:inline">Cobrar</span>
          </button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                onClick={(e) => e.stopPropagation()}
                className="p-1.5 rounded-md hover:bg-muted transition-colors flex items-center justify-center focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:outline-none"
                data-testid={`menu-acoes-${parcela.id}`}
                aria-label="Mais ações da parcela"
              >
                <MoreVertical className="w-4 h-4 text-muted-foreground" strokeWidth={ICON} />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52" onClick={(e) => e.stopPropagation()}>
              <DropdownMenuItem
                onSelect={() => setTimeout(() => handleExcluirParcela(parcela), 50)}
                className="flex items-center gap-3 px-4 py-3 text-sm text-red-400 focus:text-red-400 focus:bg-red-500/10 cursor-pointer"
                data-testid={`excluir-parcela-${parcela.id}`}
              >
                <Trash2 className="w-4 h-4" strokeWidth={ICON} />
                <span>Excluir parcela</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {(temJurosOuMulta || ultimaCobrancaTxt) && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 pl-[3.4rem] text-xs text-muted-foreground font-mono">
          {(parcela.valor_multa || 0) > 0 && (
            <span>Multa <span className="text-red-400">{formatarMoeda(parcela.valor_multa)}</span></span>
          )}
          {(parcela.valor_juros_mora || 0) > 0 && (
            <span>Mora <span className="text-orange-400">{formatarMoeda(parcela.valor_juros_mora)}</span></span>
          )}
          {temJurosOuMulta && (
            <span>Original <span className="text-foreground/70">{formatarMoeda(parcela.valor_total)}</span></span>
          )}
          {ultimaCobrancaTxt && (
            <span className="inline-flex items-center gap-1 text-emerald-400/80">
              <MessageCircle className="w-3 h-3" strokeWidth={ICON} /> {ultimaCobrancaTxt}
            </span>
          )}
        </div>
      )}
    </div>
  );
};

// ---------- KPI ----------
const KpiCard = ({ label, amount, format = (n) => n, hint, Icon, tone = 'default', highlight = false, testId, delay = 0, delta }) => {
  const toneText = {
    default: 'text-foreground',
    green: 'text-emerald-400',
    red: 'text-red-400',
  }[tone];
  return (
    <div
      className={`relative rounded-xl bg-card p-6 ring-1 transition-all duration-200 hover:-translate-y-px animate-slide-up ${
        highlight ? 'ring-emerald-500/30 bg-gradient-to-br from-emerald-500/[0.06] to-transparent' : 'ring-border hover:ring-foreground/20'
      }`}
      style={{ animationDelay: `${delay}ms` }}
      data-testid={testId}
    >
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">{label}</p>
        <Icon className={`w-4 h-4 ${highlight ? 'text-emerald-400' : 'text-muted-foreground'}`} strokeWidth={ICON} />
      </div>
      <AnimatedNumber value={amount} format={format} className={`font-mono text-2xl sm:text-[1.7rem] font-semibold tracking-tight ${toneText}`} />
      <div className="mt-1.5 flex items-center gap-2 flex-wrap">
        {delta && (
          <span
            className={`inline-flex items-center gap-0.5 text-xs font-medium ${delta.pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}
            data-testid={`${testId}-delta`}
          >
            {delta.pct >= 0 ? <ArrowUpRight className="w-3.5 h-3.5" strokeWidth={ICON} /> : <ArrowDownRight className="w-3.5 h-3.5" strokeWidth={ICON} />}
            {Math.abs(delta.pct).toFixed(1)}% <span className="text-muted-foreground font-normal">{delta.label}</span>
          </span>
        )}
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </div>
    </div>
  );
};

const Pagamentos = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isMember = !!user?.owner_id;

  const [pagamentos, setPagamentos] = useState([]);
  const [parcelasPendentes, setParcelasPendentes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filtroMetodo, setFiltroMetodo] = useState('');
  const [filtroData, setFiltroData] = useState(null);
  const [filtroClienteHistorico, setFiltroClienteHistorico] = useState('');
  const [filtroStatus, setFiltroStatus] = useState('todos');
  const [filtroCliente, setFiltroCliente] = useState('');
  const [filtroOrdenacao, setFiltroOrdenacao] = useState('vencimento');
  const [showModal, setShowModal] = useState(false);
  const [parcelaSelecionada, setParcelaSelecionada] = useState(null);
  const [cobrancaModal, setCobrancaModal] = useState({ open: false, parcela: null });
  const [activeTab, setActiveTab] = useState('pendentes');
  const [enviandoWhatsApp, setEnviandoWhatsApp] = useState(false);
  const [expandedClientes, setExpandedClientes] = useState(new Set());
  const [collapsedEmprestimos, setCollapsedEmprestimos] = useState(new Set());
  const [parcelasSelecionadas, setParcelasSelecionadas] = useState(new Set());
  const [confirmacoes, setConfirmacoes] = useState([]);
  const [cobrandoEmMassa, setCobrandoEmMassa] = useState(false);
  const modal = useModal();

  useEffect(() => {
    const url = new URLSearchParams(window.location.search);
    const filtroQS = url.get('filtro');
    const clienteQS = url.get('cliente');
    if (filtroQS) {
      setActiveTab('pendentes');
      setFiltroStatus(filtroQS);
    }
    if (clienteQS) {
      setActiveTab('pendentes');
      setFiltroCliente(clienteQS);
    }
  }, []);

  const [formPagamento, setFormPagamento] = useState({
    valor_pago: '',
    data_pagamento: hojeISO(),
    metodo_pagamento: 'pix',
    observacoes: '',
    quitar_ignorando_restante: false,
  });

  const carregarDados = useCallback(async ({ silencioso = false } = {}) => {
    try {
      if (!silencioso) setLoading(true);
      setError('');
      const [pagamentosRes, parcelasRes] = await Promise.all([
        pagamentosAPI.listar(),
        parcelasAPI.listarPendentes(),
      ]);
      setPagamentos(pagamentosRes.data);
      setParcelasPendentes(parcelasRes.data);
    } catch (err) {
      console.error('Erro ao carregar dados:', err);
      setError('Não foi possível carregar os dados.');
    } finally {
      if (!silencioso) setLoading(false);
    }
  }, []);

  useEffect(() => { carregarDados(); }, [carregarDados]);

  const handleRegistrarPagamento = (parcela) => {
    setParcelaSelecionada(parcela);
    const valorDevido = parcela.valor_total - parcela.valor_pago + (parcela.valor_multa || 0) + (parcela.valor_juros_mora || 0);
    setFormPagamento({
      valor_pago: valorDevido.toFixed(2),
      data_pagamento: hojeISO(),
      metodo_pagamento: 'pix',
      observacoes: '',
      quitar_ignorando_restante: false,
    });
    setShowModal(true);
  };

  const toggleClienteExpanded = (clienteId) => {
    setExpandedClientes((prev) => {
      const next = new Set(prev);
      next.has(clienteId) ? next.delete(clienteId) : next.add(clienteId);
      return next;
    });
  };

  const toggleEmprestimoCollapsed = (empKey) => {
    setCollapsedEmprestimos((prev) => {
      const next = new Set(prev);
      next.has(empKey) ? next.delete(empKey) : next.add(empKey);
      return next;
    });
  };

  const handleCobrarEmprestimo = async (emprestimo, empIdx) => {
    const ids = (emprestimo.parcelas || []).map((p) => p.id);
    if (ids.length === 0) return;
    const confirmado = await modal.confirm(
      `Cobrar Empréstimo ${empIdx + 1} via WhatsApp`,
      `Enviar cobrança para ${ids.length} parcela(s) em aberto deste empréstimo?`,
      'As mensagens serão enviadas em fila respeitando anti-spam.'
    );
    if (!confirmado) return;
    setCobrandoEmMassa(true);
    try {
      const { data } = await parcelasAPI.cobrarEmMassa(ids);
      modal.success('Cobranças disparadas', `${data.enviadas} enviada(s) com sucesso${data.falhas > 0 ? ` • ${data.falhas} falha(s)` : ''}.`);
      carregarDados({ silencioso: true });
    } catch (err) {
      modal.error('Erro ao cobrar empréstimo', err.response?.data?.detail || 'Falha ao processar cobrança.');
    } finally {
      setCobrandoEmMassa(false);
    }
  };

  const handleSubmitPagamento = async (e) => {
    e.preventDefault();
    try {
      const data = {
        parcela_id: parcelaSelecionada.id,
        valor_pago: parseFloat(formPagamento.valor_pago),
        data_pagamento: formPagamento.data_pagamento,
        metodo_pagamento: formPagamento.metodo_pagamento,
        observacoes: formPagamento.observacoes || null,
        quitar_ignorando_restante: formPagamento.quitar_ignorando_restante,
      };
      const parcela = parcelaSelecionada;
      const { data: registrado } = await pagamentosAPI.criar(data);
      setShowModal(false);
      setParcelaSelecionada(null);
      setConfirmacoes((prev) => [{
        id: registrado.id,
        cliente: parcela.cliente_nome || 'Cliente',
        emprestimoRef: (parcela.emprestimo_id || '').slice(-6).toUpperCase(),
        numero: parcela.numero_parcela,
        valorPago: registrado.valor_pago,
        restante: registrado.saldo_parcela_restante,
        quitou: registrado.status_parcela_apos === 'pago',
        perdoado: registrado.valor_perdoado || 0,
      }, ...prev.filter((c) => c.id !== registrado.id)].slice(0, 6));
      toast({
        title: registrado.status_parcela_apos === 'pago' ? 'Parcela quitada' : 'Pagamento parcial registrado',
        description: `${formatarMoeda(registrado.valor_pago)} de ${parcela.cliente_nome || 'cliente'}.`,
      });
      carregarDados({ silencioso: true });
    } catch (err) {
      modal.error('Erro no Pagamento', err.response?.data?.detail || 'Não foi possível registrar o pagamento. Tente novamente.');
    }
  };

  const baixarReciboConfirmacao = async (pagamentoId) => {
    try {
      const { data } = await pagamentosAPI.recibo(pagamentoId);
      const url = window.URL.createObjectURL(new Blob([data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `recibo_${pagamentoId.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Erro ao baixar recibo:', err);
      modal.error('Erro no Recibo', 'Não foi possível gerar o recibo agora. Tente pelo histórico de pagamentos.');
    }
  };

  const handleEnviarWhatsApp = (parcela) => setCobrancaModal({ open: true, parcela });

  const fecharCobrancaModal = () => {
    if (enviandoWhatsApp) return;
    setCobrancaModal({ open: false, parcela: null });
  };

  const executarEnvioCobranca = async (templateId = null) => {
    const parcela = cobrancaModal.parcela;
    if (!parcela) return;
    setEnviandoWhatsApp(true);
    try {
      const response = await whatsappAPI.enviarCobrancaParcela(parcela.id, false, templateId);
      if (response.data?.success === false) {
        await whatsappAPI.enviarCobrancaParcela(parcela.id, true, templateId);
        setEnviandoWhatsApp(false);
        setCobrancaModal({ open: false, parcela: null });
        modal.success('Mensagem na fila', `Limite anti-spam atingido. A cobrança de ${parcela.cliente_nome} será enviada ${formatarEtaFila(response.data)}.`);
        carregarDados({ silencioso: true });
        return;
      }
      setEnviandoWhatsApp(false);
      setCobrancaModal({ open: false, parcela: null });
      modal.success('Mensagem enviada', `WhatsApp para ${parcela.cliente_nome}: ${formatarStatusEntrega(response.data?.status_envio)}.`);
      carregarDados({ silencioso: true });
    } catch (err) {
      setEnviandoWhatsApp(false);
      setCobrancaModal({ open: false, parcela: null });
      const errorStatus = err.response?.status;
      const errorMessage = err.response?.data?.detail || err.message || 'Erro ao enviar mensagem';
      if (errorStatus === 503) {
        if (errorMessage.includes('número não sincronizado')) {
          modal.error('WhatsApp com problema', 'WhatsApp está conectado mas o número não foi sincronizado. Reconecte em Configurações > WhatsApp.');
        } else if (errorMessage.includes('desconectado')) {
          modal.error('WhatsApp desconectado', 'Seu WhatsApp foi desconectado. Reconecte em Configurações > WhatsApp.');
        } else {
          modal.error('WhatsApp não configurado', 'Você precisa conectar seu WhatsApp primeiro. Acesse Configurações > WhatsApp.');
        }
      } else if (errorStatus === 400) {
        modal.error('Dados inválidos', errorMessage);
      } else {
        modal.error('Erro ao enviar', errorMessage);
      }
    }
  };

  const handleExcluirParcela = async (parcela) => {
    const confirmar = await modal.confirm(
      'Excluir Parcela?',
      `Deseja realmente excluir a parcela ${parcela.numero_parcela}/${parcela.total_parcelas || '?'}?`,
      'Esta ação não pode ser desfeita.'
    );
    if (confirmar) {
      try {
        await parcelasAPI.excluir(parcela.id);
        modal.success('Parcela excluída', 'A parcela foi excluída com sucesso.');
        carregarDados({ silencioso: true });
      } catch (err) {
        modal.error('Erro ao excluir', err.response?.data?.detail || 'Não foi possível excluir a parcela.');
      }
    }
  };

  const handleEnviarConfirmacaoPagamento = async (pagamento) => {
    setEnviandoWhatsApp(true);
    try {
      const response = await whatsappAPI.enviarConfirmacaoPagamento(pagamento.id);
      setEnviandoWhatsApp(false);
      const modo = response.data?.modo;
      if (modo === 'fila') {
        modal.success('Confirmação na fila', `Confirmação de pagamento para ${pagamento.cliente_nome || 'o cliente'} será enviada em instantes.`);
      } else {
        modal.success('Confirmação enviada', `Confirmação de pagamento enviada com sucesso para ${pagamento.cliente_nome || 'o cliente'}.`);
      }
    } catch (err) {
      setEnviandoWhatsApp(false);
      const errorMessage = err.response?.data?.detail || err.message || 'Erro ao enviar confirmação';
      if (errorMessage.includes('WhatsApp não está conectado') || errorMessage.includes('Nenhuma conexão WhatsApp ativa')) {
        modal.error('WhatsApp não conectado', 'Você precisa conectar seu WhatsApp primeiro. Acesse Config. > WhatsApp.');
      } else {
        modal.error('Erro ao enviar confirmação', errorMessage);
      }
    }
  };

  const toggleSelecionarParcela = (parcelaId) => {
    setParcelasSelecionadas((prev) => {
      const next = new Set(prev);
      next.has(parcelaId) ? next.delete(parcelaId) : next.add(parcelaId);
      return next;
    });
  };

  const toggleSelecionarTodas = () => {
    setParcelasSelecionadas((prev) => {
      if (prev.size === parcelasOrdenadas.length) return new Set();
      return new Set(parcelasOrdenadas.map((p) => p.id));
    });
  };

  const handleCobrarEmMassa = async () => {
    const ids = Array.from(parcelasSelecionadas);
    if (ids.length === 0) {
      modal.error('Nenhuma parcela selecionada', 'Selecione ao menos 1 parcela para cobrar.');
      return;
    }
    const confirmado = await modal.confirm(
      'Cobrar em Massa via WhatsApp',
      `Enviar mensagem de cobrança para ${ids.length} parcela(s)?`,
      'As mensagens serão enviadas em fila respeitando anti-spam.'
    );
    if (!confirmado) return;
    setCobrandoEmMassa(true);
    try {
      const { data } = await parcelasAPI.cobrarEmMassa(ids);
      setParcelasSelecionadas(new Set());
      modal.success('Cobranças disparadas', `${data.enviadas} enviada(s) com sucesso${data.falhas > 0 ? ` • ${data.falhas} falha(s)` : ''}.`);
      carregarDados({ silencioso: true });
    } catch (err) {
      modal.error('Erro na cobrança em massa', err.response?.data?.detail || 'Falha ao processar lote.');
    } finally {
      setCobrandoEmMassa(false);
    }
  };

  const handleEstornarPagamento = async (pagamento) => {
    const confirmado = await modal.confirm(
      'Estornar Pagamento?',
      `Deseja estornar o pagamento de ${formatarMoeda(pagamento.valor_pago)} de ${pagamento.cliente_nome || 'cliente'}?`,
      'A parcela voltará para o status anterior. Esta ação será registrada no histórico de auditoria.'
    );
    if (!confirmado) return;
    try {
      await pagamentosAPI.estornar(pagamento.id);
      modal.success('Pagamento estornado', 'O valor foi revertido e a parcela ficou pendente novamente.');
      carregarDados({ silencioso: true });
    } catch (err) {
      modal.error('Erro ao estornar', err.response?.data?.detail || 'Não foi possível estornar.');
    }
  };

  const handleExportarHistorico = () => {
    if (pagamentosFiltrados.length === 0) {
      modal.error('Nada para exportar', 'Não há pagamentos para exportar com os filtros atuais.');
      return;
    }
    const header = ['Data', 'Cliente', 'Telefone', 'Parcela', 'Valor Pago', 'Método', 'Tipo', 'Observações'];
    const rows = pagamentosFiltrados.map((p) => [
      formatarDataHora(p.data_pagamento),
      p.cliente_nome || '',
      p.cliente_telefone || '',
      `${p.numero_parcela || '-'}/${p.total_parcelas || '-'}`,
      (p.valor_pago || 0).toFixed(2).replace('.', ','),
      (p.metodo_pagamento || '').toUpperCase(),
      p.tipo === 'amortizacao' ? 'Amortização' : 'Pagamento',
      (p.observacoes || '').replace(/[\r\n,;]/g, ' '),
    ]);
    const csv = [header, ...rows].map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(';')).join('\n');
    const bom = '\uFEFF';
    const blob = new Blob([bom + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `historico_pagamentos_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const pagamentosFiltrados = pagamentos.filter((pag) => {
    if (filtroMetodo && pag.metodo_pagamento !== filtroMetodo) return false;
    if (filtroClienteHistorico) {
      const busca = filtroClienteHistorico.toLowerCase();
      if (!pag.cliente_nome?.toLowerCase().includes(busca)) return false;
    }
    if (filtroData) {
      const dataPag = new Date(pag.data_pagamento);
      if (dataPag.toDateString() !== filtroData.toDateString()) return false;
    }
    return true;
  });

  const totalPagamentos = pagamentosFiltrados.reduce((sum, pag) => sum + pag.valor_pago, 0);
  const totalPendente = parcelasPendentes.reduce(
    (sum, p) => sum + (p.valor_total - p.valor_pago + (p.valor_multa || 0) + (p.valor_juros_mora || 0)), 0
  );
  const parcelasAtrasadas = parcelasPendentes.filter((p) => p.status === 'atrasado');
  const totalAtrasado = parcelasAtrasadas.reduce(
    (sum, p) => sum + (p.valor_total - p.valor_pago + (p.valor_multa || 0) + (p.valor_juros_mora || 0)), 0
  );
  const parcelasVencemHoje = parcelasPendentes.filter((p) => isToday(p.data_vencimento));

  const parcelasFiltradas = parcelasPendentes.filter((parcela) => {
    if (filtroStatus === 'vence_hoje') {
      if (!isToday(parcela.data_vencimento)) return false;
    } else if (filtroStatus !== 'todos' && parcela.status !== filtroStatus) {
      return false;
    }
    if (filtroCliente) {
      const busca = filtroCliente.toLowerCase();
      const nomeMatch = parcela.cliente_nome?.toLowerCase().includes(busca);
      const telefoneMatch = parcela.cliente_telefone?.includes(filtroCliente);
      if (!nomeMatch && !telefoneMatch) return false;
    }
    return true;
  });

  const parcelasOrdenadas = [...parcelasFiltradas].sort((a, b) => {
    switch (filtroOrdenacao) {
      case 'vencimento': return new Date(a.data_vencimento) - new Date(b.data_vencimento);
      case 'valor': return (b.valor_total - b.valor_pago) - (a.valor_total - a.valor_pago);
      case 'cliente': return (a.cliente_nome || '').localeCompare(b.cliente_nome || '');
      case 'dias_atraso': return (b.dias_atraso || 0) - (a.dias_atraso || 0);
      default: return 0;
    }
  });

  const clientesComParcelas = useMemo(() => {
    const gruposCliente = parcelasOrdenadas.reduce((acc, parcela) => {
      const cid = parcela.cliente_id;
      if (!acc[cid]) {
        acc[cid] = {
          cliente_id: cid,
          cliente_nome: parcela.cliente_nome,
          cliente_telefone: parcela.cliente_telefone,
          emprestimos: {},
          total_devido: 0,
          total_parcelas: 0,
          parcelas_atrasadas: 0,
          vencimento_mais_urgente: null,
          max_dias_atraso: 0,
        };
      }
      const eid = parcela.emprestimo_id;
      if (!acc[cid].emprestimos[eid]) {
        acc[cid].emprestimos[eid] = {
          emprestimo_id: eid,
          valor_emprestimo: parcela.valor_emprestimo,
          sem_prazo: parcela.emprestimo_sem_prazo,
          periodicidade: parcela.emprestimo_periodicidade,
          data_inicio: parcela.emprestimo_data_inicio,
          taxa_semanal: parcela.emprestimo_taxa_semanal,
          taxa_mensal: parcela.emprestimo_taxa_mensal,
          parcelas: [],
          total_devido_emp: 0,
          parcelas_atrasadas_emp: 0,
        };
      }
      acc[cid].emprestimos[eid].parcelas.push(parcela);
      const valorDevido = parcela.valor_total - parcela.valor_pago + (parcela.valor_multa || 0) + (parcela.valor_juros_mora || 0);
      acc[cid].emprestimos[eid].total_devido_emp += valorDevido;
      acc[cid].total_devido += valorDevido;
      acc[cid].total_parcelas++;
      const venc = new Date(parcela.data_vencimento).getTime();
      if (acc[cid].vencimento_mais_urgente === null || venc < acc[cid].vencimento_mais_urgente) {
        acc[cid].vencimento_mais_urgente = venc;
      }
      if ((parcela.dias_atraso || 0) > acc[cid].max_dias_atraso) {
        acc[cid].max_dias_atraso = parcela.dias_atraso || 0;
      }
      if (parcela.status === 'atrasado') {
        acc[cid].emprestimos[eid].parcelas_atrasadas_emp++;
        acc[cid].parcelas_atrasadas++;
      }
      return acc;
    }, {});

    const ordenarClientes = (a, b) => {
      switch (filtroOrdenacao) {
        case 'vencimento': return a.vencimento_mais_urgente - b.vencimento_mais_urgente;
        case 'valor': return b.total_devido - a.total_devido;
        case 'cliente': return (a.cliente_nome || '').localeCompare(b.cliente_nome || '');
        case 'dias_atraso': return b.max_dias_atraso - a.max_dias_atraso || a.vencimento_mais_urgente - b.vencimento_mais_urgente;
        default: return a.vencimento_mais_urgente - b.vencimento_mais_urgente;
      }
    };

    return Object.values(gruposCliente).map((cliente) => ({
      ...cliente,
      emprestimos: Object.values(cliente.emprestimos).sort((a, b) =>
        b.parcelas_atrasadas_emp - a.parcelas_atrasadas_emp || b.total_devido_emp - a.total_devido_emp
      ),
    })).sort(ordenarClientes);
  }, [parcelasOrdenadas, filtroOrdenacao]);

  // Recebido no mês atual vs mês anterior (para a variação nos KPIs)
  const _now = new Date();
  const _sameMonth = (iso, off) => {
    if (!iso) return false;
    const d = new Date(iso);
    const r = new Date(_now.getFullYear(), _now.getMonth() - off, 1);
    return d.getMonth() === r.getMonth() && d.getFullYear() === r.getFullYear();
  };
  const recebidoMes = pagamentos.filter((p) => _sameMonth(p.data_pagamento, 0)).reduce((s, p) => s + p.valor_pago, 0);
  const recebidoMesAnt = pagamentos.filter((p) => _sameMonth(p.data_pagamento, 1)).reduce((s, p) => s + p.valor_pago, 0);
  const deltaRecebidoPct = recebidoMesAnt > 0
    ? ((recebidoMes - recebidoMesAnt) / recebidoMesAnt) * 100
    : (recebidoMes > 0 ? 100 : 0);
  const taxaPctNum = totalPagamentos + totalPendente > 0 ? (totalPagamentos / (totalPagamentos + totalPendente)) * 100 : 0;

  if (loading) return <Loading message="Carregando pagamentos..." />;

  const inputBase = 'w-full bg-transparent border-0 border-b border-border px-1 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-emerald-500 transition-colors';

  return (
    <Layout>
      {enviandoWhatsApp && (
        <div className="fixed inset-0 bg-[#050807]/70 backdrop-blur-md z-50 flex items-center justify-center">
          <div className="bg-card rounded-xl p-8 ring-1 ring-border shadow-[0_32px_64px_rgba(0,0,0,0.5)] max-w-sm mx-4">
            <div className="flex flex-col items-center gap-4">
              <div className="relative">
                <div className="w-14 h-14 border-2 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <MessageCircle className="w-6 h-6 text-emerald-400" strokeWidth={ICON} />
                </div>
              </div>
              <div className="text-center">
                <h3 className="text-base font-semibold text-foreground mb-1 font-cabinet">Enviando mensagem…</h3>
                <p className="text-sm text-muted-foreground">Aguarde enquanto enviamos via WhatsApp</p>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="container mx-auto px-4 sm:px-6 py-8 font-satoshi">
        <header className="mb-8">
          <h1 className="font-cabinet font-black text-3xl sm:text-4xl tracking-tighter text-foreground" data-testid="pagamentos-title">
            Pagamentos
          </h1>
          <p className="text-muted-foreground mt-1.5">Gerencie recebimentos e parcelas em aberto</p>
        </header>

        {error && <ErrorMessage message={error} onRetry={carregarDados} />}

        {/* KPIs */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <KpiCard testId="total-recebido-card" label="Total recebido" tone="green" Icon={ArrowDownRight}
            amount={totalPagamentos} format={formatarMoeda}
            delta={{ pct: deltaRecebidoPct, label: 'vs mês anterior' }}
            hint={`${formatarMoeda(recebidoMes)} este mês`} delay={0} />
          <KpiCard testId="total-pendente-card" label="Total a receber" highlight Icon={Wallet}
            amount={totalPendente} format={formatarMoeda} hint={`${parcelasPendentes.length} parcelas · com multa e mora`} delay={60} />
          <KpiCard testId="atrasadas-card" label="Em atraso" tone={totalAtrasado > 0 ? 'red' : 'default'} Icon={ArrowUpRight}
            amount={totalAtrasado} format={formatarMoeda} hint={`${parcelasAtrasadas.length} parcela${parcelasAtrasadas.length === 1 ? '' : 's'} atrasada${parcelasAtrasadas.length === 1 ? '' : 's'}`} delay={120} />
          <KpiCard testId="taxa-recebimento-card" label="Taxa de recebimento" Icon={Percent}
            amount={taxaPctNum} format={(n) => (totalPagamentos + totalPendente > 0 ? `${n.toFixed(1)}%` : '—')} hint="recebido / total" delay={180} />
        </div>

        {/* Tabs — sem bloco, underline animado */}
        <div className="flex items-center gap-6 border-b border-border mb-6">
          {[
            { id: 'pendentes', label: 'Parcelas pendentes', count: parcelasPendentes.length },
            { id: 'historico', label: 'Histórico', count: pagamentos.length },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`relative -mb-px pb-3 text-sm font-medium transition-colors ${
                activeTab === t.id ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
              }`}
              data-testid={`tab-${t.id}`}
            >
              {t.label} <span className="font-mono text-xs text-muted-foreground">({t.count})</span>
              {activeTab === t.id && <span className="absolute left-0 right-0 -bottom-px h-0.5 rounded-full bg-emerald-500" />}
            </button>
          ))}
        </div>

        {/* Confirmações */}
        {confirmacoes.length > 0 && (
          <div className="mb-6 space-y-2" data-testid="confirmacoes-pagamento">
            {confirmacoes.map((c) => (
              <div
                key={c.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl ring-1 ring-emerald-500/30 bg-emerald-500/[0.06] px-4 py-3 animate-slide-up"
                data-testid={`confirmacao-${c.id}`}
              >
                <div className="flex items-start gap-3 min-w-0">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 mt-0.5 shrink-0" strokeWidth={ICON} />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground">
                      {c.quitou ? 'Parcela quitada' : 'Pagamento parcial registrado'} — {c.cliente}
                    </p>
                    <p className="text-xs text-muted-foreground font-mono">
                      #{c.emprestimoRef} · Parcela {c.numero ?? '—'} · Recebido{' '}
                      <span className="text-foreground">{formatarMoeda(c.valorPago)}</span>
                      {c.perdoado > 0 && ` · desconto ${formatarMoeda(c.perdoado)}`}
                      {!c.quitou && c.restante != null && ` · falta ${formatarMoeda(c.restante)}`}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => baixarReciboConfirmacao(c.id)}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-md bg-emerald-500 text-white hover:bg-emerald-600 transition-colors shadow-sm focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:outline-none"
                    data-testid={`confirmacao-recibo-${c.id}`}
                    title="Baixar recibo em PDF"
                  >
                    <Receipt className="w-4 h-4" strokeWidth={ICON} /> Baixar recibo
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmacoes((prev) => prev.filter((x) => x.id !== c.id))}
                    className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                    title="Fechar"
                    data-testid={`confirmacao-fechar-${c.id}`}
                  >
                    <X className="w-4 h-4" strokeWidth={ICON} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ============ TAB PENDENTES ============ */}
        {activeTab === 'pendentes' && (
          <div data-testid="parcelas-pendentes-table">
            {/* Filtros — sticky glass, inputs minimalistas */}
            <div className="sticky top-0 z-20 -mx-4 sm:-mx-6 px-4 sm:px-6 py-4 mb-2 bg-background/80 backdrop-blur-xl border-b border-border">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-muted-foreground mb-1">Status</label>
                  <select value={filtroStatus} onChange={(e) => setFiltroStatus(e.target.value)} className={inputBase}>
                    <option value="todos">Todos</option>
                    <option value="atrasado">Atrasadas ({parcelasPendentes.filter((p) => p.status === 'atrasado').length})</option>
                    <option value="vence_hoje">Vencem hoje ({parcelasVencemHoje.length})</option>
                    <option value="pendente">Pendentes ({parcelasPendentes.filter((p) => p.status === 'pendente').length})</option>
                    <option value="parcial">Parciais ({parcelasPendentes.filter((p) => p.status === 'parcial').length})</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-muted-foreground mb-1">Buscar cliente</label>
                  <div className="relative">
                    <Search className="absolute left-1 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" strokeWidth={ICON} />
                    <input
                      type="text" value={filtroCliente} onChange={(e) => setFiltroCliente(e.target.value)}
                      placeholder="Nome ou telefone" data-testid="filtro-cliente"
                      className={`${inputBase} pl-7`}
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-muted-foreground mb-1">Ordenar por</label>
                  <select value={filtroOrdenacao} onChange={(e) => setFiltroOrdenacao(e.target.value)} className={inputBase}>
                    <option value="vencimento">Vencimento</option>
                    <option value="valor">Maior valor</option>
                    <option value="cliente">Nome do cliente</option>
                    <option value="dias_atraso">Dias de atraso</option>
                  </select>
                </div>
                <div className="flex items-end">
                  <button
                    onClick={() => { setFiltroStatus('todos'); setFiltroCliente(''); setFiltroOrdenacao('vencimento'); }}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                  >
                    <RefreshCw className="w-4 h-4" strokeWidth={ICON} /> Limpar filtros
                  </button>
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-3">
                Mostrando <span className="font-mono text-foreground">{parcelasOrdenadas.length}</span> de{' '}
                <span className="font-mono text-foreground">{parcelasPendentes.length}</span> parcelas ·{' '}
                {clientesComParcelas.length} {clientesComParcelas.length === 1 ? 'cliente' : 'clientes'}
              </p>
            </div>

            {/* Selecionar todas */}
            {parcelasOrdenadas.length > 0 && (
              <div className="flex items-center justify-between py-2" data-testid="acoes-em-massa-bar">
                <button
                  onClick={toggleSelecionarTodas}
                  className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                  data-testid="btn-selecionar-todas"
                >
                  {parcelasSelecionadas.size > 0 && parcelasSelecionadas.size === parcelasOrdenadas.length
                    ? <CheckSquare className="w-4 h-4 text-emerald-400" strokeWidth={ICON} />
                    : <Square className="w-4 h-4" strokeWidth={ICON} />}
                  {parcelasSelecionadas.size > 0 ? `${parcelasSelecionadas.size} selecionada${parcelasSelecionadas.size === 1 ? '' : 's'}` : 'Selecionar todas'}
                </button>
              </div>
            )}

            {parcelasPendentes.length === 0 ? (
              <EmptyState icon={Inbox} titulo="Nenhuma parcela pendente" subtitulo="Tudo em dia por aqui." testId="sem-parcelas-message" />
            ) : (
              <div className="divide-y divide-border">
                {clientesComParcelas.map((cliente, cIdx) => (
                  <section key={cliente.cliente_id} className="animate-slide-up py-6 first:pt-0 last:pb-0" style={{ animationDelay: `${Math.min(cIdx * 40, 240)}ms` }}>
                    {/* Header do cliente — minimal, sem badge soup */}
                    <div className="flex items-center justify-between gap-3 mb-3">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="h-11 w-11 rounded-full bg-emerald-500/10 ring-1 ring-emerald-500/20 flex items-center justify-center shrink-0">
                          <span className="text-emerald-400 font-cabinet font-bold text-lg">
                            {(cliente.cliente_nome || '').trim().charAt(0).toUpperCase() || '?'}
                          </span>
                        </div>
                        <div className="min-w-0">
                          <h3 className="font-cabinet font-bold text-base text-foreground truncate">{cliente.cliente_nome}</h3>
                          <p className="text-xs text-muted-foreground font-mono truncate">
                            {cliente.cliente_telefone || '—'} · {cliente.total_parcelas} {cliente.total_parcelas === 1 ? 'parcela' : 'parcelas'}
                            {cliente.emprestimos.length > 1 && ` · ${cliente.emprestimos.length} empréstimos`}
                            {cliente.parcelas_atrasadas > 0 && <span className="text-red-400"> · {cliente.parcelas_atrasadas} atrasada{cliente.parcelas_atrasadas > 1 ? 's' : ''}</span>}
                          </p>
                        </div>
                      </div>
                      <div className="text-right shrink-0">
                        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Total devido</div>
                        <div className="font-mono font-semibold text-lg text-foreground">{formatarMoeda(cliente.total_devido)}</div>
                      </div>
                    </div>

                    {/* Empréstimos */}
                    <div className="space-y-3">
                      {cliente.emprestimos.map((emprestimo, empIdx) => {
                        const empKey = `${cliente.cliente_id}-${emprestimo.emprestimo_id}`;
                        const isExpanded = expandedClientes.has(empKey);
                        const isCollapsed = collapsedEmprestimos.has(empKey);
                        const parcelaMaisUrgente = emprestimo.parcelas.reduce((prev, curr) =>
                          new Date(curr.data_vencimento) < new Date(prev.data_vencimento) ? curr : prev
                        );
                        const parcelasRestantes = emprestimo.parcelas.filter((p) => p.id !== parcelaMaisUrgente.id);
                        const ref = (emprestimo.emprestimo_id || '').slice(-6).toUpperCase();
                        const isAberto = emprestimo.sem_prazo;
                        const isSemanal = emprestimo.periodicidade === 'semanal';
                        const TipoIcon = isAberto ? Repeat : Layers;
                        const tipoLabel = isAberto ? `Juros ${isSemanal ? 'semanal' : 'mensal'}` : `Parcelado ${parcelaMaisUrgente.total_parcelas || '∞'}x`;
                        const taxa = isAberto ? (isSemanal ? emprestimo.taxa_semanal : emprestimo.taxa_mensal) : emprestimo.taxa_mensal;
                        const taxaLabel = taxa ? `${taxa}%${isAberto ? (isSemanal ? '/sem' : '/mês') : '/mês'}` : null;
                        const totalP = parcelaMaisUrgente.total_parcelas || 0;
                        const pagas = !isAberto && totalP > 0 ? Math.max(0, totalP - emprestimo.parcelas.length) : 0;
                        const pct = totalP > 0 ? Math.min(100, Math.round((pagas / totalP) * 100)) : 0;

                        return (
                          <div key={empKey} className="rounded-xl bg-card ring-1 ring-border overflow-hidden">
                            {/* Header do empréstimo */}
                            <div
                              onClick={() => toggleEmprestimoCollapsed(empKey)}
                              className="px-4 py-3 border-b border-border cursor-pointer select-none hover:bg-muted/40 transition-colors"
                              data-testid={`emprestimo-header-${emprestimo.emprestimo_id}`}
                            >
                              <div className="flex items-center justify-between gap-3">
                                <div className="flex items-center gap-2.5 min-w-0">
                                  <ChevronDown className={`w-4 h-4 text-muted-foreground shrink-0 transition-transform ${isCollapsed ? '-rotate-90' : ''}`} strokeWidth={ICON} />
                                  <span className={`flex items-center justify-center w-7 h-7 rounded-md shrink-0 ${isAberto ? 'bg-violet-500/10 text-violet-300' : 'bg-muted text-muted-foreground'}`}>
                                    <TipoIcon className="w-4 h-4" strokeWidth={ICON} />
                                  </span>
                                  <button
                                    onClick={(e) => { e.stopPropagation(); navigate(`/emprestimos/${emprestimo.emprestimo_id}`); }}
                                    className="inline-flex items-center gap-2 text-sm font-semibold text-foreground hover:text-emerald-400 transition-colors group min-w-0"
                                    data-testid={`emprestimo-ref-${emprestimo.emprestimo_id}`}
                                    title="Ver detalhes do empréstimo"
                                  >
                                    <span className="truncate">Empréstimo {empIdx + 1}</span>
                                    <span className="font-mono text-[10px] text-muted-foreground group-hover:text-emerald-400 shrink-0">#{ref}</span>
                                    <span className="text-[11px] font-medium text-muted-foreground whitespace-nowrap shrink-0">{tipoLabel}</span>
                                    <ChevronRight className="w-3.5 h-3.5 opacity-40 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all shrink-0" strokeWidth={ICON} />
                                  </button>
                                </div>
                                <div className="text-right shrink-0">
                                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground leading-none">Devido</div>
                                  <div className="font-mono text-sm font-semibold text-foreground">{formatarMoeda(emprestimo.total_devido_emp)}</div>
                                </div>
                              </div>
                              <div className="flex flex-wrap items-center justify-between gap-2 mt-2 pl-[3.4rem]">
                                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-muted-foreground font-mono">
                                  {emprestimo.valor_emprestimo != null && <span>Capital <span className="text-foreground/70">{formatarMoeda(emprestimo.valor_emprestimo)}</span></span>}
                                  {taxaLabel && <span>Taxa <span className="text-foreground/70">{taxaLabel}</span></span>}
                                  <span>{emprestimo.parcelas.length} em aberto</span>
                                  {emprestimo.parcelas_atrasadas_emp > 0 && <span className="text-red-400">{emprestimo.parcelas_atrasadas_emp} atrasada{emprestimo.parcelas_atrasadas_emp > 1 ? 's' : ''}</span>}
                                </div>
                                <button
                                  onClick={(e) => { e.stopPropagation(); handleCobrarEmprestimo(emprestimo, empIdx); }}
                                  disabled={cobrandoEmMassa}
                                  className="inline-flex items-center gap-1.5 text-[11px] font-medium text-emerald-400 hover:text-emerald-300 transition-colors disabled:opacity-50 shrink-0"
                                  data-testid={`btn-cobrar-emprestimo-${emprestimo.emprestimo_id}`}
                                  title="Cobrar todas as parcelas em aberto deste empréstimo"
                                >
                                  <Send className="w-3.5 h-3.5" strokeWidth={ICON} /> Cobrar tudo
                                </button>
                              </div>
                              {!isAberto && totalP > 0 && (
                                <div className="flex items-center gap-2 mt-2.5 pl-[3.4rem]">
                                  <div className="flex-1 h-0.5 rounded-full bg-muted overflow-hidden">
                                    <div className="h-full bg-emerald-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
                                  </div>
                                  <span className="font-mono text-[10px] text-muted-foreground whitespace-nowrap" data-testid={`emprestimo-progresso-${emprestimo.emprestimo_id}`}>{pagas}/{totalP}</span>
                                </div>
                              )}
                            </div>

                            {!isCollapsed && (
                              <div className="px-3 sm:px-4">
                                <ParcelaRow
                                  parcela={parcelaMaisUrgente}
                                  handleRegistrarPagamento={handleRegistrarPagamento}
                                  handleEnviarWhatsApp={handleEnviarWhatsApp}
                                  handleExcluirParcela={handleExcluirParcela}
                                  formatarData={formatarData}
                                  formatarMoeda={formatarMoeda}
                                  selecionavel={true}
                                  selecionada={parcelasSelecionadas.has(parcelaMaisUrgente.id)}
                                  onToggleSelecionar={toggleSelecionarParcela}
                                />
                                {isExpanded && parcelasRestantes.map((parcela) => (
                                  <ParcelaRow
                                    key={parcela.id}
                                    parcela={parcela}
                                    handleRegistrarPagamento={handleRegistrarPagamento}
                                    handleEnviarWhatsApp={handleEnviarWhatsApp}
                                    handleExcluirParcela={handleExcluirParcela}
                                    formatarData={formatarData}
                                    formatarMoeda={formatarMoeda}
                                    selecionavel={true}
                                    selecionada={parcelasSelecionadas.has(parcela.id)}
                                    onToggleSelecionar={toggleSelecionarParcela}
                                  />
                                ))}
                                {parcelasRestantes.length > 0 && (
                                  <button
                                    onClick={() => toggleClienteExpanded(empKey)}
                                    className="w-full py-2.5 text-sm font-medium text-emerald-400 hover:text-emerald-300 transition-colors flex items-center justify-center gap-1.5"
                                  >
                                    {isExpanded
                                      ? <><ChevronUp className="w-4 h-4" strokeWidth={ICON} /> Ocultar {parcelasRestantes.length} {parcelasRestantes.length === 1 ? 'parcela' : 'parcelas'}</>
                                      : <><ChevronDown className="w-4 h-4" strokeWidth={ICON} /> Ver mais {parcelasRestantes.length} {parcelasRestantes.length === 1 ? 'parcela' : 'parcelas'}</>}
                                  </button>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </section>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ============ TAB HISTÓRICO ============ */}
        {activeTab === 'historico' && (
          <>
            <div className="sticky top-0 z-20 -mx-4 sm:-mx-6 px-4 sm:px-6 py-4 mb-4 bg-background/80 backdrop-blur-xl border-b border-border">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-muted-foreground mb-1">Método</label>
                  <select value={filtroMetodo} onChange={(e) => setFiltroMetodo(e.target.value)} className={inputBase} data-testid="filtro-metodo">
                    <option value="">Todos</option>
                    <option value="pix">PIX</option>
                    <option value="transferencia">Transferência</option>
                    <option value="dinheiro">Dinheiro</option>
                    <option value="cartao">Cartão</option>
                    <option value="boleto">Boleto</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-muted-foreground mb-1">Cliente</label>
                  <input
                    type="text" value={filtroClienteHistorico} onChange={(e) => setFiltroClienteHistorico(e.target.value)}
                    placeholder="Nome do cliente" className={inputBase} data-testid="filtro-cliente-historico"
                  />
                </div>
                <div>
                  <label className="block text-[11px] uppercase tracking-wider text-muted-foreground mb-1">Data</label>
                  <DatePickerBR value={filtroData} onChange={setFiltroData} placeholder="Selecione" testId="filtro-data" clearable={true} />
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => { setFiltroMetodo(''); setFiltroData(null); setFiltroClienteHistorico(''); }}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                    data-testid="limpar-filtros-button"
                  >
                    <RefreshCw className="w-4 h-4" strokeWidth={ICON} /> Limpar
                  </button>
                  <button
                    onClick={handleExportarHistorico}
                    className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium text-emerald-300 hover:bg-emerald-500/10 transition-colors"
                    data-testid="btn-exportar-csv" title="Exportar histórico em CSV"
                  >
                    <Download className="w-4 h-4" strokeWidth={ICON} /> CSV
                  </button>
                </div>
              </div>
            </div>

            <div className="rounded-xl bg-card ring-1 ring-border overflow-hidden" data-testid="pagamentos-table">
              {pagamentosFiltrados.length === 0 ? (
                <EmptyState icon={Inbox} titulo="Nenhum pagamento encontrado" subtitulo="Ajuste os filtros para ver o histórico." testId="sem-pagamentos-message" />
              ) : (
                <>
                  {/* Desktop */}
                  <div className="hidden md:block overflow-x-auto">
                    <table className="min-w-full">
                      <thead>
                        <tr className="border-b border-border">
                          {['Cliente', 'Parcela', 'Data/Hora', 'Valor', 'Método', 'Observações', ''].map((h, i) => (
                            <th key={i} className={`px-5 py-3 text-[11px] font-medium text-muted-foreground uppercase tracking-wider ${i === 6 ? 'text-right' : 'text-left'}`}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody data-testid="pagamentos-table-body">
                        {pagamentosFiltrados.map((pagamento) => (
                          <tr key={pagamento.id} data-testid={`pagamento-row-${pagamento.id}`} className="border-b border-border last:border-b-0 hover:bg-muted/40 transition-colors">
                            <td className="px-5 py-3.5">
                              <div className="flex items-center gap-3">
                                <div className="h-9 w-9 rounded-full bg-emerald-500/10 ring-1 ring-emerald-500/20 flex items-center justify-center shrink-0">
                                  <span className="text-emerald-400 font-semibold text-sm">{(pagamento.cliente_nome || '').trim().charAt(0).toUpperCase() || '?'}</span>
                                </div>
                                <div className="min-w-0">
                                  <p className="text-sm font-medium text-foreground truncate">{pagamento.cliente_nome || 'Cliente'}</p>
                                  <p className="text-xs text-muted-foreground font-mono">{pagamento.cliente_telefone || '—'}</p>
                                </div>
                              </div>
                            </td>
                            <td className="px-5 py-3.5 font-mono text-sm text-foreground whitespace-nowrap">
                              {pagamento.numero_parcela || '-'}/{pagamento.total_parcelas || '∞'}
                            </td>
                            <td className="px-5 py-3.5 font-mono text-sm text-muted-foreground whitespace-nowrap">{formatarDataHora(pagamento.data_pagamento)}</td>
                            <td className="px-5 py-3.5 font-mono text-sm font-semibold text-emerald-400 whitespace-nowrap">{formatarMoeda(pagamento.valor_pago)}</td>
                            <td className="px-5 py-3.5">
                              <span className="text-xs font-medium text-muted-foreground">{pagamento.metodo_pagamento.toUpperCase()}</span>
                              {pagamento.tipo === 'amortizacao' && <span className="ml-2 text-[10px] font-medium text-violet-300">AMORT.</span>}
                            </td>
                            <td className="px-5 py-3.5 text-sm text-muted-foreground max-w-[16rem] truncate">{pagamento.observacoes || '—'}</td>
                            <td className="px-5 py-3.5">
                              <div className="flex items-center justify-end gap-1">
                                <button
                                  onClick={() => handleEnviarConfirmacaoPagamento(pagamento)}
                                  className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-emerald-300 hover:bg-emerald-500/10 transition-colors"
                                  title="Enviar confirmação por WhatsApp" data-testid={`btn-confirmar-${pagamento.id}`}
                                >
                                  <MessageCircle className="w-3.5 h-3.5" strokeWidth={ICON} /><span className="hidden lg:inline">Confirmar</span>
                                </button>
                                {pagamento.tipo !== 'amortizacao' && (
                                  <button
                                    onClick={() => handleEstornarPagamento(pagamento)}
                                    className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-red-400 hover:bg-red-500/10 transition-colors"
                                    title="Estornar pagamento" data-testid={`btn-estornar-${pagamento.id}`}
                                  >
                                    <RotateCcw className="w-3.5 h-3.5" strokeWidth={ICON} /><span className="hidden lg:inline">Estornar</span>
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Mobile */}
                  <div className="md:hidden divide-y divide-border">
                    {pagamentosFiltrados.map((pagamento) => (
                      <div key={pagamento.id} className="p-4" data-testid={`pagamento-card-${pagamento.id}`}>
                        <div className="flex items-center gap-3 mb-3">
                          <div className="h-10 w-10 rounded-full bg-emerald-500/10 ring-1 ring-emerald-500/20 flex items-center justify-center shrink-0">
                            <span className="text-emerald-400 font-bold">{(pagamento.cliente_nome || '').trim().charAt(0).toUpperCase() || '?'}</span>
                          </div>
                          <div className="min-w-0 flex-1">
                            <h3 className="font-cabinet font-bold text-foreground truncate">{pagamento.cliente_nome || 'Cliente'}</h3>
                            <p className="text-xs text-muted-foreground font-mono">{pagamento.cliente_telefone || '—'}</p>
                          </div>
                          <span className="font-mono font-semibold text-emerald-400">{formatarMoeda(pagamento.valor_pago)}</span>
                        </div>
                        <div className="flex items-center gap-x-4 gap-y-1 flex-wrap text-xs text-muted-foreground font-mono mb-3">
                          <span>Parcela {pagamento.numero_parcela || '-'}/{pagamento.total_parcelas || '∞'}</span>
                          <span>{formatarDataHora(pagamento.data_pagamento)}</span>
                          <span>{pagamento.metodo_pagamento.toUpperCase()}</span>
                        </div>
                        {pagamento.observacoes && <p className="text-sm text-foreground/80 mb-3">{pagamento.observacoes}</p>}
                        <div className="grid grid-cols-2 gap-2">
                          <button
                            onClick={() => handleEnviarConfirmacaoPagamento(pagamento)}
                            className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20 transition-colors"
                            data-testid={`btn-confirmar-mobile-${pagamento.id}`}
                          >
                            <MessageCircle className="w-4 h-4" strokeWidth={ICON} /> Confirmar
                          </button>
                          {pagamento.tipo !== 'amortizacao' && (
                            <button
                              onClick={() => handleEstornarPagamento(pagamento)}
                              className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-md text-sm font-medium bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
                              data-testid={`btn-estornar-mobile-${pagamento.id}`}
                            >
                              <RotateCcw className="w-4 h-4" strokeWidth={ICON} /> Estornar
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          </>
        )}
      </div>

      {/* Barra flutuante de ação em massa */}
      {activeTab === 'pendentes' && parcelasSelecionadas.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 animate-slide-up">
          <div className="flex items-center gap-3 rounded-full bg-emerald-600 text-white pl-5 pr-2 py-2 shadow-[0_16px_40px_rgba(0,0,0,0.5)]">
            <span className="text-sm font-medium">{parcelasSelecionadas.size} selecionada{parcelasSelecionadas.size === 1 ? '' : 's'}</span>
            <button
              onClick={handleCobrarEmMassa}
              disabled={cobrandoEmMassa}
              className="inline-flex items-center gap-2 rounded-full bg-white text-emerald-700 px-4 py-2 text-sm font-semibold hover:bg-white/90 transition-colors disabled:opacity-60"
              data-testid="btn-cobrar-em-massa"
            >
              <Send className="w-4 h-4" strokeWidth={ICON} />
              {cobrandoEmMassa ? 'Enviando…' : 'Cobrar via WhatsApp'}
            </button>
          </div>
        </div>
      )}

      {showModal && parcelaSelecionada && (
        <PagamentoDetalheModal
          parcela={parcelaSelecionada}
          form={formPagamento}
          setForm={setFormPagamento}
          onSubmit={handleSubmitPagamento}
          onClose={() => { setShowModal(false); setParcelaSelecionada(null); }}
          onCobrar={() => { const p = parcelaSelecionada; setShowModal(false); setParcelaSelecionada(null); setCobrancaModal({ open: true, parcela: p }); }}
          historico={pagamentos.filter((pg) => pg.parcela_id === parcelaSelecionada.id)}
          onRecibo={baixarReciboConfirmacao}
        />
      )}

      <CobrancaModal
        isOpen={cobrancaModal.open}
        parcela={cobrancaModal.parcela}
        onClose={fecharCobrancaModal}
        onConfirm={executarEnvioCobranca}
        enviando={enviandoWhatsApp}
      />
    </Layout>
  );
};

const EmptyState = ({ icon: Icon, titulo, subtitulo, testId }) => (
  <div className="flex flex-col items-center justify-center py-16 text-center" data-testid={testId}>
    <Icon className="w-12 h-12 text-muted-foreground/30 mb-4" strokeWidth={1.25} />
    <p className="font-cabinet font-bold text-lg text-foreground">{titulo}</p>
    {subtitulo && <p className="text-sm text-muted-foreground mt-1">{subtitulo}</p>}
  </div>
);

export default Pagamentos;
