import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminSuporteAPI, superadminAPI } from '../api/api';
import Layout from '../components/Layout';
import { toast } from '../hooks/use-toast';

// Adicionar estilo inline para animação
const styles = `
  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(-10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  .animate-fade-in {
    animation: fadeIn 0.3s ease-in-out;
  }
`;

const AdminSuporte = () => {
  const navigate = useNavigate();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [atualizando, setAtualizando] = useState(false);
  const [mensagemSucesso, setMensagemSucesso] = useState('');
  const [estatisticas, setEstatisticas] = useState({});

  const [filtros, setFiltros] = useState({
    status: '',
    categoria: '',
    prioridade: ''
  });

  // Estado para Modal de Criação
  const [modalAberto, setModalAberto] = useState(false);
  const [usuarios, setUsuarios] = useState([]);
  const [buscandoUsuarios, setBuscandoUsuarios] = useState(false);
  const [novoTicket, setNovoTicket] = useState({
    usuario_id: '',
    assunto: '',
    categoria: 'emprestimo',
    prioridade: 'media',
    mensagem: ''
  });
  const [criandoTicket, setCriandoTicket] = useState(false);
  const [termoBuscaUsuario, setTermoBuscaUsuario] = useState('');

  // Estado para Modal de Exclusão
  const [modalExclusaoOpen, setModalExclusaoOpen] = useState(false);
  const [ticketExclusaoId, setTicketExclusaoId] = useState(null);

  useEffect(() => {
    carregarDados();
    // Auto-reload a cada 15 segundos
    const interval = setInterval(carregarDados, 15000);
    return () => clearInterval(interval);
  }, [filtros]);

  // Buscar usuários para selecionar
  useEffect(() => {
    if (modalAberto && usuarios.length === 0) {
      buscarUsuarios();
    }
  }, [modalAberto]);

  const buscarUsuarios = async () => {
    setBuscandoUsuarios(true);
    try {
      // Buscar todos os usuários (limitado pelo backend, idealmente paginado ou search on type)
      // Usando listarUsuarios do painel administrativo como base, mas filtrando se necessário
      const response = await superadminAPI.listarUsuarios({ limit: 100 });
      setUsuarios(response.data.usuarios || []);
    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível buscar usuários.", variant: 'destructive' });
      console.error('Erro ao buscar usuários:', error);
    } finally {
      setBuscandoUsuarios(false);
    }
  };

  const handleCriarTicket = async (e) => {
    e.preventDefault();
    if (!novoTicket.usuario_id || !novoTicket.assunto || !novoTicket.mensagem) {
      alert('Preencha todos os campos obrigatórios');
      return;
    }

    setCriandoTicket(true);
    try {
      await adminSuporteAPI.criarTicket(novoTicket);
      setMensagemSucesso('Ticket criado com sucesso!');
      setModalAberto(false);
      setNovoTicket({
        usuario_id: '',
        assunto: '',
        categoria: 'emprestimo',
        prioridade: 'media',
        mensagem: ''
      });
      carregarDados(true);
    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível criar ticket.", variant: 'destructive' });
      console.error('Erro ao criar ticket:', error);
    } finally {
      setCriandoTicket(false);
    }
  };

  const usuariosFiltrados = usuarios.filter(u =>
    u.nome.toLowerCase().includes(termoBuscaUsuario.toLowerCase()) ||
    u.email.toLowerCase().includes(termoBuscaUsuario.toLowerCase())
  );

  const carregarDados = async (mostrarMensagem = false) => {
    if (mostrarMensagem) {
      setAtualizando(true);
    }

    try {
      const [ticketsRes, statsRes] = await Promise.all([
        adminSuporteAPI.listarTickets(filtros),
        adminSuporteAPI.obterEstatisticas()
      ]);

      setTickets(ticketsRes.data);
      setEstatisticas(statsRes.data);

      if (mostrarMensagem) {
        setMensagemSucesso('Dados atualizados com sucesso!');
        setTimeout(() => setMensagemSucesso(''), 3000);
      }
    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível carregar dados.", variant: 'destructive' });
      console.error('Erro ao carregar dados:', error);
    } finally {
      setLoading(false);
      setAtualizando(false);
    }
  };

  const handleAtualizar = () => {
    carregarDados(true);
  };

  const handleDeletarTicket = (numero_ticket) => {
    setTicketExclusaoId(numero_ticket);
    setModalExclusaoOpen(true);
  };

  const confirmarExclusao = async () => {
    if (!ticketExclusaoId) return;

    try {
      await adminSuporteAPI.deletarTicket(ticketExclusaoId);
      setMensagemSucesso('Ticket excluído com sucesso!');
      setTimeout(() => setMensagemSucesso(''), 3000);
      carregarDados();
    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível excluir ticket.", variant: 'destructive' });
      console.error('Erro ao excluir ticket:', error);
    } finally {
      setModalExclusaoOpen(false);
      setTicketExclusaoId(null);
    }
  };

  const getStatusBadge = (status) => {
    const cores = {
      aberto: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      em_atendimento: 'bg-blue-100 text-blue-800 border-blue-200',
      resolvido: 'bg-green-100 text-green-800 border-green-200',
      fechado: 'bg-gray-100 text-gray-800 border-gray-200'
    };
    return cores[status] || cores.aberto;
  };

  const getPrioridadeBadge = (prioridade) => {
    const cores = {
      baixa: 'bg-slate-100 text-slate-600',
      media: 'bg-yellow-100 text-yellow-700',
      alta: 'bg-orange-100 text-orange-700',
      urgente: 'bg-red-100 text-red-700'
    };
    return cores[prioridade] || cores.media;
  };

  const limparFiltros = () => {
    setFiltros({ status: '', categoria: '', prioridade: '' });
  };

  return (
    <Layout>
      <style>{styles}</style>
      <div className="container mx-auto px-4 py-8">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="font-cabinet font-black text-3xl sm:text-4xl tracking-tighter text-foreground">Suporte - Painel Admin</h1>
              <p className="text-muted-foreground mt-1">
                Gerencie todos os tickets de suporte
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setModalAberto(true)}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition flex items-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Novo Ticket
              </button>
              <button
                onClick={handleAtualizar}
                disabled={atualizando}
                className={`px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition flex items-center gap-2 ${atualizando ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
              >
                <svg className={`w-5 h-5 ${atualizando ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                {atualizando ? 'Atualizando...' : 'Atualizar'}
              </button>
            </div>
          </div>

          {/* Mensagem de Sucesso */}
          {mensagemSucesso && (
            <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg flex items-center gap-2 animate-fade-in">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {mensagemSucesso}
            </div>
          )}

          {/* Estatísticas */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-card rounded-lg border border-border p-6">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-purple-100 rounded-lg">
                  <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total de Tickets</p>
                  <p className="text-3xl font-bold text-foreground">{estatisticas.total || 0}</p>
                </div>
              </div>
            </div>

            <div className="bg-card rounded-lg border border-border p-6">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-yellow-100 rounded-lg">
                  <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Abertos</p>
                  <p className="text-3xl font-bold text-yellow-600">{estatisticas.abertos || 0}</p>
                </div>
              </div>
            </div>

            <div className="bg-card rounded-lg border border-border p-6">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-100 rounded-lg">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Em Atendimento</p>
                  <p className="text-3xl font-bold text-blue-600">{estatisticas.em_atendimento || 0}</p>
                </div>
              </div>
            </div>

            <div className="bg-card rounded-lg border border-border p-6">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-green-100 rounded-lg">
                  <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Resolvidos</p>
                  <p className="text-3xl font-bold text-green-600">{estatisticas.resolvidos || 0}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Filtros */}
          <div className="bg-card rounded-lg border border-border p-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Status</label>
                <select
                  value={filtros.status}
                  onChange={(e) => setFiltros({ ...filtros, status: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground"
                >
                  <option value="">Todos</option>
                  <option value="aberto">Aberto</option>
                  <option value="em_atendimento">Em Atendimento</option>
                  <option value="resolvido">Resolvido</option>
                  <option value="fechado">Fechado</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Categoria</label>
                <select
                  value={filtros.categoria}
                  onChange={(e) => setFiltros({ ...filtros, categoria: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground"
                >
                  <option value="">Todas</option>
                  <option value="emprestimo">Empréstimo</option>
                  <option value="pagamento">Pagamento</option>
                  <option value="tecnico">Técnico</option>
                  <option value="outro">Outro</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Prioridade</label>
                <select
                  value={filtros.prioridade}
                  onChange={(e) => setFiltros({ ...filtros, prioridade: e.target.value })}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground"
                >
                  <option value="">Todas</option>
                  <option value="baixa">Baixa</option>
                  <option value="media">Média</option>
                  <option value="alta">Alta</option>
                  <option value="urgente">Urgente</option>
                </select>
              </div>

              <div className="flex items-end">
                <button
                  onClick={limparFiltros}
                  className="w-full px-4 py-2 bg-muted hover:bg-muted/80 text-foreground rounded-md transition"
                >
                  Limpar Filtros
                </button>
              </div>
            </div>
          </div>

          {/* Lista de Tickets */}
          <div className="bg-card rounded-lg border border-border overflow-hidden">
            {loading ? (
              <div className="p-8 text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
                <p className="text-muted-foreground mt-2">Carregando tickets...</p>
              </div>
            ) : !Array.isArray(tickets) || tickets.length === 0 ? (
              <div className="p-8 text-center">
                <p className="text-muted-foreground">Nenhum ticket encontrado</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-border">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Ticket</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Usuário</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Assunto</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Categoria</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Prioridade</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Msgs</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Atualizado</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {tickets.map((ticket) => (
                      <tr key={ticket.numero_ticket} className="hover:bg-muted/50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-foreground">{ticket.numero_ticket}</span>
                            {ticket.mensagens_nao_lidas_admin > 0 && (
                              <span className="px-2 py-0.5 bg-red-500 text-white rounded-full text-xs font-bold">
                                {ticket.mensagens_nao_lidas_admin}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div>
                            <p className="font-medium text-foreground">{ticket.usuario_nome}</p>
                            <p className="text-xs text-muted-foreground">{ticket.usuario_email}</p>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <p className="text-sm text-foreground max-w-xs truncate">{ticket.assunto}</p>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-sm text-foreground capitalize">{ticket.categoria}</span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 rounded-full text-xs font-semibold border ${getStatusBadge(ticket.status)}`}>
                            {ticket.status.replace('_', ' ').toUpperCase()}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getPrioridadeBadge(ticket.prioridade)}`}>
                            {ticket.prioridade}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-sm text-foreground">{ticket.total_mensagens}</span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-xs text-muted-foreground">
                            {new Date(ticket.atualizado_em).toLocaleString('pt-BR', {
                              day: '2-digit',
                              month: '2-digit',
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <button
                            onClick={() => navigate(`/admin/suporte/${ticket.numero_ticket}`)}
                            className="text-purple-600 hover:text-purple-700 font-medium text-sm"
                          >
                            Abrir
                          </button>
                          <button
                            onClick={() => handleDeletarTicket(ticket.numero_ticket)}
                            className="text-red-500 hover:text-red-700 font-medium text-sm ml-3"
                            title="Excluir Permanentemente"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Modal Criar Ticket */}
        {modalAberto && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-card border border-border rounded-lg shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
              <h2 className="text-xl font-bold text-foreground mb-4">Novo Ticket (Admin)</h2>

              <form onSubmit={handleCriarTicket} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Usuário *</label>
                  <input
                    type="text"
                    placeholder="Buscar por nome ou email..."
                    value={termoBuscaUsuario}
                    onChange={(e) => setTermoBuscaUsuario(e.target.value)}
                    className="w-full px-3 py-2 bg-background border border-border rounded-md mb-2 text-foreground"
                  />
                  <select
                    value={novoTicket.usuario_id}
                    onChange={(e) => setNovoTicket({ ...novoTicket, usuario_id: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground"
                    required
                  >
                    <option value="">Selecione um usuário...</option>
                    {usuariosFiltrados.map(usuario => (
                      <option key={usuario.id} value={usuario.id}>
                        {usuario.nome} ({usuario.email})
                      </option>
                    ))}
                  </select>
                  {usuariosFiltrados.length === 0 && termoBuscaUsuario && (
                    <p className="text-xs text-muted-foreground mt-1">Nenhum usuário encontrado.</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Assunto *</label>
                  <input
                    type="text"
                    value={novoTicket.assunto}
                    onChange={(e) => setNovoTicket({ ...novoTicket, assunto: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground"
                    required
                    minLength={5}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">Categoria</label>
                    <select
                      value={novoTicket.categoria}
                      onChange={(e) => setNovoTicket({ ...novoTicket, categoria: e.target.value })}
                      className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground"
                    >
                      <option value="emprestimo">Empréstimo</option>
                      <option value="pagamento">Pagamento</option>
                      <option value="tecnico">Técnico</option>
                      <option value="outro">Outro</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1">Prioridade</label>
                    <select
                      value={novoTicket.prioridade}
                      onChange={(e) => setNovoTicket({ ...novoTicket, prioridade: e.target.value })}
                      className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground"
                    >
                      <option value="baixa">Baixa</option>
                      <option value="media">Média</option>
                      <option value="alta">Alta</option>
                      <option value="urgente">Urgente</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">Mensagem Inicial *</label>
                  <textarea
                    value={novoTicket.mensagem}
                    onChange={(e) => setNovoTicket({ ...novoTicket, mensagem: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground h-32 resize-none"
                    required
                    minLength={10}
                  />
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t border-border">
                  <button
                    type="button"
                    onClick={() => setModalAberto(false)}
                    className="px-4 py-2 text-muted-foreground hover:text-foreground transition"
                    disabled={criandoTicket}
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={criandoTicket}
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition flex items-center gap-2"
                  >
                    {criandoTicket ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                        Criando...
                      </>
                    ) : (
                      'Criar Ticket'
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

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
                Tem certeza que deseja excluir o ticket <strong>{ticketExclusaoId}</strong> permanentemente?
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
      </div>
    </Layout>
  );
};

export default AdminSuporte;
