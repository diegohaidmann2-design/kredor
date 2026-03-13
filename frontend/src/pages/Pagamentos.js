import React, { useState, useEffect, useCallback } from 'react';
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
import { DollarSign, MessageCircle, Trash2, MoreVertical } from 'lucide-react';

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
  const [filtroStatus, setFiltroStatus] = useState('todos'); // todos, pendente, atrasado, parcial
  const [filtroCliente, setFiltroCliente] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [parcelaSelecionada, setParcelaSelecionada] = useState(null);
  const [activeTab, setActiveTab] = useState('historico');
  const [menuAbertoId, setMenuAbertoId] = useState(null);
  const [enviandoWhatsApp, setEnviandoWhatsApp] = useState(false);
  const modal = useModal();

  // Redirecionar membros para o dashboard
  useEffect(() => {
    if (isMember) {
      navigate('/dashboard');
    }
  }, [isMember, navigate]);

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
      
      modal.success(
        '✅ Mensagem enviada!',
        `WhatsApp enviado com sucesso para ${parcela.cliente_nome}`
      );
      
    } catch (err) {
      // Parar loading
      setEnviandoWhatsApp(false);
      
      const errorMessage = err.response?.data?.detail || err.message || 'Erro ao enviar mensagem';
      
      // Se erro for por WhatsApp não conectado, mostrar mensagem específica
      if (errorMessage.includes('WhatsApp não está conectado') || 
          errorMessage.includes('Nenhuma conexão WhatsApp ativa')) {
        modal.error(
          '❌ WhatsApp não conectado',
          'Você precisa conectar seu WhatsApp primeiro. Acesse Config. > WhatsApp para conectar.'
        );
      } else {
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

  const pagamentosFiltrados = pagamentos.filter(pag => {
    if (filtroMetodo && pag.metodo_pagamento !== filtroMetodo) return false;
    if (filtroData) {
      const dataPag = new Date(pag.data_pagamento);
      // Comparar apenas a data (sem hora)
      if (dataPag.toDateString() !== filtroData.toDateString()) return false;
    }
    return true;
  });

  const totalPagamentos = pagamentosFiltrados.reduce((sum, pag) => sum + pag.valor_pago, 0);
  const totalPendente = parcelasPendentes.reduce((sum, p) => sum + (p.valor_total - p.valor_pago), 0);
  const parcelasAtrasadas = parcelasPendentes.filter(p => p.status === 'atrasado');

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
            <p className="text-sm text-muted-foreground mb-1">Total Pendente</p>
            <p className="text-2xl font-bold text-blue-500">{formatarMoeda(totalPendente)}</p>
            <p className="text-xs text-muted-foreground mt-1">{parcelasPendentes.length} parcelas</p>
          </div>
          <div className="bg-card rounded-lg border border-border p-4" data-testid="atrasadas-card">
            <p className="text-sm text-muted-foreground mb-1">Parcelas Atrasadas</p>
            <p className={`text-2xl font-bold ${parcelasAtrasadas.length > 0 ? 'text-red-500' : 'text-foreground'}`}>
              {parcelasAtrasadas.length}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {formatarMoeda(parcelasAtrasadas.reduce((sum, p) => sum + (p.valor_total - p.valor_pago), 0))}
            </p>
          </div>
          <div className="bg-card rounded-lg border border-border p-4">
            <p className="text-sm text-muted-foreground mb-1">Média por Pagamento</p>
            <p className="text-2xl font-bold text-foreground">
              {formatarMoeda(pagamentos.length > 0 ? totalPagamentos / pagamentos.length : 0)}
            </p>
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
          <div className="bg-card rounded-lg border border-border overflow-hidden" data-testid="parcelas-pendentes-table">
            
            {/* Barra de Filtros */}
            <div className="border-b border-border bg-muted/30 p-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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

                {/* Botão Limpar Filtros */}
                <div className="flex items-end">
                  <button
                    onClick={() => {
                      setFiltroStatus('todos');
                      setFiltroCliente('');
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
                    {parcelasPendentes.filter(p => {
                      // Aplicar filtros
                      if (filtroStatus !== 'todos' && p.status !== filtroStatus) return false;
                      if (filtroCliente && !p.cliente_nome?.toLowerCase().includes(filtroCliente.toLowerCase()) && 
                          !p.cliente_telefone?.includes(filtroCliente)) return false;
                      return true;
                    }).length}
                  </span> de <span className="font-semibold text-foreground">{parcelasPendentes.length}</span> parcelas
                </p>
              </div>
            </div>

            {parcelasPendentes.length === 0 ? (
              <div className="p-8 text-center" data-testid="sem-parcelas-message">
                <p className="text-muted-foreground">Nenhuma parcela pendente</p>
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
                        <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Vencimento</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Valor</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Status</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Ações</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border bg-card">
                      {parcelasFiltradas.map((parcela) => {
                        const valorDevido = parcela.valor_total - parcela.valor_pago;
                        return (
                          <tr key={parcela.id} data-testid={`parcela-row-${parcela.id}`} className="hover:bg-muted/30 transition-colors">
                            <td className="px-6 py-4">
                              <div className="flex items-start space-x-3">
                                <div className="flex-shrink-0">
                                  <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                                    <span className="text-primary font-semibold text-sm">
                                      {parcela.cliente_nome ? parcela.cliente_nome.charAt(0).toUpperCase() : '?'}
                                    </span>
                                  </div>
                                </div>
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm font-semibold text-foreground truncate">
                                    {parcela.cliente_nome || 'Cliente não encontrado'}
                                  </p>
                                  <p className="text-xs text-muted-foreground mt-0.5">
                                    {parcela.cliente_telefone || 'Telefone não informado'}
                                  </p>
                                  <div className="mt-1.5 flex items-center gap-2 flex-wrap">
                                    <span className="inline-flex items-center text-xs text-muted-foreground">
                                      <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                        <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4z"/>
                                        <path fillRule="evenodd" d="M18 9H2v5a2 2 0 002 2h12a2 2 0 002-2V9zM4 13a1 1 0 011-1h1a1 1 0 110 2H5a1 1 0 01-1-1zm5-1a1 1 0 100 2h1a1 1 0 100-2H9z" clipRule="evenodd"/>
                                      </svg>
                                      Empréstimo: {formatarMoeda(parcela.valor_emprestimo || 0)}
                                    </span>
                                    <span className="inline-flex items-center text-xs text-muted-foreground">
                                      <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd"/>
                                      </svg>
                                      {parcela.taxa_juros || 0}% a.m.
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm font-medium text-foreground">
                                {parcela.numero_parcela}/{parcela.total_parcelas || '?'}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                Parcela
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-foreground">
                                {formatarData(parcela.data_vencimento)}
                              </div>
                              {parcela.dias_atraso > 0 && (
                                <div className="flex items-center mt-1">
                                  <svg className="w-3 h-3 text-red-500 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
                                  </svg>
                                  <span className="text-xs text-red-500 font-semibold">
                                    {parcela.dias_atraso}d de atraso
                                  </span>
                                </div>
                              )}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm font-bold text-foreground">
                                {formatarMoeda(valorDevido)}
                              </div>
                              {(parcela.valor_multa > 0 || parcela.valor_juros_mora > 0) && (
                                <div className="text-xs text-red-500 mt-1">
                                  + {formatarMoeda((parcela.valor_multa || 0) + (parcela.valor_juros_mora || 0))} multa
                                </div>
                              )}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`inline-flex items-center px-2.5 py-1 text-xs font-bold rounded-full ${
                                parcela.status === 'atrasado'
                                  ? 'bg-red-500/20 text-red-400 ring-1 ring-red-500/30'
                                  : parcela.status === 'parcial'
                                    ? 'bg-amber-500/20 text-amber-400 ring-1 ring-amber-500/30'
                                    : 'bg-blue-500/20 text-blue-400 ring-1 ring-blue-500/30'
                              }`}>
                                {parcela.status === 'atrasado' ? '⚠️ ATRASADO' :
                                  parcela.status === 'parcial' ? '⏳ PARCIAL' : '📅 PENDENTE'}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="relative">
                                <button
                                  onClick={() => setMenuAbertoId(menuAbertoId === parcela.id ? null : parcela.id)}
                                  className="p-2 hover:bg-muted rounded-lg transition-colors"
                                  data-testid={`menu-acoes-${parcela.id}`}
                                >
                                  <MoreVertical className="w-5 h-5 text-muted-foreground" />
                                </button>
                                
                                {menuAbertoId === parcela.id && (
                                  <>
                                    {/* Overlay para fechar o menu ao clicar fora */}
                                    <div 
                                      className="fixed inset-0 z-10" 
                                      onClick={() => setMenuAbertoId(null)}
                                    />
                                    
                                    {/* Menu Dropdown */}
                                    <div className="absolute right-0 mt-2 w-56 bg-card rounded-lg shadow-lg border border-border z-20">
                                      <div className="py-1">
                                        <button
                                          onClick={() => {
                                            handleRegistrarPagamento(parcela);
                                            setMenuAbertoId(null);
                                          }}
                                          className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-foreground hover:bg-muted transition-colors"
                                          data-testid={`registrar-pagamento-${parcela.id}`}
                                        >
                                          <DollarSign className="w-4 h-4 text-emerald-500" />
                                          <span>Registrar Pagamento</span>
                                        </button>
                                        
                                        <button
                                          onClick={() => {
                                            handleEnviarWhatsApp(parcela);
                                            setMenuAbertoId(null);
                                          }}
                                          className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-foreground hover:bg-muted transition-colors"
                                          data-testid={`enviar-whatsapp-${parcela.id}`}
                                        >
                                          <MessageCircle className="w-4 h-4 text-green-500" />
                                          <span>Enviar WhatsApp</span>
                                        </button>
                                        
                                        <div className="border-t border-border my-1"></div>
                                        
                                        <button
                                          onClick={() => {
                                            handleExcluirParcela(parcela);
                                            setMenuAbertoId(null);
                                          }}
                                          className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-destructive hover:bg-destructive/10 transition-colors"
                                          data-testid={`excluir-parcela-${parcela.id}`}
                                        >
                                          <Trash2 className="w-4 h-4" />
                                          <span>Excluir Parcela</span>
                                        </button>
                                      </div>
                                    </div>
                                  </>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Versão Mobile - Cards Melhorados */}
                <div className="md:hidden divide-y divide-border">
                  {parcelasPendentes.map((parcela) => {
                    const valorDevido = parcela.valor_total - parcela.valor_pago;
                    return (
                      <div key={parcela.id} className="p-4 hover:bg-muted/30 transition-colors" data-testid={`parcela-card-${parcela.id}`}>
                        {/* Cabeçalho do Card */}
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-start space-x-3 flex-1">
                            <div className="flex-shrink-0">
                              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                                <span className="text-primary font-bold text-lg">
                                  {parcela.cliente_nome ? parcela.cliente_nome.charAt(0).toUpperCase() : '?'}
                                </span>
                              </div>
                            </div>
                            <div className="flex-1 min-w-0">
                              <h3 className="font-bold text-foreground text-base truncate">
                                {parcela.cliente_nome || 'Cliente não encontrado'}
                              </h3>
                              <p className="text-xs text-muted-foreground mt-0.5">
                                {parcela.cliente_telefone || 'Telefone não informado'}
                              </p>
                              <div className="mt-1.5">
                                <span className={`inline-flex items-center px-2 py-0.5 text-xs font-bold rounded-full ${
                                  parcela.status === 'atrasado'
                                    ? 'bg-red-500/20 text-red-400'
                                    : parcela.status === 'parcial'
                                      ? 'bg-amber-500/20 text-amber-400'
                                      : 'bg-blue-500/20 text-blue-400'
                                }`}>
                                  {parcela.status === 'atrasado' ? '⚠️ ATRASADO' :
                                    parcela.status === 'parcial' ? '⏳ PARCIAL' : '📅 PENDENTE'}
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
                              {formatarMoeda(parcela.valor_emprestimo || 0)}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-muted-foreground flex items-center">
                              <svg className="w-3.5 h-3.5 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd"/>
                              </svg>
                              Taxa de Juros
                            </span>
                            <span className="font-semibold text-foreground">
                              {parcela.taxa_juros || 0}% a.m.
                            </span>
                          </div>
                        </div>

                        {/* Detalhes da Parcela */}
                        <div className="space-y-2.5 text-sm mb-3">
                          <div className="flex justify-between items-center">
                            <span className="text-muted-foreground font-medium">Parcela:</span>
                            <span className="font-bold text-foreground">
                              {parcela.numero_parcela}/{parcela.total_parcelas || '?'}
                            </span>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="text-muted-foreground font-medium">Vencimento:</span>
                            <div className="text-right">
                              <div className="text-foreground font-semibold">
                                {formatarData(parcela.data_vencimento)}
                              </div>
                              {parcela.dias_atraso > 0 && (
                                <div className="flex items-center justify-end mt-0.5">
                                  <svg className="w-3 h-3 text-red-500 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
                                  </svg>
                                  <span className="text-xs text-red-500 font-bold">
                                    {parcela.dias_atraso}d de atraso
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                          <div className="flex justify-between items-center pt-2 border-t border-border">
                            <span className="text-muted-foreground font-medium">Valor a Pagar:</span>
                            <div className="text-right">
                              <div className="font-bold text-foreground text-lg">
                                {formatarMoeda(valorDevido)}
                              </div>
                              {(parcela.valor_multa > 0 || parcela.valor_juros_mora > 0) && (
                                <div className="text-xs text-red-500 font-semibold mt-0.5">
                                  + {formatarMoeda((parcela.valor_multa || 0) + (parcela.valor_juros_mora || 0))} multa
                                </div>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Menu de Ações */}
                        <div className="space-y-2">
                          <button
                            onClick={() => handleRegistrarPagamento(parcela)}
                            className="w-full flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white font-semibold py-3 px-4 rounded-lg transition-colors shadow-sm"
                            data-testid={`registrar-pagamento-mobile-${parcela.id}`}
                          >
                            <DollarSign className="w-4 h-4" />
                            <span>Registrar Pagamento</span>
                          </button>
                          
                          <div className="grid grid-cols-2 gap-2">
                            <button
                              onClick={() => handleEnviarWhatsApp(parcela)}
                              className="flex items-center justify-center gap-2 bg-green-500 hover:bg-green-600 text-white font-medium py-2.5 px-4 rounded-lg transition-colors text-sm"
                              data-testid={`enviar-whatsapp-mobile-${parcela.id}`}
                            >
                              <MessageCircle className="w-4 h-4" />
                              <span>WhatsApp</span>
                            </button>
                            
                            <button
                              onClick={() => handleExcluirParcela(parcela)}
                              className="flex items-center justify-center gap-2 bg-red-500 hover:bg-red-600 text-white font-medium py-2.5 px-4 rounded-lg transition-colors text-sm"
                              data-testid={`excluir-parcela-mobile-${parcela.id}`}
                            >
                              <Trash2 className="w-4 h-4" />
                              <span>Excluir</span>
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        )}

        {/* Tab: Histórico */}
        {activeTab === 'historico' && (
          <>
            {/* Filtros */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
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
                <label className="block text-sm font-medium text-foreground mb-2">Data</label>
                <DatePickerBR
                  value={filtroData}
                  onChange={setFiltroData}
                  placeholder="Selecione uma data"
                  testId="filtro-data"
                  clearable={true}
                />
              </div>
              <div className="bg-card rounded-lg border border-border p-4 flex items-end">
                <button
                  onClick={() => { setFiltroMetodo(''); setFiltroData(null); }}
                  className="w-full px-4 py-2 bg-muted hover:bg-muted/80 text-foreground rounded-md text-sm font-medium transition"
                  data-testid="limpar-filtros-button"
                >
                  Limpar Filtros
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
                                {pagamento.numero_parcela || '-'}/{pagamento.total_parcelas || '?'}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                Parcela
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
                            </td>
                            <td className="px-6 py-4">
                              <div className="text-sm text-muted-foreground max-w-xs truncate">
                                {pagamento.observacoes || '-'}
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
                              <div className="mt-1.5">
                                <span className="inline-flex items-center px-2 py-0.5 text-xs font-bold rounded-full bg-emerald-500/20 text-emerald-400">
                                  ✓ PAGO
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
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" data-testid="pagamento-modal">
          <div className="bg-card rounded-lg border border-border shadow-xl max-w-md w-full">
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
