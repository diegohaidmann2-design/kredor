import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import ErrorMessage from '../components/ErrorMessage';
import Button from '../components/Button';
import { useModal } from '../components/Modal';
import { emprestimosAPI, pagamentosAPI, clientesAPI } from '../api/api';
import { formatarMoeda, formatarData, getStatusColor, getStatusLabel, getMetodoCalculoLabel } from '../utils/formatters';
import { MoreVertical, Trash2, FileText, DollarSign, Download, FileSpreadsheet, CheckCircle } from 'lucide-react';

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
  const modal = useModal();
  const [formPagamento, setFormPagamento] = useState({
    valor_pago: '',
    metodo_pagamento: 'pix',
    observacoes: ''
  });

  const carregarDados = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      
      const [emprestimoRes, parcelasRes] = await Promise.all([
        emprestimosAPI.obter(id),
        emprestimosAPI.listarParcelas(id)
      ]);
      
      setEmprestimo(emprestimoRes.data);
      setParcelas(parcelasRes.data);
      
      // Carregar dados do cliente
      const clienteRes = await clientesAPI.obter(emprestimoRes.data.cliente_id);
      setCliente(clienteRes.data);
    } catch (err) {
      console.error('Erro ao carregar dados:', err);
      setError('Erro ao carregar dados do empréstimo');
    } finally {
      setLoading(false);
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
      metodo_pagamento: 'pix',
      observacoes: ''
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
        metodo_pagamento: formPagamento.metodo_pagamento,
        observacoes: formPagamento.observacoes || null
      };

      await pagamentosAPI.criar(data);
      setShowPagamentoModal(false);
      setParcelaSelecionada(null);
      carregarDados();
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
      await carregarDados();
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
      await carregarDados();
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
