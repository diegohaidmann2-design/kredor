import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import ScoreBadge from '../components/ScoreBadge';
import { analiseAPI } from '../api/api';
import { Search, RefreshCw, Eye, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { toast } from '../hooks/use-toast';

const AnaliseClientes = () => {
  const [clientes, setClientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState({
    classificacao: '',
    score_min: '',
    score_max: '',
    ordenar: 'score_desc'
  });
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [clienteSelecionado, setClienteSelecionado] = useState(null);
  const [showDetalheModal, setShowDetalheModal] = useState(false);
  const [detalhesScore, setDetalhesScore] = useState(null);
  const [loadingDetalhes, setLoadingDetalhes] = useState(false);

  useEffect(() => {
    carregarClientes();
  }, [filtros, page]);

  const carregarClientes = async () => {
    try {
      setLoading(true);
      // Filter out empty string values to avoid 422 validation errors
      const params = {
        page,
        limit: 50,
        ordenar: filtros.ordenar
      };
      // Only add filters if they have valid values
      if (filtros.classificacao) params.classificacao = filtros.classificacao;
      if (filtros.score_min !== '' && filtros.score_min !== null && filtros.score_min !== undefined) {
        params.score_min = parseInt(filtros.score_min);
      }
      if (filtros.score_max !== '' && filtros.score_max !== null && filtros.score_max !== undefined) {
        params.score_max = parseInt(filtros.score_max);
      }
      
      const response = await analiseAPI.listarClientesComScore(params);
      setClientes(response.data.clientes);
      setTotal(response.data.total);
    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível carregar clientes.", variant: 'destructive' });
      console.error('Erro ao carregar clientes:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFiltroChange = (campo, valor) => {
    setFiltros(prev => ({ ...prev, [campo]: valor }));
    setPage(1);
  };

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor);
  };

  const formatarData = (data) => {
    if (!data) return '-';
    return new Date(data).toLocaleDateString('pt-BR');
  };

  const handleVerDetalhes = async (cliente) => {
    setClienteSelecionado(cliente);
    setShowDetalheModal(true);
    setLoadingDetalhes(true);
    
    try {
      const response = await analiseAPI.obterDetalheScore(cliente.id);
      setDetalhesScore(response.data);
    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível carregar detalhes.", variant: 'destructive' });
      console.error('Erro ao carregar detalhes:', error);
    } finally {
      setLoadingDetalhes(false);
    }
  };

  const handleRecalcular = async (clienteId) => {
    try {
      await analiseAPI.recalcularScore(clienteId);
      carregarClientes();
      alert('Score recalculado com sucesso!');
    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível recalcular.", variant: 'destructive' });
      console.error('Erro ao recalcular:', error);
      alert('Erro ao recalcular score');
    }
  };

  const getRecomendacaoTexto = (recomendacao) => {
    const recomendacoes = {
      'elegivel_taxa_reduzida': '✅ Elegível para taxa reduzida',
      'elegivel_normal': '✅ Elegível para crédito normal',
      'analise_caso_a_caso': '⚠️ Requer análise detalhada',
      'condicoes_restritivas': '⚠️ Apenas com condições restritivas',
      'negar_credito': '❌ Não recomendado para crédito'
    };
    return recomendacoes[recomendacao] || recomendacao;
  };

  if (loading && clientes.length === 0) {
    return <Loading message="Carregando clientes..." />;
  }

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <div className="space-y-8">
          {/* Header */}
          <div>
            <h1 className="text-2xl sm:text-3xl font-display font-bold text-foreground">
              Clientes com Score
            </h1>
            <p className="text-muted-foreground mt-2 text-base">
              Análise detalhada de {total} clientes
            </p>
          </div>

        {/* Filtros */}
        <div className="bg-card rounded-xl border border-border p-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Classificação */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Classificação
              </label>
              <select
                value={filtros.classificacao}
                onChange={(e) => handleFiltroChange('classificacao', e.target.value)}
                className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">Todas</option>
                <option value="A">🟢 A - Excelente</option>
                <option value="B">🔵 B - Bom</option>
                <option value="C">🟡 C - Regular</option>
                <option value="D">🟠 D - Risco</option>
                <option value="E">🔴 E - Alto Risco</option>
              </select>
            </div>

            {/* Score Mínimo */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Score Mínimo
              </label>
              <input
                type="number"
                min="0"
                max="100"
                value={filtros.score_min}
                onChange={(e) => handleFiltroChange('score_min', e.target.value)}
                placeholder="0"
                className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {/* Score Máximo */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Score Máximo
              </label>
              <input
                type="number"
                min="0"
                max="100"
                value={filtros.score_max}
                onChange={(e) => handleFiltroChange('score_max', e.target.value)}
                placeholder="100"
                className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {/* Ordenar */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">
                Ordenar por
              </label>
              <select
                value={filtros.ordenar}
                onChange={(e) => handleFiltroChange('ordenar', e.target.value)}
                className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="score_desc">Score (maior primeiro)</option>
                <option value="score_asc">Score (menor primeiro)</option>
                <option value="nome">Nome</option>
              </select>
            </div>
          </div>
        </div>

        {/* Tabela/Cards */}
        <div className="bg-card rounded-xl border border-border overflow-hidden">
          {/* Versão Desktop - Tabela */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted/50 border-b border-border">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Cliente</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Score</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Classificação</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Emp. Ativos</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Total Devido</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Último Pagto</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {clientes.map((cliente) => (
                  <motion.tr
                    key={cliente.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="hover:bg-muted/50"
                  >
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-foreground">{cliente.nome}</p>
                        <p className="text-xs text-muted-foreground">
                          {cliente.cpf_cnpj?.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '***.$2.***-**')}
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-2xl font-bold text-primary">{cliente.score.toFixed(1)}</div>
                    </td>
                    <td className="px-4 py-3">
                      <ScoreBadge score={cliente.score} classificacao={cliente.classificacao} size="sm" />
                    </td>
                    <td className="px-4 py-3 text-foreground">{cliente.emprestimos_ativos}</td>
                    <td className="px-4 py-3 text-foreground font-medium">
                      {formatarMoeda(cliente.total_devido)}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground text-sm">
                      {formatarData(cliente.ultimo_pagamento)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleVerDetalhes(cliente)}
                          className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition"
                          title="Ver Detalhes do Score"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleRecalcular(cliente.id)}
                          className="p-2 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded-lg transition"
                          title="Recalcular Score"
                        >
                          <RefreshCw className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Versão Mobile - Cards */}
          <div className="md:hidden divide-y divide-border">
            {clientes.map((cliente) => (
              <motion.div
                key={cliente.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="p-4"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h3 className="font-semibold text-foreground">{cliente.nome}</h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {cliente.cpf_cnpj?.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '***.$2.***-**')}
                    </p>
                  </div>
                  <div className="text-2xl font-bold text-primary">{cliente.score.toFixed(1)}</div>
                </div>
                
                <div className="mb-3">
                  <ScoreBadge score={cliente.score} classificacao={cliente.classificacao} size="sm" />
                </div>

                <div className="space-y-2 text-sm mb-3">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Empréstimos Ativos:</span>
                    <span className="text-foreground font-medium">{cliente.emprestimos_ativos}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Total Devido:</span>
                    <span className="text-foreground font-medium">{formatarMoeda(cliente.total_devido)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Último Pagamento:</span>
                    <span className="text-foreground">{formatarData(cliente.ultimo_pagamento)}</span>
                  </div>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => handleVerDetalhes(cliente)}
                    className="flex-1 inline-flex items-center justify-center gap-2 px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition text-sm font-medium"
                  >
                    <Eye className="w-4 h-4" />
                    Ver Detalhes
                  </button>
                  <button
                    onClick={() => handleRecalcular(cliente.id)}
                    className="px-3 py-2 bg-muted text-foreground rounded-lg hover:bg-muted/80 transition"
                    title="Recalcular"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Paginação */}
        {total > 50 && (
          <div className="flex justify-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 bg-card border border-border rounded-lg disabled:opacity-50"
            >
              Anterior
            </button>
            <span className="px-4 py-2 text-foreground">
              Página {page} de {Math.ceil(total / 50)}
            </span>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={page >= Math.ceil(total / 50)}
              className="px-4 py-2 bg-card border border-border rounded-lg disabled:opacity-50"
            >
              Próxima
            </button>
          </div>
        )}

        {/* Modal de Detalhes (próxima parte) */}
        {showDetalheModal && (
          <ModalDetalhesScore
            cliente={clienteSelecionado}
            detalhes={detalhesScore}
            loading={loadingDetalhes}
            onClose={() => setShowDetalheModal(false)}
            getRecomendacaoTexto={getRecomendacaoTexto}
            formatarMoeda={formatarMoeda}
          />
        )}
        </div>
      </div>
    </Layout>
  );
};

// Componente de Modal de Detalhes (continua na próxima mensagem devido ao tamanho)
const ModalDetalhesScore = ({ cliente, detalhes, loading, onClose, getRecomendacaoTexto, formatarMoeda }) => {
  if (!cliente) return null;

  return (
    <div 
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50"
      onClick={onClose}
    >
      <div 
        className="bg-card rounded-xl border border-border shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6">
          {/* Header */}
          <div className="flex items-start justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold text-foreground">Score de Crédito</h2>
              <p className="text-muted-foreground mt-1">{cliente.nome}</p>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {loading ? (
            <div className="py-12 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
              <p className="text-muted-foreground mt-4">Carregando detalhes...</p>
            </div>
          ) : detalhes ? (
            <div className="space-y-6">
              {/* Score Principal */}
              <div className="text-center py-6 bg-muted/30 rounded-lg">
                <div className="text-6xl font-bold text-primary mb-2">{detalhes.score.toFixed(1)}</div>
                <ScoreBadge score={detalhes.score} classificacao={detalhes.classificacao} size="lg" />
              </div>

              {/* Componentes do Score */}
              <div>
                <h3 className="text-lg font-semibold text-foreground mb-4">Componentes do Score</h3>
                <div className="space-y-3">
                  {Object.entries(detalhes.componentes).map(([key, comp]) => (
                    <div key={key} className="bg-muted/30 p-4 rounded-lg">
                      <div className="flex justify-between mb-2">
                        <span className="text-sm font-medium text-foreground capitalize">
                          {key.replace('_', ' ')}
                        </span>
                        <span className="text-sm font-bold text-foreground">
                          {comp.pontos.toFixed(1)}/{comp.maximo} pts
                        </span>
                      </div>
                      <div className="w-full bg-muted rounded-full h-2">
                        <div 
                          className="bg-primary h-2 rounded-full transition-all"
                          style={{ width: `${comp.percentual}%` }}
                        ></div>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">{comp.percentual.toFixed(1)}%</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Métricas */}
              <div>
                <h3 className="text-lg font-semibold text-foreground mb-4">Estatísticas</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-muted/30 p-3 rounded-lg">
                    <p className="text-xs text-muted-foreground">Total Empréstimos</p>
                    <p className="text-xl font-bold text-foreground">{detalhes.metricas.total_emprestimos}</p>
                  </div>
                  <div className="bg-muted/30 p-3 rounded-lg">
                    <p className="text-xs text-muted-foreground">Empréstimos Quitados</p>
                    <p className="text-xl font-bold text-emerald-500">{detalhes.metricas.emprestimos_quitados}</p>
                  </div>
                  <div className="bg-muted/30 p-3 rounded-lg">
                    <p className="text-xs text-muted-foreground">Taxa de Pontualidade</p>
                    <p className="text-xl font-bold text-foreground">{detalhes.metricas.taxa_pontualidade}%</p>
                  </div>
                  <div className="bg-muted/30 p-3 rounded-lg">
                    <p className="text-xs text-muted-foreground">Média Dias Atraso</p>
                    <p className="text-xl font-bold text-foreground">{detalhes.metricas.media_dias_atraso}</p>
                  </div>
                </div>
              </div>

              {/* Recomendação */}
              <div className="bg-primary/10 border border-primary/20 p-4 rounded-lg">
                <h3 className="text-sm font-semibold text-foreground mb-2">Recomendação</h3>
                <p className="text-foreground">{getRecomendacaoTexto(detalhes.recomendacao)}</p>
              </div>

              {/* Ações */}
              <div className="flex gap-3 pt-4 border-t border-border">
                <Link
                  to={`/clientes/${cliente.id}/emprestimos`}
                  className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition"
                >
                  Ver Empréstimos
                </Link>
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-muted text-foreground rounded-lg hover:bg-muted/80 transition"
                >
                  Fechar
                </button>
              </div>
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-8">Erro ao carregar detalhes</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default AnaliseClientes;
