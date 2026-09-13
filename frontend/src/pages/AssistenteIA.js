import React, { useState, useRef, useEffect } from 'react';
import Layout from '../components/Layout';
import Button from '../components/Button';
import { assistenteAPI } from '../api/api';

import { useModal } from '../components/Modal';

const AssistenteIA = () => {
  const modal = useModal();
  const [mensagem, setMensagem] = useState('');
  const [chat, setChat] = useState([
    {
      tipo: 'bot',
      texto: 'Olá! Sou o Assistente IA do Kredor, powered by Gemini. Como posso ajudá-lo hoje?\n\nPosso responder sobre:\n• Cálculos de juros (Simples, Compostos, Price, SAC)\n• Gestão de clientes e empréstimos\n• Relatórios financeiros\n• Inadimplência e cobrança'
    }
  ]);
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [error, setError] = useState(null);
  const chatContainerRef = useRef(null);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chat]);

  const handleEnviar = async () => {
    if (!mensagem.trim() || loading) return;

    const novaMensagem = mensagem;
    setMensagem('');
    setError(null);

    setChat(prev => [...prev, { tipo: 'user', texto: novaMensagem }]);

    setLoading(true);

    try {
      const response = await assistenteAPI.chat({
        mensagem: novaMensagem,
        session_id: sessionId
      });

      const { resposta, session_id } = response.data;

      if (!sessionId) {
        setSessionId(session_id);
      }

      setChat(prev => [...prev, { tipo: 'bot', texto: resposta }]);
    } catch (err) {
      console.error('Erro ao enviar mensagem:', err);

      if (err.response && err.response.status === 403) {
        modal.warning(
          'Funcionalidade indisponível no seu plano',
          'O Assistente IA é um recurso exclusivo dos planos Profissional e Enterprise. Faça upgrade para ter acesso a respostas inteligentes em tempo real.'
        );
        // Remove a mensagem do usuário do chat visual para não ficar "pendurada" ou adiciona msg de erro do bot
        setChat(prev => [...prev, {
          tipo: 'bot',
          texto: '🔒 Recurso indisponível no seu plano atual.',
          error: true
        }]);
      } else {
        setChat(prev => [...prev, {
          tipo: 'bot',
          texto: 'Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.',
          error: true
        }]);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleEnviar();
    }
  };

  const sugestoes = [
    'Como funciona a Tabela Price?',
    'Qual a diferença entre SAC e Price?',
    'Como calcular juros de mora?',
    'Como gerar um relatório de inadimplência?',
    'Como cadastrar um novo cliente?'
  ];

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground" data-testid="assistente-title">
            Assistente IA
          </h1>
          <p className="text-muted-foreground mt-1">
            Powered by <span className="font-semibold text-primary">Gemini 3 Flash</span> • Pergunte qualquer coisa sobre o sistema
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Chat */}
          <div className="lg:col-span-2 bg-card rounded-lg border border-border overflow-hidden flex flex-col" style={{ height: '600px' }}>
            <div
              ref={chatContainerRef}
              className="flex-1 overflow-y-auto p-6 space-y-4"
              data-testid="chat-container"
            >
              {chat.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.tipo === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[85%] rounded-lg px-4 py-3 ${msg.tipo === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : msg.error
                          ? 'bg-red-500/10 text-red-400 border border-red-500/30'
                          : 'bg-muted text-foreground'
                      }`}
                  >
                    {msg.tipo === 'bot' && (
                      <div className="flex items-center mb-2">
                        <div className="w-6 h-6 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center mr-2">
                          <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                          </svg>
                        </div>
                        <span className="text-xs font-semibold text-muted-foreground">Assistente IA</span>
                      </div>
                    )}
                    <p className="text-sm whitespace-pre-line leading-relaxed">{msg.texto}</p>
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="bg-muted rounded-lg px-4 py-3">
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                      <span className="text-xs text-muted-foreground ml-2">Gemini está pensando...</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {error && (
              <div className="px-4 py-2 bg-red-500/10 border-t border-red-500/30">
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}

            <div className="border-t border-border p-4 bg-muted/50">
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={mensagem}
                  onChange={(e) => setMensagem(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Digite sua pergunta..."
                  className="flex-1 px-4 py-3 bg-background border border-border rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                  data-testid="input-mensagem"
                  disabled={loading}
                />
                <Button
                  onClick={handleEnviar}
                  disabled={loading || !mensagem.trim()}
                  testId="enviar-mensagem-button"
                  className="px-6"
                >
                  {loading ? (
                    <svg className="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  ) : (
                    'Enviar'
                  )}
                </Button>
              </div>
            </div>
          </div>

          {/* Sugestões */}
          <div className="space-y-4">
            <div className="bg-card rounded-lg border border-border p-6">
              <h2 className="font-bold text-lg text-foreground mb-4 flex items-center">
                <svg className="w-5 h-5 mr-2 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM15.657 5.757a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707zM18 10a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1zM5.05 6.464A1 1 0 106.464 5.05l-.707-.707a1 1 0 00-1.414 1.414l.707.707zM5 10a1 1 0 01-1 1H3a1 1 0 110-2h1a1 1 0 011 1zM8 16v-1h4v1a2 2 0 11-4 0zM12 14c.015-.34.208-.646.477-.859a4 4 0 10-4.954 0c.27.213.462.519.476.859h4.002z" />
                </svg>
                Perguntas Sugeridas
              </h2>
              <div className="space-y-2">
                {sugestoes.map((sugestao, idx) => (
                  <button
                    key={idx}
                    onClick={() => setMensagem(sugestao)}
                    disabled={loading}
                    className="w-full text-left text-sm px-3 py-2 bg-muted/50 hover:bg-primary/10 hover:text-primary rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed text-foreground"
                    data-testid={`sugestao-${idx}`}
                  >
                    {sugestao}
                  </button>
                ))}
              </div>
            </div>

            <div className="bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-lg p-4">
              <h3 className="font-semibold text-blue-400 mb-2 flex items-center">
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Powered by Gemini
              </h3>
              <ul className="text-sm text-blue-400/80 space-y-1">
                <li>• Respostas inteligentes em tempo real</li>
                <li>• Contexto personalizado do seu sistema</li>
                <li>• Suporte a cálculos financeiros</li>
                <li>• Explicações detalhadas</li>
              </ul>
            </div>

            {sessionId && (
              <div className="bg-muted/50 rounded-lg p-3 text-xs text-muted-foreground">
                <span className="font-medium">Sessão:</span> {sessionId.slice(-8)}
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default AssistenteIA;
