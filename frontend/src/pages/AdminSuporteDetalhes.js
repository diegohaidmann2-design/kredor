import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { adminSuporteAPI, uploadAPI, BACKEND_URL } from '../api/api';
import Layout from '../components/Layout';
import { toast } from '../hooks/use-toast';

const AdminSuporteDetalhes = () => {
  const { numero_ticket } = useParams();
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);

  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [novaMensagem, setNovaMensagem] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [atualizandoStatus, setAtualizandoStatus] = useState(false);
  const fileInputRef = useRef(null);

  // Estado para Modal de Exclusão
  const [modalExclusaoOpen, setModalExclusaoOpen] = useState(false);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

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

      await adminSuporteAPI.responderTicket(numero_ticket, {
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
      const response = await adminSuporteAPI.obterTicket(numero_ticket);
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
      await adminSuporteAPI.responderTicket(numero_ticket, {
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

  const atribuirTicket = async () => {
    try {
      await adminSuporteAPI.atribuirTicket(numero_ticket);
      await carregarTicket();
    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível atribuir ticket.", variant: 'destructive' });
      console.error('Erro ao atribuir ticket:', error);
    }
  };

  const atualizarStatus = async (novoStatus) => {
    setAtualizandoStatus(true);
    try {
      await adminSuporteAPI.atualizarStatus(numero_ticket, {
        status: novoStatus
      });
      await carregarTicket();
    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível atualizar status.", variant: 'destructive' });
      console.error('Erro ao atualizar status:', error);
    } finally {
      setAtualizandoStatus(false);
    }
  };

  const handleDeletarTicket = () => {
    setModalExclusaoOpen(true);
  };

  const confirmarExclusao = async () => {
    try {
      await adminSuporteAPI.deletarTicket(numero_ticket);
      alert('Ticket excluído com sucesso!');
      navigate('/admin/suporte');
    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível excluir ticket.", variant: 'destructive' });
      console.error('Erro ao excluir ticket:', error);
      alert('Erro ao excluir ticket.');
    } finally {
      setModalExclusaoOpen(false);
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
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <button
              onClick={() => navigate('/admin/suporte')}
              className="text-purple-600 hover:text-purple-700 flex items-center gap-2 mb-4"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Voltar para lista
            </button>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Informações do Ticket */}
              <div className="lg:col-span-2">
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

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Cliente</p>
                      <p className="font-medium text-foreground">{ticket.usuario_nome}</p>
                      <p className="text-xs text-muted-foreground">{ticket.usuario_email}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Categoria</p>
                      <p className="font-medium text-foreground capitalize">{ticket.categoria}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Prioridade</p>
                      <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${ticket.prioridade === 'baixa' ? 'bg-slate-100 text-slate-600' :
                        ticket.prioridade === 'media' ? 'bg-yellow-100 text-yellow-700' :
                          ticket.prioridade === 'alta' ? 'bg-orange-100 text-orange-700' :
                            'bg-red-100 text-red-700'
                        }`}>
                        {ticket.prioridade}
                      </span>
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
                        Atribuído a: <span className="font-medium text-foreground">{ticket.atribuido_nome}</span>
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Ações Rápidas */}
              <div className="space-y-4">
                <div className="bg-card rounded-lg border border-border p-4">
                  <h3 className="font-bold text-foreground mb-3">Ações Rápidas</h3>

                  {!ticket.atribuido_a && (
                    <button
                      onClick={atribuirTicket}
                      className="w-full mb-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition text-sm"
                    >
                      Atribuir a Mim
                    </button>
                  )}

                  <div className="space-y-2">
                    <button
                      onClick={() => atualizarStatus('em_atendimento')}
                      disabled={atualizandoStatus || ticket.status === 'em_atendimento'}
                      className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition text-sm disabled:opacity-50"
                    >
                      Marcar Em Atendimento
                    </button>

                    <button
                      onClick={() => atualizarStatus('resolvido')}
                      disabled={atualizandoStatus || ticket.status === 'resolvido'}
                      className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition text-sm disabled:opacity-50"
                    >
                      Marcar Resolvido
                    </button>

                    <button
                      onClick={() => atualizarStatus('fechado')}
                      disabled={atualizandoStatus || ticket.status === 'fechado'}
                      className="w-full px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition text-sm disabled:opacity-50"
                    >
                      Fechar Ticket
                    </button>

                    <button
                      onClick={handleDeletarTicket}
                      className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition text-sm mt-4 border-t border-red-500 pt-2"
                    >
                      Excluir Ticket Permanentemente
                    </button>
                  </div>
                </div>


                <div className="bg-card rounded-lg border border-border p-4">
                  <h3 className="font-bold text-foreground mb-3">Estatísticas</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Total de Mensagens:</span>
                      <span className="font-medium text-foreground">{ticket.total_mensagens}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Não Lidas (Admin):</span>
                      <span className="font-medium text-foreground">{ticket.mensagens_nao_lidas_admin}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Última Atualização:</span>
                      <span className="font-medium text-foreground">
                        {new Date(ticket.atualizado_em).toLocaleString('pt-BR', {
                          day: '2-digit',
                          month: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Chat */}
          <div className="bg-card rounded-lg border border-border overflow-hidden">
            {/* Mensagens */}
            <div className="h-[500px] overflow-y-auto p-6 space-y-4">
              {ticket.mensagens.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.remetente_tipo === 'admin' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[70%] ${msg.remetente_tipo === 'admin'
                    ? 'bg-purple-600 text-white'
                    : 'bg-muted text-foreground'
                    } rounded-lg p-4`}>
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-semibold text-sm">{msg.remetente_nome}</p>
                      <span className={`px-2 py-0.5 rounded text-xs ${msg.remetente_tipo === 'admin'
                        ? 'bg-purple-700 text-purple-100'
                        : 'bg-muted-foreground/20 text-muted-foreground'
                        }`}>
                        {msg.remetente_tipo === 'admin' ? 'Suporte' : 'Cliente'}
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
                          className="flex items-center gap-2 p-3 bg-purple-700/50 rounded-lg hover:bg-purple-700/80 transition"
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
                    <p className={`text-xs mt-2 ${msg.remetente_tipo === 'admin'
                      ? 'text-purple-200'
                      : 'text-muted-foreground'
                      }`}>
                      {new Date(msg.enviado_em).toLocaleString('pt-BR')}
                      {!msg.lida && msg.remetente_tipo === 'usuario' && (
                        <span className="ml-2 text-yellow-500">● Não lida</span>
                      )}
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
                    placeholder="Digite sua resposta..."
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

      {/* Modal de Confirmação de Exclusão */}
      {modalExclusaoOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-lg shadow-xl w-full max-w-md p-6">
            <div className="flex items-center gap-3 text-red-600 mb-4">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <h2 className="text-xl font-bold">Confirmar Exclusão</h2>
            </div>

            <p className="text-foreground mb-6">
              Tem certeza que deseja excluir este ticket permanentemente?
              <br />
              <span className="text-sm text-muted-foreground">Esta ação não pode ser desfeita.</span>
            </p>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setModalExclusaoOpen(false)}
                className="px-4 py-2 text-muted-foreground hover:text-foreground transition bg-muted/50 rounded-lg hover:bg-muted"
              >
                Cancelar
              </button>
              <button
                onClick={confirmarExclusao}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition font-medium"
              >
                Confirmar Exclusão
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

export default AdminSuporteDetalhes;
