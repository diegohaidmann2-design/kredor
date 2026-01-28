import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import ErrorMessage from '../components/ErrorMessage';
import Button from '../components/Button';
import { useModal } from '../components/Modal';
import { pagamentosAPI, parcelasAPI } from '../api/api';
import { formatarMoeda, formatarData, formatarDataHora } from '../utils/formatters';
import { DatePickerBR } from '../components/ui/date-picker-br';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

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
  const [showModal, setShowModal] = useState(false);
  const [parcelaSelecionada, setParcelaSelecionada] = useState(null);
  const [activeTab, setActiveTab] = useState('historico');
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

  if (loading) return <Loading message="Carregando pagamentos..." />;

  return (
    <Layout>
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
            {parcelasPendentes.length === 0 ? (
              <div className="p-8 text-center" data-testid="sem-parcelas-message">
                <p className="text-muted-foreground">Nenhuma parcela pendente</p>
              </div>
            ) : (
              <>
                {/* Versão Desktop - Tabela */}
                <div className="hidden md:block overflow-x-auto">
                  <table className="min-w-full divide-y divide-border">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Cliente</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Parcela</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Vencimento</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Valor</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Ações</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {parcelasPendentes.map((parcela) => {
                        const valorDevido = parcela.valor_total - parcela.valor_pago;
                        return (
                          <tr key={parcela.id} data-testid={`parcela-row-${parcela.id}`} className="hover:bg-muted/50">
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm font-medium text-foreground">{parcela.cliente_nome}</div>
                              <div className="text-xs text-muted-foreground">Emp: {formatarMoeda(parcela.valor_emprestimo)}</div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                              {parcela.numero_parcela}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                              {formatarData(parcela.data_vencimento)}
                              {parcela.dias_atraso > 0 && (
                                <span className="ml-2 text-red-500 text-xs font-medium">
                                  ({parcela.dias_atraso}d atraso)
                                </span>
                              )}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm font-medium text-foreground">{formatarMoeda(valorDevido)}</div>
                              {(parcela.valor_multa > 0 || parcela.valor_juros_mora > 0) && (
                                <div className="text-xs text-red-500">
                                  + {formatarMoeda((parcela.valor_multa || 0) + (parcela.valor_juros_mora || 0))} multa
                                </div>
                              )}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`px-2 py-1 text-xs font-semibold rounded-full ${parcela.status === 'atrasado'
                                  ? 'bg-red-500/20 text-red-400'
                                  : parcela.status === 'parcial'
                                    ? 'bg-amber-500/20 text-amber-400'
                                    : 'bg-blue-500/20 text-blue-400'
                                }`}>
                                {parcela.status === 'atrasado' ? 'ATRASADO' :
                                  parcela.status === 'parcial' ? 'PARCIAL' : 'PENDENTE'}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <Button
                                onClick={() => handleRegistrarPagamento(parcela)}
                                variant="primary"
                                className="text-sm px-3 py-1"
                                testId={`registrar-pagamento-${parcela.id}`}
                              >
                                Registrar Pagamento
                              </Button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Versão Mobile - Cards */}
                <div className="md:hidden divide-y divide-border">
                  {parcelasPendentes.map((parcela) => {
                    const valorDevido = parcela.valor_total - parcela.valor_pago;
                    return (
                      <div key={parcela.id} className="p-4" data-testid={`parcela-card-${parcela.id}`}>
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <h3 className="font-semibold text-foreground text-base">{parcela.cliente_nome}</h3>
                            <p className="text-xs text-muted-foreground mt-0.5">Empréstimo: {formatarMoeda(parcela.valor_emprestimo)}</p>
                            <span className={`inline-flex mt-2 px-2 py-0.5 text-xs font-semibold rounded-full ${parcela.status === 'atrasado'
                                ? 'bg-red-500/20 text-red-400'
                                : parcela.status === 'parcial'
                                  ? 'bg-amber-500/20 text-amber-400'
                                  : 'bg-blue-500/20 text-blue-400'
                              }`}>
                              {parcela.status === 'atrasado' ? 'ATRASADO' :
                                parcela.status === 'parcial' ? 'PARCIAL' : 'PENDENTE'}
                            </span>
                          </div>
                        </div>

                        <div className="space-y-2 text-sm mb-3">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Parcela:</span>
                            <span className="font-medium text-foreground">{parcela.numero_parcela}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Vencimento:</span>
                            <span className="text-foreground">
                              {formatarData(parcela.data_vencimento)}
                              {parcela.dias_atraso > 0 && (
                                <span className="ml-1 text-red-500 font-medium">
                                  ({parcela.dias_atraso}d)
                                </span>
                              )}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Valor:</span>
                            <div className="text-right">
                              <div className="font-medium text-foreground">{formatarMoeda(valorDevido)}</div>
                              {(parcela.valor_multa > 0 || parcela.valor_juros_mora > 0) && (
                                <div className="text-xs text-red-500">
                                  + {formatarMoeda((parcela.valor_multa || 0) + (parcela.valor_juros_mora || 0))} multa
                                </div>
                              )}
                            </div>
                          </div>
                        </div>

                        <Button
                          onClick={() => handleRegistrarPagamento(parcela)}
                          variant="primary"
                          className="w-full text-sm"
                          testId={`registrar-pagamento-${parcela.id}`}
                        >
                          Registrar Pagamento
                        </Button>
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
                  {/* Versão Desktop - Tabela */}
                  <div className="hidden md:block overflow-x-auto">
                    <table className="min-w-full divide-y divide-border">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Data/Hora</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Valor</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Método</th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Observações</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border" data-testid="pagamentos-table-body">
                        {pagamentosFiltrados.map((pagamento) => (
                          <tr key={pagamento.id} data-testid={`pagamento-row-${pagamento.id}`} className="hover:bg-muted/50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                              {formatarDataHora(pagamento.data_pagamento)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-emerald-500">
                              {formatarMoeda(pagamento.valor_pago)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-500/20 text-blue-400">
                                {pagamento.metodo_pagamento.toUpperCase()}
                              </span>
                            </td>
                            <td className="px-6 py-4 text-sm text-muted-foreground">
                              {pagamento.observacoes || '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Versão Mobile - Cards */}
                  <div className="md:hidden divide-y divide-border">
                    {pagamentosFiltrados.map((pagamento) => (
                      <div key={pagamento.id} className="p-4" data-testid={`pagamento-card-${pagamento.id}`}>
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <p className="text-2xl font-bold text-emerald-500">{formatarMoeda(pagamento.valor_pago)}</p>
                            <p className="text-xs text-muted-foreground mt-1">{formatarDataHora(pagamento.data_pagamento)}</p>
                          </div>
                          <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-500/20 text-blue-400">
                            {pagamento.metodo_pagamento.toUpperCase()}
                          </span>
                        </div>
                        {pagamento.observacoes && (
                          <div className="mt-2 p-2 bg-muted/50 rounded text-sm text-muted-foreground">
                            {pagamento.observacoes}
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
