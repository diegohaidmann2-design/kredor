import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { suporteAPI, uploadAPI, BACKEND_URL } from '../api/api';
import Layout from '../components/Layout';
import { toast } from '../hooks/use-toast';

const SuporteDetalhes = () => {
  const { numero_ticket } = useParams();
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);

  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [novaMensagem, setNovaMensagem] = useState('');
  const [enviando, setEnviando] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validar tamanho (5MB)
    if (file.size > 5 * 1024 * 1024) {
      alert('Arquivo muito grande. Máximo 5MB.');
      return;
    }

    setEnviando(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await uploadAPI.uploadFile(formData);
      const { url, type } = response.data;

      // Enviar mensagem automaticamente com o anexo
      await suporteAPI.enviarMensagem(numero_ticket, {
        mensagem: type === 'imagem' ? 'Imagem enviada' : 'Arquivo enviado',
        tipo: type,
        arquivo_url: url
      });

      await carregarTicket();
    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível enviar arquivo.", variant: 'destructive' });
      console.error('Erro ao enviar arquivo:', error);
      alert('Erro ao enviar arquivo');
    } finally {
      setEnviando(false);
      // Limpar input
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  useEffect(() => {
    carregarTicket();
    // Auto-reload a cada 10 segundos
    const interval = setInterval(carregarTicket, 10000);
    return () => clearInterval(interval);
  }, [numero_ticket]);

  useEffect(() => {
    scrollToBottom();
  }, [ticket?.mensagens]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const carregarTicket = async () => {
    try {
      const response = await suporteAPI.obterTicket(numero_ticket);
      setTicket(response.data);
    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível carregar ticket.", variant: 'destructive' });
      console.error('Erro ao carregar ticket:', error);
    } finally {
      setLoading(false);
    }
  };

  const enviarMensagem = async (e) => {
    e.preventDefault();
    if (!novaMensagem.trim()) return;

    setEnviando(true);
    try {
      await suporteAPI.enviarMensagem(numero_ticket, {
        mensagem: novaMensagem
      });
      setNovaMensagem('');
      await carregarTicket();
    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível enviar mensagem.", variant: 'destructive' });
      console.error('Erro ao enviar mensagem:', error);
    } finally {
      setEnviando(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      enviarMensagem(e);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
        </div>
      </Layout>
    );
  }

  if (!ticket) {
    return (
      <Layout>
        <div className="text-center py-8">
          <p className="text-muted-foreground">Ticket não encontrado</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <button
              onClick={() => navigate('/suporte')}
              className="text-purple-600 hover:text-purple-700 flex items-center gap-2 mb-4"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Voltar
            </button>

            <div className="bg-card rounded-lg border border-border p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h1 className="text-2xl font-bold text-foreground">{ticket.numero_ticket}</h1>
                  <p className="text-xl text-foreground mt-1">{ticket.assunto}</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-semibold ${ticket.status === 'aberto' ? 'bg-yellow-100 text-yellow-800' :
                  ticket.status === 'em_atendimento' ? 'bg-blue-100 text-blue-800' :
                    ticket.status === 'resolvido' ? 'bg-green-100 text-green-800' :
                      'bg-gray-100 text-gray-800'
                  }`}>
                  {(ticket.status || '').replace('_', ' ').toUpperCase()}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Categoria</p>
                  <p className="font-medium text-foreground capitalize">{ticket.categoria}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Prioridade</p>
                  <p className="font-medium text-foreground capitalize">{ticket.prioridade}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Criado em</p>
                  <p className="font-medium text-foreground">
                    {new Date(ticket.criado_em).toLocaleString('pt-BR')}
                  </p>
                </div>
              </div>

              {ticket.atribuido_nome && (
                <div className="mt-4 pt-4 border-t border-border">
                  <p className="text-sm text-muted-foreground">
                    Atendente: <span className="font-medium text-foreground">{ticket.atribuido_nome}</span>
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Chat */}
          <div className="bg-card rounded-lg border border-border overflow-hidden">
            {/* Mensagens */}
            <div className="h-[500px] overflow-y-auto p-6 space-y-4">
              {ticket.mensagens.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.remetente_tipo === 'usuario' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[70%] ${msg.remetente_tipo === 'usuario'
                    ? 'bg-purple-600 text-white'
                    : 'bg-muted text-foreground'
                    } rounded-lg p-4`}>
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-semibold text-sm">{msg.remetente_nome}</p>
                      <span className={`px-2 py-0.5 rounded text-xs ${msg.remetente_tipo === 'usuario'
                        ? 'bg-purple-700 text-purple-100'
                        : 'bg-muted-foreground/20 text-muted-foreground'
                        }`}>
                        {msg.remetente_tipo === 'usuario' ? 'Você' : 'Suporte'}
                      </span>
                    </div>

                    {msg.tipo === 'imagem' && msg.arquivo_url ? (
                      <div className="mb-2">
                        <img
                          src={`${BACKEND_URL}${msg.arquivo_url}`}
                          alt="Anexo"
                          className="max-w-full rounded-lg cursor-pointer hover:opacity-90 transition"
                          onClick={() => window.open(`${BACKEND_URL}${msg.arquivo_url}`, '_blank')}
                          style={{ maxHeight: '200px' }}
                        />
                      </div>
                    ) : msg.tipo === 'arquivo' && msg.arquivo_url ? (
                      <div className="mb-2">
                        <a
                          href={`${BACKEND_URL}${msg.arquivo_url}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 p-3 bg-background/50 rounded-lg hover:bg-background/80 transition"
                        >
                          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                          </svg>
                          <span className="underline">Visualizar Anexo</span>
                        </a>
                      </div>
                    ) : (
                      <p className="whitespace-pre-wrap">{msg.conteudo}</p>
                    )}
                    <p className={`text-xs mt-2 ${msg.remetente_tipo === 'usuario'
                      ? 'text-purple-200'
                      : 'text-muted-foreground'
                      }`}>
                      {new Date(msg.enviado_em).toLocaleString('pt-BR')}
                    </p>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            {ticket.status !== 'fechado' && (
              <form onSubmit={enviarMensagem} className="border-t border-border p-4">
                <div className="flex gap-2">
                  <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    onChange={handleFileUpload}
                    accept=".jpg,.jpeg,.png,.pdf"
                  />
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={enviando}
                    className="px-3 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
                    title="Anexar arquivo"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                    </svg>
                  </button>
                  <textarea
                    value={novaMensagem}
                    onChange={(e) => setNovaMensagem(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Digite sua mensagem..."
                    className="flex-1 px-3 py-2 bg-background border border-border rounded-md text-foreground resize-none h-20"
                    disabled={enviando}
                  />
                  <button
                    type="submit"
                    disabled={enviando || !novaMensagem.trim()}
                    className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition disabled:opacity-50 disabled:cursor-not-allowed h-20"
                  >
                    {enviando ? (
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    ) : (
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                      </svg>
                    )}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default SuporteDetalhes;
