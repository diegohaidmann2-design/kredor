import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';


import { notificacoesAPI } from '../api/api';

const NotificationBell = () => {
  const navigate = useNavigate();
  const [notificacoes, setNotificacoes] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    carregarNotificacoes();
    // Auto-reload a cada 30 segundos
    const interval = setInterval(carregarNotificacoes, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const carregarNotificacoes = async () => {
    try {
      const response = await notificacoesAPI.listar();
      if (Array.isArray(response.data)) {
        setNotificacoes(response.data);
      } else {
        console.warn('Resposta de notificações inválida:', response.data);
        setNotificacoes([]);
      }
    } catch (error) {
      console.error('Erro ao carregar notificações:', error);
      setNotificacoes([]);
    }
  };

  const marcarComoLida = async (notificacaoId) => {
    try {
      await notificacoesAPI.marcarLida(notificacaoId);
      await carregarNotificacoes();
    } catch (error) {
      console.error('Erro ao marcar notificação como lida:', error);
    }
  };

  const marcarTodasComoLidas = async () => {
    setLoading(true);
    try {
      await notificacoesAPI.marcarTodasLidas();
      await carregarNotificacoes();
    } catch (error) {
      console.error('Erro ao marcar todas como lidas:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleNotificationClick = (notificacao) => {
    if (!notificacao.lida) {
      marcarComoLida(notificacao.id);
    }
    if (notificacao.link) {
      navigate(notificacao.link);
    }
    setIsOpen(false);
  };

  // Garante que é array antes de filtrar
  const listaNotificacoes = Array.isArray(notificacoes) ? notificacoes : [];
  const naoLidas = listaNotificacoes.filter(n => !n.lida).length;

  const getIconeNotificacao = (tipo) => {
    const iconClass = "w-5 h-5";
    
    switch (tipo) {
      case 'suporte_novo':
        return (
          <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-purple-500/20 rounded-full">
            <svg className={`${iconClass} text-purple-400`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </div>
        );
      case 'suporte_resposta':
      case 'suporte_mensagem':
        return (
          <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-blue-500/20 rounded-full">
            <svg className={`${iconClass} text-blue-400`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
        );
      case 'pagamento':
        return (
          <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-green-500/20 rounded-full">
            <svg className={`${iconClass} text-green-400`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        );
      case 'vencimento':
        return (
          <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-yellow-500/20 rounded-full">
            <svg className={`${iconClass} text-yellow-400`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        );
      case 'atraso':
        return (
          <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-red-500/20 rounded-full">
            <svg className={`${iconClass} text-red-400`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
        );
      case 'trial_expirando':
      case 'assinatura_expirando':
        return (
          <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-orange-500/20 rounded-full">
            <svg className={`${iconClass} text-orange-400`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        );
      case 'boas_vindas':
        return (
          <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-indigo-500/20 rounded-full">
            <svg className={`${iconClass} text-indigo-400`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        );
      case 'admin_novo_usuario':
        return (
          <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-cyan-500/20 rounded-full">
            <svg className={`${iconClass} text-cyan-400`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
            </svg>
          </div>
        );
      case 'admin_resumo_diario':
        return (
          <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-violet-500/20 rounded-full">
            <svg className={`${iconClass} text-violet-400`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
        );
      case 'sistema':
      default:
        return (
          <div className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-slate-500/20 rounded-full">
            <svg className={`${iconClass} text-slate-400`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
        );
    }
  };

  const formatarTempo = (data) => {
    const agora = new Date();
    const dataNotif = new Date(data);
    const diffMs = agora - dataNotif;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHoras = Math.floor(diffMs / 3600000);
    const diffDias = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Agora';
    if (diffMins < 60) return `${diffMins}min atrás`;
    if (diffHoras < 24) return `${diffHoras}h atrás`;
    if (diffDias < 7) return `${diffDias}d atrás`;
    return dataNotif.toLocaleDateString('pt-BR');
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Botão do Sininho */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-muted-foreground hover:text-foreground transition rounded-lg hover:bg-muted"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        
        {/* Badge de notificações não lidas */}
        {naoLidas > 0 && (
          <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-5 w-5 bg-red-500 text-white text-xs font-bold items-center justify-center">
              {naoLidas > 9 ? '9+' : naoLidas}
            </span>
          </span>
        )}
      </button>

      {/* Dropdown de Notificações - Abre para a DIREITA (fora da sidebar) */}
      {isOpen && (
        <div 
          className="fixed bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
          style={{ 
            width: '400px', 
            maxHeight: '500px',
            top: '80px',
            left: '220px',
            zIndex: 9999
          }}
        >
          {/* Header */}
          <div className="px-4 py-3 border-b border-border bg-muted/50">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold text-foreground text-base">Notificações</h3>
                {naoLidas > 0 && (
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {naoLidas} não lida{naoLidas > 1 ? 's' : ''}
                  </p>
                )}
              </div>
              {naoLidas > 0 && (
                <button
                  onClick={marcarTodasComoLidas}
                  disabled={loading}
                  className="text-xs text-purple-500 hover:text-purple-400 font-medium disabled:opacity-50 transition-colors"
                >
                  {loading ? 'Marcando...' : 'Marcar todas como lidas'}
                </button>
              )}
            </div>
          </div>

          {/* Lista de Notificações */}
          <div className="overflow-y-auto" style={{ maxHeight: '380px' }}>
            {listaNotificacoes.length === 0 ? (
              <div className="p-8 text-center">
                <div className="w-16 h-16 mx-auto mb-3 bg-muted rounded-full flex items-center justify-center">
                  <svg className="w-8 h-8 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                  </svg>
                </div>
                <p className="text-muted-foreground font-medium">Nenhuma notificação</p>
                <p className="text-muted-foreground text-xs mt-1">
                  Você será notificado sobre vencimentos e atualizações
                </p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {listaNotificacoes.slice(0, 10).map((notif) => (
                  <div
                    key={notif.id}
                    onClick={() => handleNotificationClick(notif)}
                    className={`p-4 cursor-pointer transition-colors ${
                      !notif.lida 
                        ? 'bg-purple-500/10 hover:bg-purple-500/20' 
                        : 'hover:bg-muted/50'
                    }`}
                  >
                    <div className="flex gap-3">
                      {/* Ícone */}
                      {getIconeNotificacao(notif.tipo)}
                      
                      {/* Conteúdo */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <p className={`text-sm font-semibold leading-tight ${
                            !notif.lida ? 'text-foreground' : 'text-muted-foreground'
                          }`}>
                            {notif.titulo}
                          </p>
                          {!notif.lida && (
                            <span className="flex-shrink-0 w-2 h-2 bg-purple-500 rounded-full mt-1.5"></span>
                          )}
                        </div>
                        
                        <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                          {notif.mensagem}
                        </p>
                        
                        <div className="flex items-center gap-2 mt-2">
                          <span className="text-xs text-muted-foreground">
                            {formatarTempo(notif.created_at)}
                          </span>
                          {notif.link && (
                            <span className="text-xs text-purple-500 font-medium">
                              Ver detalhes →
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          {listaNotificacoes.length > 0 && (
            <div className="px-4 py-3 border-t border-border bg-muted/50 text-center">
              <button
                onClick={() => {
                  navigate('/notificacoes');
                  setIsOpen(false);
                }}
                className="text-sm text-purple-500 hover:text-purple-400 font-medium transition-colors"
              >
                Ver todas as notificações
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
