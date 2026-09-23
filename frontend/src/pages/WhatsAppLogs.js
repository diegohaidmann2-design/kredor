import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import ErrorMessage from '../components/ErrorMessage';
import { whatsappAPI } from '../api/api';
import { formatarDataHora } from '../utils/formatters';
import { 
  MessageCircle, 
  CheckCircle, 
  XCircle, 
  Clock, 
  AlertCircle,
  Activity,
  TrendingUp,
  AlertTriangle
} from 'lucide-react';

const WhatsAppLogs = () => {
  const [logs, setLogs] = useState([]);
  const [estatisticas, setEstatisticas] = useState(null);
  const [statusServico, setStatusServico] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filtroTipo, setFiltroTipo] = useState('');
  const [filtroStatus, setFiltroStatus] = useState('');

  useEffect(() => {
    carregarDados();
  }, [filtroTipo, filtroStatus]);

  const carregarDados = async () => {
    try {
      setLoading(true);
      setError('');

      const params = {};
      if (filtroTipo) params.tipo = filtroTipo;
      if (filtroStatus) params.status = filtroStatus;

      const [logsRes, statsRes, statusRes] = await Promise.all([
        whatsappAPI.listarLogs(params),
        whatsappAPI.obterEstatisticasLogs(),
        whatsappAPI.verificarStatusServico()
      ]);

      setLogs(logsRes.data.items);
      setEstatisticas(statsRes.data);
      setStatusServico(statusRes.data);
    } catch (err) {
      console.error('Erro ao carregar dados:', err);
      setError('Não foi possível carregar os logs de WhatsApp.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'enviado':
        return 'bg-green-500/20 text-green-400 ring-green-500/30';
      case 'erro':
        return 'bg-red-500/20 text-red-400 ring-red-500/30';
      case 'pendente':
        return 'bg-yellow-500/20 text-yellow-400 ring-yellow-500/30';
      default:
        return 'bg-gray-500/20 text-gray-400 ring-gray-500/30';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'enviado':
        return <CheckCircle className="w-4 h-4" />;
      case 'erro':
        return <XCircle className="w-4 h-4" />;
      case 'pendente':
        return <Clock className="w-4 h-4" />;
      default:
        return <AlertCircle className="w-4 h-4" />;
    }
  };

  const getStatusServicoColor = (status) => {
    switch (status) {
      case 'funcionando':
        return 'bg-green-500';
      case 'com_problemas':
        return 'bg-yellow-500';
      case 'inativo':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  if (loading) return <Loading message="Carregando logs..." />;

  return (
    <Layout>
      <div className="p-4 md:p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="font-cabinet font-black text-3xl sm:text-4xl tracking-tighter text-foreground flex items-center gap-3">
            <MessageCircle className="w-8 h-8 text-green-500" strokeWidth={1.75} />
            Auditoria WhatsApp
          </h1>
          <p className="text-muted-foreground mt-2">
            Monitore todos os envios e o status do serviço WhatsApp
          </p>
        </div>

        {error && <ErrorMessage message={error} />}

        {/* Status do Serviço */}
        {statusServico && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            {/* Card Principal de Status */}
            <div className="lg:col-span-1 bg-card rounded-lg border border-border p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-foreground">Status do Serviço</h3>
                <Activity className="w-5 h-5 text-muted-foreground" />
              </div>
              
              <div className="flex items-center gap-3 mb-4">
                <div className={`w-4 h-4 rounded-full ${getStatusServicoColor(statusServico.status_geral)} animate-pulse`}></div>
                <span className="text-2xl font-bold text-foreground capitalize">
                  {statusServico.status_geral.replace('_', ' ')}
                </span>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Conexão:</span>
                  <span className={`font-semibold ${statusServico.conexao.ativa ? 'text-green-400' : 'text-red-400'}`}>
                    {statusServico.conexao.ativa ? 'Ativa' : 'Inativa'}
                  </span>
                </div>
                
                {statusServico.conexao.numero_telefone && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Número:</span>
                    <span className="font-semibold text-foreground">
                      {statusServico.conexao.numero_telefone}
                    </span>
                  </div>
                )}

                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Taxa de Sucesso:</span>
                  <span className="font-semibold text-foreground">
                    {statusServico.ultimos_envios.taxa_sucesso}%
                  </span>
                </div>
              </div>

              {/* Problemas */}
              {statusServico.problemas && statusServico.problemas.length > 0 && (
                <div className="mt-4 pt-4 border-t border-border">
                  <div className="flex items-center gap-2 text-yellow-400 mb-2">
                    <AlertTriangle className="w-4 h-4" />
                    <span className="text-sm font-semibold">Problemas Detectados</span>
                  </div>
                  <div className="space-y-2">
                    {statusServico.problemas.map((problema, idx) => (
                      <div 
                        key={idx}
                        className={`text-xs p-2 rounded ${
                          problema.gravidade === 'alta' 
                            ? 'bg-red-500/10 text-red-400' 
                            : 'bg-yellow-500/10 text-yellow-400'
                        }`}
                      >
                        {problema.mensagem}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Estatísticas */}
            {estatisticas && (
              <>
                <div className="bg-card rounded-lg border border-border p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-foreground">Envios</h3>
                    <TrendingUp className="w-5 h-5 text-blue-400" />
                  </div>
                  <div className="space-y-4">
                    <div>
                      <div className="text-3xl font-bold text-foreground">
                        {estatisticas.total_envios}
                      </div>
                      <div className="text-sm text-muted-foreground">Total de Envios</div>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div>
                        <div className="text-xl font-bold text-foreground">{estatisticas.hoje}</div>
                        <div className="text-xs text-muted-foreground">Hoje</div>
                      </div>
                      <div>
                        <div className="text-xl font-bold text-foreground">{estatisticas.ultimos_7_dias}</div>
                        <div className="text-xs text-muted-foreground">7 dias</div>
                      </div>
                      <div>
                        <div className="text-xl font-bold text-foreground">{estatisticas.ultimos_30_dias}</div>
                        <div className="text-xs text-muted-foreground">30 dias</div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-card rounded-lg border border-border p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-foreground">Performance</h3>
                    <Activity className="w-5 h-5 text-green-400" />
                  </div>
                  <div className="space-y-4">
                    <div>
                      <div className="text-3xl font-bold text-green-400">
                        {estatisticas.taxa_sucesso}%
                      </div>
                      <div className="text-sm text-muted-foreground">Taxa de Sucesso</div>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div>
                        <div className="text-xl font-bold text-green-400">{estatisticas.status.enviados}</div>
                        <div className="text-xs text-muted-foreground">Enviados</div>
                      </div>
                      <div>
                        <div className="text-xl font-bold text-red-400">{estatisticas.status.erros}</div>
                        <div className="text-xs text-muted-foreground">Erros</div>
                      </div>
                      <div>
                        <div className="text-xl font-bold text-yellow-400">{estatisticas.status.pendentes}</div>
                        <div className="text-xs text-muted-foreground">Pendentes</div>
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* Filtros */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-card rounded-lg border border-border p-4">
            <label className="block text-sm font-medium text-foreground mb-2">Tipo</label>
            <select
              value={filtroTipo}
              onChange={(e) => setFiltroTipo(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground"
            >
              <option value="">Todos</option>
              <option value="cobranca_manual">Cobrança Manual</option>
              <option value="confirmacao_pagamento">Confirmação Pagamento</option>
              <option value="lembrete_automatico">Lembrete Automático</option>
            </select>
          </div>

          <div className="bg-card rounded-lg border border-border p-4">
            <label className="block text-sm font-medium text-foreground mb-2">Status</label>
            <select
              value={filtroStatus}
              onChange={(e) => setFiltroStatus(e.target.value)}
              className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground"
            >
              <option value="">Todos</option>
              <option value="enviado">Enviado</option>
              <option value="erro">Erro</option>
              <option value="pendente">Pendente</option>
            </select>
          </div>

          <div className="bg-card rounded-lg border border-border p-4 flex items-end">
            <button
              onClick={() => { setFiltroTipo(''); setFiltroStatus(''); }}
              className="w-full px-4 py-2 bg-muted hover:bg-muted/80 text-foreground rounded-md text-sm font-medium"
            >
              Limpar Filtros
            </button>
          </div>
        </div>

        {/* Tabela de Logs */}
        <div className="bg-card rounded-lg border border-border overflow-hidden">
          {logs.length === 0 ? (
            <div className="p-8 text-center">
              <MessageCircle className="w-16 h-16 text-muted-foreground mx-auto mb-4 opacity-50" />
              <p className="text-muted-foreground">Nenhum log encontrado</p>
            </div>
          ) : (
            <>
              {/* Desktop */}
              <div className="hidden md:block overflow-x-auto">
                <table className="min-w-full divide-y divide-border">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Data/Hora</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Cliente</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Tipo</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Número</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Mensagem</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {logs.map((log, index) => (
                      <tr key={log.id || index} className="hover:bg-muted/30">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                          {formatarDataHora(log.created_at)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-foreground">
                            {log.cliente_nome || 'N/A'}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-xs font-medium text-muted-foreground">
                            {log.tipo?.replace('_', ' ').toUpperCase()}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                          {log.numero_destino || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex items-center gap-2 px-2.5 py-1 text-xs font-bold rounded-full ring-1 ${getStatusColor(log.status)}`}>
                            {getStatusIcon(log.status)}
                            {log.status?.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm text-muted-foreground max-w-md truncate">
                            {log.mensagem?.substring(0, 100)}...
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile */}
              <div className="md:hidden divide-y divide-border">
                {logs.map((log, index) => (
                  <div key={log.id || index} className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="font-semibold text-foreground">
                          {log.cliente_nome || 'N/A'}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {formatarDataHora(log.created_at)}
                        </div>
                      </div>
                      <span className={`inline-flex items-center gap-1 px-2 py-1 text-xs font-bold rounded-full ring-1 ${getStatusColor(log.status)}`}>
                        {getStatusIcon(log.status)}
                        {log.status}
                      </span>
                    </div>
                    <div className="text-sm text-muted-foreground mb-2">
                      <span className="font-medium">Tipo:</span> {log.tipo?.replace('_', ' ')}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      <span className="font-medium">Número:</span> {log.numero_destino || '-'}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default WhatsAppLogs;
