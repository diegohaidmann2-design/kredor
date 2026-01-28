import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { auditoriaAPI } from '../api/api';
import { formatarDataHora } from '../utils/formatters';

const Auditoria = () => {
  const [logs, setLogs] = useState([]);
  const [estatisticas, setEstatisticas] = useState({
    total: 0,
    hoje: 0,
    ultimos_7_dias: 0,
    usuarios_ativos: 0
  });
  const [loading, setLoading] = useState(true);
  const [filtroAcao, setFiltroAcao] = useState('');
  const [filtroEntidade, setFiltroEntidade] = useState('');
  const [dataInicio, setDataInicio] = useState('');
  const [dataFim, setDataFim] = useState('');

  // Estado para Modal de Limpeza
  const [modalLimpezaOpen, setModalLimpezaOpen] = useState(false);
  const [textoConfirmacao, setTextoConfirmacao] = useState('');
  const [limpando, setLimpando] = useState(false);

  const carregarDados = useCallback(async () => {
    try {
      setLoading(true);

      const params = {};
      if (filtroAcao) params.acao = filtroAcao;
      if (filtroEntidade) params.entidade = filtroEntidade;
      if (dataInicio) params.data_inicio = dataInicio;
      if (dataFim) params.data_fim = dataFim;

      const [logsRes, statsRes] = await Promise.all([
        auditoriaAPI.listar(params),
        auditoriaAPI.estatisticas()
      ]);

      setLogs(logsRes.data);
      setEstatisticas(statsRes.data);
    } catch (error) {
      console.error('Erro ao carregar auditoria:', error);
    } finally {
      setLoading(false);
    }
  }, [filtroAcao, filtroEntidade, dataInicio, dataFim]);

  useEffect(() => {
    carregarDados();
  }, [carregarDados]);

  const limparFiltros = () => {
    setFiltroAcao('');
    setFiltroEntidade('');
    setDataInicio('');
    setDataFim('');
  };

  const getAcaoColor = (acao) => {
    switch (acao) {
      case 'criar':
        return 'bg-emerald-500/20 text-emerald-400';
      case 'editar':
        return 'bg-blue-500/20 text-blue-400';
      case 'deletar':
        return 'bg-red-500/20 text-red-400';
      case 'login':
        return 'bg-purple-500/20 text-purple-400';
      default:
        return 'bg-slate-500/20 text-slate-400';
    }
  };

  const handleLimparLogs = async (e) => {
    e.preventDefault();
    if (textoConfirmacao !== 'LIMPAR') return;

    setLimpando(true);
    try {
      await auditoriaAPI.limpar();
      setModalLimpezaOpen(false);
      carregarDados();
      // Opcional: Mostrar feedback visual melhor que alert
      alert('Logs limpos com sucesso!');
    } catch (error) {
      console.error('Erro ao limpar logs:', error);
      alert('Erro ao limpar logs.');
    } finally {
      setLimpando(false);
    }
  };

  const getEntidadeIcon = (entidade) => {
    switch (entidade) {
      case 'cliente':
        return '👤';
      case 'emprestimo':
        return '💰';
      case 'pagamento':
        return '💳';
      case 'usuario':
        return '🔐';
      default:
        return '📄';
    }
  };

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground" data-testid="auditoria-title">
            Auditoria
          </h1>
          <p className="text-muted-foreground mt-1">Registro de todas as ações do sistema</p>
        </div>

        {/* Filtros */}
        <div className="bg-card rounded-lg border border-border p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">Ação</label>
              <select
                value={filtroAcao}
                onChange={(e) => setFiltroAcao(e.target.value)}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                data-testid="filtro-acao"
              >
                <option value="">Todas</option>
                <option value="criar">Criar</option>
                <option value="editar">Editar</option>
                <option value="deletar">Deletar</option>
                <option value="login">Login</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">Entidade</label>
              <select
                value={filtroEntidade}
                onChange={(e) => setFiltroEntidade(e.target.value)}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                data-testid="filtro-entidade"
              >
                <option value="">Todas</option>
                <option value="cliente">Cliente</option>
                <option value="emprestimo">Empréstimo</option>
                <option value="pagamento">Pagamento</option>
                <option value="usuario">Usuário</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">Data Início</label>
              <input
                type="date"
                value={dataInicio}
                onChange={(e) => setDataInicio(e.target.value)}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                data-testid="filtro-data-inicio"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-2">Data Fim</label>
              <input
                type="date"
                value={dataFim}
                onChange={(e) => setDataFim(e.target.value)}
                className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                data-testid="filtro-data-fim"
              />
            </div>
            <div className="flex flex-col justify-end gap-2">
              <button
                onClick={limparFiltros}
                className="w-full h-10 px-4 bg-muted hover:bg-muted/80 text-foreground rounded-md transition"
                data-testid="limpar-filtros-button"
              >
                Limpar Filtros
              </button>
              <button
                onClick={() => {
                  setTextoConfirmacao('');
                  setModalLimpezaOpen(true);
                }}
                className="w-full h-10 px-4 bg-red-600 hover:bg-red-700 text-white rounded-md transition"
              >
                Limpar Logs
              </button>
            </div>
          </div>
        </div>

        {/* Estatísticas */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-card rounded-lg border border-border p-4">
            <p className="text-sm text-muted-foreground mb-1">Total de Logs</p>
            <p className="text-2xl font-bold text-foreground" data-testid="stat-total">
              {estatisticas.total}
            </p>
          </div>
          <div className="bg-card rounded-lg border border-border p-4">
            <p className="text-sm text-muted-foreground mb-1">Hoje</p>
            <p className="text-2xl font-bold text-blue-500" data-testid="stat-hoje">
              {estatisticas.hoje}
            </p>
          </div>
          <div className="bg-card rounded-lg border border-border p-4">
            <p className="text-sm text-muted-foreground mb-1">Últimos 7 dias</p>
            <p className="text-2xl font-bold text-emerald-500" data-testid="stat-semana">
              {estatisticas.ultimos_7_dias}
            </p>
          </div>
          <div className="bg-card rounded-lg border border-border p-4">
            <p className="text-sm text-muted-foreground mb-1">Usuários Ativos</p>
            <p className="text-2xl font-bold text-purple-500" data-testid="stat-usuarios">
              {estatisticas.usuarios_ativos}
            </p>
          </div>
        </div>

        {/* Logs */}
        <div className="bg-card rounded-lg border border-border overflow-hidden">
          {loading ? (
            <div className="p-8 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
              <p className="text-muted-foreground mt-2">Carregando logs...</p>
            </div>
          ) : logs.length === 0 ? (
            <div className="p-8 text-center">
              <svg className="w-16 h-16 text-muted-foreground mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <p className="text-muted-foreground">Nenhum log de auditoria encontrado</p>
              <p className="text-sm text-muted-foreground mt-1">As ações do sistema serão registradas aqui automaticamente</p>
            </div>
          ) : (
            <>
              {/* Versão Desktop - Tabela */}
              <div className="hidden md:block overflow-x-auto">
                <table className="min-w-full divide-y divide-border">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Data/Hora</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Usuário</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Ação</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Entidade</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Detalhes</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">IP</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border" data-testid="auditoria-table-body">
                    {logs.map((log) => (
                      <tr key={log.id} data-testid={`log-row-${log.id}`} className="hover:bg-muted/50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                          {formatarDataHora(log.created_at)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                          {log.usuario_email}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs font-semibold rounded-full capitalize ${getAcaoColor(log.acao)}`}>
                            {log.acao}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                          <span className="mr-1">{getEntidadeIcon(log.entidade)}</span>
                          <span className="capitalize">{log.entidade}</span>
                        </td>
                        <td className="px-6 py-4 text-sm text-muted-foreground max-w-xs truncate" title={log.detalhes}>
                          {log.detalhes}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                          {log.ip || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Versão Mobile - Cards */}
              <div className="md:hidden divide-y divide-border">
                {logs.map((log) => (
                  <div key={log.id} className="p-4" data-testid={`log-card-${log.id}`}>
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`px-2 py-0.5 text-xs font-semibold rounded-full capitalize ${getAcaoColor(log.acao)}`}>
                            {log.acao}
                          </span>
                          <span className="text-sm text-foreground">
                            <span className="mr-1">{getEntidadeIcon(log.entidade)}</span>
                            <span className="capitalize">{log.entidade}</span>
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground">{formatarDataHora(log.created_at)}</p>
                      </div>
                    </div>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Usuário:</span>
                        <span className="text-foreground font-medium">{log.usuario_email}</span>
                      </div>
                      {log.detalhes && (
                        <div className="pt-2 border-t border-border">
                          <p className="text-xs text-muted-foreground mb-1">Detalhes:</p>
                          <p className="text-sm text-foreground">{log.detalhes}</p>
                        </div>
                      )}
                      {log.ip && (
                        <div className="flex justify-between text-xs">
                          <span className="text-muted-foreground">IP:</span>
                          <span className="text-muted-foreground font-mono">{log.ip}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Nota */}
        <div className="mt-6 bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
          <h3 className="font-semibold text-amber-400 mb-2 flex items-center">
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            Importante
          </h3>
          <p className="text-sm text-amber-400/80">
            Os logs de auditoria são mantidos por 90 dias e não podem ser editados ou deletados.
            Use esta ferramenta para rastreamento de operações e compliance.
          </p>
        </div>
      </div>

      {/* Modal de Confirmação de Limpeza */}
      {
        modalLimpezaOpen && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-card border border-border rounded-lg shadow-xl w-full max-w-md p-6">
              <div className="flex items-center gap-3 text-red-600 mb-4">
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                <h2 className="text-xl font-bold">Limpar Todos os Logs</h2>
              </div>

              <p className="text-foreground mb-4">
                Esta ação excluirá <strong>permanentemente</strong> todo o histórico de auditoria.
                Isso não pode ser desfeito.
              </p>

              <form onSubmit={handleLimparLogs}>
                <div className="mb-6">
                  <label className="block text-sm text-muted-foreground mb-2">
                    Para confirmar, digite <strong>LIMPAR</strong> abaixo:
                  </label>
                  <input
                    type="text"
                    value={textoConfirmacao}
                    onChange={(e) => setTextoConfirmacao(e.target.value)}
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground"
                    placeholder="LIMPAR"
                    required
                  />
                </div>

                <div className="flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setModalLimpezaOpen(false)}
                    className="px-4 py-2 text-muted-foreground hover:text-foreground transition bg-muted/50 rounded-lg hover:bg-muted"
                    disabled={limpando}
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={textoConfirmacao !== 'LIMPAR' || limpando}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {limpando ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        Limpando...
                      </>
                    ) : (
                      'Confirmar Limpeza'
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )
      }
    </Layout >
  );
};

export default Auditoria;
