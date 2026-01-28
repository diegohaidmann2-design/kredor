import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import { suporteAPI } from '../api/api';

const Suporte = () => {
  const navigate = useNavigate();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalAberto, setModalAberto] = useState(false);
  const [filtroStatus, setFiltroStatus] = useState('');

  const [novoTicket, setNovoTicket] = useState({
    assunto: '',
    categoria: 'tecnico',
    mensagem: '',
    prioridade: 'media'
  });

  useEffect(() => {
    carregarTickets();
  }, [filtroStatus]);

  const carregarTickets = async () => {
    try {
      const params = filtroStatus ? { status: filtroStatus } : {};
      const response = await suporteAPI.listarTickets(params);
      setTickets(response.data);
    } catch (error) {
      console.error('Erro ao carregar tickets:', error);
    } finally {
      setLoading(false);
    }
  };

  const criarTicket = async (e) => {
    e.preventDefault();
    try {
      await suporteAPI.criarTicket(novoTicket);
      setModalAberto(false);
      setNovoTicket({ assunto: '', categoria: 'tecnico', mensagem: '', prioridade: 'media' });
      carregarTickets();
    } catch (error) {
      console.error('Erro ao criar ticket:', error);
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

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-foreground">Meus Tickets de Suporte</h1>
              <p className="text-muted-foreground mt-1">
                Acompanhe suas solicitações de ajuda
              </p>
            </div>
            <button
              onClick={() => setModalAberto(true)}
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Novo Ticket
            </button>
          </div>

          {/* Filtros */}
          <div className="bg-card rounded-lg border border-border p-4">
            <label className="block text-sm font-medium text-foreground mb-2">Filtrar por Status</label>
            <select
              value={filtroStatus}
              onChange={(e) => setFiltroStatus(e.target.value)}
              className="px-3 py-2 bg-background border border-border rounded-md text-foreground"
            >
              <option value="">Todos</option>
              <option value="aberto">Aberto</option>
              <option value="em_atendimento">Em Atendimento</option>
              <option value="resolvido">Resolvido</option>
              <option value="fechado">Fechado</option>
            </select>
          </div>

          {/* Lista de Tickets */}
          <div className="space-y-4">
            {loading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
              </div>
            ) : !Array.isArray(tickets) || tickets.length === 0 ? (
              <div className="bg-card rounded-lg border border-border p-8 text-center">
                <p className="text-muted-foreground">Nenhum ticket encontrado</p>
              </div>
            ) : (
              tickets.map((ticket) => (
                <div
                  key={ticket.numero_ticket}
                  onClick={() => navigate(`/suporte/${ticket.numero_ticket}`)}
                  className="bg-card rounded-lg border border-border p-4 hover:shadow-md transition cursor-pointer"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="font-bold text-foreground">{ticket.numero_ticket}</h3>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${getStatusBadge(ticket.status)}`}>
                          {ticket.status.replace('_', ' ').toUpperCase()}
                        </span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${getPrioridadeBadge(ticket.prioridade)}`}>
                          {ticket.prioridade}
                        </span>
                        {ticket.mensagens_nao_lidas_usuario > 0 && (
                          <span className="px-2 py-0.5 bg-red-500 text-white rounded-full text-xs font-bold">
                            {ticket.mensagens_nao_lidas_usuario} nova{ticket.mensagens_nao_lidas_usuario > 1 ? 's' : ''}
                          </span>
                        )}
                      </div>
                      <p className="text-foreground font-medium mb-1">{ticket.assunto}</p>
                      <p className="text-sm text-muted-foreground">
                        Categoria: {ticket.categoria} • {ticket.total_mensagens} mensagens
                      </p>
                      {ticket.atribuido_nome && (
                        <p className="text-xs text-muted-foreground mt-1">
                          Atendente: {ticket.atribuido_nome}
                        </p>
                      )}
                    </div>
                    <div className="text-right text-sm text-muted-foreground">
                      {new Date(ticket.atualizado_em).toLocaleString('pt-BR')}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Modal Criar Ticket */}
        {modalAberto && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-card rounded-lg max-w-2xl w-full p-6">
              <h2 className="text-2xl font-bold text-foreground mb-4">Novo Ticket de Suporte</h2>

              <form onSubmit={criarTicket} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Assunto *</label>
                  <input
                    type="text"
                    value={novoTicket.assunto}
                    onChange={(e) => setNovoTicket({ ...novoTicket, assunto: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground"
                    required
                    minLength={5}
                    maxLength={200}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">Categoria *</label>
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
                    <label className="block text-sm font-medium text-foreground mb-2">Prioridade</label>
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
                  <label className="block text-sm font-medium text-foreground mb-2">Mensagem *</label>
                  <textarea
                    value={novoTicket.mensagem}
                    onChange={(e) => setNovoTicket({ ...novoTicket, mensagem: e.target.value })}
                    className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground h-32"
                    required
                    minLength={10}
                  />
                </div>

                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setModalAberto(false)}
                    className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
                  >
                    Criar Ticket
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default Suporte;