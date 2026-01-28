import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import Button from '../components/Button';
import { useModal } from '../components/Modal';
import { notificacoesAPI } from '../api/api';
import { formatarDataHora } from '../utils/formatters';

const Notificacoes = () => {
  const [notificacoes, setNotificacoes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [verificando, setVerificando] = useState(false);
  const [filtro, setFiltro] = useState('todas');
  const [error, setError] = useState('');
  const modal = useModal();

  const carregarNotificacoes = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const response = await notificacoesAPI.listar({
        apenas_nao_lidas: filtro === 'nao_lidas'
      });
      setNotificacoes(response.data);
    } catch (err) {
      console.error('Erro ao carregar notificações:', err);
      setError('Erro ao carregar notificações');
    } finally {
      setLoading(false);
    }
  }, [filtro]);

  useEffect(() => {
    carregarNotificacoes();
  }, [carregarNotificacoes]);

  const marcarComoLida = async (id) => {
    try {
      await notificacoesAPI.marcarLida(id);
      setNotificacoes(prev => prev.map(n =>
        n.id === id ? { ...n, lida: true } : n
      ));
    } catch (err) {
      console.error('Erro ao marcar como lida:', err);
    }
  };

  const marcarTodasComoLidas = async () => {
    try {
      await notificacoesAPI.marcarTodasLidas();
      setNotificacoes(prev => prev.map(n => ({ ...n, lida: true })));
    } catch (err) {
      console.error('Erro ao marcar todas como lidas:', err);
    }
  };

  const limparTodasNotificacoes = () => {
    modal.confirm(
      'Limpar Todas as Notificações',
      'Tem certeza que deseja apagar TODAS as notificações? Esta ação não pode ser desfeita.',
      async () => {
        try {
          await notificacoesAPI.limparTodas();
          setNotificacoes([]);
          modal.success('Sucesso', 'Todas as notificações foram removidas.');
        } catch (err) {
          console.error('Erro ao limpar notificações:', err);
          modal.error('Erro', 'Não foi possível limpar as notificações.');
        }
      }
    );
  };

  const excluirNotificacao = async (id) => {
    try {
      await notificacoesAPI.excluir(id);
      setNotificacoes(prev => prev.filter(n => n.id !== id));
    } catch (err) {
      console.error('Erro ao excluir notificação:', err);
    }
  };

  const verificarVencimentos = async () => {
    try {
      setVerificando(true);
      const response = await notificacoesAPI.verificarVencimentos();
      modal.success('Verificação Concluída', response.data.message || 'Vencimentos verificados com sucesso.');
      carregarNotificacoes();
    } catch (err) {
      console.error('Erro ao verificar vencimentos:', err);
      modal.error('Erro na Verificação', 'Não foi possível verificar os vencimentos. Tente novamente.');
    } finally {
      setVerificando(false);
    }
  };

  const getIconeNotificacao = (tipo) => {
    const icones = {
      vencimento: '📅',
      atraso: '⚠️',
      pagamento: '💰',
      sistema: '⚙️'
    };
    return icones[tipo] || '🔔';
  };

  const getCorNotificacao = (tipo) => {
    const cores = {
      vencimento: 'border-amber-500 bg-amber-500/10',
      atraso: 'border-red-500 bg-red-500/10',
      pagamento: 'border-emerald-500 bg-emerald-500/10',
      sistema: 'border-blue-500 bg-blue-500/10'
    };
    return cores[tipo] || 'border-slate-500 bg-slate-500/10';
  };

  const naoLidas = notificacoes.filter(n => !n.lida).length;
  const totalVencimentos = notificacoes.filter(n => n.tipo === 'vencimento').length;
  const totalAtrasos = notificacoes.filter(n => n.tipo === 'atraso').length;

  if (loading) return <Loading message="Carregando notificações..." />;

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground" data-testid="notificacoes-title">
              Notificações
            </h1>
            <p className="text-muted-foreground mt-1">
              {naoLidas > 0 ? `${naoLidas} não lida${naoLidas > 1 ? 's' : ''}` : 'Todas as notificações lidas'}
            </p>
          </div>
          <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
            <Button
              onClick={verificarVencimentos}
              variant="primary"
              testId="verificar-vencimentos"
              disabled={verificando}
              className="w-full sm:w-auto justify-center"
            >
              {verificando ? (
                <span className="flex items-center">
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Verificando...
                </span>
              ) : (
                <>
                  <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
                  </svg>
                  Verificar Vencimentos
                </>
              )}
            </Button>
            {naoLidas > 0 && (
              <Button
                onClick={marcarTodasComoLidas}
                variant="secondary"
                testId="marcar-todas-lidas"
                className="w-full sm:w-auto justify-center"
              >
                Marcar Todas como Lidas
              </Button>
            )}

            {notificacoes.length > 0 && (
              <Button
                onClick={limparTodasNotificacoes}
                variant="danger"
                className="bg-red-500 hover:bg-red-600 text-white w-full sm:w-auto justify-center"
                testId="limpar-todas"
              >
                Limpar Todas
              </Button>
            )}
          </div>
        </div>

        {error && (
          <div className="mb-6 bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {/* Cards de Resumo */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-card rounded-lg border border-border p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total</p>
                <p className="text-2xl font-bold text-foreground">{notificacoes.length}</p>
              </div>
              <div className="text-3xl">🔔</div>
            </div>
          </div>
          <div className="bg-card rounded-lg border border-border p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Não Lidas</p>
                <p className="text-2xl font-bold text-blue-500">{naoLidas}</p>
              </div>
              <div className="text-3xl">📩</div>
            </div>
          </div>
          <div className="bg-card rounded-lg border border-border p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Vencimentos</p>
                <p className="text-2xl font-bold text-amber-500">{totalVencimentos}</p>
              </div>
              <div className="text-3xl">📅</div>
            </div>
          </div>
          <div className="bg-card rounded-lg border border-border p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Atrasos</p>
                <p className="text-2xl font-bold text-red-500">{totalAtrasos}</p>
              </div>
              <div className="text-3xl">⚠️</div>
            </div>
          </div>
        </div>

        {/* Filtros */}
        <div className="flex flex-wrap gap-2 mb-6">
          <button
            onClick={() => setFiltro('todas')}
            className={`px-4 py-2 rounded-lg transition ${filtro === 'todas'
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-foreground hover:bg-muted/80'
              }`}
            data-testid="filtro-todas"
          >
            Todas
          </button>
          <button
            onClick={() => setFiltro('nao_lidas')}
            className={`px-4 py-2 rounded-lg transition ${filtro === 'nao_lidas'
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-foreground hover:bg-muted/80'
              }`}
            data-testid="filtro-nao-lidas"
          >
            Não Lidas ({naoLidas})
          </button>
        </div>

        {/* Lista de Notificações */}
        <div className="space-y-3">
          {notificacoes.length === 0 ? (
            <div className="bg-card rounded-lg border border-border p-8 text-center" data-testid="sem-notificacoes">
              <div className="text-6xl mb-4">🔔</div>
              <h3 className="text-xl font-semibold text-foreground mb-2">Nenhuma notificação</h3>
              <p className="text-muted-foreground mb-4">
                Clique em "Verificar Vencimentos" para gerar alertas de parcelas próximas do vencimento ou atrasadas.
              </p>
              <Button onClick={verificarVencimentos} variant="primary" disabled={verificando}>
                Verificar Agora
              </Button>
            </div>
          ) : (
            notificacoes.map((notif) => (
              <div
                key={notif.id}
                className={`bg-card rounded-lg border border-border overflow-hidden transition hover:border-muted-foreground ${!notif.lida ? 'border-l-4 ' + getCorNotificacao(notif.tipo).split(' ')[0] : ''
                  }`}
                data-testid={`notificacao-${notif.id}`}
              >
                <div className={`p-6 ${!notif.lida ? getCorNotificacao(notif.tipo).split(' ')[1] : ''}`}>
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-4 flex-1">
                      <div className="text-3xl">{getIconeNotificacao(notif.tipo)}</div>
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1">
                          <h3 className="font-bold text-foreground">{notif.titulo}</h3>
                          {!notif.lida && (
                            <span className="px-2 py-0.5 text-xs bg-primary text-primary-foreground rounded-full">
                              Nova
                            </span>
                          )}
                          <span className={`px-2 py-0.5 text-xs rounded-full ${notif.tipo === 'atraso' ? 'bg-red-500/20 text-red-400' :
                            notif.tipo === 'vencimento' ? 'bg-amber-500/20 text-amber-400' :
                              notif.tipo === 'pagamento' ? 'bg-emerald-500/20 text-emerald-400' :
                                'bg-slate-500/20 text-slate-400'
                            }`}>
                            {notif.tipo?.toUpperCase()}
                          </span>
                        </div>
                        <p className="text-muted-foreground">{notif.mensagem}</p>
                        <p className="text-xs text-muted-foreground mt-2">
                          {formatarDataHora(notif.created_at)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2 ml-4">
                      {!notif.lida && (
                        <button
                          onClick={() => marcarComoLida(notif.id)}
                          className="text-sm text-primary hover:text-primary/80 whitespace-nowrap"
                          data-testid={`marcar-lida-${notif.id}`}
                        >
                          Marcar como lida
                        </button>
                      )}
                      <button
                        onClick={() => excluirNotificacao(notif.id)}
                        className="text-muted-foreground hover:text-red-500 transition"
                        title="Excluir notificação"
                      >
                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Info sobre notificações automáticas */}
        <div className="mt-8 bg-blue-500/10 border border-blue-500/30 rounded-lg p-6">
          <h3 className="font-semibold text-blue-400 mb-2 flex items-center">
            <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
            Como funcionam as notificações
          </h3>
          <ul className="text-sm text-blue-400/80 space-y-1">
            <li>• <strong>Vencimentos:</strong> Alertas para parcelas que vencem nos próximos 7 dias</li>
            <li>• <strong>Atrasos:</strong> Alertas para parcelas já vencidas e não pagas</li>
            <li>• <strong>Pagamentos:</strong> Confirmações de pagamentos recebidos</li>
            <li>• Clique em "Verificar Vencimentos" para atualizar as notificações manualmente</li>
          </ul>
        </div>
      </div>
    </Layout>
  );
};

export default Notificacoes;
