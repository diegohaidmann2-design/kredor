import React, { useState, useEffect, useCallback, useMemo } from 'react';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import Button from '../components/Button';
import { useModal } from '../components/Modal';
import { superadminAPI } from '../api/api';
import { formatarMoeda, formatarData } from '../utils/formatters';
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Legend,
  BarChart, Bar
} from 'recharts';
import { 
  TrendingUp, TrendingDown, Users, DollarSign, Activity,
  Download, Eye, RefreshCw, Mail, Search, ArrowUpDown,
  ChevronLeft, ChevronRight
} from 'lucide-react';
import { toast } from '../hooks/use-toast';

const COLORS = ['#6b7280', '#3b82f6', '#8b5cf6', '#f59e0b'];

// Hook para debounce
const useDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = useState(value);
  
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    
    return () => clearTimeout(handler);
  }, [value, delay]);
  
  return debouncedValue;
};

const SuperAdmin = () => {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [usuarios, setUsuarios] = useState([]);
  const [totalUsuarios, setTotalUsuarios] = useState(0);
  const [filtro, setFiltro] = useState({ 
    ativo: '', 
    plano: '', 
    busca: '',
    dataInicio: '',
    dataFim: ''
  });
  const [ordenacao, setOrdenacao] = useState({ campo: 'created_at', direcao: 'desc' });
  const [paginacao, setPaginacao] = useState({ pagina: 1, limite: 10 });
  const [modalUsuario, setModalUsuario] = useState(null);
  const [modalDetalhes, setModalDetalhes] = useState(null);
  const [loadingActions, setLoadingActions] = useState({});
  const [error, setError] = useState('');
  const modal = useModal();

  // Debounce da busca
  const buscaDebounced = useDebounce(filtro.busca, 500);

  const carregarDashboard = useCallback(async () => {
    try {
      const response = await superadminAPI.dashboard();
      setDashboard(response.data);
    } catch (err) {
      if (err.response?.status === 403) {
        setError('Acesso restrito a super administradores');
      } else {
        setError('Erro ao carregar dashboard');
      }
    }
  }, []);

  const carregarUsuarios = useCallback(async () => {
    try {
      const params = {
        pagina: paginacao.pagina,
        limite: paginacao.limite,
        ordenar_por: ordenacao.campo,
        direcao: ordenacao.direcao
      };
      
      if (filtro.ativo !== '') params.ativo = filtro.ativo === 'true';
      if (filtro.plano) params.plano = filtro.plano;
      if (buscaDebounced) params.busca = buscaDebounced;
      if (filtro.dataInicio) params.data_inicio = filtro.dataInicio;
      if (filtro.dataFim) params.data_fim = filtro.dataFim;
      
      const response = await superadminAPI.listarUsuarios(params);
      setUsuarios(response.data.usuarios || []);
      setTotalUsuarios(response.data.total || 0);
    } catch (err) {
      toast({ title: 'Erro', description: "Não foi possível carregar usuários.", variant: 'destructive' });
      console.error('Erro ao carregar usuários:', err);
    }
  }, [filtro.ativo, filtro.plano, buscaDebounced, filtro.dataInicio, filtro.dataFim, paginacao, ordenacao]);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await carregarDashboard();
      await carregarUsuarios();
      setLoading(false);
    };
    init();
  }, [carregarDashboard, carregarUsuarios]);

  // Calcular métricas avançadas
  const metricas = useMemo(() => {
    if (!dashboard?.stats) return null;
    
    const stats = dashboard.stats;
    const taxaConversao = stats.total_usuarios > 0 
      ? ((stats.usuarios_pagantes / stats.total_usuarios) * 100).toFixed(1)
      : 0;
    
    const receitaPorPlano = {
      basico: stats.receita_basico || 0,
      profissional: stats.receita_profissional || 0,
      enterprise: stats.receita_enterprise || 0
    };
    
    return {
      taxaConversao,
      churnRate: stats.churn_rate || 0,
      crescimentoMoM: stats.crescimento_mom || 0,
      receitaPorPlano
    };
  }, [dashboard]);

  const handleDesativar = async (usuarioId) => {
    modal.confirm(
      'Desativar Usuário',
      'Tem certeza que deseja desativar este usuário? Ele não poderá acessar o sistema.',
      async () => {
        setLoadingActions(prev => ({ ...prev, [usuarioId]: 'desativar' }));
        try {
          await superadminAPI.deletarUsuario(usuarioId, false);
          await carregarUsuarios();
          await carregarDashboard();
          modal.success('Usuário Desativado', 'O usuário foi desativado com sucesso.');
        } catch (err) {
          modal.error('Erro', 'Não foi possível desativar o usuário.');
        } finally {
          setLoadingActions(prev => ({ ...prev, [usuarioId]: null }));
        }
      }
    );
  };

  const handleAtivar = async (usuarioId) => {
    setLoadingActions(prev => ({ ...prev, [usuarioId]: 'ativar' }));
    try {
      await superadminAPI.ativarUsuario(usuarioId);
      await carregarUsuarios();
      await carregarDashboard();
      modal.success('Usuário Ativado', 'O usuário foi ativado com sucesso.');
    } catch (err) {
      modal.error('Erro', 'Não foi possível ativar o usuário.');
    } finally {
      setLoadingActions(prev => ({ ...prev, [usuarioId]: null }));
    }
  };

  const handleAtualizarPlano = async (usuarioId, novoPlano) => {
    setLoadingActions(prev => ({ ...prev, [usuarioId]: 'atualizar' }));
    try {
      await superadminAPI.atualizarUsuario(usuarioId, { plano: novoPlano });
      await carregarUsuarios();
      await carregarDashboard();
      setModalUsuario(null);
      modal.success('Plano Atualizado', 'O plano do usuário foi atualizado com sucesso.');
    } catch (err) {
      modal.error('Erro', 'Não foi possível atualizar o plano.');
    } finally {
      setLoadingActions(prev => ({ ...prev, [usuarioId]: null }));
    }
  };

  const handleResetarSenha = async (usuarioId, email) => {
    modal.confirm(
      'Resetar Senha',
      `Será enviado um email de redefinição de senha para ${email}. Confirma?`,
      async () => {
        setLoadingActions(prev => ({ ...prev, [usuarioId]: 'reset' }));
        try {
          await superadminAPI.resetarSenha(usuarioId);
          modal.success('Email Enviado', 'Email de redefinição de senha enviado com sucesso.');
        } catch (err) {
          modal.error('Erro', 'Não foi possível enviar o email de redefinição.');
        } finally {
          setLoadingActions(prev => ({ ...prev, [usuarioId]: null }));
        }
      }
    );
  };

  const handleVerDetalhes = async (usuario) => {
    setLoadingActions(prev => ({ ...prev, [usuario.id]: 'detalhes' }));
    try {
      const response = await superadminAPI.detalhesUsuario(usuario.id);
      setModalDetalhes(response.data);
    } catch (err) {
      modal.error('Erro', 'Não foi possível carregar os detalhes do usuário.');
    } finally {
      setLoadingActions(prev => ({ ...prev, [usuario.id]: null }));
    }
  };

  const handleExportar = async () => {
    try {
      const response = await superadminAPI.exportarUsuarios(filtro);
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `usuarios_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      modal.success('Exportado!', 'Dados exportados com sucesso.');
    } catch (err) {
      modal.error('Erro', 'Não foi possível exportar os dados.');
    }
  };

  const handleOrdenar = (campo) => {
    setOrdenacao(prev => ({
      campo,
      direcao: prev.campo === campo && prev.direcao === 'asc' ? 'desc' : 'asc'
    }));
  };

  const totalPaginas = Math.ceil(totalUsuarios / paginacao.limite);

  if (loading) return <Loading message="Carregando painel administrativo..." />;

  if (error) {
    return (
      <Layout>
        <div className="container mx-auto px-4 py-8">
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-6 py-4 rounded-lg">
            <h2 className="text-xl font-bold mb-2">Acesso Negado</h2>
            <p>{error}</p>
          </div>
        </div>
      </Layout>
    );
  }

  const stats = dashboard?.stats;

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground" data-testid="superadmin-title">
            Painel Super Admin
          </h1>
          <p className="text-muted-foreground mt-1">Gerencie todos os usuários da plataforma</p>
        </div>

        {/* Alertas */}
        {dashboard?.alertas?.length > 0 && (
          <div className="mb-6 space-y-2">
            {dashboard.alertas.map((alerta, i) => (
              <div
                key={i}
                className={`px-4 py-3 rounded-lg flex items-center ${
                  alerta.tipo === 'warning' ? 'bg-amber-500/10 border border-amber-500/30 text-amber-400' :
                  'bg-blue-500/10 border border-blue-500/30 text-blue-400'
                }`}
              >
                <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
                </svg>
                {alerta.mensagem}
              </div>
            ))}
          </div>
        )}

        {/* Cards de Estatísticas Principais */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-card rounded-lg border border-border p-6">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-muted-foreground">Total de Usuários</p>
                <Users className="w-5 h-5 text-blue-500" />
              </div>
              <p className="text-3xl font-bold text-foreground">{stats.total_usuarios}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {stats.usuarios_ativos} ativos
              </p>
            </div>

            <div className="bg-card rounded-lg border border-border p-6">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-muted-foreground">Taxa de Conversão</p>
                <TrendingUp className="w-5 h-5 text-emerald-500" />
              </div>
              <p className="text-3xl font-bold text-emerald-500">{metricas?.taxaConversao}%</p>
              <p className="text-xs text-muted-foreground mt-1">
                Trial → Pagante
              </p>
            </div>

            <div className="bg-card rounded-lg border border-border p-6">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-muted-foreground">Receita Mensal</p>
                <DollarSign className="w-5 h-5 text-purple-500" />
              </div>
              <p className="text-3xl font-bold text-purple-500">{formatarMoeda(stats.receita_mensal)}</p>
              <p className="text-xs text-emerald-400 mt-1 flex items-center gap-1">
                <TrendingUp className="w-3 h-3" />
                {metricas?.crescimentoMoM || 0}% MoM
              </p>
            </div>

            <div className="bg-card rounded-lg border border-border p-6">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-muted-foreground">Churn Rate</p>
                <Activity className="w-5 h-5 text-amber-500" />
              </div>
              <p className="text-3xl font-bold text-amber-500">{metricas?.churnRate || 0}%</p>
              <p className="text-xs text-muted-foreground mt-1">
                Cancelamentos
              </p>
            </div>
          </div>
        )}

        {/* Gráficos */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Distribuição por Plano */}
          <div className="bg-card rounded-lg border border-border p-6">
            <h2 className="text-lg font-bold text-foreground mb-4">Distribuição por Plano</h2>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={stats?.distribuicao_planos || []}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ plano, quantidade }) => `${plano}: ${quantidade}`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="quantidade"
                  nameKey="plano"
                >
                  {(stats?.distribuicao_planos || []).map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Receita por Plano */}
          <div className="bg-card rounded-lg border border-border p-6">
            <h2 className="text-lg font-bold text-foreground mb-4">Receita por Plano</h2>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={[
                { nome: 'Básico', receita: metricas?.receitaPorPlano?.basico || 0 },
                { nome: 'Pro', receita: metricas?.receitaPorPlano?.profissional || 0 },
                { nome: 'Enterprise', receita: metricas?.receitaPorPlano?.enterprise || 0 }
              ]}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="nome" stroke="#888" />
                <YAxis stroke="#888" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }}
                  formatter={(value) => formatarMoeda(value)}
                />
                <Bar dataKey="receita" fill="#8b5cf6" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Usuários Recentes */}
          <div className="bg-card rounded-lg border border-border p-6">
            <h2 className="text-lg font-bold text-foreground mb-4">Usuários Recentes</h2>
            <div className="space-y-3">
              {(dashboard?.usuarios_recentes || []).slice(0, 5).map((u, i) => (
                <div key={i} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-foreground truncate">{u.nome}</p>
                    <p className="text-xs text-muted-foreground truncate">{u.email}</p>
                  </div>
                  <span className={`ml-2 px-2 py-1 text-xs rounded-full whitespace-nowrap ${
                    u.plano === 'enterprise' ? 'bg-amber-500/20 text-amber-400' :
                    u.plano === 'profissional' ? 'bg-purple-500/20 text-purple-400' :
                    u.plano === 'basico' ? 'bg-blue-500/20 text-blue-400' :
                    'bg-slate-500/20 text-slate-400'
                  }`}>
                    {u.plano}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Lista de Usuários */}
        <div className="bg-card rounded-lg border border-border p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-foreground">Gerenciar Usuários ({totalUsuarios})</h2>
            <Button onClick={handleExportar} variant="secondary" className="gap-2">
              <Download className="w-4 h-4" />
              Exportar
            </Button>
          </div>

          {/* Filtros */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Buscar..."
                value={filtro.busca}
                onChange={(e) => setFiltro(prev => ({ ...prev, busca: e.target.value }))}
                className="w-full pl-10 pr-3 py-2 bg-background border border-border rounded-md text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <select
              value={filtro.ativo}
              onChange={(e) => setFiltro(prev => ({ ...prev, ativo: e.target.value }))}
              className="px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">Todos os status</option>
              <option value="true">Ativo</option>
              <option value="false">Inativo</option>
            </select>
            <select
              value={filtro.plano}
              onChange={(e) => setFiltro(prev => ({ ...prev, plano: e.target.value }))}
              className="px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">Todos os planos</option>
              <option value="trial">Trial</option>
              <option value="basico">Básico</option>
              <option value="profissional">Profissional</option>
              <option value="enterprise">Enterprise</option>
            </select>
            <input
              type="date"
              value={filtro.dataInicio}
              onChange={(e) => setFiltro(prev => ({ ...prev, dataInicio: e.target.value }))}
              placeholder="Data início"
              className="px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <input
              type="date"
              value={filtro.dataFim}
              onChange={(e) => setFiltro(prev => ({ ...prev, dataFim: e.target.value }))}
              placeholder="Data fim"
              className="px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          {/* Tabela Desktop */}
          <div className="hidden md:block overflow-x-auto">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-muted/50">
                <tr>
                  <th 
                    onClick={() => handleOrdenar('nome')}
                    className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase cursor-pointer hover:text-foreground transition"
                  >
                    <div className="flex items-center gap-2">
                      Nome
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Email</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Plano</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                  <th 
                    onClick={() => handleOrdenar('created_at')}
                    className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase cursor-pointer hover:text-foreground transition"
                  >
                    <div className="flex items-center gap-2">
                      Criado em
                      <ArrowUpDown className="w-3 h-3" />
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {usuarios.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-8 text-center text-muted-foreground">
                      Nenhum usuário encontrado
                    </td>
                  </tr>
                ) : (
                  usuarios.map((usuario) => (
                    <tr key={usuario.id} className="hover:bg-muted/50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <p className="font-medium text-foreground">{usuario.nome}</p>
                        <p className="text-xs text-muted-foreground">{usuario.perfil}</p>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                        {usuario.email}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          usuario.plano === 'enterprise' ? 'bg-amber-500/20 text-amber-400' :
                          usuario.plano === 'profissional' ? 'bg-purple-500/20 text-purple-400' :
                          usuario.plano === 'basico' ? 'bg-blue-500/20 text-blue-400' :
                          'bg-slate-500/20 text-slate-400'
                        }`}>
                          {usuario.plano}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          usuario.ativo ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
                        }`}>
                          {usuario.ativo ? 'Ativo' : 'Inativo'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                        {formatarData(usuario.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleVerDetalhes(usuario)}
                            disabled={loadingActions[usuario.id] === 'detalhes'}
                            className="p-2 text-blue-400 hover:bg-blue-500/20 rounded-lg transition disabled:opacity-50"
                            title="Ver detalhes"
                          >
                            {loadingActions[usuario.id] === 'detalhes' ? (
                              <RefreshCw className="w-4 h-4 animate-spin" />
                            ) : (
                              <Eye className="w-4 h-4" />
                            )}
                          </button>
                          <button
                            onClick={() => setModalUsuario(usuario)}
                            className="p-2 text-purple-400 hover:bg-purple-500/20 rounded-lg transition"
                            title="Editar plano"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                              <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                            </svg>
                          </button>
                          <button
                            onClick={() => handleResetarSenha(usuario.id, usuario.email)}
                            disabled={loadingActions[usuario.id] === 'reset'}
                            className="p-2 text-amber-400 hover:bg-amber-500/20 rounded-lg transition disabled:opacity-50"
                            title="Resetar senha"
                          >
                            {loadingActions[usuario.id] === 'reset' ? (
                              <RefreshCw className="w-4 h-4 animate-spin" />
                            ) : (
                              <Mail className="w-4 h-4" />
                            )}
                          </button>
                          {usuario.ativo ? (
                            <button
                              onClick={() => handleDesativar(usuario.id)}
                              disabled={loadingActions[usuario.id] === 'desativar'}
                              className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition disabled:opacity-50"
                              title="Desativar"
                            >
                              {loadingActions[usuario.id] === 'desativar' ? (
                                <RefreshCw className="w-4 h-4 animate-spin" />
                              ) : (
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                  <path fillRule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 018.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clipRule="evenodd" />
                                </svg>
                              )}
                            </button>
                          ) : (
                            <button
                              onClick={() => handleAtivar(usuario.id)}
                              disabled={loadingActions[usuario.id] === 'ativar'}
                              className="p-2 text-emerald-400 hover:bg-emerald-500/20 rounded-lg transition disabled:opacity-50"
                              title="Ativar"
                            >
                              {loadingActions[usuario.id] === 'ativar' ? (
                                <RefreshCw className="w-4 h-4 animate-spin" />
                              ) : (
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                </svg>
                              )}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Paginação */}
          {totalPaginas > 1 && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t border-border">
              <p className="text-sm text-muted-foreground">
                Mostrando {((paginacao.pagina - 1) * paginacao.limite) + 1} a {Math.min(paginacao.pagina * paginacao.limite, totalUsuarios)} de {totalUsuarios} usuários
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  onClick={() => setPaginacao(prev => ({ ...prev, pagina: prev.pagina - 1 }))}
                  disabled={paginacao.pagina === 1}
                  className="gap-2"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Anterior
                </Button>
                <span className="text-sm text-muted-foreground">
                  Página {paginacao.pagina} de {totalPaginas}
                </span>
                <Button
                  variant="secondary"
                  onClick={() => setPaginacao(prev => ({ ...prev, pagina: prev.pagina + 1 }))}
                  disabled={paginacao.pagina === totalPaginas}
                  className="gap-2"
                >
                  Próxima
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Modal Editar Plano */}
        {modalUsuario && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-card rounded-lg border border-border shadow-xl p-6 w-full max-w-md">
              <h3 className="text-lg font-bold text-foreground mb-4">Editar Plano do Usuário</h3>
              <div className="mb-4">
                <p className="text-sm text-muted-foreground">Nome</p>
                <p className="font-medium text-foreground">{modalUsuario.nome}</p>
              </div>
              <div className="mb-4">
                <p className="text-sm text-muted-foreground">Email</p>
                <p className="font-medium text-foreground">{modalUsuario.email}</p>
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium text-foreground mb-2">Plano</label>
                <select
                  value={modalUsuario.plano}
                  onChange={(e) => setModalUsuario(prev => ({ ...prev, plano: e.target.value }))}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground"
                >
                  <option value="trial">Trial</option>
                  <option value="basico">Básico</option>
                  <option value="profissional">Profissional</option>
                  <option value="enterprise">Enterprise</option>
                </select>
              </div>
              <div className="flex justify-end space-x-3">
                <Button variant="secondary" onClick={() => setModalUsuario(null)}>
                  Cancelar
                </Button>
                <Button 
                  variant="primary" 
                  onClick={() => handleAtualizarPlano(modalUsuario.id, modalUsuario.plano)}
                  disabled={loadingActions[modalUsuario.id] === 'atualizar'}
                >
                  {loadingActions[modalUsuario.id] === 'atualizar' ? 'Salvando...' : 'Salvar'}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Modal Detalhes Completo */}
        {modalDetalhes && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 overflow-y-auto">
            <div className="bg-card rounded-lg border border-border shadow-xl p-6 w-full max-w-2xl my-8">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold text-foreground">Detalhes do Usuário</h3>
                <button 
                  onClick={() => setModalDetalhes(null)}
                  className="text-muted-foreground hover:text-foreground transition"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Informações Básicas */}
                <div className="space-y-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Nome Completo</p>
                    <p className="font-medium text-foreground">{modalDetalhes.nome}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Email</p>
                    <p className="font-medium text-foreground">{modalDetalhes.email}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Perfil</p>
                    <p className="font-medium text-foreground capitalize">{modalDetalhes.perfil}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Plano Atual</p>
                    <span className={`inline-block px-3 py-1 text-sm rounded-full ${
                      modalDetalhes.plano === 'enterprise' ? 'bg-amber-500/20 text-amber-400' :
                      modalDetalhes.plano === 'profissional' ? 'bg-purple-500/20 text-purple-400' :
                      modalDetalhes.plano === 'basico' ? 'bg-blue-500/20 text-blue-400' :
                      'bg-slate-500/20 text-slate-400'
                    }`}>
                      {modalDetalhes.plano}
                    </span>
                  </div>
                </div>

                {/* Estatísticas de Uso */}
                <div className="space-y-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Total de Clientes</p>
                    <p className="text-2xl font-bold text-foreground">{modalDetalhes.total_clientes || 0}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Total de Empréstimos</p>
                    <p className="text-2xl font-bold text-foreground">{modalDetalhes.total_emprestimos || 0}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Último Acesso</p>
                    <p className="font-medium text-foreground">
                      {modalDetalhes.ultimo_acesso ? formatarData(modalDetalhes.ultimo_acesso) : 'Nunca'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Membro desde</p>
                    <p className="font-medium text-foreground">{formatarData(modalDetalhes.created_at)}</p>
                  </div>
                </div>
              </div>

              {/* Logs Recentes */}
              {modalDetalhes.logs_recentes && modalDetalhes.logs_recentes.length > 0 && (
                <div className="mt-6 pt-6 border-t border-border">
                  <h4 className="text-sm font-semibold text-foreground mb-3">Atividades Recentes</h4>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {modalDetalhes.logs_recentes.map((log, i) => (
                      <div key={i} className="flex items-center justify-between text-sm p-2 bg-muted/30 rounded">
                        <span className="text-foreground">{log.acao}</span>
                        <span className="text-muted-foreground text-xs">{formatarData(log.data)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="mt-6 flex justify-end">
                <Button onClick={() => setModalDetalhes(null)}>
                  Fechar
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default SuperAdmin;
