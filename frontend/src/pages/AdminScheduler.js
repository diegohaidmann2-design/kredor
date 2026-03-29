import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { formatDateBR } from '../utils/timezone';
import { schedulerAPI } from '../api/api';

const AdminScheduler = () => {
  const [loading, setLoading] = useState(true);
  const [recarregando, setRecarregando] = useState(false);
  const [status, setStatus] = useState(null);
  const [estatisticas, setEstatisticas] = useState(null);
  const [historico, setHistorico] = useState([]);
  const [executando, setExecutando] = useState({});
  const [abaAtiva, setAbaAtiva] = useState('status');

  useEffect(() => {
    carregarDados();
    const interval = setInterval(carregarDados, 30000);
    return () => clearInterval(interval);
  }, []);

  const carregarDados = async () => {
    try {
      setRecarregando(true);
      
      const [statusRes, statsRes, historicoRes] = await Promise.allSettled([
        schedulerAPI.status(),
        schedulerAPI.estatisticas(),
        schedulerAPI.historico(20)
      ]);

      if (statusRes.status === 'fulfilled' && statusRes.value?.data) {
        setStatus(statusRes.value.data);
      } else {
        console.warn('Falha ao carregar status:', statusRes.reason);
      }

      if (statsRes.status === 'fulfilled' && statsRes.value?.data?.estatisticas) {
        setEstatisticas(statsRes.value.data.estatisticas);
      } else {
        console.warn('Falha ao carregar estatísticas:', statsRes.reason);
      }

      if (historicoRes.status === 'fulfilled' && historicoRes.value?.data?.jobs_execucoes) {
        setHistorico(historicoRes.value.data.jobs_execucoes);
      } else {
        console.warn('Falha ao carregar histórico:', historicoRes.reason);
        // Não zerar histórico se falhar, manter o anterior ou array vazio se for primeira carga
        if (!historico.length) setHistorico([]);
      }

      setLoading(false);
    } catch (error) {
      console.error('Erro crítico ao carregar dados:', error);
      setLoading(false);
    } finally {
      setRecarregando(false);
    }
  };

  const executarJob = async (jobName) => {
    try {
      setExecutando({ ...executando, [jobName]: true });
      
      await schedulerAPI.executarJob(jobName);
      
      showToast(`Job "${jobName}" executado com sucesso!`, 'success');
      setTimeout(carregarDados, 2000);
      
    } catch (error) {
      console.error('Erro ao executar job:', error);
      const msg = error.response?.data?.detail || 'Erro ao executar job';
      showToast(msg, 'error');
    } finally {
      setExecutando({ ...executando, [jobName]: false });
    }
  };

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

  const formatarData = (data) => {
    if (!data) return '-';
    return formatDateBR(data);  // 🆕 Usar timezone de São Paulo
  };

  const jobs = [
    {
      name: 'verificar-planos',
      titulo: 'Verificar Planos Expirados',
      descricao: 'Verifica e desativa planos expirados automaticamente',
      icone: '🔍',
      cor: 'purple'
    },
    {
      name: 'verificar-vencimentos',
      titulo: 'Notificações de Vencimento',
      descricao: 'Verifica parcelas vencendo/vencidas e envia notificações via Sistema e WhatsApp (conforme configurado)',
      icone: '🔔',
      cor: 'yellow'
    },
    {
      name: 'verificar-assinaturas',
      titulo: 'Notificações de Assinaturas',
      descricao: 'Verifica assinaturas expirando e cria notificações para usuários',
      icone: '⚠️',
      cor: 'orange'
    },
    {
      name: 'resumo-diario',
      titulo: 'Resumo Diário Admin',
      descricao: 'Gera resumo diário com métricas do sistema para administradores',
      icone: '📊',
      cor: 'indigo'
    },
    {
      name: 'lembretes-trial',
      titulo: 'Lembretes de Trial',
      descricao: 'Envia lembretes para usuários em período de trial',
      icone: '⏰',
      cor: 'blue'
    },
    {
      name: 'lembretes-assinatura',
      titulo: 'Lembretes de Assinatura',
      descricao: 'Envia lembretes de renovação de assinatura',
      icone: '📧',
      cor: 'green'
    },
    {
      name: 'relatorio-semanal',
      titulo: 'Relatório Semanal',
      descricao: 'Gera relatório semanal de métricas e performance',
      icone: '📊',
      cor: 'yellow'
    },
    {
      name: 'reconciliacao',
      titulo: 'Reconciliação de Dados',
      descricao: 'Verifica e corrige inconsistências no banco de dados',
      icone: '🔄',
      cor: 'red'
    },
    {
      name: 'processar-pagamentos',
      titulo: 'Processar Pagamentos Pendentes',
      descricao: 'Processa pagamentos pendentes do Stripe (roda a cada 5 minutos)',
      icone: '💳',
      cor: 'emerald'
    }
  ];

  if (loading) {
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
      <div className="container mx-auto px-4 py-8">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Scheduler & Jobs</h1>
            <p className="text-muted-foreground mt-1">
              Gerencie jobs automáticos e tarefas agendadas
            </p>
          </div>
          <button
            onClick={carregarDados}
            disabled={recarregando}
            className={`px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition flex items-center gap-2 ${
              recarregando ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            <svg 
              className={`w-5 h-5 ${recarregando ? 'animate-spin' : ''}`} 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {recarregando ? 'Atualizando...' : 'Atualizar'}
          </button>
        </div>

        {/* Status do Scheduler */}
        {status && (
          <div className="bg-card rounded-lg p-6 border border-border">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${status?.scheduler?.status === 'running' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                <div>
                  <h3 className="text-lg font-semibold text-foreground">
                    Scheduler Status: {status?.scheduler?.status === 'running' ? 'ATIVO' : 'INATIVO'}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {status?.scheduler?.jobs?.length || 0} jobs agendados
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-muted-foreground">Última verificação</p>
                <p className="text-sm font-mono text-foreground">{formatarData(status.timestamp)}</p>
              </div>
            </div>
          </div>
        )}

        {/* Cards de Estatísticas */}
        {estatisticas && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-card rounded-lg p-6 border border-border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Jobs (24h)</p>
                  <p className="text-3xl font-bold text-blue-400 mt-1">{estatisticas.jobs_executados_24h}</p>
                </div>
                <div className="p-3 bg-blue-500/10 rounded-lg">
                  <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
              </div>
            </div>

            <div className="bg-card rounded-lg p-6 border border-border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Logs (24h)</p>
                  <p className="text-3xl font-bold text-green-400 mt-1">{estatisticas.logs_planos_24h}</p>
                </div>
                <div className="p-3 bg-green-500/10 rounded-lg">
                  <svg className="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
              </div>
            </div>

            <div className="bg-card rounded-lg p-6 border border-border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Expirações (7d)</p>
                  <p className="text-3xl font-bold text-orange-400 mt-1">{estatisticas.planos_expirados_7d}</p>
                </div>
                <div className="p-3 bg-orange-500/10 rounded-lg">
                  <svg className="w-8 h-8 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
            </div>

            <div className="bg-card rounded-lg p-6 border border-border">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Correções (7d)</p>
                  <p className="text-3xl font-bold text-purple-400 mt-1">{estatisticas.correcoes_automaticas_7d}</p>
                </div>
                <div className="p-3 bg-purple-500/10 rounded-lg">
                  <svg className="w-8 h-8 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Alerta sobre Notificações WhatsApp */}
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <svg className="w-6 h-6 text-yellow-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-yellow-500 mb-1">
                ℹ️ Sistema de Notificações Atualizado
              </h3>
              <p className="text-sm text-foreground mb-2">
                O job <strong>"Notificações de Vencimento"</strong> agora suporta envio automático via <strong>WhatsApp</strong> além das notificações internas.
              </p>
              <div className="text-xs text-muted-foreground space-y-1">
                <p>• <strong>Configurável por usuário:</strong> Cada gestor pode configurar períodos e canais em <code className="bg-muted px-1 py-0.5 rounded">Configurações → Notificações</code></p>
                <p>• <strong>Templates personalizáveis:</strong> Mensagens WhatsApp podem ser customizadas com variáveis</p>
                <p>• <strong>Execução:</strong> Roda automaticamente a cada hora (8h-20h) ou pode ser executado manualmente abaixo</p>
              </div>
            </div>
          </div>
        </div>


        {/* Abas */}
        <div className="bg-card rounded-lg border border-border overflow-hidden">
          <div className="flex border-b border-border">
            <button
              onClick={() => setAbaAtiva('status')}
              className={`flex-1 px-6 py-3 font-medium transition ${
                abaAtiva === 'status'
                  ? 'bg-purple-500/10 text-purple-400 border-b-2 border-purple-500'
                  : 'text-muted-foreground hover:bg-muted/30'
              }`}
            >
              Executar Jobs
            </button>
            <button
              onClick={() => setAbaAtiva('historico')}
              className={`flex-1 px-6 py-3 font-medium transition ${
                abaAtiva === 'historico'
                  ? 'bg-purple-500/10 text-purple-400 border-b-2 border-purple-500'
                  : 'text-muted-foreground hover:bg-muted/30'
              }`}
            >
              Histórico
            </button>
          </div>

          <div className="p-6">
            {abaAtiva === 'status' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {jobs.map((job) => (
                  <div key={job.name} className="bg-background rounded-lg p-6 border border-border hover:border-purple-500/50 transition">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <span className="text-4xl">{job.icone}</span>
                        <div>
                          <h4 className="text-lg font-semibold text-foreground">{job.titulo}</h4>
                          <p className="text-sm text-muted-foreground mt-1">{job.descricao}</p>
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => executarJob(job.name)}
                      disabled={executando[job.name]}
                      className={`w-full px-4 py-2 bg-${job.cor}-600 text-white rounded-lg hover:bg-${job.cor}-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2`}
                    >
                      {executando[job.name] ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                          Executando...
                        </>
                      ) : (
                        <>
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          Executar Agora
                        </>
                      )}
                    </button>
                  </div>
                ))}
              </div>
            )}

            {abaAtiva === 'historico' && (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Job</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Executado Em</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Resultado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {historico.length === 0 ? (
                      <tr>
                        <td colSpan="4" className="px-4 py-8 text-center text-muted-foreground">
                          Nenhum histórico de execução encontrado
                        </td>
                      </tr>
                    ) : (
                      historico.map((item, index) => (
                        <tr key={index} className="hover:bg-muted/30 transition">
                          <td className="px-4 py-3">
                            <span className="font-semibold text-foreground">{item.job}</span>
                          </td>
                          <td className="px-4 py-3 text-sm text-foreground">
                            {formatarData(item.executado_em)}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                              item.success ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
                            }`}>
                              {item.success ? 'Sucesso' : 'Erro'}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-muted-foreground">
                            {item.resultado?.message || JSON.stringify(item.resultado || {}).substring(0, 50)}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
      </div>
    </Layout>
  );
};

export default AdminScheduler;
