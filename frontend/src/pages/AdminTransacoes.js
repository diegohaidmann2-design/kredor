import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import { adminTransacoesAPI } from '../api/api';
import { toast } from '../hooks/use-toast';

// Adicionar estilo inline para animação
const styles = `
  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  .animate-fade-in {
    animation: fadeIn 0.3s ease-in-out;
  }
`;

const AdminTransacoes = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [atualizando, setAtualizando] = useState(false);
  const [mensagemSucesso, setMensagemSucesso] = useState('');
  const [metricas, setMetricas] = useState(null);
  const [transacoes, setTransacoes] = useState([]);
  const [filtros, setFiltros] = useState({
    status: '',
    metodo: '',
    email: '',
    skip: 0,
    limit: 50
  });
  const [abaAtiva, setAbaAtiva] = useState('todas'); // todas, pix-pendentes, cartoes-recusados
  const [modalAberto, setModalAberto] = useState(null);
  const [transacaoSelecionada, setTransacaoSelecionada] = useState(null);

  // Helper para mostrar mensagens
  const showToast = (message, type = 'info') => {
    const bgColors = {
      success: 'bg-green-600',
      error: 'bg-red-600',
      info: 'bg-blue-600'
    };

    const toastEl = document.createElement('div');
    toastEl.className = `fixed top-4 right-4 ${bgColors[type]} text-white px-6 py-3 rounded-lg shadow-lg z-50 transition-opacity`;
    toastEl.textContent = message;
    document.body.appendChild(toastEl);

    setTimeout(() => {
      toastEl.style.opacity = '0';
      setTimeout(() => toastEl.remove(), 300);
    }, 3000);
  };

  useEffect(() => {
    carregarDados();
  }, [abaAtiva, filtros]);

  const carregarDados = async (mostrarMensagem = false) => {
    if (mostrarMensagem) {
      setAtualizando(true);
    }

    try {
      if (!mostrarMensagem) {
        setLoading(true);
      }

      // 1. Carregar Métricas
      const resMetricas = await adminTransacoesAPI.metricas();
      setMetricas(resMetricas.data);

      // 2. Carregar Transações (baseado na aba)
      const listarPorAba = {
        'pix-pendentes': adminTransacoesAPI.listarPixPendentes,
        'cartoes-recusados': adminTransacoesAPI.listarCartoesRecusados,
      };
      const listar = listarPorAba[abaAtiva] || adminTransacoesAPI.listar;
      const resTransacoes = await listar(filtros);
      setTransacoes(resTransacoes.data.transacoes || []);

      if (mostrarMensagem) {
        setMensagemSucesso('Transações atualizadas com sucesso!');
        setTimeout(() => setMensagemSucesso(''), 3000);
      }

    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível carregar dados.", variant: 'destructive' });
      console.error('Erro ao carregar dados:', error);
      showToast(error.message || 'Erro ao carregar dados', 'error');
    } finally {
      setLoading(false);
      setAtualizando(false);
    }
  };

  const handleAtualizar = () => {
    carregarDados(true);
  };

  const enviarEmailRecuperacao = async (transacaoId) => {
    try {
      await adminTransacoesAPI.enviarEmail(transacaoId);
      showToast('Email de recuperação enviado!', 'success');
      carregarDados();
      setModalAberto(null);
    } catch (error) {
      showToast('Erro ao enviar email', 'error');
    }
  };

  const gerarCupom = async (transacaoId, desconto) => {
    try {
      const { data } = await adminTransacoesAPI.gerarCupomTransacao(transacaoId, desconto);
      showToast(`Cupom gerado: ${data.cupom}`);
      carregarDados();
      setModalAberto(null);
    } catch (error) {
      showToast('Erro ao gerar cupom', 'error');
    }
  };

  const formatarData = (data) => {
    if (!data) return '-';
    return new Date(data).toLocaleString('pt-BR');
  };

  const formatarValor = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor);
  };

  const getStatusBadge = (status) => {
    const cores = {
      pendente: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
      processando: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
      aprovado: 'bg-green-500/10 text-green-400 border-green-500/30',
      recusado: 'bg-red-500/10 text-red-400 border-red-500/30',
      expirado: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
      cancelado: 'bg-orange-500/10 text-orange-400 border-orange-500/30'
    };

    return (
      <span className={`px-2 py-1 rounded-full text-xs font-semibold border ${cores[status] || cores.pendente}`}>
        {status.toUpperCase()}
      </span>
    );
  };

  if (loading && !metricas) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <style>{styles}</style>
      <div className="container mx-auto px-4 py-8">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-foreground">Monitoramento de Transações</h1>
              <p className="text-muted-foreground mt-1">
                Gerencie pagamentos não concluídos e recupere vendas perdidas
              </p>
            </div>
            <button
              onClick={handleAtualizar}
              disabled={atualizando}
              className={`px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition flex items-center gap-2 ${atualizando ? 'opacity-50 cursor-not-allowed' : ''
                }`}
            >
              <svg className={`w-5 h-5 ${atualizando ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {atualizando ? 'Atualizando...' : 'Atualizar'}
            </button>
          </div>

          {/* Mensagem de Sucesso */}
          {mensagemSucesso && (
            <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg flex items-center gap-2 animate-fade-in">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {mensagemSucesso}
            </div>
          )}

          {/* Cards de Métricas */}
          {metricas && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-card rounded-lg p-6 border border-border">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Transações</p>
                    <p className="text-3xl font-bold text-foreground mt-1">{metricas.total_transacoes}</p>
                  </div>
                  <div className="p-3 bg-blue-500/10 rounded-lg">
                    <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-2">{metricas.periodo}</p>
              </div>

              <div className="bg-card rounded-lg p-6 border border-border">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">PIX Pendentes</p>
                    <p className="text-3xl font-bold text-yellow-400 mt-1">{metricas.pix_pendentes}</p>
                  </div>
                  <div className="p-3 bg-yellow-500/10 rounded-lg">
                    <svg className="w-8 h-8 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-2">Aguardando pagamento</p>
              </div>

              <div className="bg-card rounded-lg p-6 border border-border">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Cartões Recusados</p>
                    <p className="text-3xl font-bold text-red-400 mt-1">{metricas.cartoes_recusados}</p>
                  </div>
                  <div className="p-3 bg-red-500/10 rounded-lg">
                    <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </div>
                </div>
                <p className="text-xs text-red-400 mt-2">-{formatarValor(metricas.valor_perdido)}</p>
              </div>

              <div className="bg-card rounded-lg p-6 border border-border">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Taxa de Conversão</p>
                    <p className="text-3xl font-bold text-green-400 mt-1">{metricas.taxa_conversao}%</p>
                  </div>
                  <div className="p-3 bg-green-500/10 rounded-lg">
                    <svg className="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                    </svg>
                  </div>
                </div>
                <p className="text-xs text-green-400 mt-2">+{formatarValor(metricas.valor_aprovado)}</p>
              </div>
            </div>
          )}

          {/* Abas */}
          <div className="bg-card rounded-lg border border-border overflow-hidden">
            <div className="flex border-b border-border overflow-x-auto">
              <button
                onClick={() => setAbaAtiva('todas')}
                className={`px-6 py-4 font-medium transition ${abaAtiva === 'todas'
                  ? 'bg-purple-500/10 text-purple-400 border-b-2 border-purple-500'
                  : 'text-muted-foreground hover:bg-muted/50'
                  }`}
              >
                Todas as Transações
              </button>
              <button
                onClick={() => setAbaAtiva('pix-pendentes')}
                className={`px-6 py-4 font-medium transition ${abaAtiva === 'pix-pendentes'
                  ? 'bg-yellow-500/10 text-yellow-400 border-b-2 border-yellow-500'
                  : 'text-muted-foreground hover:bg-muted/50'
                  }`}
              >
                PIX Pendentes
              </button>
              <button
                onClick={() => setAbaAtiva('cartoes-recusados')}
                className={`px-6 py-4 font-medium transition ${abaAtiva === 'cartoes-recusados'
                  ? 'bg-red-500/10 text-red-400 border-b-2 border-red-500'
                  : 'text-muted-foreground hover:bg-muted/50'
                  }`}
              >
                Cartões Recusados
              </button>
            </div>

            {/* Filtros */}
            <div className="p-4 bg-muted/30 border-b border-border">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <input
                  type="text"
                  placeholder="Buscar por email..."
                  value={filtros.email}
                  onChange={(e) => setFiltros({ ...filtros, email: e.target.value, skip: 0 })}
                  className="px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
                <select
                  value={filtros.status}
                  onChange={(e) => setFiltros({ ...filtros, status: e.target.value, skip: 0 })}
                  className="px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="">Todos os status</option>
                  <option value="pendente">Pendente</option>
                  <option value="processando">Processando</option>
                  <option value="aprovado">Aprovado</option>
                  <option value="recusado">Recusado</option>
                  <option value="expirado">Expirado</option>
                </select>
                <select
                  value={filtros.metodo}
                  onChange={(e) => setFiltros({ ...filtros, metodo: e.target.value, skip: 0 })}
                  className="px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="">Todos os métodos</option>
                  <option value="pix">PIX</option>
                  <option value="cartao_credito">Cartão de Crédito</option>
                </select>
                <button
                  onClick={() => setFiltros({ status: '', metodo: '', email: '', skip: 0, limit: 50 })}
                  className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
                >
                  Limpar Filtros
                </button>
              </div>
            </div>

            {/* Tabela de Transações */}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Data</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Cliente</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Plano</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Valor</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Método</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {transacoes.length === 0 ? (
                    <tr>
                      <td colSpan="7" className="px-4 py-8 text-center text-muted-foreground">
                        Nenhuma transação encontrada
                      </td>
                    </tr>
                  ) : (
                    transacoes.map((transacao) => (
                      <tr key={transacao.id} className="hover:bg-muted/30 transition">
                        <td className="px-4 py-3 text-sm text-foreground">
                          {formatarData(transacao.criado_em)}
                        </td>
                        <td className="px-4 py-3">
                          <div>
                            <p className="text-sm font-medium text-foreground">{transacao.usuario_nome}</p>
                            <p className="text-xs text-muted-foreground">{transacao.usuario_email}</p>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-foreground">{transacao.plano_nome}</td>
                        <td className="px-4 py-3 text-sm font-semibold text-foreground">
                          {formatarValor(transacao.valor)}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className="px-2 py-1 bg-blue-500/10 text-blue-400 rounded text-xs">
                            {transacao.metodo_pagamento === 'pix' ? 'PIX' : 'Cartão'}
                          </span>
                        </td>
                        <td className="px-4 py-3">{getStatusBadge(transacao.status)}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            {!transacao.email_enviado && (
                              <button
                                onClick={() => {
                                  setTransacaoSelecionada(transacao);
                                  setModalAberto('email');
                                }}
                                className="p-2 bg-blue-500/10 text-blue-400 rounded hover:bg-blue-500/20 transition"
                                title="Enviar Email"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                                </svg>
                              </button>
                            )}
                            {!transacao.cupom_gerado && (
                              <button
                                onClick={() => {
                                  setTransacaoSelecionada(transacao);
                                  setModalAberto('cupom');
                                }}
                                className="p-2 bg-green-500/10 text-green-400 rounded hover:bg-green-500/20 transition"
                                title="Gerar Cupom"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                              </button>
                            )}
                            <button
                              onClick={() => {
                                setTransacaoSelecionada(transacao);
                                setModalAberto('detalhes');
                              }}
                              className="p-2 bg-purple-500/10 text-purple-400 rounded hover:bg-purple-500/20 transition"
                              title="Ver Detalhes"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                              </svg>
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Modal de Email */}
          {modalAberto === 'email' && transacaoSelecionada && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setModalAberto(null)}>
              <div className="bg-card rounded-lg p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
                <h3 className="text-xl font-bold text-foreground mb-4">Enviar Email de Recuperação</h3>
                <p className="text-muted-foreground mb-6">
                  Deseja enviar um email de recuperação para <strong>{transacaoSelecionada.usuario_email}</strong>?
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={() => enviarEmailRecuperacao(transacaoSelecionada.id)}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                  >
                    Enviar Email
                  </button>
                  <button
                    onClick={() => setModalAberto(null)}
                    className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Modal de Cupom */}
          {modalAberto === 'cupom' && transacaoSelecionada && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setModalAberto(null)}>
              <div className="bg-card rounded-lg p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
                <h3 className="text-xl font-bold text-foreground mb-4">Gerar Cupom de Desconto</h3>
                <p className="text-muted-foreground mb-4">
                  Gerar cupom para <strong>{transacaoSelecionada.usuario_email}</strong>
                </p>
                <div className="space-y-3">
                  <button
                    onClick={() => gerarCupom(transacaoSelecionada.id, 10)}
                    className="w-full px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition text-left"
                  >
                    <span className="font-semibold">10% de desconto</span>
                    <span className="block text-sm text-green-200">Economia: {formatarValor(transacaoSelecionada.valor * 0.1)}</span>
                  </button>
                  <button
                    onClick={() => gerarCupom(transacaoSelecionada.id, 15)}
                    className="w-full px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition text-left"
                  >
                    <span className="font-semibold">15% de desconto</span>
                    <span className="block text-sm text-green-200">Economia: {formatarValor(transacaoSelecionada.valor * 0.15)}</span>
                  </button>
                  <button
                    onClick={() => gerarCupom(transacaoSelecionada.id, 20)}
                    className="w-full px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition text-left"
                  >
                    <span className="font-semibold">20% de desconto</span>
                    <span className="block text-sm text-green-200">Economia: {formatarValor(transacaoSelecionada.valor * 0.2)}</span>
                  </button>
                  <button
                    onClick={() => setModalAberto(null)}
                    className="w-full px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Modal de Detalhes */}
          {modalAberto === 'detalhes' && transacaoSelecionada && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 overflow-y-auto" onClick={() => setModalAberto(null)}>
              <div className="bg-card rounded-lg p-6 max-w-2xl w-full mx-4 my-8" onClick={(e) => e.stopPropagation()}>
                <h3 className="text-xl font-bold text-foreground mb-4">Detalhes da Transação</h3>

                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">ID da Transação</p>
                      <p className="text-sm font-mono text-foreground">{transacaoSelecionada.id}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Data</p>
                      <p className="text-sm text-foreground">{formatarData(transacaoSelecionada.criado_em)}</p>
                    </div>
                  </div>

                  <div className="border-t border-border pt-4">
                    <h4 className="font-semibold text-foreground mb-2">Dados do Cliente</h4>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <p className="text-sm text-muted-foreground">Nome</p>
                        <p className="text-sm text-foreground">{transacaoSelecionada.usuario_nome}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Email</p>
                        <p className="text-sm text-foreground">{transacaoSelecionada.usuario_email}</p>
                      </div>
                      {transacaoSelecionada.usuario_cpf && (
                        <div>
                          <p className="text-sm text-muted-foreground">CPF</p>
                          <p className="text-sm text-foreground">{transacaoSelecionada.usuario_cpf}</p>
                        </div>
                      )}
                      {transacaoSelecionada.usuario_telefone && (
                        <div>
                          <p className="text-sm text-muted-foreground">Telefone</p>
                          <p className="text-sm text-foreground">{transacaoSelecionada.usuario_telefone}</p>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="border-t border-border pt-4">
                    <h4 className="font-semibold text-foreground mb-2">Dados do Pagamento</h4>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <p className="text-sm text-muted-foreground">Plano</p>
                        <p className="text-sm text-foreground">{transacaoSelecionada.plano_nome}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Valor</p>
                        <p className="text-sm font-semibold text-foreground">{formatarValor(transacaoSelecionada.valor)}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Método</p>
                        <p className="text-sm text-foreground">
                          {transacaoSelecionada.metodo_pagamento === 'pix' ? 'PIX' : 'Cartão de Crédito'}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Status</p>
                        <div className="mt-1">{getStatusBadge(transacaoSelecionada.status)}</div>
                      </div>
                      {transacaoSelecionada.payment_id && (
                        <div>
                          <p className="text-sm text-muted-foreground">Payment ID</p>
                          <p className="text-sm font-mono text-foreground">{transacaoSelecionada.payment_id}</p>
                        </div>
                      )}
                      {transacaoSelecionada.motivo_recusa && (
                        <div className="col-span-2">
                          <p className="text-sm text-muted-foreground">Motivo da Recusa</p>
                          <p className="text-sm text-red-400">{transacaoSelecionada.motivo_recusa}</p>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="border-t border-border pt-4">
                    <h4 className="font-semibold text-foreground mb-2">Remarketing</h4>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <p className="text-sm text-muted-foreground">Email Enviado</p>
                        <p className="text-sm text-foreground">
                          {transacaoSelecionada.email_enviado ? (
                            <span className="text-green-400">✓ Sim - {formatarData(transacaoSelecionada.data_email)}</span>
                          ) : (
                            <span className="text-gray-400">✗ Não</span>
                          )}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Cupom Gerado</p>
                        <p className="text-sm text-foreground">
                          {transacaoSelecionada.cupom_gerado ? (
                            <span className="text-green-400 font-mono">{transacaoSelecionada.cupom_gerado}</span>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-6 flex justify-end">
                  <button
                    onClick={() => setModalAberto(null)}
                    className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
                  >
                    Fechar
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default AdminTransacoes;
