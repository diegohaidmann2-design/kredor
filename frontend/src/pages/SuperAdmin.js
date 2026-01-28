import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import Button from '../components/Button';
import { useModal } from '../components/Modal';
import { superadminAPI } from '../api/api';
import { formatarMoeda, formatarData } from '../utils/formatters';
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip
} from 'recharts';

const COLORS = ['#6b7280', '#3b82f6', '#8b5cf6', '#f59e0b'];

const SuperAdmin = () => {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [usuarios, setUsuarios] = useState([]);
  const [totalUsuarios, setTotalUsuarios] = useState(0);
  const [filtro, setFiltro] = useState({ ativo: '', plano: '', busca: '' });
  const [modalUsuario, setModalUsuario] = useState(null);
  const [error, setError] = useState('');
  const modal = useModal();

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
      const params = {};
      if (filtro.ativo !== '') params.ativo = filtro.ativo === 'true';
      if (filtro.plano) params.plano = filtro.plano;
      if (filtro.busca) params.busca = filtro.busca;
      
      const response = await superadminAPI.listarUsuarios(params);
      setUsuarios(response.data.usuarios);
      setTotalUsuarios(response.data.total);
    } catch (err) {
      console.error('Erro ao carregar usuários:', err);
    }
  }, [filtro]);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await carregarDashboard();
      await carregarUsuarios();
      setLoading(false);
    };
    init();
  }, [carregarDashboard, carregarUsuarios]);

  const handleDesativar = async (usuarioId) => {
    modal.confirm(
      'Desativar Usuário',
      'Tem certeza que deseja desativar este usuário? Ele não poderá acessar o sistema.',
      async () => {
        try {
          await superadminAPI.deletarUsuario(usuarioId, false);
          carregarUsuarios();
          carregarDashboard();
          modal.success('Usuário Desativado', 'O usuário foi desativado com sucesso.');
        } catch (err) {
          modal.error('Erro', 'Não foi possível desativar o usuário.');
        }
      }
    );
  };

  const handleAtivar = async (usuarioId) => {
    try {
      await superadminAPI.ativarUsuario(usuarioId);
      carregarUsuarios();
      carregarDashboard();
      modal.success('Usuário Ativado', 'O usuário foi ativado com sucesso.');
    } catch (err) {
      modal.error('Erro', 'Não foi possível ativar o usuário.');
    }
  };

  const handleAtualizarPlano = async (usuarioId, novoPlano) => {
    try {
      await superadminAPI.atualizarUsuario(usuarioId, { plano: novoPlano });
      carregarUsuarios();
      carregarDashboard();
      setModalUsuario(null);
      modal.success('Plano Atualizado', 'O plano do usuário foi atualizado com sucesso.');
    } catch (err) {
      modal.error('Erro', 'Não foi possível atualizar o plano.');
    }
  };

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

        {/* Cards de Estatísticas */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-card rounded-lg border border-border p-6">
              <p className="text-sm text-muted-foreground mb-1">Total de Usuários</p>
              <p className="text-3xl font-bold text-foreground">{stats.total_usuarios}</p>
            </div>
            <div className="bg-card rounded-lg border border-border p-6">
              <p className="text-sm text-muted-foreground mb-1">Usuários Ativos</p>
              <p className="text-3xl font-bold text-emerald-500">{stats.usuarios_ativos}</p>
            </div>
            <div className="bg-card rounded-lg border border-border p-6">
              <p className="text-sm text-muted-foreground mb-1">Usuários Pagantes</p>
              <p className="text-3xl font-bold text-blue-500">{stats.usuarios_pagantes}</p>
            </div>
            <div className="bg-card rounded-lg border border-border p-6">
              <p className="text-sm text-muted-foreground mb-1">Receita Mensal</p>
              <p className="text-3xl font-bold text-purple-500">{formatarMoeda(stats.receita_mensal)}</p>
            </div>
          </div>
        )}

        {/* Gráfico de Distribuição */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
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

          {/* Usuários Recentes */}
          <div className="lg:col-span-2 bg-card rounded-lg border border-border p-6">
            <h2 className="text-lg font-bold text-foreground mb-4">Usuários Recentes</h2>
            <div className="space-y-3">
              {(dashboard?.usuarios_recentes || []).slice(0, 5).map((u, i) => (
                <div key={i} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                  <div>
                    <p className="font-medium text-foreground">{u.nome}</p>
                    <p className="text-sm text-muted-foreground">{u.email}</p>
                  </div>
                  <span className={`px-2 py-1 text-xs rounded-full ${
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
          </div>

          {/* Filtros */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
            <input
              type="text"
              placeholder="Buscar por nome ou email..."
              value={filtro.busca}
              onChange={(e) => setFiltro(prev => ({ ...prev, busca: e.target.value }))}
              className="px-3 py-2 bg-background border border-border rounded-md text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
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
            <Button onClick={carregarUsuarios} variant="secondary">
              Filtrar
            </Button>
          </div>

          {/* Tabela */}
          <>
            {/* Versão Desktop - Tabela */}
            <div className="hidden md:block overflow-x-auto">
              <table className="min-w-full divide-y divide-border">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Nome</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Email</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Plano</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Criado em</th>
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
                              onClick={() => setModalUsuario(usuario)}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 rounded-lg transition text-sm font-medium"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                              </svg>
                              Editar
                            </button>
                            {usuario.ativo ? (
                              <button
                                onClick={() => handleDesativar(usuario.id)}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded-lg transition text-sm font-medium"
                              >
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                  <path fillRule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 018.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clipRule="evenodd" />
                                </svg>
                                Desativar
                              </button>
                            ) : (
                              <button
                                onClick={() => handleAtivar(usuario.id)}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 rounded-lg transition text-sm font-medium"
                              >
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                </svg>
                                Ativar
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

            {/* Versão Mobile - Cards */}
            <div className="md:hidden">
              {usuarios.length === 0 ? (
                <div className="px-6 py-8 text-center text-muted-foreground">
                  Nenhum usuário encontrado
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {usuarios.map((usuario) => (
                    <div key={usuario.id} className="p-4">
                      <div className="mb-3">
                        <p className="font-semibold text-foreground">{usuario.nome}</p>
                        <p className="text-sm text-muted-foreground">{usuario.email}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">{usuario.perfil}</p>
                      </div>

                      <div className="flex items-center gap-2 mb-3">
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          usuario.plano === 'enterprise' ? 'bg-amber-500/20 text-amber-400' :
                          usuario.plano === 'profissional' ? 'bg-purple-500/20 text-purple-400' :
                          usuario.plano === 'basico' ? 'bg-blue-500/20 text-blue-400' :
                          'bg-slate-500/20 text-slate-400'
                        }`}>
                          {usuario.plano}
                        </span>
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          usuario.ativo ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
                        }`}>
                          {usuario.ativo ? 'Ativo' : 'Inativo'}
                        </span>
                      </div>

                      <div className="flex justify-between text-sm mb-3">
                        <span className="text-muted-foreground">Criado em:</span>
                        <span className="text-foreground">{formatarData(usuario.created_at)}</span>
                      </div>

                      <div className="flex gap-2">
                        <button
                          onClick={() => setModalUsuario(usuario)}
                          className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 rounded-lg transition text-sm font-medium"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                            <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                          </svg>
                          Editar
                        </button>
                        {usuario.ativo ? (
                          <button
                            onClick={() => handleDesativar(usuario.id)}
                            className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded-lg transition text-sm font-medium"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                              <path fillRule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 018.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clipRule="evenodd" />
                            </svg>
                            Desativar
                          </button>
                        ) : (
                          <button
                            onClick={() => handleAtivar(usuario.id)}
                            className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 rounded-lg transition text-sm font-medium"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                            Ativar
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        </div>

        {/* Modal Editar Usuário */}
        {modalUsuario && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-card rounded-lg border border-border shadow-xl p-6 w-full max-w-md">
              <h3 className="text-lg font-bold text-foreground mb-4">Editar Usuário</h3>
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
                <Button variant="primary" onClick={() => handleAtualizarPlano(modalUsuario.id, modalUsuario.plano)}>
                  Salvar
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
