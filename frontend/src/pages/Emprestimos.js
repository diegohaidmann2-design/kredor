import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import ErrorMessage from '../components/ErrorMessage';
import Button from '../components/Button';
import { useModal } from '../components/Modal';
import { emprestimosAPI, clientesAPI, pagamentosAPI } from '../api/api';
import { formatarMoeda, formatarData, getStatusColor, getStatusLabel, getMetodoCalculoLabel, hojeISO } from '../utils/formatters';
import RestanteDoPagamento from '../components/pagamentos/RestanteDoPagamento';
import { Eye, DollarSign, Trash2, MoreVertical, Plus, Search, Filter, Pencil } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import useAutosave, { useUnsavedChangesWarning } from '../hooks/useAutosave';
import DraftRecovery, { SaveStatusBadge } from '../components/DraftRecovery';
import { getDraftTimestamp } from '../utils/storageUtils';
import NovoEmprestimoModal from '../components/emprestimos/NovoEmprestimoModal';
import EditarEmprestimoModal from '../components/emprestimos/EditarEmprestimoModal';
import DetalhesEmprestimoModal from '../components/emprestimos/DetalhesEmprestimoModal';
import PagamentosDoEmprestimo, { ResumoPagamentos, baixarReciboPagamento } from '../components/emprestimos/PagamentosDoEmprestimo';
import LixeiraEmprestimos from '../components/emprestimos/LixeiraEmprestimos';
import { toast } from '../hooks/use-toast';

const Emprestimos = ({ somenteQuitados = false }) => {
  const [emprestimos, setEmprestimos] = useState([]);
  const [emprestimosFiltrados, setEmprestimosFiltrados] = useState([]);
  const [termoBusca, setTermoBusca] = useState('');
  const [clientes, setClientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showNovoEmprestimo, setShowNovoEmprestimo] = useState(false);
  const [showEditarEmprestimo, setShowEditarEmprestimo] = useState(false);
  const [showDetalhes, setShowDetalhes] = useState(false);
  const [showLixeira, setShowLixeira] = useState(false);
  const [showDraftRecovery, setShowDraftRecovery] = useState(false);
  const [showProrrogarModal, setShowProrrogarModal] = useState(false);
  const [periodosProrrogacao, setPeriodosProrrogacao] = useState(1);
  const [previewProrrogacao, setPreviewProrrogacao] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [emprestimoSelecionado, setEmprestimoSelecionado] = useState(null);
  const [showAmortizarModalLista, setShowAmortizarModalLista] = useState(false);
  const [amortizarFormLista, setAmortizarFormLista] = useState({ valor_amortizacao: '', metodo_pagamento: 'pix', recalcular_juros: true, observacoes: '' });
  const [showIncorporarModalLista, setShowIncorporarModalLista] = useState(false);
  const [incorporarFormLista, setIncorporarFormLista] = useState({ valor_juros: '', baixar_parcelas: true, recalcular_juros: true, observacoes: '' });
  const [jurosEmAbertoLista, setJurosEmAbertoLista] = useState(0);
  const [showReceberModal, setShowReceberModal] = useState(false);
  const [receberParcelas, setReceberParcelas] = useState([]);
  const [receberForm, setReceberForm] = useState({ parcela_id: '', valor_pago: '', data_pagamento: hojeISO(), metodo_pagamento: 'pix', observacoes: '', quitar_ignorando_restante: false });
  const [submittingAcao, setSubmittingAcao] = useState(false);
  // Empréstimo com o histórico de pagamentos aberto na listagem (um por vez).
  const [historicoAberto, setHistoricoAberto] = useState(null);
  const alternarHistorico = (id) => setHistoricoAberto((atual) => (atual === id ? null : id));
  const buttonRefs = useRef({});
  const modal = useModal();
  const [formData, setFormData] = useState({
    cliente_id: '',
    valor_principal: '',
    taxa_juros_mensal: '',
    prazo_meses: '',
    metodo_calculo: 'tabela_price',
    periodo_carencia_meses: 0,
    taxa_multa_atraso: 2.0,
    taxa_juros_mora_diario: 0.033,
    periodicidade: 'mensal',
    taxa_juros_semanal: '',
    prazo_semanas: '',
    data_inicio: new Date().toISOString().split('T')[0],
    dia_vencimento: null
  });
  const navigate = useNavigate();
  const user = { role: 'admin', is_owner: true }; // Mock user for testing purposes

  // Sistema de autosave
  const autosave = useAutosave('emprestimo', formData, {
    enabled: showNovoEmprestimo,
    delay: 3000,
    encrypt: false,
  });

  // Aviso ao sair com dados não salvos
  useUnsavedChangesWarning(
    showNovoEmprestimo && autosave.hasUnsavedChanges,
    'Você tem um empréstimo em andamento. Deseja realmente sair?'
  );

  useEffect(() => {
    carregarDados();
  }, [somenteQuitados]); // ✅ Recarregar quando mudar entre ativos/quitados

  // Função para normalizar strings (remove acentos e case)
  const normalizeString = (str) => {
    if (!str || typeof str !== 'string') return '';
    return str
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();
  };

  // Aplicar filtro sempre que emprestimos ou termoBusca mudarem
  useEffect(() => {
    if (!termoBusca.trim()) {
      setEmprestimosFiltrados([...emprestimos]);
      return;
    }

    const termoNormalizado = normalizeString(termoBusca);
    const termoApenasNumeros = termoBusca.replace(/\D/g, '');
    
    const filtrados = emprestimos.filter(emprestimo => {
      // Buscar por nome do cliente
      const clienteNome = getClienteNome(emprestimo.cliente_id);
      const nomeNorm = normalizeString(clienteNome);
      
      // Buscar por valor (apenas números)
      const valorStr = emprestimo.valor_principal.toString().replace(/\D/g, '');
      
      // Buscar por status
      const statusNorm = normalizeString(getStatusLabel(emprestimo.status));
      
      // Buscar por método de cálculo
      const metodoNorm = normalizeString(getMetodoCalculoLabel(emprestimo.metodo_calculo));
      
      const matchNome = nomeNorm.includes(termoNormalizado);
      const matchValor = termoApenasNumeros && valorStr.includes(termoApenasNumeros);
      const matchStatus = statusNorm.includes(termoNormalizado);
      const matchMetodo = metodoNorm.includes(termoNormalizado);
      
      return matchNome || matchValor || matchStatus || matchMetodo;
    });

    setEmprestimosFiltrados([...filtrados]);
  }, [emprestimos, termoBusca, clientes]);

  // Verificar rascunho ao abrir modal
  useEffect(() => {
    if (showNovoEmprestimo && autosave.exists()) {
      setShowDraftRecovery(true);
    }
  }, [showNovoEmprestimo]);

  const carregarDados = async ({ silencioso = false } = {}) => {
    try {
      // Silencioso: a tela continua visível enquanto atualiza. Ligar o loading aqui trocava
      // a página inteira pelo "Carregando..." a cada ação concluída.
      if (!silencioso) setLoading(true);
      setError('');
      
      // ✅ Chamar API com filtro correto baseado na prop somenteQuitados
      const params = somenteQuitados 
        ? { status: 'quitado' } 
        : { excluir_quitados: true };
      
      const [emprestimosRes, clientesRes] = await Promise.all([
        emprestimosAPI.listar(params),
        clientesAPI.listar()
      ]);
      // A API agora retorna {items: [...], pagination: {...}}
      const empData = emprestimosRes.data;
      const cliData = clientesRes.data;
      const emprestimosData = empData.items || empData;
      setEmprestimos(emprestimosData);
      setEmprestimosFiltrados(emprestimosData); // Inicializa com todos os empréstimos
      setClientes(cliData.items || cliData);
    } catch (err) {
      console.error('Erro ao carregar dados:', err);
      setError('Não foi possível carregar os dados.');
    } finally {
      if (!silencioso) setLoading(false);
    }
  };

  // Função de busca de empréstimos
  const handleBusca = (termo) => {
    setTermoBusca(termo);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  // Funções de recuperação de rascunho
  const handleRecoverDraft = () => {
    const draft = autosave.restore();
    if (draft) {
      setFormData(draft);
      setShowDraftRecovery(false);
      modal.success('Rascunho Recuperado!', 'Seus dados foram restaurados.');
    }
  };

  const handleDiscardDraft = () => {
    autosave.clear();
    setShowDraftRecovery(false);
  };

  const handleClearDraft = () => {
    if (window.confirm('Deseja limpar o rascunho salvo?')) {
      autosave.clear();
      modal.success('Rascunho Limpo', 'O rascunho foi removido.');
    }
  };

  const resetForm = () => {
    setFormData({
      cliente_id: '',
      valor_principal: '',
      taxa_juros_mensal: '',
      prazo_meses: '',
      metodo_calculo: 'tabela_price',
      periodo_carencia_meses: 0,
      taxa_multa_atraso: 2.0,
      taxa_juros_mora_diario: 0.033,
      data_inicio: new Date().toISOString().split('T')[0]
    });
  };

  const getClienteNome = (clienteId) => {
    const cliente = clientes.find(c => c.id === clienteId);
    return cliente ? cliente.nome : 'N/A';
  };

  const getClienteTelefone = (clienteId) => {
    const cliente = clientes.find(c => c.id === clienteId);
    return cliente ? (cliente.telefone || '') : '';
  };

  // Taxa de juros para empréstimos sem prazo (Aberto): usa a taxa da periodicidade
  const getTaxaSemPrazoLabel = (emprestimo) => {
    const semanal = emprestimo.periodicidade === 'semanal';
    const taxa = semanal ? emprestimo.taxa_juros_semanal : emprestimo.taxa_juros_mensal;
    if (taxa === null || taxa === undefined || taxa === '') return null;
    return `${taxa}% / ${semanal ? 'sem' : 'mês'}`;
  };

  // Taxa/prazo para empréstimos COM prazo (null-safe para registros legados)
  const getTaxaComPrazoLabel = (emprestimo) => {
    const t = emprestimo.taxa_juros_mensal;
    const p = emprestimo.prazo_meses;
    const temTaxa = !(t === null || t === undefined || t === '');
    const temPrazo = !(p === null || p === undefined || p === '');
    if (!temTaxa && !temPrazo) return '—';
    return `${temTaxa ? `${t}%` : '—'} / ${temPrazo ? `${p}m` : '—'}`;
  };

  const baixarReciboQuitacao = async (emprestimo) => {
    try {
      const response = await emprestimosAPI.reciboQuitacao(emprestimo.id);
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `recibo_quitacao_${emprestimo.id.substring(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Erro ao gerar recibo de quitação:', err);
      modal.error('Erro', 'Não foi possível gerar o recibo de quitação.');
    }
  };

  const enviarReciboWhatsApp = (emprestimo) => {
    const nome = getClienteNome(emprestimo.cliente_id);
    const telefoneRaw = getClienteTelefone(emprestimo.cliente_id);
    const telefone = (telefoneRaw || '').replace(/\D/g, '');
    if (!telefone) {
      modal.info('Telefone não cadastrado', 'O cliente não possui telefone cadastrado para envio via WhatsApp.');
      return;
    }
    const telefoneIntl = telefone.startsWith('55') ? telefone : `55${telefone}`;
    const capital = formatarMoeda(emprestimo.valor_principal || 0);
    const total = formatarMoeda(emprestimo.valor_total_com_juros || emprestimo.valor_principal || 0);
    const contrato = emprestimo.id.substring(0, 8).toUpperCase();
    const mensagem =
      `✅ *RECIBO DE QUITAÇÃO*\n\n` +
      `Olá ${nome}! Confirmamos a *quitação total* do seu empréstimo.\n\n` +
      `📄 Contrato: #${contrato}\n` +
      `💰 Valor emprestado: ${capital}\n` +
      `💵 Valor total pago: ${total}\n\n` +
      `O empréstimo encontra-se *TOTALMENTE QUITADO*. Obrigado pela confiança! 🤝`;
    const link = `https://wa.me/${telefoneIntl}?text=${encodeURIComponent(mensagem)}`;
    window.open(link, '_blank', 'noopener,noreferrer');
  };

  const handleExcluir = (emprestimo) => {
    modal.confirm(
      'Excluir Empréstimo',
      `Tem certeza que deseja excluir o empréstimo de ${getClienteNome(emprestimo.cliente_id)}? Esta ação não pode ser desfeita.`,
      async () => {
        try {
          await emprestimosAPI.deletar(emprestimo.id);
          modal.success('Empréstimo Excluído', 'O empréstimo foi excluído com sucesso.');
          carregarDados({ silencioso: true });
        } catch (err) {
          modal.error('Erro', err.response?.data?.detail || 'Não foi possível excluir o empréstimo.');
        }
      }
    );
  };

  const handleQuitarEmprestimoAberto = async (emprestimo) => {
    modal.confirm(
      'Quitar Empréstimo Aberto',
      `Deseja quitar o empréstimo de ${getClienteNome(emprestimo.cliente_id)}? Será cobrado o capital + juros do período atual, as parcelas futuras serão canceladas e o empréstimo será encerrado.`,
      async () => {
        try {
          const response = await emprestimosAPI.quitarAberto(emprestimo.id);
          modal.success(
            'Empréstimo Quitado!',
            `Quitação registrada (parcela #${response.data.parcela_numero}). Valor total: R$ ${response.data.valor_total.toFixed(2)}.`
          );
          carregarDados({ silencioso: true });
        } catch (err) {
          modal.error('Erro', err.response?.data?.detail || 'Não foi possível gerar a parcela final.');
        }
      }
    );
  };

  const handleRegistrarPagamento = (emprestimoId) => {
    navigate(`/emprestimos/${emprestimoId}`);
  };

  const handleAbrirProrrogacao = (emprestimo) => {
    if (emprestimo.status !== 'ativo' && emprestimo.status !== 'inadimplente') {
      modal.info('Prorrogação Não Disponível', 'Apenas empréstimos ativos ou inadimplentes podem ser prorrogados.');
      return;
    }
    
    setEmprestimoSelecionado(emprestimo);
    setPeriodosProrrogacao(1);
    setShowProrrogarModal(true);
  };

  const handleProrrogar = async () => {
    if (!emprestimoSelecionado) return;
    
    if (periodosProrrogacao < 1) {
      modal.error('Erro', 'Quantidade de períodos deve ser maior que zero.');
      return;
    }
    
    try {
      const response = await emprestimosAPI.prorrogar(emprestimoSelecionado.id, periodosProrrogacao);
      
      setShowProrrogarModal(false);
      modal.success(
        'Empréstimo Prorrogado!',
        `${response.data.mensagem}. ${response.data.novas_parcelas_criadas.length} novas parcelas foram criadas.`
      );
      
      // Recarregar dados
      await carregarDados({ silencioso: true });
    } catch (err) {
      modal.error('Erro ao Prorrogar', err.response?.data?.detail || 'Não foi possível prorrogar o empréstimo. Tente novamente.');
    }
  };

  // Buscar prévia da prorrogação (debounce) quando o modal está aberto
  useEffect(() => {
    if (!showProrrogarModal || !emprestimoSelecionado || !periodosProrrogacao || periodosProrrogacao < 1) {
      setPreviewProrrogacao(null);
      return;
    }
    let cancelado = false;
    setLoadingPreview(true);
    const t = setTimeout(async () => {
      try {
        const resp = await emprestimosAPI.prorrogarPreview(emprestimoSelecionado.id, periodosProrrogacao);
        if (!cancelado) setPreviewProrrogacao(resp.data);
      } catch (err) {
        if (!cancelado) setPreviewProrrogacao({ erro: err.response?.data?.detail || 'Não foi possível calcular a prévia.' });
      } finally {
        if (!cancelado) setLoadingPreview(false);
      }
    }, 350);
    return () => { cancelado = true; clearTimeout(t); };
  }, [showProrrogarModal, emprestimoSelecionado, periodosProrrogacao]);

  // ==================== AMORTIZAR (lista) ====================
  const handleAbrirAmortizarLista = (emprestimo) => {
    if (!emprestimo.sem_prazo || emprestimo.status !== 'ativo') {
      modal.info('Indisponível', 'Amortização disponível apenas em empréstimos sem prazo (Apenas Juros) ativos.');
      return;
    }
    setEmprestimoSelecionado(emprestimo);
    setAmortizarFormLista({ valor_amortizacao: '', metodo_pagamento: 'pix', recalcular_juros: true, observacoes: '' });
    setShowAmortizarModalLista(true);
  };

  const handleAmortizarSubmitLista = async (e) => {
    e.preventDefault();
    if (!emprestimoSelecionado) return;
    const valor = parseFloat(amortizarFormLista.valor_amortizacao);
    if (!valor || valor <= 0) { modal.error('Erro', 'Informe um valor válido para amortizar.'); return; }
    if (valor > emprestimoSelecionado.valor_principal) { modal.error('Erro', 'O valor não pode ser maior que o capital atual.'); return; }
    setSubmittingAcao(true);
    try {
      const resp = await emprestimosAPI.amortizar(emprestimoSelecionado.id, {
        valor_amortizacao: valor,
        metodo_pagamento: amortizarFormLista.metodo_pagamento,
        recalcular_juros: amortizarFormLista.recalcular_juros,
        observacoes: amortizarFormLista.observacoes || null,
      });
      setShowAmortizarModalLista(false);
      const d = resp.data;
      modal.success('Amortização Registrada!', `Novo capital: ${formatarMoeda(d.principal_atual)}.` + (d.quitado ? ' Empréstimo quitado.' : ''));
      await carregarDados({ silencioso: true });
    } catch (err) {
      modal.error('Erro na Amortização', err.response?.data?.detail || 'Não foi possível amortizar o capital.');
    } finally { setSubmittingAcao(false); }
  };

  // ==================== INCORPORAR JUROS (lista) ====================
  const handleAbrirIncorporarLista = async (emprestimo) => {
    if (!emprestimo.sem_prazo || emprestimo.status !== 'ativo') {
      modal.info('Indisponível', 'Incorporação de juros disponível apenas em empréstimos sem prazo (Apenas Juros) ativos.');
      return;
    }
    setEmprestimoSelecionado(emprestimo);
    setIncorporarFormLista({ valor_juros: '', baixar_parcelas: true, recalcular_juros: true, observacoes: '' });
    setJurosEmAbertoLista(0);
    setShowIncorporarModalLista(true);
    try {
      const parcRes = await emprestimosAPI.listarParcelas(emprestimo.id);
      const parcelas = parcRes.data || [];
      const aberto = parcelas
        .filter(p => ['pendente', 'atrasado', 'parcial'].includes(p.status))
        .reduce((s, p) => s + Math.max((p.valor_total || 0) - (p.valor_pago || 0) + (p.valor_multa || 0) + (p.valor_juros_mora || 0), 0), 0);
      setJurosEmAbertoLista(aberto);
      setIncorporarFormLista(f => ({ ...f, valor_juros: aberto > 0 ? aberto.toFixed(2) : '' }));
    } catch (err) { /* mantém 0 */ }
  };

  const handleIncorporarSubmitLista = async (e) => {
    e.preventDefault();
    if (!emprestimoSelecionado) return;
    const valor = parseFloat(incorporarFormLista.valor_juros);
    if (!valor || valor <= 0) { modal.error('Erro', 'Informe um valor de juros válido para incorporar.'); return; }
    setSubmittingAcao(true);
    try {
      const resp = await emprestimosAPI.incorporarJuros(emprestimoSelecionado.id, {
        valor_juros: valor,
        baixar_parcelas: incorporarFormLista.baixar_parcelas,
        recalcular_juros: incorporarFormLista.recalcular_juros,
        observacoes: incorporarFormLista.observacoes || null,
      });
      setShowIncorporarModalLista(false);
      const d = resp.data;
      let msg = `Novo capital: ${formatarMoeda(d.principal_atual)}.`;
      if (d.parcelas_baixadas > 0) msg += ` ${d.parcelas_baixadas} parcela(s) baixada(s).`;
      modal.success('Juros Incorporados!', msg);
      await carregarDados({ silencioso: true });
    } catch (err) {
      modal.error('Erro na Incorporação', err.response?.data?.detail || 'Não foi possível incorporar os juros.');
    } finally { setSubmittingAcao(false); }
  };

  // ==================== RECEBER PAGAMENTO (total ou parcial) ====================
  const saldoParcela = (p) => Math.max((p.valor_total || 0) - (p.valor_pago || 0) + (p.valor_multa || 0) + (p.valor_juros_mora || 0), 0);

  const handleAbrirReceber = async (emprestimo) => {
    if (!['ativo', 'inadimplente'].includes(emprestimo.status)) {
      modal.info('Indisponível', 'Só é possível registrar pagamentos em empréstimos ativos ou inadimplentes.');
      return;
    }
    setEmprestimoSelecionado(emprestimo);
    try {
      const parcRes = await emprestimosAPI.listarParcelas(emprestimo.id);
      const abertas = (parcRes.data || [])
        .filter(p => ['pendente', 'atrasado', 'parcial'].includes(p.status))
        .sort((a, b) => a.numero_parcela - b.numero_parcela);
      if (abertas.length === 0) {
        modal.info('Sem parcelas em aberto', 'Este empréstimo não possui parcelas pendentes para receber.');
        return;
      }
      setReceberParcelas(abertas);
      const primeira = abertas[0];
      setReceberForm({ parcela_id: primeira.id, valor_pago: saldoParcela(primeira).toFixed(2), data_pagamento: hojeISO(), metodo_pagamento: 'pix', observacoes: '', quitar_ignorando_restante: false });
      setShowReceberModal(true);
    } catch (err) {
      modal.error('Erro', err.response?.data?.detail || 'Não foi possível carregar as parcelas do empréstimo.');
    }
  };

  const handleSelecionarParcelaReceber = (parcelaId) => {
    const p = receberParcelas.find(x => x.id === parcelaId);
    if (!p) return;
    setReceberForm(f => ({ ...f, parcela_id: parcelaId, valor_pago: saldoParcela(p).toFixed(2), quitar_ignorando_restante: false }));
  };

  const handleReceberSubmit = async (e) => {
    e.preventDefault();
    const parcela = receberParcelas.find(x => x.id === receberForm.parcela_id);
    if (!parcela) { modal.error('Erro', 'Selecione uma parcela.'); return; }
    const valor = parseFloat(receberForm.valor_pago);
    const saldo = saldoParcela(parcela);
    if (!valor || valor <= 0) { modal.error('Erro', 'Informe um valor válido.'); return; }
    if (valor > saldo + 0.001) { modal.error('Erro', `O valor não pode ser maior que o saldo da parcela (${formatarMoeda(saldo)}).`); return; }
    setSubmittingAcao(true);
    try {
      const { data: pagamentoRegistrado } = await pagamentosAPI.criar({
        parcela_id: parcela.id,
        valor_pago: valor,
        data_pagamento: receberForm.data_pagamento,
        metodo_pagamento: receberForm.metodo_pagamento,
        observacoes: receberForm.observacoes || null,
        quitar_ignorando_restante: receberForm.quitar_ignorando_restante,
      });
      setShowReceberModal(false);
      const restante = Math.max(saldo - valor, 0);
      // O recibo é opcional: só é gerado se o usuário pedir.
      modal.success('Pagamento Registrado!', restante > 0
        ? `Recebido ${formatarMoeda(valor)}. Saldo restante da parcela: ${formatarMoeda(restante)}.`
        : `Parcela quitada com ${formatarMoeda(valor)}.`, {
        confirmText: 'Baixar recibo (PDF)',
        cancelText: 'Fechar',
        onConfirm: async () => {
          try {
            await baixarReciboPagamento(pagamentoRegistrado.id);
          } catch (err) {
            modal.error('Erro no Recibo', 'O pagamento foi registrado, mas não foi possível gerar o recibo agora. Tente pelo histórico de pagamentos do empréstimo.');
          }
        },
        onCancel: () => {},
      });
      await carregarDados({ silencioso: true });
    } catch (err) {
      modal.error('Erro no Pagamento', err.response?.data?.detail || 'Não foi possível registrar o pagamento.');
    } finally { setSubmittingAcao(false); }
  };

  // Componente reutilizável do Dropdown Menu de Ações
  const renderAcoesMenu = (emprestimo) => (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition"
          title="Mais ações"
        >
          <MoreVertical className="w-4 h-4" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {emprestimo.status !== 'quitado' && (
          <DropdownMenuItem
            onClick={() => {
              setEmprestimoSelecionado(emprestimo);
              setShowEditarEmprestimo(true);
            }}
            className="flex items-center gap-3 cursor-pointer"
          >
            <Pencil className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium">Editar Empréstimo</span>
          </DropdownMenuItem>
        )}
        
        <DropdownMenuItem
          onClick={() => {
            setEmprestimoSelecionado(emprestimo);
            setShowDetalhes(true);
          }}
          className="flex items-center gap-3 cursor-pointer"
        >
          <Eye className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium">Ver Detalhes</span>
        </DropdownMenuItem>
        
        {/* Botão de Prorrogação (empréstimos ativos/inadimplentes) */}
        {(emprestimo.status === 'ativo' || emprestimo.status === 'inadimplente') && (
          <DropdownMenuItem
            onClick={() => handleAbrirProrrogacao(emprestimo)}
            className="flex items-center gap-3 cursor-pointer hover:bg-primary/10"
            data-testid="btn-prorrogar-menu"
          >
            <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm font-medium">Prorrogar Empréstimo</span>
          </DropdownMenuItem>
        )}

        {/* Receber Pagamento (total ou parcial) — empréstimos ativos/inadimplentes */}
        {(emprestimo.status === 'ativo' || emprestimo.status === 'inadimplente') && (
          <DropdownMenuItem
            onClick={() => handleAbrirReceber(emprestimo)}
            className="flex items-center gap-3 cursor-pointer hover:bg-emerald-500/10"
            data-testid="menu-receber-pagamento"
          >
            <DollarSign className="w-4 h-4 text-emerald-500" />
            <span className="text-sm font-medium">Receber Pagamento</span>
          </DropdownMenuItem>
        )}

        {emprestimo.sem_prazo && emprestimo.status === 'ativo' && (
          <DropdownMenuItem
            onClick={() => handleAbrirAmortizarLista(emprestimo)}
            className="flex items-center gap-3 cursor-pointer"
            data-testid="menu-amortizar"
          >
            <svg className="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
            <span className="text-sm font-medium">Amortizar Capital</span>
          </DropdownMenuItem>
        )}

        {emprestimo.sem_prazo && emprestimo.status === 'ativo' && (
          <DropdownMenuItem
            onClick={() => handleAbrirIncorporarLista(emprestimo)}
            className="flex items-center gap-3 cursor-pointer"
            data-testid="menu-incorporar"
          >
            <svg className="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
            </svg>
            <span className="text-sm font-medium">Incorporar Juros</span>
          </DropdownMenuItem>
        )}
        
        <DropdownMenuItem
          onClick={async () => {
            try {
              const response = await emprestimosAPI.compartilharPDF(emprestimo.id);
              const blob = new Blob([response.data], { type: 'application/pdf' });
              const url = window.URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `emprestimo_${emprestimo.id.substring(0,8)}.pdf`;
              document.body.appendChild(a);
              a.click();
              window.URL.revokeObjectURL(url);
              document.body.removeChild(a);
            } catch (err) {
              toast({ title: 'Erro', description: "Não foi possível gerar PDF.", variant: 'destructive' });
              console.error('Erro ao gerar PDF:', err);
            }
          }}
          className="flex items-center gap-3 cursor-pointer"
        >
          <svg className="w-4 h-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
          </svg>
          <span className="text-sm font-medium">Compartilhar PDF</span>
        </DropdownMenuItem>
        
        {emprestimo.sem_prazo && emprestimo.status === 'ativo' && (
          <DropdownMenuItem
            onClick={() => handleQuitarEmprestimoAberto(emprestimo)}
            className="flex items-center gap-3 cursor-pointer border-t"
          >
            <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm font-medium text-emerald-600">Quitar Empréstimo</span>
          </DropdownMenuItem>
        )}
        
        {emprestimo.status === 'quitado' && (
          <>
            <DropdownMenuItem
              onClick={() => baixarReciboQuitacao(emprestimo)}
              className="flex items-center gap-3 cursor-pointer border-t"
              data-testid="btn-recibo-quitacao-pdf"
            >
              <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="text-sm font-medium text-emerald-700">Recibo de Quitação (PDF)</span>
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => enviarReciboWhatsApp(emprestimo)}
              className="flex items-center gap-3 cursor-pointer"
              data-testid="btn-recibo-quitacao-whatsapp"
            >
              <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 24 24">
                <path d="M.057 24l1.687-6.163a11.867 11.867 0 01-1.587-5.946C.16 5.335 5.495 0 12.05 0a11.817 11.817 0 018.413 3.488 11.824 11.824 0 013.48 8.414c-.003 6.557-5.338 11.892-11.893 11.892a11.9 11.9 0 01-5.688-1.448L.057 24zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884a9.86 9.86 0 001.51 5.26l-.999 3.648 3.978-1.607zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z" />
              </svg>
              <span className="text-sm font-medium text-green-700">Enviar Recibo no WhatsApp</span>
            </DropdownMenuItem>
          </>
        )}

        {emprestimo.status !== 'quitado' && (
          <DropdownMenuItem
            onClick={() => handleExcluir(emprestimo)}
            className="flex items-center gap-3 cursor-pointer hover:bg-destructive/10"
          >
            <Trash2 className="w-4 h-4 text-destructive" />
            <span className="text-sm font-medium text-destructive">Excluir</span>
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );

  if (loading) return <Loading message="Carregando empréstimos..." />;

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-foreground" data-testid="emprestimos-title">
              {somenteQuitados ? 'Empréstimos Quitados' : 'Empréstimos Ativos'}
            </h1>
            <p className="text-muted-foreground mt-1 text-sm sm:base">
              {somenteQuitados ? 'Empréstimos que já foram totalmente pagos' : 'Gerencie empréstimos em andamento'}
            </p>
          </div>

          <div className="grid grid-cols-2 sm:flex gap-2 w-full sm:w-auto">
            {(user?.role === 'admin' || user?.is_owner) && (
              <Button
                variant="outline"
                className="gap-2 text-red-600 border-red-200 hover:bg-red-50 dark:hover:bg-red-900/20 text-xs sm:text-sm px-2 sm:px-4"
                onClick={() => setShowLixeira(true)}
              >
                <Trash2 className="h-4 w-4" />
                Lixeira
              </Button>
            )}

            <Button 
              onClick={() => setShowNovoEmprestimo(true)} 
              className="gap-2 text-xs sm:text-sm px-2 sm:px-4"
              data-testid="btn-novo-emprestimo"
            >
              <Plus className="h-4 w-4" />
              Novo Empréstimo
            </Button>
          </div>
        </div>

        {/* Filtros e Busca */}
        {error && <ErrorMessage message={error} onRetry={carregarDados} />}

        {/* Campo de Busca */}
        <div className="mb-4">
          <div className="relative max-w-md">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg 
                className="h-5 w-5 text-muted-foreground" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" 
                />
              </svg>
            </div>
            <input
              type="text"
              value={termoBusca}
              onChange={(e) => handleBusca(e.target.value)}
              placeholder="Buscar por cliente, valor, status ou método..."
              className="w-full pl-10 pr-4 py-2.5 bg-background border border-input rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
              data-testid="buscar-emprestimo-input"
            />
            {termoBusca && (
              <button
                onClick={() => handleBusca('')}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-muted-foreground hover:text-foreground transition"
                title="Limpar busca"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
          {termoBusca && (
            <p className="text-sm text-muted-foreground mt-2">
              {emprestimosFiltrados.length === 0 
                ? 'Nenhum empréstimo encontrado' 
                : `${emprestimosFiltrados.length} empréstimo${emprestimosFiltrados.length !== 1 ? 's' : ''} encontrado${emprestimosFiltrados.length !== 1 ? 's' : ''}`
              }
            </p>
          )}
        </div>

        <div className="bg-card rounded-lg border border-border overflow-hidden" data-testid="emprestimos-table-container">
          {emprestimosFiltrados.length === 0 ? (
            <div className="p-8 text-center" data-testid="sem-emprestimos-message">
              <p className="text-muted-foreground">
                {termoBusca ? 'Nenhum empréstimo encontrado com os critérios de busca' : 'Nenhum empréstimo registrado'}
              </p>
            </div>
          ) : (
            <>
              {/* Versão Desktop - Tabela */}
              <div className="hidden md:block overflow-x-auto">
                <table className="min-w-full divide-y divide-border">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Cliente
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Valor Principal
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Total com Juros
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Taxa/Prazo
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Método
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Data Início
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider sticky right-0 bg-muted/50 z-10">
                        Ações
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border" data-testid="emprestimos-table-body">
                    {emprestimosFiltrados.map((emprestimo) => (
                      <React.Fragment key={emprestimo.id}>
                      <tr data-testid={`emprestimo-row-${emprestimo.id}`} className="hover:bg-muted/50">
                        <td className="px-4 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-foreground max-w-[200px] truncate" title={getClienteNome(emprestimo.cliente_id)}>
                            {getClienteNome(emprestimo.cliente_id)}
                          </div>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-foreground">
                          {formatarMoeda(emprestimo.valor_principal)}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap">
                          {emprestimo.sem_prazo ? (
                            <div className="flex flex-col">
                              <span className="text-sm font-semibold text-amber-600">
                                {formatarMoeda(emprestimo.valor_total_com_juros || emprestimo.valor_principal)} ⚡
                              </span>
                              <span className="text-xs text-muted-foreground">
                                Acumulado
                              </span>
                            </div>
                          ) : (
                            <span className="text-sm font-semibold text-emerald-500">
                              {formatarMoeda(emprestimo.valor_total_com_juros)}
                            </span>
                          )}
                          <ResumoPagamentos
                            emprestimo={emprestimo}
                            aberto={historicoAberto === emprestimo.id}
                            onToggle={() => alternarHistorico(emprestimo.id)}
                          />
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-muted-foreground">
                          {emprestimo.sem_prazo ? (
                            <div className="flex flex-col" data-testid={`taxa-prazo-${emprestimo.id}`}>
                              <span className="inline-flex items-center gap-1">
                                <span>🔄</span>
                                <span className="font-medium text-amber-600">Aberto</span>
                              </span>
                              {getTaxaSemPrazoLabel(emprestimo) && (
                                <span className="text-xs text-foreground" data-testid={`taxa-juros-${emprestimo.id}`}>
                                  {getTaxaSemPrazoLabel(emprestimo)}
                                </span>
                              )}
                            </div>
                          ) : (
                            <span data-testid={`taxa-prazo-${emprestimo.id}`}>{getTaxaComPrazoLabel(emprestimo)}</span>
                          )}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-muted-foreground">
                          {getMetodoCalculoLabel(emprestimo.metodo_calculo)}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-muted-foreground">
                          {formatarData(emprestimo.data_inicio)}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(emprestimo.status)}`}>
                            {getStatusLabel(emprestimo.status)}
                          </span>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap sticky right-0 bg-card z-10 border-l border-border">
                          <div className="flex items-center justify-end gap-2">
                            {/* Botão de Pagamento Rápido — oculto para quitados */}
                            {emprestimo.status !== 'quitado' && (
                              <button
                                onClick={() => handleRegistrarPagamento(emprestimo.id)}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium rounded-md transition-colors shadow-sm"
                                title="Registrar Pagamento"
                                data-testid={`btn-pagar-${emprestimo.id}`}
                              >
                                <DollarSign className="w-4 h-4" />
                                <span className="hidden sm:inline">Pagar</span>
                              </button>
                            )}

                            {/* Menu de Ações */}
                            {renderAcoesMenu(emprestimo)}
                          </div>
                        </td>
                      </tr>
                      {historicoAberto === emprestimo.id && (
                        <tr data-testid={`historico-row-${emprestimo.id}`} className="bg-muted/30">
                          <td colSpan={8} className="px-6 py-3">
                            <PagamentosDoEmprestimo
                              emprestimo={emprestimo}
                              clienteNome={getClienteNome(emprestimo.cliente_id)}
                              clienteTelefone={getClienteTelefone(emprestimo.cliente_id)}
                            />
                          </td>
                        </tr>
                      )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Versão Mobile - Cards */}
              <div className="md:hidden divide-y divide-border">
                {emprestimosFiltrados.map((emprestimo) => (
                  <div key={emprestimo.id} className="p-4 hover:bg-muted/50 transition-colors">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-semibold text-foreground text-base">
                          {getClienteNome(emprestimo.cliente_id)}
                        </h3>
                        <span className={`inline-flex mt-1 px-2 py-0.5 text-xs font-semibold rounded-full ${getStatusColor(emprestimo.status)}`}>
                          {getStatusLabel(emprestimo.status)}
                        </span>
                      </div>
                      <div className="flex gap-2">
                        {/* Botão de Pagamento Mobile — oculto para quitados */}
                        {emprestimo.status !== 'quitado' && (
                          <button
                            onClick={() => handleRegistrarPagamento(emprestimo.id)}
                            className="p-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg transition"
                            title="Registrar Pagamento"
                          >
                            <DollarSign className="w-4 h-4" />
                          </button>
                        )}
                        {renderAcoesMenu(emprestimo)}
                      </div>
                    </div>

                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Valor Principal:</span>
                        <span className="font-medium text-foreground">{formatarMoeda(emprestimo.valor_principal)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Total com Juros:</span>
                        {emprestimo.sem_prazo ? (
                          <div className="flex flex-col items-end">
                            <span className="font-semibold text-amber-600">
                              {formatarMoeda(emprestimo.valor_total_com_juros || emprestimo.valor_principal)} ⚡
                            </span>
                            <span className="text-xs text-muted-foreground">Acumulado</span>
                          </div>
                        ) : (
                          <span className="font-semibold text-emerald-500">{formatarMoeda(emprestimo.valor_total_com_juros)}</span>
                        )}
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Taxa/Prazo:</span>
                        {emprestimo.sem_prazo ? (
                          <div className="flex flex-col items-end">
                            <span className="inline-flex items-center gap-1">
                              <span>🔄</span>
                              <span className="font-medium text-amber-600">Aberto</span>
                            </span>
                            {getTaxaSemPrazoLabel(emprestimo) && (
                              <span className="text-xs text-foreground">{getTaxaSemPrazoLabel(emprestimo)}</span>
                            )}
                          </div>
                        ) : (
                          <span className="text-foreground">{getTaxaComPrazoLabel(emprestimo)}</span>
                        )}
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Método:</span>
                        <span className="text-foreground">{getMetodoCalculoLabel(emprestimo.metodo_calculo)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Data Início:</span>
                        <span className="text-foreground">{formatarData(emprestimo.data_inicio)}</span>
                      </div>
                    </div>

                    <ResumoPagamentos
                      variante="card"
                      emprestimo={emprestimo}
                      aberto={historicoAberto === emprestimo.id}
                      onToggle={() => alternarHistorico(emprestimo.id)}
                    />
                    {historicoAberto === emprestimo.id && (
                      <div className="mt-3 rounded-lg border border-border bg-muted/30 px-3 py-2">
                        <PagamentosDoEmprestimo
                          variante="card"
                          emprestimo={emprestimo}
                          clienteNome={getClienteNome(emprestimo.cliente_id)}
                          clienteTelefone={getClienteTelefone(emprestimo.cliente_id)}
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Modal de Criação */}
      <NovoEmprestimoModal
        open={showNovoEmprestimo}
        onOpenChange={setShowNovoEmprestimo}
        onSuccess={carregarDados}
        clientes={clientes}
        formData={formData}
        setFormData={setFormData}
        resetForm={resetForm}
        autosave={autosave}
        showDraftRecovery={showDraftRecovery}
        setShowDraftRecovery={setShowDraftRecovery}
        handleRecoverDraft={handleRecoverDraft}
        handleDiscardDraft={handleDiscardDraft}
        handleClearDraft={handleClearDraft}
      />

      {/* Modal de Recuperação de Rascunho */}
      <DraftRecovery
        isOpen={showDraftRecovery}
        onRecover={handleRecoverDraft}
        onDiscard={handleDiscardDraft}
        draftTimestamp={getDraftTimestamp('emprestimo')}
        title="Rascunho de Empréstimo Encontrado"
        description="Encontramos um empréstimo que você estava criando."
      />
      {emprestimoSelecionado && (
        <EditarEmprestimoModal
          open={showEditarEmprestimo}
          onOpenChange={setShowEditarEmprestimo}
          emprestimo={emprestimoSelecionado}
          onSuccess={carregarDados}
          clientes={clientes}
        />
      )}

      {emprestimoSelecionado && (
        <DetalhesEmprestimoModal
          open={showDetalhes}
          onOpenChange={setShowDetalhes}
          emprestimo={emprestimoSelecionado}
          onUpdate={carregarDados}
        />
      )}

      <LixeiraEmprestimos
        open={showLixeira}
        onOpenChange={setShowLixeira}
        onRestored={carregarDados}
      />

      {/* Modal de Prorrogação */}
      {showProrrogarModal && emprestimoSelecionado && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" data-testid="prorrogar-modal">
          <div className="bg-card rounded-lg border border-border shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h2 className="text-2xl font-bold text-foreground mb-4">
                Prorrogar Empréstimo
              </h2>
              
              <div className="mb-4 p-3 bg-muted/50 rounded-lg border border-border">
                <p className="text-sm text-muted-foreground mb-1">
                  <strong>Cliente:</strong> {getClienteNome(emprestimoSelecionado.cliente_id)}
                </p>
                <p className="text-sm text-muted-foreground">
                  <strong>Valor:</strong> {formatarMoeda(emprestimoSelecionado.valor_principal)}
                </p>
              </div>
              
              <div className="mb-6 p-4 bg-primary/10 rounded-lg border border-primary/20">
                <p className="text-sm text-muted-foreground mb-2">
                  <strong>Como funciona:</strong>
                </p>
                {emprestimoSelecionado.metodo_calculo === 'apenas_juros' ? (
                  <>
                    <p className="text-sm text-muted-foreground mb-2">
                      • A última parcela (com capital) vira parcela de juros
                    </p>
                    <p className="text-sm text-muted-foreground mb-2">
                      • Novas parcelas de juros são criadas
                    </p>
                    <p className="text-sm text-muted-foreground">
                      • Nova última parcela com capital é criada
                    </p>
                  </>
                ) : (
                  <>
                    <p className="text-sm text-muted-foreground mb-2">
                      • As parcelas já pagas são mantidas
                    </p>
                    <p className="text-sm text-muted-foreground mb-2">
                      • O saldo devedor é redistribuído nas parcelas em aberto + as novas
                    </p>
                    <p className="text-sm text-muted-foreground">
                      • O valor de cada parcela é recalculado ({getMetodoCalculoLabel(emprestimoSelecionado.metodo_calculo)})
                    </p>
                  </>
                )}
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-foreground mb-2">
                  Quantidade de {emprestimoSelecionado.periodicidade === 'semanal' ? 'semanas' : 'meses'} <span className="text-destructive">*</span>
                </label>
                <input
                  type="number"
                  value={periodosProrrogacao}
                  onChange={(e) => setPeriodosProrrogacao(parseInt(e.target.value) || 1)}
                  required
                  min="1"
                  max="12"
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  data-testid="input-periodos-prorrogacao"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Prorrogar por quantos {emprestimoSelecionado.periodicidade === 'semanal' ? 'semanas' : 'meses'}?
                </p>
              </div>

              {/* Prévia da prorrogação */}
              <div className="mb-6" data-testid="prorrogacao-preview">
                <h3 className="text-sm font-semibold text-foreground mb-2">Prévia do novo cronograma</h3>
                {loadingPreview && (
                  <p className="text-sm text-muted-foreground" data-testid="preview-loading">Calculando prévia…</p>
                )}
                {!loadingPreview && previewProrrogacao?.erro && (
                  <p className="text-sm text-destructive" data-testid="preview-erro">{previewProrrogacao.erro}</p>
                )}
                {!loadingPreview && previewProrrogacao && !previewProrrogacao.erro && (
                  <div className="rounded-lg border border-border overflow-hidden">
                    <div className="max-h-48 overflow-y-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-muted/50 sticky top-0">
                          <tr>
                            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Parcela</th>
                            <th className="text-left px-3 py-2 font-medium text-muted-foreground">Vencimento</th>
                            <th className="text-right px-3 py-2 font-medium text-muted-foreground">Valor</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border" data-testid="preview-parcelas">
                          {(previewProrrogacao.parcelas_preview || []).map((p) => (
                            <tr key={p.numero_parcela}>
                              <td className="px-3 py-1.5 text-foreground">#{p.numero_parcela}</td>
                              <td className="px-3 py-1.5 text-muted-foreground">{formatarData(p.data_vencimento)}</td>
                              <td className="px-3 py-1.5 text-right font-medium text-foreground">{formatarMoeda(p.valor_total)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="bg-primary/10 border-t border-primary/20 px-3 py-2 space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">Total de parcelas</span>
                        <span className="font-semibold text-foreground" data-testid="preview-total-parcelas">{previewProrrogacao.novo_total_parcelas}</span>
                      </div>
                      {previewProrrogacao.tipo === 'prazo_fixo' && (
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">Valor de cada nova parcela</span>
                          <span className="font-semibold text-foreground" data-testid="preview-valor-parcela">{formatarMoeda(previewProrrogacao.valor_parcela)}</span>
                        </div>
                      )}
                      {previewProrrogacao.novo_valor_total_com_juros != null && (
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">Novo total com juros</span>
                          <span className="font-semibold text-emerald-600" data-testid="preview-total-juros">{formatarMoeda(previewProrrogacao.novo_valor_total_com_juros)}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowProrrogarModal(false)}
                  className="flex-1"
                >
                  Cancelar
                </Button>
                <Button
                  onClick={handleProrrogar}
                  className="flex-1"
                  data-testid="confirmar-prorrogacao-btn"
                >
                  Confirmar Prorrogação
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Amortizar Capital (lista) */}
      {/* Modal Receber Pagamento (total ou parcial) */}
      {showReceberModal && emprestimoSelecionado && (() => {
        const parcelaSel = receberParcelas.find(x => x.id === receberForm.parcela_id);
        const saldo = parcelaSel ? saldoParcela(parcelaSel) : 0;
        const valorNum = parseFloat(receberForm.valor_pago) || 0;
        const restante = Math.max(saldo - valorNum, 0);
        return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" data-testid="receber-pagamento-modal">
          <div className="bg-card rounded-lg border border-border shadow-xl max-w-md w-full">
            <form onSubmit={handleReceberSubmit} className="p-6">
              <h2 className="text-2xl font-bold text-foreground mb-2">Receber Pagamento</h2>
              <p className="text-sm text-muted-foreground mb-6">Registre um pagamento total ou parcial. O saldo restante continua em aberto até o vencimento.</p>

              {receberParcelas.length > 1 && (
                <div className="mb-4">
                  <label className="block text-sm font-medium text-foreground mb-2">Parcela</label>
                  <select
                    value={receberForm.parcela_id}
                    onChange={(e) => handleSelecionarParcelaReceber(e.target.value)}
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    data-testid="receber-parcela-select"
                  >
                    {receberParcelas.map(p => (
                      <option key={p.id} value={p.id}>
                        Parcela {p.numero_parcela}{p.total_parcelas ? `/${p.total_parcelas}` : ''} — vence {formatarData(p.data_vencimento)} — saldo {formatarMoeda(saldoParcela(p))}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="mb-4 p-4 bg-muted/50 rounded-lg border border-border">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Saldo da parcela:</span>
                  <span className="font-semibold text-foreground" data-testid="receber-saldo-parcela">{formatarMoeda(saldo)}</span>
                </div>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-foreground mb-2">Valor recebido (R$) *</label>
                <input
                  type="number" step="0.01" min="0.01" max={saldo}
                  value={receberForm.valor_pago}
                  onChange={(e) => setReceberForm({ ...receberForm, valor_pago: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="Ex: 10000,00" required data-testid="receber-valor-input"
                />
                <p className="text-xs text-muted-foreground mt-1">Máximo: {formatarMoeda(saldo)}</p>
              </div>

              <div className="mb-4 p-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10" data-testid="receber-saldo-restante">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">{restante > 0 ? 'Saldo restante:' : 'Situação:'}</span>
                  <span className="font-bold text-emerald-500">{restante > 0 ? formatarMoeda(restante) : 'Parcela quitada'}</span>
                </div>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-foreground mb-2">Data do pagamento *</label>
                <input
                  type="date"
                  value={receberForm.data_pagamento}
                  onChange={(e) => setReceberForm({ ...receberForm, data_pagamento: e.target.value })}
                  required
                  max={hojeISO()}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  data-testid="receber-data-input"
                />
                <p className="text-xs text-muted-foreground mt-1">Dia em que o cliente pagou. Multa e mora são calculadas por esta data.</p>
              </div>

              <div className="mb-4">
                <RestanteDoPagamento
                  parcelaId={receberForm.parcela_id}
                  valorPago={receberForm.valor_pago}
                  dataPagamento={receberForm.data_pagamento}
                  ignorar={receberForm.quitar_ignorando_restante}
                  onChangeIgnorar={(v) => setReceberForm((f) => ({ ...f, quitar_ignorando_restante: v }))}
                />
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-foreground mb-2">Forma de pagamento</label>
                <select
                  value={receberForm.metodo_pagamento}
                  onChange={(e) => setReceberForm({ ...receberForm, metodo_pagamento: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  data-testid="receber-metodo-select"
                >
                  <option value="pix">PIX</option>
                  <option value="dinheiro">Dinheiro</option>
                  <option value="transferencia">Transferência</option>
                  <option value="cartao">Cartão</option>
                  <option value="boleto">Boleto</option>
                </select>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-foreground mb-2">Observações (opcional)</label>
                <textarea value={receberForm.observacoes}
                  onChange={(e) => setReceberForm({ ...receberForm, observacoes: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary" rows={2} />
              </div>

              <div className="flex gap-3">
                <Button type="button" variant="outline" onClick={() => setShowReceberModal(false)} className="flex-1" disabled={submittingAcao}>Cancelar</Button>
                <Button type="submit" className="flex-1" disabled={submittingAcao} testId="confirmar-receber-btn">
                  {submittingAcao ? 'Processando...' : 'Registrar pagamento'}
                </Button>
              </div>
            </form>
          </div>
        </div>
        );
      })()}

      {showAmortizarModalLista && emprestimoSelecionado && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" data-testid="amortizar-modal-lista">
          <div className="bg-card rounded-lg border border-border shadow-xl max-w-md w-full">
            <form onSubmit={handleAmortizarSubmitLista} className="p-6">
              <h2 className="text-2xl font-bold text-foreground mb-2">Amortizar Capital</h2>
              <p className="text-sm text-muted-foreground mb-6">Registre um pagamento parcial do capital. O empréstimo continua com o novo capital.</p>

              <div className="mb-4 p-4 bg-muted/50 rounded-lg border border-border">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Capital atual:</span>
                  <span className="font-semibold text-foreground">{formatarMoeda(emprestimoSelecionado.valor_principal)}</span>
                </div>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-foreground mb-2">Valor da amortização (R$) *</label>
                <input
                  type="number" step="0.01" min="0.01" max={emprestimoSelecionado.valor_principal}
                  value={amortizarFormLista.valor_amortizacao}
                  onChange={(e) => setAmortizarFormLista({ ...amortizarFormLista, valor_amortizacao: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="Ex: 1000,00" required data-testid="amortizar-valor-input-lista"
                />
                <p className="text-xs text-muted-foreground mt-1">Máximo: {formatarMoeda(emprestimoSelecionado.valor_principal)}</p>
              </div>

              <div className="mb-4 p-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10" data-testid="amortizar-novo-capital-lista">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Novo capital:</span>
                  <span className="font-bold text-emerald-500">
                    {formatarMoeda(Math.max(emprestimoSelecionado.valor_principal - (parseFloat(amortizarFormLista.valor_amortizacao) || 0), 0))}
                  </span>
                </div>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-foreground mb-2">Forma de pagamento</label>
                <select
                  value={amortizarFormLista.metodo_pagamento}
                  onChange={(e) => setAmortizarFormLista({ ...amortizarFormLista, metodo_pagamento: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="pix">PIX</option>
                  <option value="dinheiro">Dinheiro</option>
                  <option value="transferencia">Transferência</option>
                  <option value="cartao">Cartão</option>
                  <option value="boleto">Boleto</option>
                </select>
              </div>

              <div className="mb-4 flex items-start gap-2">
                <input type="checkbox" id="amort_recalc_lista" checked={amortizarFormLista.recalcular_juros}
                  onChange={(e) => setAmortizarFormLista({ ...amortizarFormLista, recalcular_juros: e.target.checked })} className="mt-1" />
                <label htmlFor="amort_recalc_lista" className="text-sm text-foreground">Recalcular os juros das próximas parcelas com o novo capital</label>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-foreground mb-2">Observações (opcional)</label>
                <textarea value={amortizarFormLista.observacoes}
                  onChange={(e) => setAmortizarFormLista({ ...amortizarFormLista, observacoes: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary" rows={2} />
              </div>

              <div className="flex gap-3">
                <Button type="button" variant="outline" onClick={() => setShowAmortizarModalLista(false)} className="flex-1" disabled={submittingAcao}>Cancelar</Button>
                <Button type="submit" className="flex-1" disabled={submittingAcao} testId="confirmar-amortizacao-btn-lista">
                  {submittingAcao ? 'Processando...' : 'Confirmar amortização'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Incorporar Juros (lista) */}
      {showIncorporarModalLista && emprestimoSelecionado && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" data-testid="incorporar-modal-lista">
          <div className="bg-card rounded-lg border border-border shadow-xl max-w-md w-full">
            <form onSubmit={handleIncorporarSubmitLista} className="p-6">
              <h2 className="text-2xl font-bold text-foreground mb-2">Incorporar Juros ao Capital</h2>
              <p className="text-sm text-muted-foreground mb-6">Soma juros não pagos ao capital. Não é um recebimento — apenas converte juros em capital.</p>

              <div className="mb-4 p-4 bg-muted/50 rounded-lg border border-border">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-muted-foreground">Capital atual:</span>
                  <span className="font-semibold text-foreground">{formatarMoeda(emprestimoSelecionado.valor_principal)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Juros em aberto:</span>
                  <span className="font-medium text-amber-500" data-testid="incorporar-juros-aberto-lista">{formatarMoeda(jurosEmAbertoLista)}</span>
                </div>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-foreground mb-2">Valor de juros a incorporar (R$) *</label>
                <input
                  type="number" step="0.01" min="0.01"
                  value={incorporarFormLista.valor_juros}
                  onChange={(e) => setIncorporarFormLista({ ...incorporarFormLista, valor_juros: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="Ex: 200,00" required data-testid="incorporar-valor-input-lista"
                />
                {jurosEmAbertoLista > 0 && (
                  <button type="button" onClick={() => setIncorporarFormLista({ ...incorporarFormLista, valor_juros: jurosEmAbertoLista.toFixed(2) })}
                    className="text-xs text-primary hover:underline mt-1">
                    Usar total em aberto ({formatarMoeda(jurosEmAbertoLista)})
                  </button>
                )}
              </div>

              <div className="mb-4 p-4 rounded-lg border border-amber-500/30 bg-amber-500/10" data-testid="incorporar-novo-capital-lista">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Novo capital:</span>
                  <span className="font-bold text-amber-500">
                    {formatarMoeda(emprestimoSelecionado.valor_principal + (parseFloat(incorporarFormLista.valor_juros) || 0))}
                  </span>
                </div>
              </div>

              <div className="mb-3 flex items-start gap-2">
                <input type="checkbox" id="inc_baixar_lista" checked={incorporarFormLista.baixar_parcelas}
                  onChange={(e) => setIncorporarFormLista({ ...incorporarFormLista, baixar_parcelas: e.target.checked })} className="mt-1" />
                <label htmlFor="inc_baixar_lista" className="text-sm text-foreground">Baixar as parcelas de juros em aberto correspondentes</label>
              </div>
              <div className="mb-4 flex items-start gap-2">
                <input type="checkbox" id="inc_recalc_lista" checked={incorporarFormLista.recalcular_juros}
                  onChange={(e) => setIncorporarFormLista({ ...incorporarFormLista, recalcular_juros: e.target.checked })} className="mt-1" />
                <label htmlFor="inc_recalc_lista" className="text-sm text-foreground">Recalcular juros das próximas parcelas com o novo capital</label>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-foreground mb-2">Observações (opcional)</label>
                <textarea value={incorporarFormLista.observacoes}
                  onChange={(e) => setIncorporarFormLista({ ...incorporarFormLista, observacoes: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary" rows={2}
                  placeholder="Ex: Cliente não pagou os juros de 2 meses" />
              </div>

              <div className="flex gap-3">
                <Button type="button" variant="outline" onClick={() => setShowIncorporarModalLista(false)} className="flex-1" disabled={submittingAcao}>Cancelar</Button>
                <Button type="submit" className="flex-1" disabled={submittingAcao} testId="confirmar-incorporacao-btn-lista">
                  {submittingAcao ? 'Processando...' : 'Confirmar incorporação'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Layout>
  );
};

export default Emprestimos;
