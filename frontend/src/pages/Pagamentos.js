import React, { useState, useEffect, useCallback, useMemo } from 'react';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import ErrorMessage from '../components/ErrorMessage';
import Button from '../components/Button';
import { useModal } from '../components/Modal';
import { pagamentosAPI, parcelasAPI, whatsappAPI } from '../api/api';
import { formatarMoeda, formatarData, formatarDataHora } from '../utils/formatters';
import { DatePickerBR } from '../components/ui/date-picker-br';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { DollarSign, MessageCircle, Trash2, MoreVertical, Download, RotateCcw, CheckSquare, Square } from 'lucide-react';

// Componente para linha de parcela (DRY)
const ParcelaRow = ({ parcela, handleRegistrarPagamento, handleEnviarWhatsApp, handleExcluirParcela, menuAbertoId, setMenuAbertoId, formatarData, formatarMoeda, selecionavel, selecionada, onToggleSelecionar }) => {
  const valorDevido = parcela.valor_total - parcela.valor_pago + (parcela.valor_multa || 0) + (parcela.valor_juros_mora || 0);
  const temJurosOuMulta = (parcela.valor_multa || 0) > 0 || (parcela.valor_juros_mora || 0) > 0;
  
  // Calcular "última cobrança há X dias"
  let ultimaCobrancaTxt = null;
  if (parcela.ultima_cobranca_em) {
    const diff = Math.floor((Date.now() - new Date(parcela.ultima_cobranca_em).getTime()) / (1000 * 60 * 60 * 24));
    ultimaCobrancaTxt = diff <= 0 ? 'Cobrado hoje' : `Cobrado há ${diff}d`;
  }
  
  return (
    <div className="flex flex-col gap-2 py-3 px-3 sm:px-4 bg-muted/20 rounded-lg hover:bg-muted/30 transition-colors border border-border/50">
      {/* Linha principal */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-4">
        <div className="flex flex-wrap items-center gap-2 sm:gap-4 flex-1">
          {/* Checkbox de seleção em massa */}
          {selecionavel && (
            <button
              onClick={(e) => { e.stopPropagation(); onToggleSelecionar(parcela.id); }}
              className="p-1 hover:bg-muted rounded transition-colors flex-shrink-0"
              data-testid={`checkbox-parcela-${parcela.id}`}
              aria-label={selecionada ? 'Desselecionar parcela' : 'Selecionar parcela'}
            >
              {selecionada ? (
                <CheckSquare className="w-5 h-5 text-primary" />
              ) : (
                <Square className="w-5 h-5 text-muted-foreground" />
              )}
            </button>
          )}
          <span className="text-sm font-medium text-foreground min-w-[50px] sm:min-w-[60px]">
            {parcela.numero_parcela}/{parcela.total_parcelas || '∞'}
          </span>
          <span className="text-xs sm:text-sm text-muted-foreground min-w-[80px] sm:min-w-[90px]">{formatarData(parcela.data_vencimento)}</span>
          {parcela.dias_atraso > 0 && (
            <span className="text-xs text-red-500 font-medium whitespace-nowrap">{parcela.dias_atraso}d atraso</span>
          )}
          <span className="text-sm font-semibold text-foreground min-w-[90px] sm:min-w-[100px]">{formatarMoeda(valorDevido)}</span>
          <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium whitespace-nowrap ${
            parcela.status === 'atrasado' ? 'bg-red-500/10 text-red-500' :
            parcela.status === 'parcial' ? 'bg-yellow-500/10 text-yellow-500' :
            'bg-blue-500/10 text-blue-500'
          }`}>
            {parcela.status === 'atrasado' ? '⚠️ ATRASADO' :
             parcela.status === 'parcial' ? '⏳ PARCIAL' : '📅 PENDENTE'}
          </span>
          {ultimaCobrancaTxt && (
            <span
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-green-500/10 text-green-600 dark:text-green-400 whitespace-nowrap"
              title={`Última cobrança: ${new Date(parcela.ultima_cobranca_em).toLocaleString('pt-BR')}`}
            >
              <MessageCircle className="w-3 h-3" /> {ultimaCobrancaTxt}
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-1 self-end sm:self-auto">
          {/* Botão "Pagar" inline (1 clique) */}
          <button
            onClick={(e) => { e.stopPropagation(); handleRegistrarPagamento(parcela); }}
            className="inline-flex items-center gap-1 px-3 py-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 rounded-md text-xs font-medium transition-colors min-h-[36px]"
            data-testid={`btn-pagar-inline-${parcela.id}`}
            title="Registrar Pagamento"
          >
            <DollarSign className="w-4 h-4" />
            <span className="hidden sm:inline">Pagar</span>
          </button>
          {/* Botão "Cobrar" inline (1 clique) */}
          <button
            onClick={(e) => { e.stopPropagation(); handleEnviarWhatsApp(parcela); }}
            className="inline-flex items-center gap-1 px-3 py-2 bg-green-500/10 hover:bg-green-500/20 text-green-600 dark:text-green-400 rounded-md text-xs font-medium transition-colors min-h-[36px]"
            data-testid={`btn-cobrar-inline-${parcela.id}`}
            title="Enviar Cobrança via WhatsApp"
          >
            <MessageCircle className="w-4 h-4" />
            <span className="hidden sm:inline">Cobrar</span>
          </button>
          
          {/* Menu mais opções */}
          <div className="relative">
            <button 
              onClick={(e) => {
                e.stopPropagation();
                setMenuAbertoId(menuAbertoId === parcela.id ? null : parcela.id);
              }}
              className="p-2 sm:p-2 hover:bg-muted rounded-md transition-colors min-h-[36px] min-w-[36px] flex items-center justify-center" 
              data-testid={`menu-acoes-${parcela.id}`}
            >
              <MoreVertical className="w-4 h-4 text-muted-foreground" />
            </button>
            
            {menuAbertoId === parcela.id && (
              <>
                <div 
                  className="fixed inset-0" 
                  style={{ zIndex: 100 }} 
                  onClick={(e) => { e.stopPropagation(); setMenuAbertoId(null); }} 
                />
                <div 
                  className="absolute right-0 sm:right-0 mt-2 w-56 bg-card rounded-lg shadow-xl border border-border" 
                  style={{ zIndex: 110 }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setMenuAbertoId(null);
                      setTimeout(() => handleExcluirParcela(parcela), 50);
                    }}
                    className="w-full flex items-center gap-3 px-4 py-3 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 transition-colors min-h-[44px] rounded-lg"
                    data-testid={`excluir-parcela-${parcela.id}`}
                  >
                    <Trash2 className="w-4 h-4 text-red-500" />
                    <span>Excluir Parcela</span>
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
      
      {/* Detalhes adicionais: Multa e Juros de Mora */}
      {temJurosOuMulta && (
        <div className="flex flex-wrap gap-3 text-xs text-muted-foreground pl-2 border-l-2 border-red-500/30">
          {(parcela.valor_multa || 0) > 0 && (
            <span className="flex items-center gap-1">
              <span className="text-red-500">💰</span>
              Multa: <span className="font-semibold text-red-500">{formatarMoeda(parcela.valor_multa)}</span>
            </span>
          )}
          {(parcela.valor_juros_mora || 0) > 0 && (
            <span className="flex items-center gap-1">
              <span className="text-orange-500">📈</span>
              Juros Mora: <span className="font-semibold text-orange-500">{formatarMoeda(parcela.valor_juros_mora)}</span>
            </span>
          )}
          <span className="flex items-center gap-1">
            <span>📊</span>
            Valor Original: <span className="font-semibold">{formatarMoeda(parcela.valor_total)}</span>
          </span>
        </div>
      )}
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
  const [filtroStatus, setFiltroStatus] = useState('todos'); // todos, pendente, atrasado, parcial
  const [filtroCliente, setFiltroCliente] = useState('');
  const [filtroOrdenacao, setFiltroOrdenacao] = useState('vencimento'); // vencimento, valor, cliente, dias_atraso
  const [showModal, setShowModal] = useState(false);
  const [parcelaSelecionada, setParcelaSelecionada] = useState(null);
  const [activeTab, setActiveTab] = useState('pendentes');
  const [menuAbertoId, setMenuAbertoId] = useState(null);
  const [enviandoWhatsApp, setEnviandoWhatsApp] = useState(false);
  const [expandedClientes, setExpandedClientes] = useState(new Set());
  // Seleção em massa
  const [parcelasSelecionadas, setParcelasSelecionadas] = useState(new Set());
  const [cobrandoEmMassa, setCobrandoEmMassa] = useState(false);
  const modal = useModal();

  // Redirecionar membros para o dashboard
  useEffect(() => {
    if (isMember) {
      navigate('/dashboard');
    }
  }, [isMember, navigate]);

  // Aplicar filtros vindos via query string (?filtro=atrasado&cliente=Nome)
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
    metodo_pagamento: 'pix',
    observacoes: ''
  });

  const carregarDados = useCallback(async () => {
    try {
      setLoading(true);
      setError('');

      const [pagamentosRes, parcelasRes] = await Promise.all([
        pagamentosAPI.listar(),
        parcelasAPI.listarPendentes()
      ]);

      setPagamentos(pagamentosRes.data);
      setParcelasPendentes(parcelasRes.data);
    } catch (err) {
      console.error('Erro ao carregar dados:', err);
      setError('Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    carregarDados();
  }, [carregarDados]);

  const handleRegistrarPagamento = (parcela) => {
    setParcelaSelecionada(parcela);
    const valorDevido = parcela.valor_total - parcela.valor_pago + (parcela.valor_multa || 0) + (parcela.valor_juros_mora || 0);
    setFormPagamento({
      valor_pago: valorDevido.toFixed(2),
      metodo_pagamento: 'pix',
      observacoes: ''
    });
    setShowModal(true);
  };

  const toggleClienteExpanded = (clienteId) => {
    setExpandedClientes(prev => {
      const next = new Set(prev);
      next.has(clienteId) ? next.delete(clienteId) : next.add(clienteId);
      return next;
    });
  };

  const handleSubmitPagamento = async (e) => {
    e.preventDefault();

    try {
      const data = {
        parcela_id: parcelaSelecionada.id,
        valor_pago: parseFloat(formPagamento.valor_pago),
        metodo_pagamento: formPagamento.metodo_pagamento,
        observacoes: formPagamento.observacoes || null
      };

      await pagamentosAPI.criar(data);
      setShowModal(false);
      setParcelaSelecionada(null);
      carregarDados();
      modal.success('Pagamento Registrado!', 'O pagamento foi registrado com sucesso e a parcela foi atualizada.');
    } catch (err) {
      modal.error('Erro no Pagamento', err.response?.data?.detail || 'Não foi possível registrar o pagamento. Tente novamente.');
    }
  };

  const handleEnviarWhatsApp = async (parcela) => {
    // Fechar menu dropdown
    setMenuAbertoId(null);
    
    // Mostrar loading
    setEnviandoWhatsApp(true);
    
    try {
      // Enviar mensagem via Evolution API
      const response = await whatsappAPI.enviarCobrancaParcela(parcela.id);
      
      // Parar loading
      setEnviandoWhatsApp(false);
      
      const modo = response.data?.modo;
      if (modo === 'fila') {
        modal.success(
          '✅ Mensagem na fila!',
          `WhatsApp para ${parcela.cliente_nome} será enviado em instantes.`
        );
      } else {
        modal.success(
          '✅ Mensagem enviada!',
          `WhatsApp enviado com sucesso para ${parcela.cliente_nome}`
        );
      }
      
    } catch (err) {
      // Parar loading
      setEnviandoWhatsApp(false);
      
      const errorStatus = err.response?.status;
      const errorMessage = err.response?.data?.detail || err.message || 'Erro ao enviar mensagem';
      
      // Erro 503: WhatsApp não configurado/conectado
      if (errorStatus === 503) {
        if (errorMessage.includes('número não sincronizado')) {
          modal.error(
            '⚠️ WhatsApp com problema',
            'WhatsApp está conectado mas o número não foi sincronizado. Por favor, reconecte seu WhatsApp em Configurações > WhatsApp.'
          );
        } else if (errorMessage.includes('desconectado')) {
          modal.error(
            '❌ WhatsApp desconectado',
            'Seu WhatsApp foi desconectado. Por favor, reconecte em Configurações > WhatsApp.'
          );
        } else {
          modal.error(
            '❌ WhatsApp não configurado',
            'Você precisa conectar seu WhatsApp primeiro. Acesse Configurações > WhatsApp para conectar.'
          );
        }
      } 
      // Erro 400: Dados inválidos (ex: cliente sem telefone)
      else if (errorStatus === 400) {
        modal.error('⚠️ Dados inválidos', errorMessage);
      }
      // Outros erros
      else {
        modal.error('❌ Erro ao enviar', errorMessage);
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
        carregarDados();
      } catch (err) {
        modal.error('Erro ao excluir', err.response?.data?.detail || 'Não foi possível excluir a parcela.');
      }
    }
  };

  const handleEnviarConfirmacaoPagamento = async (pagamento) => {
    // Mostrar loading
    setEnviandoWhatsApp(true);
    
    try {
      // Enviar confirmação via WhatsApp
      const response = await whatsappAPI.enviarConfirmacaoPagamento(pagamento.id);
      
      // Parar loading
      setEnviandoWhatsApp(false);
      
      const modo = response.data?.modo;
      if (modo === 'fila') {
        modal.success(
          '✅ Confirmação na fila!',
          `Confirmação de pagamento para ${pagamento.cliente_nome || 'o cliente'} será enviada em instantes.`
        );
      } else {
        modal.success(
          '✅ Confirmação enviada!',
          `Confirmação de pagamento enviada com sucesso para ${pagamento.cliente_nome || 'o cliente'}`
        );
      }
      
    } catch (err) {
      // Parar loading
      setEnviandoWhatsApp(false);
      
      const errorMessage = err.response?.data?.detail || err.message || 'Erro ao enviar confirmação';
      
      // Se erro for por WhatsApp não conectado, mostrar mensagem específica
      if (errorMessage.includes('WhatsApp não está conectado') || 
          errorMessage.includes('Nenhuma conexão WhatsApp ativa')) {
        modal.error(
          '❌ WhatsApp não conectado',
          'Você precisa conectar seu WhatsApp primeiro. Acesse Config. > WhatsApp para conectar.'
        );
      } else {
        modal.error('❌ Erro ao enviar confirmação', errorMessage);
      }
    }
  };

  // ✅ Seleção em massa
  const toggleSelecionarParcela = (parcelaId) => {
    setParcelasSelecionadas(prev => {
      const next = new Set(prev);
      if (next.has(parcelaId)) next.delete(parcelaId);
      else next.add(parcelaId);
      return next;
    });
  };

  const toggleSelecionarTodas = () => {
    setParcelasSelecionadas(prev => {
      if (prev.size === parcelasOrdenadas.length) return new Set();
      return new Set(parcelasOrdenadas.map(p => p.id));
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
      modal.success(
        '✅ Cobranças disparadas',
        `${data.enviadas} enviada(s) com sucesso${data.falhas > 0 ? ` • ${data.falhas} falha(s)` : ''}.`
      );
      carregarDados();
    } catch (err) {
      modal.error('Erro na cobrança em massa', err.response?.data?.detail || 'Falha ao processar lote.');
    } finally {
      setCobrandoEmMassa(false);
    }
  };

  // ✅ Estorno de pagamento
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
      carregarDados();
    } catch (err) {
      modal.error('Erro ao estornar', err.response?.data?.detail || 'Não foi possível estornar.');
    }
  };

  // ✅ Exportar histórico para CSV
  const handleExportarHistorico = () => {
    if (pagamentosFiltrados.length === 0) {
      modal.error('Nada para exportar', 'Não há pagamentos para exportar com os filtros atuais.');
      return;
    }
    const header = ['Data', 'Cliente', 'Telefone', 'Parcela', 'Valor Pago', 'Método', 'Tipo', 'Observações'];
    const rows = pagamentosFiltrados.map(p => [
      formatarDataHora(p.data_pagamento),
      p.cliente_nome || '',
      p.cliente_telefone || '',
      `${p.numero_parcela || '-'}/${p.total_parcelas || '-'}`,
      (p.valor_pago || 0).toFixed(2).replace('.', ','),
      (p.metodo_pagamento || '').toUpperCase(),
      p.tipo === 'amortizacao' ? 'Amortização' : 'Pagamento',
      (p.observacoes || '').replace(/[\r\n,;]/g, ' '),
    ]);
    const csv = [header, ...rows].map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(';')).join('\n');
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

  const pagamentosFiltrados = pagamentos.filter(pag => {
    if (filtroMetodo && pag.metodo_pagamento !== filtroMetodo) return false;
    if (filtroClienteHistorico) {
      const busca = filtroClienteHistorico.toLowerCase();
      const nomeMatch = pag.cliente_nome?.toLowerCase().includes(busca);
      if (!nomeMatch) return false;
    }
    if (filtroData) {
      const dataPag = new Date(pag.data_pagamento);
      // Comparar apenas a data (sem hora)
      if (dataPag.toDateString() !== filtroData.toDateString()) return false;
    }
    return true;
  });

  const totalPagamentos = pagamentosFiltrados.reduce((sum, pag) => sum + pag.valor_pago, 0);
  // ✅ FIX: Total Pendente agora considera multa + juros de mora
  const totalPendente = parcelasPendentes.reduce(
    (sum, p) => sum + (p.valor_total - p.valor_pago + (p.valor_multa || 0) + (p.valor_juros_mora || 0)),
    0
  );
  const parcelasAtrasadas = parcelasPendentes.filter(p => p.status === 'atrasado');
  const totalAtrasado = parcelasAtrasadas.reduce(
    (sum, p) => sum + (p.valor_total - p.valor_pago + (p.valor_multa || 0) + (p.valor_juros_mora || 0)),
    0
  );

  // Aplicar filtros nas parcelas pendentes
  const parcelasFiltradas = parcelasPendentes.filter(parcela => {
    // Filtro por status
    if (filtroStatus !== 'todos' && parcela.status !== filtroStatus) {
      return false;
    }
    
    // Filtro por cliente (nome ou telefone)
    if (filtroCliente) {
      const busca = filtroCliente.toLowerCase();
      const nomeMatch = parcela.cliente_nome?.toLowerCase().includes(busca);
      const telefoneMatch = parcela.cliente_telefone?.includes(filtroCliente);
      if (!nomeMatch && !telefoneMatch) {
        return false;
      }
    }
    
    return true;
  });

  // Ordenar parcelas filtradas
  const parcelasOrdenadas = [...parcelasFiltradas].sort((a, b) => {
    switch (filtroOrdenacao) {
      case 'vencimento':
        return new Date(a.data_vencimento) - new Date(b.data_vencimento);
      case 'valor':
        return (b.valor_total - b.valor_pago) - (a.valor_total - a.valor_pago);
      case 'cliente':
        return (a.cliente_nome || '').localeCompare(b.cliente_nome || '');
      case 'dias_atraso':
        return (b.dias_atraso || 0) - (a.dias_atraso || 0);
      default:
        return 0;
    }
  });

  // Agrupar por cliente com useMemo para performance
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
          parcelas_atrasadas: 0
        };
      }
      
      // Agrupar por empréstimo dentro do cliente
      const eid = parcela.emprestimo_id;
      if (!acc[cid].emprestimos[eid]) {
        acc[cid].emprestimos[eid] = {
          emprestimo_id: eid,
          parcelas: [],
          total_devido_emp: 0,
          parcelas_atrasadas_emp: 0
        };
      }
      
      acc[cid].emprestimos[eid].parcelas.push(parcela);
      const valorDevido = parcela.valor_total - parcela.valor_pago + (parcela.valor_multa || 0) + (parcela.valor_juros_mora || 0);
      acc[cid].emprestimos[eid].total_devido_emp += valorDevido;
      acc[cid].total_devido += valorDevido;
      acc[cid].total_parcelas++;
      
      if (parcela.status === 'atrasado') {
        acc[cid].emprestimos[eid].parcelas_atrasadas_emp++;
        acc[cid].parcelas_atrasadas++;
      }
      
      return acc;
    }, {});
    
    return Object.values(gruposCliente).map(cliente => ({
      ...cliente,
      emprestimos: Object.values(cliente.emprestimos).sort((a, b) => 
        b.parcelas_atrasadas_emp - a.parcelas_atrasadas_emp || b.total_devido_emp - a.total_devido_emp
      )
    })).sort((a, b) => 
      b.parcelas_atrasadas - a.parcelas_atrasadas || b.total_devido - a.total_devido
    );
  }, [parcelasOrdenadas]);

  if (loading) return <Loading message="Carregando pagamentos..." />;

  return (
    <Layout>
      {/* Overlay de Loading ao enviar WhatsApp */}
      {enviandoWhatsApp && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-card rounded-lg p-8 shadow-2xl border border-border max-w-sm mx-4">
            <div className="flex flex-col items-center gap-4">
              <div className="relative">
                <div className="w-16 h-16 border-4 border-primary/30 border-t-primary rounded-full animate-spin"></div>
                <div className="absolute inset-0 flex items-center justify-center">
                  <MessageCircle className="w-8 h-8 text-primary animate-pulse" />
                </div>
              </div>
              <div className="text-center">
                <h3 className="text-lg font-semibold text-foreground mb-2">
                  Enviando mensagem...
                </h3>
                <p className="text-sm text-muted-foreground">
                  Aguarde enquanto enviamos a mensagem via WhatsApp
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground" data-testid="pagamentos-title">
            Pagamentos
          </h1>
          <p className="text-muted-foreground mt-1">Gerencie pagamentos e parcelas pendentes</p>
        </div>

        {error && <ErrorMessage message={error} onRetry={carregarDados} />}

        {/* Cards de Resumo */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-card rounded-lg border border-border p-4" data-testid="total-recebido-card">
            <p className="text-sm text-muted-foreground mb-1">Total Recebido</p>
            <p className="text-2xl font-bold text-emerald-500">{formatarMoeda(totalPagamentos)}</p>
            <p className="text-xs text-muted-foreground mt-1">{pagamentos.length} pagamentos</p>
          </div>
          <div className="bg-card rounded-lg border border-border p-4" data-testid="total-pendente-card">
            <p className="text-sm text-muted-foreground mb-1">Total a Receber</p>
            <p className="text-2xl font-bold text-blue-500">{formatarMoeda(totalPendente)}</p>
            <p className="text-xs text-muted-foreground mt-1">{parcelasPendentes.length} parcelas (c/ multa+mora)</p>
          </div>
          <div className="bg-card rounded-lg border border-border p-4" data-testid="atrasadas-card">
            <p className="text-sm text-muted-foreground mb-1">Em Atraso (valor)</p>
            <p className={`text-2xl font-bold ${totalAtrasado > 0 ? 'text-red-500' : 'text-foreground'}`}>
              {formatarMoeda(totalAtrasado)}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {parcelasAtrasadas.length} parcela{parcelasAtrasadas.length === 1 ? '' : 's'} atrasada{parcelasAtrasadas.length === 1 ? '' : 's'}
            </p>
          </div>
          <div className="bg-card rounded-lg border border-border p-4" data-testid="taxa-recebimento-card">
            <p className="text-sm text-muted-foreground mb-1">Taxa de Recebimento</p>
            <p className="text-2xl font-bold text-foreground">
              {totalPagamentos + totalPendente > 0
                ? `${((totalPagamentos / (totalPagamentos + totalPendente)) * 100).toFixed(1)}%`
                : '—'}
            </p>
            <p className="text-xs text-muted-foreground mt-1">recebido / total</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-card rounded-lg border border-border overflow-hidden mb-6">
          <div className="flex border-b border-border">
            <button
              onClick={() => setActiveTab('pendentes')}
              className={`flex-1 px-6 py-4 text-center font-medium transition ${activeTab === 'pendentes'
                  ? 'bg-primary/10 text-primary border-b-2 border-primary'
                  : 'text-muted-foreground hover:bg-muted/50'
                }`}
              data-testid="tab-pendentes"
            >
              Parcelas Pendentes ({parcelasPendentes.length})
            </button>
            <button
              onClick={() => setActiveTab('historico')}
              className={`flex-1 px-6 py-4 text-center font-medium transition ${activeTab === 'historico'
                  ? 'bg-primary/10 text-primary border-b-2 border-primary'
                  : 'text-muted-foreground hover:bg-muted/50'
                }`}
              data-testid="tab-historico"
            >
              Histórico de Pagamentos ({pagamentos.length})
            </button>
          </div>
        </div>

        {/* Tab: Parcelas Pendentes */}
        {activeTab === 'pendentes' && (
          <div className="bg-card rounded-lg border border-border" data-testid="parcelas-pendentes-table">
            
            {/* Barra de Filtros */}
            <div className="border-b border-border bg-muted/30 p-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {/* Filtro por Status */}
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-2">
                    Status
                  </label>
                  <select
                    value={filtroStatus}
                    onChange={(e) => setFiltroStatus(e.target.value)}
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="todos">📋 Todos</option>
                    <option value="atrasado">⚠️ Atrasadas ({parcelasPendentes.filter(p => p.status === 'atrasado').length})</option>
                    <option value="pendente">📅 Pendentes ({parcelasPendentes.filter(p => p.status === 'pendente').length})</option>
                    <option value="parcial">⏳ Parciais ({parcelasPendentes.filter(p => p.status === 'parcial').length})</option>
                  </select>
                </div>

                {/* Filtro por Cliente */}
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-2">
                    Buscar Cliente
                  </label>
                  <input
                    type="text"
                    value={filtroCliente}
                    onChange={(e) => setFiltroCliente(e.target.value)}
                    placeholder="Nome ou telefone..."
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>

                {/* Ordenar por */}
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-2">
                    Ordenar por
                  </label>
                  <select
                    value={filtroOrdenacao}
                    onChange={(e) => setFiltroOrdenacao(e.target.value)}
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="vencimento">📅 Vencimento</option>
                    <option value="valor">💰 Maior Valor</option>
                    <option value="cliente">👤 Nome do Cliente</option>
                    <option value="dias_atraso">⚠️ Dias de Atraso</option>
                  </select>
                </div>

                {/* Botão Limpar Filtros */}
                <div className="flex items-end">
                  <button
                    onClick={() => {
                      setFiltroStatus('todos');
                      setFiltroCliente('');
                      setFiltroOrdenacao('vencimento');
                    }}
                    className="w-full px-4 py-2 bg-muted hover:bg-muted/80 text-foreground rounded-md text-sm font-medium transition-colors"
                  >
                    🔄 Limpar Filtros
                  </button>
                </div>
              </div>

              {/* Contador de Resultados */}
              <div className="mt-3 pt-3 border-t border-border">
                <p className="text-xs text-muted-foreground">
                  Mostrando <span className="font-semibold text-foreground">
                    {parcelasOrdenadas.length}
                  </span> de <span className="font-semibold text-foreground">{parcelasPendentes.length}</span> parcelas
                  <span className="ml-2">
                    ({clientesComParcelas.length} {clientesComParcelas.length === 1 ? 'cliente' : 'clientes'})
                  </span>
                </p>
              </div>
            </div>

            {/* Barra de Ações em Massa */}
            {parcelasOrdenadas.length > 0 && (
              <div
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 sm:p-4 bg-muted/40 border-b border-border"
                data-testid="acoes-em-massa-bar"
              >
                <div className="flex items-center gap-3">
                  <button
                    onClick={toggleSelecionarTodas}
                    className="flex items-center gap-2 text-sm font-medium text-foreground hover:text-primary transition-colors"
                    data-testid="btn-selecionar-todas"
                  >
                    {parcelasSelecionadas.size > 0 && parcelasSelecionadas.size === parcelasOrdenadas.length ? (
                      <CheckSquare className="w-5 h-5 text-primary" />
                    ) : (
                      <Square className="w-5 h-5 text-muted-foreground" />
                    )}
                    {parcelasSelecionadas.size > 0
                      ? `${parcelasSelecionadas.size} selecionada${parcelasSelecionadas.size === 1 ? '' : 's'}`
                      : 'Selecionar todas'}
                  </button>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    onClick={handleCobrarEmMassa}
                    disabled={parcelasSelecionadas.size === 0 || cobrandoEmMassa}
                    variant="primary"
                    testId="btn-cobrar-em-massa"
                  >
                    <MessageCircle className="w-4 h-4 mr-2" />
                    {cobrandoEmMassa ? 'Enviando...' : `Cobrar via WhatsApp${parcelasSelecionadas.size > 0 ? ` (${parcelasSelecionadas.size})` : ''}`}
                  </Button>
                </div>
              </div>
            )}

            {parcelasPendentes.length === 0 ? (
              <div className="p-8 text-center" data-testid="sem-parcelas-message">
                <p className="text-muted-foreground">Nenhuma parcela pendente</p>
              </div>
            ) : (
              /* VISUALIZAÇÃO AGRUPADA - SEMPRE */
              <div className="divide-y divide-border">
                {clientesComParcelas.map((cliente) => (
                  <div key={cliente.cliente_id} className="px-4 sm:px-6 py-4 hover:bg-muted/30 transition-colors">
                    {/* Header do Cliente */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                      <div className="flex items-center gap-3 sm:gap-4 flex-1 min-w-0">
                        <div className="h-10 w-10 sm:h-12 sm:w-12 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                          <span className="text-primary font-bold text-base sm:text-lg">
                            {cliente.cliente_nome?.charAt(0).toUpperCase() || '?'}
                          </span>
                        </div>
                        
                        <div className="flex-1 min-w-0">
                          <h3 className="text-sm sm:text-base font-semibold text-foreground truncate">{cliente.cliente_nome}</h3>
                          <p className="text-xs sm:text-sm text-muted-foreground truncate">{cliente.cliente_telefone}</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center justify-between sm:justify-end gap-3 sm:gap-4 flex-wrap">
                        <div className="text-left sm:text-right">
                          <div className="text-xs text-muted-foreground">Total Devido</div>
                          <div className="text-base sm:text-lg font-bold text-foreground">{formatarMoeda(cliente.total_devido)}</div>
                        </div>
                        
                        <div className="flex flex-wrap gap-1">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-500/10 text-blue-500 whitespace-nowrap">
                            {cliente.total_parcelas} {cliente.total_parcelas === 1 ? 'parcela' : 'parcelas'}
                          </span>
                          {cliente.emprestimos.length > 1 && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-500/10 text-purple-500 whitespace-nowrap">
                              {cliente.emprestimos.length} empréstimos
                            </span>
                          )}
                          {cliente.parcelas_atrasadas > 0 && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-500/10 text-red-500 whitespace-nowrap">
                              ⚠️ {cliente.parcelas_atrasadas}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    {/* Empréstimos do Cliente */}
                    <div className="ml-0 sm:ml-16 space-y-4">
                      {cliente.emprestimos.map((emprestimo, empIdx) => {
                        const empKey = `${cliente.cliente_id}-${emprestimo.emprestimo_id}`;
                        const isExpanded = expandedClientes.has(empKey);
                        const parcelaMaisUrgente = emprestimo.parcelas.reduce((prev, curr) => 
                          curr.status === 'atrasado' ? curr : 
                          (prev.status !== 'atrasado' && new Date(curr.data_vencimento) < new Date(prev.data_vencimento)) ? curr : prev
                        );
                        const parcelasRestantes = emprestimo.parcelas.filter(p => p.id !== parcelaMaisUrgente.id);
                        
                        return (
                          <div key={empKey} className="border-l-2 border-primary/20 pl-3 sm:pl-4">
                            {/* Header do Empréstimo (se houver mais de 1) */}
                            {cliente.emprestimos.length > 1 && (
                              <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 mb-2 text-xs text-muted-foreground">
                                <span className="font-medium">Empréstimo {empIdx + 1}</span>
                                <span className="hidden sm:inline">•</span>
                                <span>{formatarMoeda(emprestimo.total_devido_emp)}</span>
                                <span className="hidden sm:inline">•</span>
                                <span>{emprestimo.parcelas.length} {emprestimo.parcelas.length === 1 ? 'parcela' : 'parcelas'}</span>
                                {emprestimo.parcelas_atrasadas_emp > 0 && (
                                  <>
                                    <span className="hidden sm:inline">•</span>
                                    <span className="text-red-500 font-medium">{emprestimo.parcelas_atrasadas_emp} atrasada{emprestimo.parcelas_atrasadas_emp > 1 ? 's' : ''}</span>
                                  </>
                                )}
                              </div>
                            )}
                            
                            {/* Parcela mais urgente */}
                            <div className="space-y-2">
                              <ParcelaRow 
                                parcela={parcelaMaisUrgente}
                                handleRegistrarPagamento={handleRegistrarPagamento}
                                handleEnviarWhatsApp={handleEnviarWhatsApp}
                                handleExcluirParcela={handleExcluirParcela}
                                menuAbertoId={menuAbertoId}
                                setMenuAbertoId={setMenuAbertoId}
                                formatarData={formatarData}
                                formatarMoeda={formatarMoeda}
                                selecionavel={true}
                                selecionada={parcelasSelecionadas.has(parcelaMaisUrgente.id)}
                                onToggleSelecionar={toggleSelecionarParcela}
                              />
                              
                              {/* Parcelas restantes */}
                              {isExpanded && parcelasRestantes.map(parcela => (
                                <ParcelaRow 
                                  key={parcela.id}
                                  parcela={parcela}
                                  handleRegistrarPagamento={handleRegistrarPagamento}
                                  handleEnviarWhatsApp={handleEnviarWhatsApp}
                                  handleExcluirParcela={handleExcluirParcela}
                                  menuAbertoId={menuAbertoId}
                                  setMenuAbertoId={setMenuAbertoId}
                                  formatarData={formatarData}
                                  formatarMoeda={formatarMoeda}
                                  selecionavel={true}
                                  selecionada={parcelasSelecionadas.has(parcela.id)}
                                  onToggleSelecionar={toggleSelecionarParcela}
                                />
                              ))}
                              
                              {/* Botão Ver Mais */}
                              {parcelasRestantes.length > 0 && (
                                <button
                                  onClick={() => toggleClienteExpanded(empKey)}
                                  className="w-full py-2.5 sm:py-2 text-sm font-medium text-primary hover:bg-primary/5 rounded-md transition-colors flex items-center justify-center gap-2 min-h-[44px]"
                                >
                                  {isExpanded 
                                    ? <><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" /></svg> <span className="hidden sm:inline">Ocultar</span> {parcelasRestantes.length} {parcelasRestantes.length === 1 ? 'parcela' : 'parcelas'}</>
                                    : <><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg> <span className="hidden sm:inline">Ver mais</span> {parcelasRestantes.length} {parcelasRestantes.length === 1 ? 'parcela' : 'parcelas'}</>
                                  }
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab: Histórico */}
        {activeTab === 'historico' && (
          <>
            {/* Filtros */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-card rounded-lg border border-border p-4">
                <label className="block text-sm font-medium text-foreground mb-2">Método</label>
                <select
                  value={filtroMetodo}
                  onChange={(e) => setFiltroMetodo(e.target.value)}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  data-testid="filtro-metodo"
                >
                  <option value="">Todos</option>
                  <option value="pix">PIX</option>
                  <option value="transferencia">Transferência</option>
                  <option value="dinheiro">Dinheiro</option>
                  <option value="cartao">Cartão</option>
                  <option value="boleto">Boleto</option>
                </select>
              </div>
              <div className="bg-card rounded-lg border border-border p-4">
                <label className="block text-sm font-medium text-foreground mb-2">Cliente</label>
                <input
                  type="text"
                  value={filtroClienteHistorico}
                  onChange={(e) => setFiltroClienteHistorico(e.target.value)}
                  placeholder="Nome do cliente..."
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  data-testid="filtro-cliente-historico"
                />
              </div>
              <div className="bg-card rounded-lg border border-border p-4">
                <label className="block text-sm font-medium text-foreground mb-2">Data</label>
                <DatePickerBR
                  value={filtroData}
                  onChange={setFiltroData}
                  placeholder="Selecione uma data"
                  testId="filtro-data"
                  clearable={true}
                />
              </div>
              <div className="bg-card rounded-lg border border-border p-4 flex items-end gap-2">
                <button
                  onClick={() => { setFiltroMetodo(''); setFiltroData(null); setFiltroClienteHistorico(''); }}
                  className="flex-1 px-4 py-2 bg-muted hover:bg-muted/80 text-foreground rounded-md text-sm font-medium transition"
                  data-testid="limpar-filtros-button"
                >
                  Limpar
                </button>
                <button
                  onClick={handleExportarHistorico}
                  className="flex-1 px-4 py-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 rounded-md text-sm font-medium transition inline-flex items-center justify-center gap-1"
                  data-testid="btn-exportar-csv"
                  title="Exportar histórico em CSV"
                >
                  <Download className="w-4 h-4" />
                  CSV
                </button>
              </div>
            </div>

            {/* Tabela de Histórico */}
            <div className="bg-card rounded-lg border border-border overflow-hidden" data-testid="pagamentos-table">
              {pagamentosFiltrados.length === 0 ? (
                <div className="p-8 text-center" data-testid="sem-pagamentos-message">
                  <p className="text-muted-foreground">Nenhum pagamento encontrado</p>
                </div>
              ) : (
                <>
                  {/* Versão Desktop - Tabela Melhorada */}
                  <div className="hidden md:block overflow-x-auto">
                    <table className="min-w-full divide-y divide-border">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Cliente / Empréstimo</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Parcela</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Data/Hora</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Valor Pago</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Método</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Observações</th>
                          <th className="px-6 py-3 text-center text-xs font-medium text-muted-foreground uppercase tracking-wider">Ações</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border bg-card" data-testid="pagamentos-table-body">
                        {pagamentosFiltrados.map((pagamento) => (
                          <tr key={pagamento.id} data-testid={`pagamento-row-${pagamento.id}`} className="hover:bg-muted/30 transition-colors">
                            <td className="px-6 py-4">
                              <div className="flex items-start space-x-3">
                                <div className="flex-shrink-0">
                                  <div className="h-10 w-10 rounded-full bg-emerald-500/10 flex items-center justify-center ring-2 ring-emerald-500/20">
                                    <span className="text-emerald-600 font-semibold text-sm">
                                      {pagamento.cliente_nome ? pagamento.cliente_nome.charAt(0).toUpperCase() : '?'}
                                    </span>
                                  </div>
                                </div>
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm font-semibold text-foreground truncate">
                                    {pagamento.cliente_nome || 'Cliente não encontrado'}
                                  </p>
                                  <p className="text-xs text-muted-foreground mt-0.5">
                                    {pagamento.cliente_telefone || 'Telefone não informado'}
                                  </p>
                                  <div className="mt-1.5 flex items-center gap-2 flex-wrap">
                                    <span className="inline-flex items-center text-xs text-muted-foreground">
                                      <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                        <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4z"/>
                                        <path fillRule="evenodd" d="M18 9H2v5a2 2 0 002 2h12a2 2 0 002-2V9zM4 13a1 1 0 011-1h1a1 1 0 110 2H5a1 1 0 01-1-1zm5-1a1 1 0 100 2h1a1 1 0 100-2H9z" clipRule="evenodd"/>
                                      </svg>
                                      Empréstimo: {formatarMoeda(pagamento.valor_emprestimo || 0)}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm font-medium text-foreground">
                                {pagamento.numero_parcela || '-'}/{pagamento.total_parcelas ? pagamento.total_parcelas : '∞'}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {pagamento.total_parcelas ? 'Parcela' : 'Empréstimo Aberto'}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-foreground">
                                {formatarDataHora(pagamento.data_pagamento)}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="flex items-center">
                                <svg className="w-4 h-4 text-emerald-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
                                </svg>
                                <span className="text-sm font-bold text-emerald-500">
                                  {formatarMoeda(pagamento.valor_pago)}
                                </span>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className="inline-flex items-center px-2.5 py-1 text-xs font-bold rounded-full bg-blue-500/20 text-blue-400 ring-1 ring-blue-500/30">
                                {pagamento.metodo_pagamento.toUpperCase()}
                              </span>
                              {pagamento.tipo === 'amortizacao' && (
                                <span className="ml-1 inline-flex items-center px-2 py-0.5 text-[10px] font-bold rounded-full bg-purple-500/20 text-purple-400 ring-1 ring-purple-500/30">
                                  AMORT.
                                </span>
                              )}
                            </td>
                            <td className="px-6 py-4">
                              <div className="text-sm text-muted-foreground max-w-xs truncate">
                                {pagamento.observacoes || '-'}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-center">
                              <div className="flex items-center justify-center gap-2">
                                <button
                                  onClick={() => handleEnviarConfirmacaoPagamento(pagamento)}
                                  className="inline-flex items-center gap-1.5 px-3 py-2 bg-green-500 hover:bg-green-600 text-white text-xs font-medium rounded-lg transition-colors"
                                  title="Enviar confirmação por WhatsApp"
                                  data-testid={`btn-confirmar-${pagamento.id}`}
                                >
                                  <MessageCircle className="w-3.5 h-3.5" />
                                  <span className="hidden lg:inline">Confirmar</span>
                                </button>
                                {pagamento.tipo !== 'amortizacao' && (
                                  <button
                                    onClick={() => handleEstornarPagamento(pagamento)}
                                    className="inline-flex items-center gap-1.5 px-3 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-600 dark:text-red-400 text-xs font-medium rounded-lg transition-colors"
                                    title="Estornar pagamento"
                                    data-testid={`btn-estornar-${pagamento.id}`}
                                  >
                                    <RotateCcw className="w-3.5 h-3.5" />
                                    <span className="hidden lg:inline">Estornar</span>
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Versão Mobile - Cards Melhorados */}
                  <div className="md:hidden divide-y divide-border">
                    {pagamentosFiltrados.map((pagamento) => (
                      <div key={pagamento.id} className="p-4 hover:bg-muted/30 transition-colors" data-testid={`pagamento-card-${pagamento.id}`}>
                        {/* Cabeçalho do Card */}
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-start space-x-3 flex-1">
                            <div className="flex-shrink-0">
                              <div className="h-12 w-12 rounded-full bg-emerald-500/10 flex items-center justify-center ring-2 ring-emerald-500/20">
                                <span className="text-emerald-600 font-bold text-lg">
                                  {pagamento.cliente_nome ? pagamento.cliente_nome.charAt(0).toUpperCase() : '?'}
                                </span>
                              </div>
                            </div>
                            <div className="flex-1 min-w-0">
                              <h3 className="font-bold text-foreground text-base truncate">
                                {pagamento.cliente_nome || 'Cliente não encontrado'}
                              </h3>
                              <p className="text-xs text-muted-foreground mt-0.5">
                                {pagamento.cliente_telefone || 'Telefone não informado'}
                              </p>
                              <div className="mt-1.5 flex gap-1 flex-wrap">
                                <span className="inline-flex items-center px-2 py-0.5 text-xs font-bold rounded-full bg-emerald-500/20 text-emerald-400">
                                  ✓ {pagamento.tipo === 'amortizacao' ? 'AMORT.' : 'PAGO'}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Informações do Empréstimo */}
                        <div className="bg-muted/30 rounded-lg p-3 mb-3 space-y-2">
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-muted-foreground flex items-center">
                              <svg className="w-3.5 h-3.5 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4z"/>
                                <path fillRule="evenodd" d="M18 9H2v5a2 2 0 002 2h12a2 2 0 002-2V9zM4 13a1 1 0 011-1h1a1 1 0 110 2H5a1 1 0 01-1-1zm5-1a1 1 0 100 2h1a1 1 0 100-2H9z" clipRule="evenodd"/>
                              </svg>
                              Empréstimo
                            </span>
                            <span className="font-semibold text-foreground">
                              {formatarMoeda(pagamento.valor_emprestimo || 0)}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-muted-foreground flex items-center">
                              <svg className="w-3.5 h-3.5 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd"/>
                              </svg>
                              Parcela Paga
                            </span>
                            <span className="font-semibold text-foreground">
                              {pagamento.numero_parcela || '-'}/{pagamento.total_parcelas || '?'}
                            </span>
                          </div>
                        </div>

                        {/* Detalhes do Pagamento */}
                        <div className="space-y-2.5 text-sm mb-3">
                          <div className="flex justify-between items-center">
                            <span className="text-muted-foreground font-medium">Data/Hora:</span>
                            <span className="text-foreground font-semibold">
                              {formatarDataHora(pagamento.data_pagamento)}
                            </span>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="text-muted-foreground font-medium">Método:</span>
                            <span className="inline-flex items-center px-2 py-0.5 text-xs font-bold rounded-full bg-blue-500/20 text-blue-400">
                              {pagamento.metodo_pagamento.toUpperCase()}
                            </span>
                          </div>
                          <div className="flex justify-between items-center pt-2 border-t border-border">
                            <span className="text-muted-foreground font-medium">Valor Pago:</span>
                            <div className="flex items-center">
                              <svg className="w-4 h-4 text-emerald-500 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
                              </svg>
                              <span className="font-bold text-emerald-500 text-lg">
                                {formatarMoeda(pagamento.valor_pago)}
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Observações */}
                        {pagamento.observacoes && (
                          <div className="mt-3 p-3 bg-muted/50 rounded-lg">
                            <p className="text-xs font-medium text-muted-foreground mb-1">Observações:</p>
                            <p className="text-sm text-foreground">{pagamento.observacoes}</p>
                          </div>
                        )}

                        {/* Ações Mobile */}
                        <div className="mt-3 grid grid-cols-2 gap-2">
                          <button
                            onClick={() => handleEnviarConfirmacaoPagamento(pagamento)}
                            className="inline-flex items-center justify-center gap-2 px-3 py-2 bg-green-500 hover:bg-green-600 text-white text-sm font-medium rounded-lg transition-colors"
                            data-testid={`btn-confirmar-mobile-${pagamento.id}`}
                          >
                            <MessageCircle className="w-4 h-4" />
                            Confirmar
                          </button>
                          {pagamento.tipo !== 'amortizacao' && (
                            <button
                              onClick={() => handleEstornarPagamento(pagamento)}
                              className="inline-flex items-center justify-center gap-2 px-3 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-600 dark:text-red-400 text-sm font-medium rounded-lg transition-colors"
                              data-testid={`btn-estornar-mobile-${pagamento.id}`}
                            >
                              <RotateCcw className="w-4 h-4" />
                              Estornar
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

      {/* Modal de Pagamento */}
      {showModal && parcelaSelecionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4" style={{ zIndex: 9999 }} data-testid="pagamento-modal">
          <div className="bg-card rounded-lg border border-border shadow-xl max-w-md w-full" style={{ position: 'relative', zIndex: 10000 }}>
            <div className="p-6">
              <h2 className="text-2xl font-bold text-foreground mb-6">Registrar Pagamento</h2>

              <div className="mb-4 p-4 bg-muted/50 rounded-lg">
                <p className="text-sm text-muted-foreground mb-1">
                  <strong className="text-foreground">Cliente:</strong> {parcelaSelecionada.cliente_nome}
                </p>
                <p className="text-sm text-muted-foreground mb-1">
                  <strong className="text-foreground">Parcela:</strong> {parcelaSelecionada.numero_parcela}
                </p>
                <p className="text-sm text-muted-foreground mb-2">
                  <strong className="text-foreground">Vencimento:</strong> {formatarData(parcelaSelecionada.data_vencimento)}
                </p>
                {parcelaSelecionada.dias_atraso > 0 && (
                  <p className="text-sm text-red-500 font-semibold mb-2">
                    {parcelaSelecionada.dias_atraso} dias de atraso
                  </p>
                )}
                <p className="text-lg font-bold text-foreground">
                  Total a pagar: {formatarMoeda(
                    parcelaSelecionada.valor_total -
                    parcelaSelecionada.valor_pago +
                    (parcelaSelecionada.valor_multa || 0) +
                    (parcelaSelecionada.valor_juros_mora || 0)
                  )}
                </p>
              </div>

              <form onSubmit={handleSubmitPagamento} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Valor Pago (R$) <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="number"
                    value={formPagamento.valor_pago}
                    onChange={(e) => setFormPagamento({ ...formPagamento, valor_pago: e.target.value })}
                    required
                    step="0.01"
                    min="0"
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    data-testid="input-valor-pago"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Método de Pagamento <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={formPagamento.metodo_pagamento}
                    onChange={(e) => setFormPagamento({ ...formPagamento, metodo_pagamento: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    data-testid="select-metodo-pagamento"
                  >
                    <option value="pix">PIX</option>
                    <option value="transferencia">Transferência Bancária</option>
                    <option value="dinheiro">Dinheiro</option>
                    <option value="cartao">Cartão</option>
                    <option value="boleto">Boleto</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Observações</label>
                  <textarea
                    value={formPagamento.observacoes}
                    onChange={(e) => setFormPagamento({ ...formPagamento, observacoes: e.target.value })}
                    rows="3"
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="Observações (opcional)"
                    data-testid="textarea-observacoes"
                  />
                </div>

                <div className="flex justify-end space-x-3 pt-4 border-t border-border">
                  <Button
                    type="button"
                    onClick={() => { setShowModal(false); setParcelaSelecionada(null); }}
                    variant="secondary"
                    testId="cancelar-button"
                  >
                    Cancelar
                  </Button>
                  <Button type="submit" variant="primary" testId="confirmar-pagamento-button">
                    Confirmar Pagamento
                  </Button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

export default Pagamentos;
