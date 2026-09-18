import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import ErrorMessage from '../components/ErrorMessage';
import Button from '../components/Button';
import { useModal } from '../components/Modal';
import { emprestimosAPI, pagamentosAPI, clientesAPI, aceiteEmprestimoAPI } from '../api/api';
import { formatarMoeda, formatarData, getStatusColor, getStatusLabel, getMetodoCalculoLabel, hojeISO } from '../utils/formatters';
import RestanteDoPagamento from '../components/pagamentos/RestanteDoPagamento';
import { MoreVertical, Trash2, FileText, DollarSign, Download, FileSpreadsheet, CheckCircle, History, ArrowDownCircle, ArrowUpCircle, Receipt, MessageCircle, RotateCcw, FileSignature } from 'lucide-react';

const EmprestimoDetalhes = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [emprestimo, setEmprestimo] = useState(null);
  const [cliente, setCliente] = useState(null);
  const [parcelas, setParcelas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [showPagamentoModal, setShowPagamentoModal] = useState(false);
  const [parcelaSelecionada, setParcelaSelecionada] = useState(null);
  const [showMenuAcoes, setShowMenuAcoes] = useState(false);
  const [showProrrogarModal, setShowProrrogarModal] = useState(false);
  const [periodosProrrogacao, setPeriodosProrrogacao] = useState(1);
  const [showAmortizarModal, setShowAmortizarModal] = useState(false);
  const [amortizarForm, setAmortizarForm] = useState({
    valor_amortizacao: '',
    metodo_pagamento: 'pix',
    observacoes: ''
  });
  const [showIncorporarModal, setShowIncorporarModal] = useState(false);
  const [incorporarForm, setIncorporarForm] = useState({
    valor_juros: '',
    baixar_parcelas: true,
    recalcular_juros: true,
    observacoes: ''
  });
  const modal = useModal();
  const [ajustes, setAjustes] = useState([]);
  const [formPagamento, setFormPagamento] = useState({
    valor_pago: '',
    data_pagamento: hojeISO(),
    metodo_pagamento: 'pix',
    observacoes: '',
    quitar_ignorando_restante: false
  });

  // Fechar modais com a tecla Esc
  useEffect(() => {
    const onKey = (e) => {
      if (e.key !== 'Escape') return;
      setShowPagamentoModal(false);
      setShowProrrogarModal(false);
      setShowAmortizarModal(false);
      setShowIncorporarModal(false);
      setShowMenuAcoes(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const carregarDados = useCallback(async ({ silencioso = false } = {}) => {
    try {
      // Silencioso: a tela continua visível enquanto atualiza. Ligar o loading aqui trocava
      // a página inteira pelo "Carregando..." a cada ação concluída.
      if (!silencioso) setLoading(true);
      setError('');
      
      const [emprestimoRes, parcelasRes] = await Promise.all([
        emprestimosAPI.obter(id),
        emprestimosAPI.listarParcelas(id)
      ]);
      
      setEmprestimo(emprestimoRes.data);
      setParcelas(parcelasRes.data);

      // Carregar histórico de ajustes (amortizações e incorporações)
      try {
        const ajustesRes = await emprestimosAPI.listarAjustes(id);
        setAjustes(ajustesRes.data?.ajustes || []);
      } catch (e) {
        setAjustes([]);
      }

      // Carregar dados do cliente
      const clienteRes = await clientesAPI.obter(emprestimoRes.data.cliente_id);
      setCliente(clienteRes.data);
    } catch (err) {
      console.error('Erro ao carregar dados:', err);
      setError('Não foi possível carregar os dados do empréstimo.');
    } finally {
      if (!silencioso) setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    carregarDados();
  }, [carregarDados]);

  const handlePagar = (parcela) => {
    setParcelaSelecionada(parcela);
    const valorDevido = parcela.valor_total - parcela.valor_pago + parcela.valor_multa + parcela.valor_juros_mora;
    setFormPagamento({
      valor_pago: valorDevido.toFixed(2),
      data_pagamento: hojeISO(),
      metodo_pagamento: 'pix',
      observacoes: '',
      quitar_ignorando_restante: false
    });
    setShowPagamentoModal(true);
  };

  const handleSubmitPagamento = async (e) => {
    e.preventDefault();
    
    // Prevenir duplo submit
    if (submitting) {
      return;
    }

    setSubmitting(true);
    
    try {
      const data = {
        parcela_id: parcelaSelecionada.id,
        valor_pago: parseFloat(formPagamento.valor_pago),
        data_pagamento: formPagamento.data_pagamento,
        metodo_pagamento: formPagamento.metodo_pagamento,
        observacoes: formPagamento.observacoes || null,
        quitar_ignorando_restante: formPagamento.quitar_ignorando_restante
      };

      await pagamentosAPI.criar(data);
      setShowPagamentoModal(false);
      setParcelaSelecionada(null);
      carregarDados({ silencioso: true });
      modal.success('Pagamento Registrado!', 'O pagamento foi registrado com sucesso e a parcela foi atualizada.');
    } catch (err) {
      modal.error('Erro no Pagamento', err.response?.data?.detail || 'Não foi possível registrar o pagamento. Tente novamente.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleExcluir = () => {
    modal.confirm(
      'Excluir Empréstimo',
      'Tem certeza que deseja excluir este empréstimo? Esta ação não pode ser desfeita e todas as parcelas serão excluídas.',
      async () => {
        try {
          await emprestimosAPI.deletar(id);
          modal.success('Empréstimo Excluído', 'O empréstimo foi excluído com sucesso.');
          navigate('/emprestimos');
        } catch (err) {
          modal.error('Erro', err.response?.data?.detail || 'Não foi possível excluir o empréstimo.');
        }
      }
    );
  };

  const handleRegistrarPagamentoRapido = () => {
    // Encontrar a primeira parcela pendente (não paga)
    const parcelaPendente = parcelas.find(p => p.status !== 'pago');
    
    if (!parcelaPendente) {
      modal.info('Sem Parcelas Pendentes', 'Todas as parcelas deste empréstimo já foram pagas.');
      return;
    }
    
    // Abrir modal de pagamento com a parcela pendente
    handlePagar(parcelaPendente);
    setShowMenuAcoes(false);
  };

  const handleExportar = async (formato) => {
    try {
      const response = await emprestimosAPI.exportar(id, formato);
      
      // Criar URL do blob e baixar
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `emprestimo_${id.slice(0, 8)}_${new Date().toISOString().slice(0, 10)}.${formato === 'excel' ? 'xlsx' : 'pdf'}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      modal.success('Exportação Concluída', `Extrato exportado com sucesso em ${formato.toUpperCase()}.`);
    } catch (err) {
      modal.error('Erro na Exportação', 'Não foi possível exportar o extrato. Tente novamente.');
    }
    setShowMenuAcoes(false);
  };

  const handleAbrirProrrogacao = () => {
    // Validar se empréstimo pode ser prorrogado
    if (emprestimo.metodo_calculo !== 'apenas_juros') {
      modal.info('Prorrogação Não Disponível', 'Apenas empréstimos com método "Apenas Juros" podem ser prorrogados.');
      return;
    }
    
    if (emprestimo.status !== 'ativo' && emprestimo.status !== 'inadimplente') {
      modal.info('Prorrogação Não Disponível', 'Apenas empréstimos ativos ou inadimplentes podem ser prorrogados.');
      return;
    }
    
    setPeriodosProrrogacao(1);
    setShowProrrogarModal(true);
    setShowMenuAcoes(false);
  };

  const handleProrrogar = async () => {
    if (periodosProrrogacao < 1) {
      modal.error('Erro', 'Quantidade de períodos deve ser maior que zero.');
      return;
    }
    
    setSubmitting(true);
    try {
      const response = await emprestimosAPI.prorrogar(id, periodosProrrogacao);
      
      setShowProrrogarModal(false);
      modal.success(
        'Empréstimo Prorrogado!',
        `${response.data.mensagem}. ${response.data.novas_parcelas_criadas.length} novas parcelas foram criadas.`
      );
      
      // Recarregar dados
      await carregarDados({ silencioso: true });
    } catch (err) {
      modal.error('Erro ao Prorrogar', err.response?.data?.detail || 'Não foi possível prorrogar o empréstimo. Tente novamente.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAbrirAmortizar = () => {
    if (!emprestimo) return;
    if (!emprestimo.sem_prazo) {
      modal.info('Indisponível', 'Amortização disponível apenas em empréstimos sem prazo (modalidade Apenas Juros).');
      return;
    }
    if (emprestimo.status !== 'ativo') {
      modal.info('Indisponível', 'Apenas empréstimos ativos podem receber amortização.');
      return;
    }
    setAmortizarForm({ valor_amortizacao: '', metodo_pagamento: 'pix', observacoes: '' });
    setShowAmortizarModal(true);
    setShowMenuAcoes(false);
  };

  const submitAmortizacao = async (recalcularJuros) => {
    const valor = parseFloat(amortizarForm.valor_amortizacao);
    if (!valor || valor <= 0) {
      modal.error('Erro', 'Informe um valor de amortização válido.');
      return;
    }
    if (valor > emprestimo.valor_principal + 0.001) {
      modal.error('Erro', `Valor maior que o capital devido (R$ ${emprestimo.valor_principal.toFixed(2)}).`);
      return;
    }

    setSubmitting(true);
    try {
      const response = await emprestimosAPI.amortizar(id, {
        valor_amortizacao: valor,
        metodo_pagamento: amortizarForm.metodo_pagamento,
        observacoes: amortizarForm.observacoes || null,
        recalcular_juros: recalcularJuros
      });
      setShowAmortizarModal(false);
      const data = response.data;
      let msg = `Capital reduzido de R$ ${data.principal_anterior.toFixed(2)} para R$ ${data.principal_atual.toFixed(2)}.`;
      if (data.quitado) msg += ' Empréstimo quitado!';
      else if (recalcularJuros) msg += ` ${data.parcelas_atualizadas} parcela(s) recalculada(s).`;
      modal.success('Amortização Registrada!', msg);
      await carregarDados({ silencioso: true });
    } catch (err) {
      modal.error('Erro na Amortização', err.response?.data?.detail || 'Não foi possível registrar a amortização.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAmortizarSubmit = async (e) => {
    e.preventDefault();
    const valor = parseFloat(amortizarForm.valor_amortizacao);
    if (!valor || valor <= 0) {
      modal.error('Erro', 'Informe um valor de amortização válido.');
      return;
    }
    if (valor > emprestimo.valor_principal + 0.001) {
      modal.error('Erro', `Valor maior que o capital devido (R$ ${emprestimo.valor_principal.toFixed(2)}).`);
      return;
    }
    // Pergunta sobre recalcular juros (botoes customizados)
    const novoCapital = emprestimo.valor_principal - valor;
    const taxa = emprestimo.taxa_juros_mensal || emprestimo.taxa_juros_semanal || 0;
    const periodo = emprestimo.periodicidade === 'semanal' ? 'semana' : 'mês';
    const novoJuros = (novoCapital * taxa / 100).toFixed(2);
    modal.showModal({
      type: 'warning',
      title: 'Recalcular juros das próximas parcelas?',
      message: `Após amortizar R$ ${valor.toFixed(2)}, o capital ficará R$ ${novoCapital.toFixed(2)}. As próximas parcelas pendentes podem ter o juros recalculado para R$ ${novoJuros} (${taxa}% sobre R$ ${novoCapital.toFixed(2)} ao ${periodo}).`,
      confirmText: 'Sim, recalcular',
      cancelText: 'Não, manter juros',
      onConfirm: () => submitAmortizacao(true),
      onCancel: () => submitAmortizacao(false),
    });
  };

  // ==================== INCORPORAÇÃO DE JUROS ====================
  const jurosEmAberto = parcelas
    .filter(p => ['pendente', 'atrasado', 'parcial'].includes(p.status))
    .reduce((sum, p) => sum + Math.max(
      (p.valor_total || 0) - (p.valor_pago || 0) + (p.valor_multa || 0) + (p.valor_juros_mora || 0),
      0
    ), 0);

  const handleAbrirIncorporar = () => {
    if (!emprestimo) return;
    if (!emprestimo.sem_prazo) {
      modal.info('Indisponível', 'Incorporação de juros disponível apenas em empréstimos sem prazo (modalidade Apenas Juros).');
      return;
    }
    if (emprestimo.status !== 'ativo') {
      modal.info('Indisponível', 'Apenas empréstimos ativos podem incorporar juros.');
      return;
    }
    setIncorporarForm({
      valor_juros: jurosEmAberto > 0 ? jurosEmAberto.toFixed(2) : '',
      baixar_parcelas: true,
      recalcular_juros: true,
      observacoes: ''
    });
    setShowIncorporarModal(true);
    setShowMenuAcoes(false);
  };

  const handleIncorporarSubmit = async (e) => {
    e.preventDefault();
    const valor = parseFloat(incorporarForm.valor_juros);
    if (!valor || valor <= 0) {
      modal.error('Erro', 'Informe um valor de juros válido para incorporar.');
      return;
    }
    setSubmitting(true);
    try {
      const response = await emprestimosAPI.incorporarJuros(id, {
        valor_juros: valor,
        baixar_parcelas: incorporarForm.baixar_parcelas,
        recalcular_juros: incorporarForm.recalcular_juros,
        observacoes: incorporarForm.observacoes || null
      });
      setShowIncorporarModal(false);
      const data = response.data;
      let msg = `Capital aumentado de R$ ${data.principal_anterior.toFixed(2)} para R$ ${data.principal_atual.toFixed(2)}.`;
      if (data.parcelas_baixadas > 0) msg += ` ${data.parcelas_baixadas} parcela(s) de juros baixada(s).`;
      if (data.recalculou_juros) msg += ` ${data.parcelas_atualizadas} parcela(s) recalculada(s).`;
      modal.success('Juros Incorporados!', msg);
      await carregarDados({ silencioso: true });
    } catch (err) {
      modal.error('Erro na Incorporação', err.response?.data?.detail || 'Não foi possível incorporar os juros.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleBaixarReciboAmortizacao = async (pagamentoId) => {
    try {
      const response = await emprestimosAPI.reciboAmortizacao(id, pagamentoId);
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `comprovante_amortizacao_${pagamentoId.slice(0, 8)}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      modal.error('Erro', 'Não foi possível gerar o comprovante de amortização.');
    }
  };

  const handleEnviarReciboWhatsapp = async (pagamentoId) => {
    modal.confirm(
      'Enviar por WhatsApp',
      'Enviar o comprovante de amortização (PDF) para o WhatsApp do cliente?',
      async () => {
        try {
          const resp = await emprestimosAPI.enviarReciboWhatsapp(id, pagamentoId);
          modal.success('Enviado!', resp.data?.message || 'Comprovante enviado pelo WhatsApp.');
        } catch (err) {
          modal.error('Erro no Envio', err.response?.data?.detail || 'Não foi possível enviar pelo WhatsApp.');
        }
      }
    );
  };

  const handleEstornarAjuste = async (ajuste) => {
    const label = ajuste.tipo === 'amortizacao' ? 'amortização' : 'incorporação de juros';
    modal.confirm(
      'Estornar Ajuste',
      `Deseja estornar esta ${label} de ${formatarMoeda(ajuste.valor)}? O capital voltará ao valor anterior a este lançamento.`,
      async () => {
        try {
          const resp = await emprestimosAPI.estornarAjuste(id, ajuste.id);
          const d = resp.data;
          let msg = `Capital ajustado de ${formatarMoeda(d.principal_anterior)} para ${formatarMoeda(d.principal_atual)}.`;
          if (d.reativado) msg += ' Empréstimo reativado.';
          modal.success('Ajuste Estornado!', msg);
          await carregarDados({ silencioso: true });
        } catch (err) {
          modal.error('Erro no Estorno', err.response?.data?.detail || 'Não foi possível estornar o ajuste.');
        }
      }
    );
  };

  const handleGerarAceite = async () => {
    setShowMenuAcoes(false);
    try {
      const { data } = await aceiteEmprestimoAPI.gerar(id);
      try { await navigator.clipboard.writeText(data.url); } catch { /* clipboard indisponível */ }
      await carregarDados({ silencioso: true });

      let extra = '';
      const wpp = data.whatsapp;
      if (wpp?.enviado) {
        extra = '\n\n✅ O link também foi enviado automaticamente por WhatsApp para o cliente.';
      } else if (wpp?.motivo === 'cliente_sem_telefone') {
        extra = '\n\n(O cliente não tem telefone cadastrado — envie o link manualmente.)';
      } else if (wpp?.motivo === 'whatsapp_nao_conectado' || wpp?.motivo === 'evolution_nao_configurada') {
        extra = '\n\n(WhatsApp não conectado — envie o link manualmente ou conecte o WhatsApp em Configurações.)';
      } else if (wpp && wpp.enviado === false) {
        extra = '\n\n(Não foi possível enviar por WhatsApp desta vez — envie o link manualmente.)';
      }

      modal.success(
        'Link de aceite gerado!',
        `O link foi copiado. Envie ao cliente para revisar os dados e assinar:\n\n${data.url}${extra}`
      );
    } catch (err) {
      modal.error('Erro', err.response?.data?.detail || 'Não foi possível gerar o link de aceite.');
    }
  };

  if (loading) return <Loading message="Carregando detalhes..." />;
  if (error) return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <ErrorMessage message={error} onRetry={carregarDados} />
      </div>
    </Layout>
  );

  const parcelasPendentes = parcelas.filter(p => p.status === 'pendente' || p.status === 'parcial').length;
  const parcelasPagas = parcelas.filter(p => p.status === 'pago').length;
  const parcelasAtrasadas = parcelas.filter(p => p.status === 'atrasado').length;
  const totalPago = parcelas.reduce((sum, p) => sum + p.valor_pago, 0);
  const isAberto = emprestimo.sem_prazo;
  const taxaExibida = emprestimo.periodicidade === 'semanal'
    ? (emprestimo.taxa_juros_semanal || 0)
    : (emprestimo.taxa_juros_mensal || 0);
  const periodoLabel = emprestimo.periodicidade === 'semanal' ? 'semana' : 'mês';
  const periodoTaxa = emprestimo.periodicidade === 'semanal' ? 'por semana' : 'ao mês';
  // Empréstimo aberto (apenas juros): não há "total com juros" fixo; o que resta
  // devido é o capital (principal). Para prazo fixo, mantém principal+juros - pago.
  const totalRestante = isAberto
    ? emprestimo.valor_principal
    : emprestimo.valor_total_com_juros - totalPago;

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <Link to="/emprestimos" className="text-primary hover:text-primary/80 mb-4 inline-block" data-testid="voltar-link">
              ← Voltar para Empréstimos
            </Link>
            <h1 className="text-3xl font-bold text-foreground" data-testid="detalhes-title">
              Detalhes do Empréstimo
            </h1>
          </div>
          
          {/* Menu de Ações */}
          <div className="relative">
            <button
              onClick={() => setShowMenuAcoes(!showMenuAcoes)}
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition"
              title="Mais ações"
            >
              <MoreVertical className="w-5 h-5" />
            </button>
            
            {showMenuAcoes && (
              <>
                <div 
                  className="fixed inset-0 z-[100]" 
                  onClick={() => setShowMenuAcoes(false)}
                />
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="absolute right-0 mt-2 w-56 bg-card border border-border rounded-lg shadow-lg z-[101] overflow-hidden"
                >
                  <div className="px-3 py-2 border-b border-border">
                    <span className="text-xs font-medium text-muted-foreground uppercase">Ações</span>
                  </div>
                  <button
                    onClick={() => {
                      handleRegistrarPagamentoRapido();
                    }}
                    className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-accent transition-colors"
                  >
                    <DollarSign className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm font-medium text-foreground">Registrar Pagamento</span>
                  </button>
                  
                  {emprestimo.metodo_calculo === 'apenas_juros' && (emprestimo.status === 'ativo' || emprestimo.status === 'inadimplente') && (
                    <button
                      onClick={handleAbrirProrrogacao}
                      className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-accent transition-colors"
                      data-testid="prorrogar-btn"
                    >
                      <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="text-sm font-medium text-foreground">Prorrogar Empréstimo</span>
                    </button>
                  )}
                  
                  {emprestimo.sem_prazo && emprestimo.status === 'ativo' && (
                    <button
                      onClick={handleAbrirAmortizar}
                      className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-accent transition-colors"
                      data-testid="amortizar-btn"
                    >
                      <svg className="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                      </svg>
                      <span className="text-sm font-medium text-foreground">Amortizar Capital</span>
                    </button>
                  )}

                  {emprestimo.sem_prazo && emprestimo.status === 'ativo' && (
                    <button
                      onClick={handleAbrirIncorporar}
                      className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-accent transition-colors"
                      data-testid="incorporar-juros-btn"
                    >
                      <svg className="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                      </svg>
                      <span className="text-sm font-medium text-foreground">Incorporar Juros</span>
                    </button>
                  )}
                  
                  <button
                    onClick={handleGerarAceite}
                    className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-accent transition-colors"
                    data-testid="gerar-aceite-btn"
                  >
                    <FileSignature className="w-4 h-4 text-primary" />
                    <span className="text-sm font-medium text-foreground">
                      {emprestimo.aceite?.status === 'aceito' ? 'Ver link de aceite' : 'Gerar link de aceite'}
                    </span>
                  </button>

                  <button
                    onClick={() => {
                      // Gerar contrato - implementar depois
                      modal.info('Em breve', 'Funcionalidade de gerar contrato em desenvolvimento.');
                      setShowMenuAcoes(false);
                    }}
                    className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-accent transition-colors"
                  >
                    <FileText className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm font-medium text-foreground">Gerar Contrato</span>
                  </button>
                  
                  <div className="px-3 py-2 border-t border-b border-border">
                    <span className="text-xs font-medium text-muted-foreground uppercase">Exportar Extrato</span>
                  </div>
                  <button
                    onClick={() => handleExportar('pdf')}
                    className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-accent transition-colors"
                  >
                    <Download className="w-4 h-4 text-red-500" />
                    <span className="text-sm font-medium text-foreground">Exportar PDF</span>
                  </button>
                  <button
                    onClick={() => handleExportar('excel')}
                    className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-accent transition-colors"
                  >
                    <FileSpreadsheet className="w-4 h-4 text-green-500" />
                    <span className="text-sm font-medium text-foreground">Exportar Excel</span>
                  </button>
                  
                  <div className="border-t border-border">
                    <button
                      onClick={() => {
                        handleExcluir();
                        setShowMenuAcoes(false);
                      }}
                      className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-destructive/10 transition-colors"
                    >
                      <Trash2 className="w-4 h-4 text-destructive" />
                      <span className="text-sm font-medium text-destructive">Excluir Empréstimo</span>
                    </button>
                  </div>
                </motion.div>
              </>
            )}
          </div>
        </div>

        {/* Informações do Empréstimo e Cliente */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Card do Empréstimo */}
          <div className="bg-card rounded-lg border border-border p-6" data-testid="emprestimo-info">
            <h2 className="text-xl font-bold text-foreground mb-4">Informações do Empréstimo</h2>
            <div className="space-y-3">
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted-foreground">Status:</span>
                <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(emprestimo.status)}`}>
                  {getStatusLabel(emprestimo.status)}
                </span>
              </div>
              {emprestimo.aceite?.status && (
                <div className="flex justify-between border-b border-border pb-2" data-testid="aceite-status-row">
                  <span className="text-muted-foreground">Aceite do cliente:</span>
                  {emprestimo.aceite.status === 'aceito' ? (
                    <span className="px-2 py-1 text-xs font-semibold rounded-full bg-emerald-500/15 text-emerald-600">
                      Aceito {emprestimo.aceite.assinado_em ? `em ${formatarData(emprestimo.aceite.assinado_em)}` : ''}
                    </span>
                  ) : (
                    <span className="px-2 py-1 text-xs font-semibold rounded-full bg-amber-500/15 text-amber-600">
                      Aguardando aceite
                    </span>
                  )}
                </div>
              )}
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted-foreground">Valor Principal:</span>
                <span className="font-semibold text-foreground" data-testid="valor-principal">
                  {formatarMoeda(emprestimo.valor_principal)}
                </span>
              </div>
              {!isAberto && (
                <div className="flex justify-between border-b border-border pb-2">
                  <span className="text-muted-foreground">Total com Juros:</span>
                  <span className="font-semibold text-emerald-500" data-testid="total-com-juros">
                    {formatarMoeda(emprestimo.valor_total_com_juros)}
                  </span>
                </div>
              )}
              {isAberto ? (
                <div className="flex justify-between border-b border-border pb-2">
                  <span className="text-muted-foreground">Juros por {periodoLabel}:</span>
                  <span className="font-semibold text-emerald-500" data-testid="juros-por-periodo">
                    {formatarMoeda(emprestimo.valor_principal * (taxaExibida / 100))}
                  </span>
                </div>
              ) : (
                <div className="flex justify-between border-b border-border pb-2">
                  <span className="text-muted-foreground">Total de Juros:</span>
                  <span className="font-semibold text-foreground">
                    {formatarMoeda(emprestimo.valor_total_juros)}
                  </span>
                </div>
              )}
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted-foreground">Taxa de Juros:</span>
                <span className="font-semibold text-foreground" data-testid="taxa-juros">{taxaExibida}% {periodoTaxa}</span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted-foreground">Prazo:</span>
                <span className="font-semibold text-foreground" data-testid="prazo-emprestimo">
                  {isAberto
                    ? 'Sem prazo (apenas juros)'
                    : `${emprestimo.prazo_meses ?? emprestimo.prazo_semanas ?? 0} ${emprestimo.periodicidade === 'semanal' ? 'semanas' : 'meses'}`}
                </span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted-foreground">Método:</span>
                <span className="font-semibold text-foreground">{getMetodoCalculoLabel(emprestimo.metodo_calculo)}</span>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <span className="text-muted-foreground">Data de Início:</span>
                <span className="font-semibold text-foreground">{formatarData(emprestimo.data_inicio)}</span>
              </div>
              {emprestimo.periodo_carencia_meses > 0 && (
                <div className="flex justify-between border-b border-border pb-2">
                  <span className="text-muted-foreground">Carência:</span>
                  <span className="font-semibold text-foreground">{emprestimo.periodo_carencia_meses} meses</span>
                </div>
              )}
            </div>
          </div>

          {/* Card do Cliente */}
          {cliente && (
            <div className="bg-card rounded-lg border border-border p-6" data-testid="cliente-info">
              <h2 className="text-xl font-bold text-foreground mb-4">Informações do Cliente</h2>
              <div className="space-y-3">
                <div className="flex justify-between border-b border-border pb-2">
                  <span className="text-muted-foreground">Nome:</span>
                  <span className="font-semibold text-foreground">{cliente.nome}</span>
                </div>
                <div className="flex justify-between border-b border-border pb-2">
                  <span className="text-muted-foreground">CPF/CNPJ:</span>
                  <span className="font-semibold text-foreground">{cliente.cpf_cnpj}</span>
                </div>
                <div className="flex justify-between border-b border-border pb-2">
                  <span className="text-muted-foreground">Telefone:</span>
                  <span className="font-semibold text-foreground">{cliente.telefone}</span>
                </div>
                <div className="flex justify-between border-b border-border pb-2">
                  <span className="text-muted-foreground">Email:</span>
                  <span className="font-semibold text-foreground">{cliente.email}</span>
                </div>
                <div className="flex justify-between border-b border-border pb-2">
                  <span className="text-muted-foreground">Status:</span>
                  <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(cliente.status)}`}>
                    {getStatusLabel(cliente.status)}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Resumo de Pagamentos */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-card rounded-lg border border-border p-4" data-testid="resumo-total-pago">
            <p className="text-sm text-muted-foreground mb-1">Total Pago</p>
            <p className="text-2xl font-bold text-emerald-500">{formatarMoeda(totalPago)}</p>
          </div>
          <div className="bg-card rounded-lg border border-border p-4" data-testid="resumo-total-restante">
            <p className="text-sm text-muted-foreground mb-1">{isAberto ? 'Capital Devedor' : 'Total Restante'}</p>
            <p className="text-2xl font-bold text-primary">{formatarMoeda(totalRestante)}</p>
          </div>
          <div className="bg-card rounded-lg border border-border p-4" data-testid="resumo-parcelas">
            <p className="text-sm text-muted-foreground mb-1">Parcelas</p>
            <p className="text-2xl font-bold text-foreground">
              {parcelasPagas}/{parcelas.length}
            </p>
          </div>
          <div className="bg-card rounded-lg border border-border p-4" data-testid="resumo-atrasadas">
            <p className="text-sm text-muted-foreground mb-1">Atrasadas</p>
            <p className={`text-2xl font-bold ${parcelasAtrasadas > 0 ? 'text-destructive' : 'text-foreground'}`}>
              {parcelasAtrasadas}
            </p>
          </div>
        </div>

        {/* Histórico de Ajustes (amortizações e incorporações) */}
        {ajustes.length > 0 && (
          <div className="bg-card rounded-lg border border-border overflow-hidden mb-8" data-testid="ajustes-timeline">
            <div className="p-4 md:p-6 border-b border-border flex items-center gap-2">
              <History className="w-5 h-5 text-primary" />
              <h2 className="text-xl font-bold text-foreground">Histórico de Ajustes ({ajustes.length})</h2>
            </div>
            <div className="p-4 md:p-6">
              <div className="relative pl-6">
                {/* linha vertical da timeline */}
                <div className="absolute left-[9px] top-1 bottom-1 w-px bg-border" />
                <div className="space-y-5">
                  {ajustes.map((aj) => {
                    const isAmort = aj.tipo === 'amortizacao';
                    return (
                      <div key={aj.id} className="relative" data-testid={`ajuste-item-${aj.tipo}`}>
                        {/* marcador */}
                        <div className={`absolute -left-[26px] top-0.5 rounded-full ${isAmort ? 'text-emerald-500' : 'text-amber-500'}`}>
                          {isAmort
                            ? <ArrowDownCircle className="w-5 h-5 bg-card rounded-full" />
                            : <ArrowUpCircle className="w-5 h-5 bg-card rounded-full" />}
                        </div>
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className={`text-sm font-semibold ${isAmort ? 'text-emerald-500' : 'text-amber-500'}`}>
                                {isAmort ? 'Amortização de Capital' : 'Incorporação de Juros'}
                              </span>
                              <span className="text-xs text-muted-foreground">{formatarData(aj.data)}</span>
                            </div>
                            <p className="text-xs text-muted-foreground mt-0.5">
                              Capital: {formatarMoeda(aj.principal_anterior)} →{' '}
                              <span className="font-medium text-foreground">{formatarMoeda(aj.principal_apos)}</span>
                              {aj.metodo_pagamento && aj.metodo_pagamento !== 'incorporacao' ? ` • ${aj.metodo_pagamento}` : ''}
                            </p>
                            {aj.observacoes && (
                              <p className="text-xs text-muted-foreground mt-0.5 italic">"{aj.observacoes}"</p>
                            )}
                          </div>
                          <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end">
                            <span className={`text-base font-bold ${isAmort ? 'text-emerald-500' : 'text-amber-500'}`}>
                              {isAmort ? '-' : '+'}{formatarMoeda(aj.valor)}
                            </span>
                            {isAmort && (
                              <>
                                <button
                                  onClick={() => handleBaixarReciboAmortizacao(aj.id)}
                                  className="inline-flex items-center gap-1.5 px-2.5 py-1.5 bg-primary/10 text-primary text-xs font-medium rounded-md hover:bg-primary/20 transition-colors"
                                  data-testid={`recibo-amortizacao-btn-${aj.id}`}
                                  title="Baixar comprovante em PDF"
                                >
                                  <Receipt className="w-3.5 h-3.5" />
                                  Recibo
                                </button>
                                <button
                                  onClick={() => handleEnviarReciboWhatsapp(aj.id)}
                                  className="inline-flex items-center gap-1.5 px-2.5 py-1.5 bg-green-500/10 text-green-600 dark:text-green-400 text-xs font-medium rounded-md hover:bg-green-500/20 transition-colors"
                                  data-testid={`whatsapp-recibo-btn-${aj.id}`}
                                  title="Enviar comprovante pelo WhatsApp"
                                >
                                  <MessageCircle className="w-3.5 h-3.5" />
                                  WhatsApp
                                </button>
                              </>
                            )}
                            <button
                              onClick={() => handleEstornarAjuste(aj)}
                              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 bg-destructive/10 text-destructive text-xs font-medium rounded-md hover:bg-destructive/20 transition-colors"
                              data-testid={`estornar-ajuste-btn-${aj.id}`}
                              title="Estornar este ajuste (reverter o capital)"
                            >
                              <RotateCcw className="w-3.5 h-3.5" />
                              Estornar
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tabela de Parcelas */}
        <div className="bg-card rounded-lg border border-border overflow-hidden" data-testid="parcelas-table">
          <div className="p-4 md:p-6 border-b border-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <h2 className="text-xl font-bold text-foreground">Parcelas ({parcelas.length})</h2>
            <div className="flex gap-2">
              <button
                onClick={() => handleExportar('pdf')}
                className="inline-flex items-center gap-2 px-3 py-1.5 bg-red-500/10 text-red-500 text-xs font-medium rounded-md hover:bg-red-500/20 transition-colors"
                data-testid="exportar-pdf-btn"
              >
                <Download className="w-3.5 h-3.5" />
                PDF
              </button>
              <button
                onClick={() => handleExportar('excel')}
                className="inline-flex items-center gap-2 px-3 py-1.5 bg-green-500/10 text-green-500 text-xs font-medium rounded-md hover:bg-green-500/20 transition-colors"
                data-testid="exportar-excel-btn"
              >
                <FileSpreadsheet className="w-3.5 h-3.5" />
                Excel
              </button>
            </div>
          </div>

          {/* Versão Desktop - Tabela */}
          <div className="hidden md:block overflow-x-auto">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">#</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Vencimento</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Valor</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Pago</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Saldo</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Dt. Pagamento</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border" data-testid="parcelas-table-body">
                {parcelas.map((parcela) => {
                  const valorDevido = parcela.valor_total - parcela.valor_pago + parcela.valor_multa + parcela.valor_juros_mora;
                  
                  return (
                    <tr key={parcela.id} data-testid={`parcela-row-${parcela.numero_parcela}`} className="hover:bg-muted/50">
                      <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-foreground">
                        {parcela.numero_parcela}
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-sm text-muted-foreground">
                        {formatarData(parcela.data_vencimento)}
                        {parcela.dias_atraso > 0 && parcela.status !== 'pago' && (
                          <span className="ml-2 text-destructive text-xs">
                            ({parcela.dias_atraso}d)
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-sm text-foreground">
                        {formatarMoeda(parcela.valor_total)}
                        {(parcela.valor_multa > 0 || parcela.valor_juros_mora > 0) && (
                          <div className="text-xs text-destructive mt-1">
                            + {formatarMoeda(parcela.valor_multa + parcela.valor_juros_mora)}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-sm text-emerald-500">
                        {formatarMoeda(parcela.valor_pago)}
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-sm text-muted-foreground">
                        {formatarMoeda(parcela.saldo_devedor)}
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(parcela.status)}`}>
                          {getStatusLabel(parcela.status)}
                        </span>
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-sm">
                        {parcela.status === 'pago' && parcela.data_pagamento ? (
                          <div className="flex items-center gap-1.5 text-emerald-500">
                            <CheckCircle className="w-3.5 h-3.5" />
                            <span>{formatarData(parcela.data_pagamento)}</span>
                          </div>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </td>
                      <td className="px-4 py-4 whitespace-nowrap text-sm font-medium">
                        {parcela.status !== 'pago' ? (
                          <button
                            onClick={() => handlePagar(parcela)}
                            className="inline-flex items-center gap-2 px-3 py-1.5 bg-primary text-primary-foreground text-xs font-medium rounded-md hover:bg-primary/90 transition-colors"
                            data-testid={`pagar-parcela-${parcela.numero_parcela}`}
                          >
                            <DollarSign className="w-3.5 h-3.5" />
                            Pagar
                          </button>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 text-emerald-500 text-xs">
                            <CheckCircle className="w-3.5 h-3.5" />
                            Quitado
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Versão Mobile - Cards */}
          <div className="md:hidden divide-y divide-border">
            {parcelas.map((parcela) => {
              const valorDevido = parcela.valor_total - parcela.valor_pago + parcela.valor_multa + parcela.valor_juros_mora;
              
              return (
                <div key={parcela.id} className="p-4" data-testid={`parcela-card-${parcela.numero_parcela}`}>
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold text-foreground">
                          Parcela {parcela.numero_parcela}
                        </span>
                        <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${getStatusColor(parcela.status)}`}>
                          {getStatusLabel(parcela.status)}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        Venc: {formatarData(parcela.data_vencimento)}
                        {parcela.dias_atraso > 0 && parcela.status !== 'pago' && (
                          <span className="ml-1 text-destructive font-medium">
                            ({parcela.dias_atraso}d atraso)
                          </span>
                        )}
                      </p>
                    </div>
                  </div>

                  <div className="space-y-2 text-sm mb-3">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Valor:</span>
                      <span className="font-medium text-foreground">
                        {formatarMoeda(parcela.valor_total)}
                        {(parcela.valor_multa > 0 || parcela.valor_juros_mora > 0) && (
                          <span className="text-destructive ml-1">
                            (+{formatarMoeda(parcela.valor_multa + parcela.valor_juros_mora)})
                          </span>
                        )}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Pago:</span>
                      <span className="font-medium text-emerald-500">{formatarMoeda(parcela.valor_pago)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Saldo Devedor:</span>
                      <span className="font-medium text-foreground">{formatarMoeda(parcela.saldo_devedor)}</span>
                    </div>
                    {parcela.status === 'pago' && parcela.data_pagamento && (
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Dt. Pagamento:</span>
                        <div className="flex items-center gap-1.5 text-emerald-500">
                          <CheckCircle className="w-3.5 h-3.5" />
                          <span>{formatarData(parcela.data_pagamento)}</span>
                        </div>
                      </div>
                    )}
                  </div>

                  {parcela.status !== 'pago' ? (
                    <button
                      onClick={() => handlePagar(parcela)}
                      className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-primary text-primary-foreground text-sm font-medium rounded-md hover:bg-primary/90 transition-colors"
                      data-testid={`pagar-parcela-${parcela.numero_parcela}`}
                    >
                      <DollarSign className="w-4 h-4" />
                      Registrar Pagamento
                    </button>
                  ) : (
                    <div className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-500/10 text-emerald-500 text-sm font-medium rounded-md">
                      <CheckCircle className="w-4 h-4" />
                      Quitado
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Modal de Prorrogação */}
      {showProrrogarModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" data-testid="prorrogar-modal">
          <div className="bg-card rounded-lg border border-border shadow-xl max-w-md w-full">
            <div className="p-6">
              <h2 className="text-2xl font-bold text-foreground mb-4">
                Prorrogar Empréstimo
              </h2>
              
              <div className="mb-6 p-4 bg-primary/10 rounded-lg border border-primary/20">
                <p className="text-sm text-muted-foreground mb-2">
                  <strong>Como funciona:</strong>
                </p>
                <p className="text-sm text-muted-foreground mb-2">
                  • A última parcela (com capital) vira parcela de juros
                </p>
                <p className="text-sm text-muted-foreground mb-2">
                  • Novas parcelas de juros são criadas
                </p>
                <p className="text-sm text-muted-foreground">
                  • Nova última parcela com capital é criada
                </p>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-foreground mb-2">
                  Quantidade de {emprestimo.periodicidade === 'semanal' ? 'semanas' : 'meses'} <span className="text-destructive">*</span>
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
                  Prorrogar por quantos {emprestimo.periodicidade === 'semanal' ? 'semanas' : 'meses'}?
                </p>
              </div>

              <div className="mb-6 p-4 bg-muted/50 rounded-lg border border-border">
                <p className="text-sm text-muted-foreground mb-2">
                  <strong>Total atual de parcelas:</strong> {parcelas.length}
                </p>
                <p className="text-sm text-muted-foreground mb-2">
                  <strong>Novas parcelas:</strong> {periodosProrrogacao + 1}
                </p>
                <p className="text-sm font-bold text-primary">
                  <strong>Novo total:</strong> {parcelas.length + periodosProrrogacao + 1} parcelas
                </p>
              </div>

              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowProrrogarModal(false)}
                  className="flex-1"
                  disabled={submitting}
                >
                  Cancelar
                </Button>
                <Button
                  onClick={handleProrrogar}
                  className="flex-1"
                  disabled={submitting}
                  data-testid="confirmar-prorrogacao-btn"
                >
                  {submitting ? 'Prorrogando...' : 'Confirmar Prorrogação'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Amortizar Capital */}
      {showAmortizarModal && emprestimo && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" data-testid="amortizar-modal">
          <div className="bg-card rounded-lg border border-border shadow-xl max-w-md w-full">
            <form onSubmit={handleAmortizarSubmit} className="p-6">
              <h2 className="text-2xl font-bold text-foreground mb-2">
                Amortizar Capital
              </h2>
              <p className="text-sm text-muted-foreground mb-6">
                Registre um pagamento direto no capital do empréstimo, reduzindo o saldo devedor.
              </p>
              
              <div className="mb-4 p-4 bg-muted/50 rounded-lg border border-border">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-muted-foreground">Capital atual:</span>
                  <span className="font-semibold text-foreground">
                    {formatarMoeda(emprestimo.valor_principal)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Taxa de juros:</span>
                  <span className="font-medium text-foreground">
                    {emprestimo.taxa_juros_mensal || emprestimo.taxa_juros_semanal}% ao {emprestimo.periodicidade === 'semanal' ? 'sem' : 'mês'}
                  </span>
                </div>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-foreground mb-2">
                  Valor da amortização (R$) *
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  max={emprestimo.valor_principal}
                  value={amortizarForm.valor_amortizacao}
                  onChange={(e) => setAmortizarForm({ ...amortizarForm, valor_amortizacao: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="Ex: 500,00"
                  required
                  data-testid="amortizar-valor-input"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Máximo: {formatarMoeda(emprestimo.valor_principal)}
                </p>
              </div>

              {/* Novo capital dinâmico */}
              <div className="mb-4 p-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10" data-testid="amortizar-novo-capital">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Novo capital:</span>
                  <span className="font-bold text-emerald-500">
                    {formatarMoeda(Math.max(emprestimo.valor_principal - (parseFloat(amortizarForm.valor_amortizacao) || 0), 0))}
                  </span>
                </div>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-foreground mb-2">
                  Método de pagamento
                </label>
                <select
                  value={amortizarForm.metodo_pagamento}
                  onChange={(e) => setAmortizarForm({ ...amortizarForm, metodo_pagamento: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  data-testid="amortizar-metodo-select"
                >
                  <option value="pix">PIX</option>
                  <option value="dinheiro">Dinheiro</option>
                  <option value="transferencia">Transferência</option>
                  <option value="boleto">Boleto</option>
                  <option value="cartao">Cartão</option>
                </select>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-foreground mb-2">
                  Observações (opcional)
                </label>
                <textarea
                  value={amortizarForm.observacoes}
                  onChange={(e) => setAmortizarForm({ ...amortizarForm, observacoes: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  rows={2}
                  placeholder="Ex: Pagou 200 de juros + 500 do capital"
                  data-testid="amortizar-obs-input"
                />
              </div>

              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowAmortizarModal(false)}
                  className="flex-1"
                  disabled={submitting}
                >
                  Cancelar
                </Button>
                <Button
                  type="submit"
                  className="flex-1"
                  disabled={submitting}
                  data-testid="confirmar-amortizacao-btn"
                >
                  {submitting ? 'Processando...' : 'Continuar'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal de Incorporar Juros */}
      {showIncorporarModal && emprestimo && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" data-testid="incorporar-modal">
          <div className="bg-card rounded-lg border border-border shadow-xl max-w-md w-full">
            <form onSubmit={handleIncorporarSubmit} className="p-6">
              <h2 className="text-2xl font-bold text-foreground mb-2">
                Incorporar Juros ao Capital
              </h2>
              <p className="text-sm text-muted-foreground mb-6">
                Soma juros não pagos ao capital do empréstimo. Não é um recebimento — apenas converte juros em capital.
              </p>

              <div className="mb-4 p-4 bg-muted/50 rounded-lg border border-border">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-muted-foreground">Capital atual:</span>
                  <span className="font-semibold text-foreground">
                    {formatarMoeda(emprestimo.valor_principal)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Juros em aberto:</span>
                  <span className="font-medium text-amber-500" data-testid="incorporar-juros-aberto">
                    {formatarMoeda(jurosEmAberto)}
                  </span>
                </div>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-foreground mb-2">
                  Valor de juros a incorporar (R$) *
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={incorporarForm.valor_juros}
                  onChange={(e) => setIncorporarForm({ ...incorporarForm, valor_juros: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="Ex: 200,00"
                  required
                  data-testid="incorporar-valor-input"
                />
                {jurosEmAberto > 0 && (
                  <button
                    type="button"
                    onClick={() => setIncorporarForm({ ...incorporarForm, valor_juros: jurosEmAberto.toFixed(2) })}
                    className="text-xs text-primary hover:underline mt-1"
                    data-testid="incorporar-usar-total-btn"
                  >
                    Usar total em aberto ({formatarMoeda(jurosEmAberto)})
                  </button>
                )}
              </div>

              {/* Novo capital dinâmico */}
              <div className="mb-4 p-4 rounded-lg border border-amber-500/30 bg-amber-500/10" data-testid="incorporar-novo-capital">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Novo capital:</span>
                  <span className="font-bold text-amber-500">
                    {formatarMoeda(emprestimo.valor_principal + (parseFloat(incorporarForm.valor_juros) || 0))}
                  </span>
                </div>
              </div>

              <div className="mb-3 flex items-start gap-2">
                <input
                  type="checkbox"
                  id="baixar_parcelas"
                  checked={incorporarForm.baixar_parcelas}
                  onChange={(e) => setIncorporarForm({ ...incorporarForm, baixar_parcelas: e.target.checked })}
                  className="mt-1"
                  data-testid="incorporar-baixar-check"
                />
                <label htmlFor="baixar_parcelas" className="text-sm text-foreground">
                  Baixar as parcelas de juros em aberto correspondentes
                </label>
              </div>

              <div className="mb-4 flex items-start gap-2">
                <input
                  type="checkbox"
                  id="recalcular_juros_inc"
                  checked={incorporarForm.recalcular_juros}
                  onChange={(e) => setIncorporarForm({ ...incorporarForm, recalcular_juros: e.target.checked })}
                  className="mt-1"
                  data-testid="incorporar-recalcular-check"
                />
                <label htmlFor="recalcular_juros_inc" className="text-sm text-foreground">
                  Recalcular juros das próximas parcelas com o novo capital
                </label>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-foreground mb-2">
                  Observações (opcional)
                </label>
                <textarea
                  value={incorporarForm.observacoes}
                  onChange={(e) => setIncorporarForm({ ...incorporarForm, observacoes: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  rows={2}
                  placeholder="Ex: Cliente não pagou os juros de 2 meses"
                  data-testid="incorporar-obs-input"
                />
              </div>

              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowIncorporarModal(false)}
                  className="flex-1"
                  disabled={submitting}
                >
                  Cancelar
                </Button>
                <Button
                  type="submit"
                  className="flex-1"
                  disabled={submitting}
                  data-testid="confirmar-incorporacao-btn"
                >
                  {submitting ? 'Processando...' : 'Confirmar incorporação'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal de Pagamento */}
      {showPagamentoModal && parcelaSelecionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" data-testid="pagamento-modal">
          <div className="bg-card rounded-lg border border-border shadow-xl max-w-md w-full">
            <div className="p-6">
              <h2 className="text-2xl font-bold text-foreground mb-6">
                Registrar Pagamento
              </h2>
              
              <div className="mb-4 p-4 bg-muted/50 rounded-lg border border-border">
                <p className="text-sm text-muted-foreground mb-2">
                  Parcela {parcelaSelecionada.numero_parcela} de {emprestimo?.prazo_meses || parcelas.length}
                </p>
                <p className="text-sm text-muted-foreground mb-2">
                  Vencimento: {formatarData(parcelaSelecionada.data_vencimento)}
                </p>
                {parcelaSelecionada.dias_atraso > 0 && (
                  <p className="text-sm text-destructive font-semibold">
                    {parcelaSelecionada.dias_atraso} dias de atraso
                  </p>
                )}
                <p className="text-lg font-bold text-foreground mt-2">
                  Total a pagar: {formatarMoeda(
                    parcelaSelecionada.valor_total - 
                    parcelaSelecionada.valor_pago + 
                    parcelaSelecionada.valor_multa + 
                    parcelaSelecionada.valor_juros_mora
                  )}
                </p>
                {(parcelaSelecionada.valor_multa > 0 || parcelaSelecionada.valor_juros_mora > 0) && (
                  <p className="text-xs text-muted-foreground mt-1">
                    (Inclui multa e juros de mora)
                  </p>
                )}
              </div>

              <form onSubmit={handleSubmitPagamento} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Valor Pago (R$) <span className="text-destructive">*</span>
                  </label>
                  <input
                    type="number"
                    value={formPagamento.valor_pago}
                    onChange={(e) => setFormPagamento({...formPagamento, valor_pago: e.target.value})}
                    required
                    step="0.01"
                    min="0"
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    data-testid="input-valor-pago"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Pagamentos parciais são permitidos
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Data do pagamento <span className="text-destructive">*</span>
                  </label>
                  <input
                    type="date"
                    value={formPagamento.data_pagamento}
                    onChange={(e) => setFormPagamento({...formPagamento, data_pagamento: e.target.value})}
                    required
                    max={hojeISO()}
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    data-testid="input-data-pagamento"
                  />
                  <p className="text-xs text-muted-foreground mt-1">Dia em que o cliente pagou. Multa e mora são calculadas por esta data.</p>
                </div>

                <RestanteDoPagamento
                  parcelaId={parcelaSelecionada?.id}
                  valorPago={formPagamento.valor_pago}
                  dataPagamento={formPagamento.data_pagamento}
                  ignorar={formPagamento.quitar_ignorando_restante}
                  onChangeIgnorar={(v) => setFormPagamento((f) => ({ ...f, quitar_ignorando_restante: v }))}
                />

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Método de Pagamento <span className="text-destructive">*</span>
                  </label>
                  <select
                    value={formPagamento.metodo_pagamento}
                    onChange={(e) => setFormPagamento({...formPagamento, metodo_pagamento: e.target.value})}
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
                  <label className="block text-sm font-medium text-foreground mb-1">
                    Observações
                  </label>
                  <textarea
                    value={formPagamento.observacoes}
                    onChange={(e) => setFormPagamento({...formPagamento, observacoes: e.target.value})}
                    rows="3"
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="Observações sobre o pagamento (opcional)"
                    data-testid="textarea-observacoes"
                  />
                </div>

                <div className="flex justify-end space-x-3 pt-4 border-t border-border">
                  <Button
                    type="button"
                    onClick={() => {
                      setShowPagamentoModal(false);
                      setParcelaSelecionada(null);
                    }}
                    variant="secondary"
                    testId="cancelar-pagamento-button"
                  >
                    Cancelar
                  </Button>
                  <Button 
                    type="submit" 
                    variant="primary" 
                    testId="confirmar-pagamento-button"
                    loading={submitting}
                    disabled={submitting}
                  >
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

export default EmprestimoDetalhes;
