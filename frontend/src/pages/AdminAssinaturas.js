import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import Button from '../components/Button';
import { useModal } from '../components/Modal';
import { superadminAPI } from '../api/api';
import { formatarMoeda, formatarData } from '../utils/formatters';
import {
  CreditCard,
  Plus,
  Search,
  RefreshCw,
  Edit,
  XCircle,
  CheckCircle,
  Calendar,
  User,
  DollarSign,
  Clock,
  Filter,
  Eye,
  RotateCcw,
  X,
  History,
  Save,
  PlusCircle,
  MoreVertical,
  Trash2
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "../components/ui/dropdown-menu";

const AdminAssinaturas = () => {
  const [assinaturas, setAssinaturas] = useState([]);
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState('criar'); // criar, editar, visualizar, renovar, logs
  const [assinaturaSelecionada, setAssinaturaSelecionada] = useState(null);
  const [logsAssinatura, setLogsAssinatura] = useState([]);
  const [salvando, setSalvando] = useState(false);
  const modal = useModal();
  
  // Filtros
  const [filtros, setFiltros] = useState({
    status: '',
    plano: '',
    busca: ''
  });
  
  // Formulário
  const [formData, setFormData] = useState({
    usuario_id: '',
    plano: 'basico',
    dias_validade: 30,
    valor: '',
    observacoes: ''
  });

  // Formulário de edição
  const [editForm, setEditForm] = useState({
    plano: '',
    status: '',
    data_expiracao: '',
    dias_extras: '',
    valor: '',
    observacoes: ''
  });

  const [diasRenovacao, setDiasRenovacao] = useState(30);

  // Estado para pesquisa de usuários no modal
  const [buscaUsuario, setBuscaUsuario] = useState('');
  const [buscaUsuarioDebounced, setBuscaUsuarioDebounced] = useState('');
  const [usuarioSelecionadoIndex, setUsuarioSelecionadoIndex] = useState(-1);
  const searchInputRef = useRef(null);
  const listRef = useRef(null);

  // Debounce para pesquisa de usuários (300ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setBuscaUsuarioDebounced(buscaUsuario);
    }, 300);
    return () => clearTimeout(timer);
  }, [buscaUsuario]);

  // Filtrar usuários com base na pesquisa
  const usuariosFiltrados = useMemo(() => {
    if (!buscaUsuarioDebounced.trim()) {
      return usuarios;
    }
    const termoBusca = buscaUsuarioDebounced.toLowerCase().trim();
    return usuarios.filter(u => 
      u.nome?.toLowerCase().includes(termoBusca) ||
      u.email?.toLowerCase().includes(termoBusca)
    );
  }, [usuarios, buscaUsuarioDebounced]);

  // Reset do índice selecionado quando a lista muda
  useEffect(() => {
    setUsuarioSelecionadoIndex(-1);
  }, [usuariosFiltrados]);

  // Scroll para o item selecionado
  useEffect(() => {
    if (usuarioSelecionadoIndex >= 0 && listRef.current) {
      const items = listRef.current.querySelectorAll('[role="option"]');
      if (items[usuarioSelecionadoIndex]) {
        items[usuarioSelecionadoIndex].scrollIntoView({ block: 'nearest' });
      }
    }
  }, [usuarioSelecionadoIndex]);

  // Keyboard navigation para lista de usuários
  const handleKeyDown = (e) => {
    if (!usuariosFiltrados.length) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setUsuarioSelecionadoIndex(prev => 
          prev < usuariosFiltrados.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setUsuarioSelecionadoIndex(prev => prev > 0 ? prev - 1 : prev);
        break;
      case 'Enter':
        e.preventDefault();
        if (usuarioSelecionadoIndex >= 0 && usuariosFiltrados[usuarioSelecionadoIndex]) {
          handleSelecionarUsuario(usuariosFiltrados[usuarioSelecionadoIndex]);
        }
        break;
      case 'Escape':
        e.preventDefault();
        setBuscaUsuario('');
        searchInputRef.current?.blur();
        break;
      default:
        break;
    }
  };

  // Selecionar usuário
  const handleSelecionarUsuario = (usuario) => {
    setFormData(prev => ({ ...prev, usuario_id: usuario.id }));
    setBuscaUsuario('');
    setUsuarioSelecionadoIndex(-1);
  };

  // Limpar pesquisa
  const limparBuscaUsuario = () => {
    setBuscaUsuario('');
    setBuscaUsuarioDebounced('');
    setUsuarioSelecionadoIndex(-1);
    searchInputRef.current?.focus();
  };

  // Encontrar usuário selecionado
  const usuarioSelecionado = useMemo(() => {
    return usuarios.find(u => u.id === formData.usuario_id);
  }, [usuarios, formData.usuario_id]);

  const carregarDados = useCallback(async () => {
    try {
      setLoading(true);
      const params = {};
      if (filtros.status) params.status = filtros.status;
      if (filtros.plano) params.plano = filtros.plano;
      if (filtros.busca) params.busca = filtros.busca;
      
      const [assinaturasRes, usuariosRes] = await Promise.all([
        superadminAPI.listarAssinaturas(params),
        superadminAPI.listarUsuarios({ limit: 500 })
      ]);
      
      setAssinaturas(assinaturasRes.data.assinaturas);
      setTotal(assinaturasRes.data.total);
      setUsuarios(usuariosRes.data.usuarios);
    } catch (err) {
      console.error('Erro ao carregar dados:', err);
      modal.error('Erro', 'Não foi possível carregar as assinaturas.');
    } finally {
      setLoading(false);
    }
  }, [filtros]);

  useEffect(() => {
    carregarDados();
  }, [carregarDados]);

  const handleCriar = () => {
    setModalMode('criar');
    setFormData({
      usuario_id: '',
      plano: 'basico',
      dias_validade: 30,
      valor: '',
      observacoes: ''
    });
    setBuscaUsuario('');
    setBuscaUsuarioDebounced('');
    setUsuarioSelecionadoIndex(-1);
    setShowModal(true);
  };

  const handleVisualizar = async (assinatura) => {
    try {
      const response = await superadminAPI.obterAssinatura(assinatura.id);
      setModalMode('visualizar');
      setAssinaturaSelecionada(response.data);
      setShowModal(true);
    } catch (err) {
      modal.error('Erro', 'Não foi possível carregar os detalhes da assinatura.');
    }
  };

  // Função para abrir edição
  const handleEditar = async (assinatura) => {
    try {
      const response = await superadminAPI.obterAssinatura(assinatura.id);
      const dados = response.data;
      
      // Formatar data para input date
      let dataExpiracao = '';
      if (dados.data_expiracao || dados.data_fim) {
        const dataStr = dados.data_expiracao || dados.data_fim;
        const data = new Date(dataStr);
        dataExpiracao = data.toISOString().split('T')[0];
      }
      
      setEditForm({
        plano: dados.plano || '',
        status: dados.status || '',
        data_expiracao: dataExpiracao,
        dias_extras: '',
        valor: dados.valor || '',
        observacoes: dados.observacoes || ''
      });
      
      setAssinaturaSelecionada(dados);
      setModalMode('editar');
      setShowModal(true);
    } catch (err) {
      modal.error('Erro', 'Não foi possível carregar os dados da assinatura.');
    }
  };

  // Função para salvar edição
  const handleSalvarEdicao = async () => {
    try {
      setSalvando(true);
      
      const id = assinaturaSelecionada.id || assinaturaSelecionada.session_id;
      if (!id) {
        modal.error('Erro', 'ID da assinatura não encontrado.');
        return;
      }

      const dados = {};
      
      // Só enviar campos que foram alterados
      if (editForm.plano && editForm.plano !== assinaturaSelecionada.plano) {
        dados.plano = editForm.plano;
      }
      if (editForm.status && editForm.status !== assinaturaSelecionada.status) {
        dados.status = editForm.status;
      }
      if (editForm.data_expiracao) {
        // Converter para ISO string com timezone
        const novaData = new Date(editForm.data_expiracao + 'T23:59:59');
        dados.data_expiracao = novaData.toISOString();
      }
      if (editForm.dias_extras && parseInt(editForm.dias_extras) > 0) {
        dados.dias_extras = parseInt(editForm.dias_extras);
      }
      if (editForm.valor !== '' && parseFloat(editForm.valor) !== assinaturaSelecionada.valor) {
        dados.valor = parseFloat(editForm.valor);
      }
      if (editForm.observacoes !== assinaturaSelecionada.observacoes) {
        dados.observacoes = editForm.observacoes;
      }
      
      if (Object.keys(dados).length === 0) {
        modal.warning('Atenção', 'Nenhuma alteração foi feita.');
        return;
      }
      
      const response = await superadminAPI.atualizarAssinatura(id, dados);
      
      // Mostrar as alterações realizadas
      const alteracoes = response.data.alteracoes || [];
      let mensagem = 'A assinatura foi atualizada com sucesso.';
      if (alteracoes.length > 0) {
        mensagem = alteracoes.map(a => a.descricao).join('\n');
      }
      
      modal.success('Assinatura Atualizada!', mensagem);
      setShowModal(false);
      carregarDados();
    } catch (err) {
      modal.error('Erro', err.response?.data?.detail || 'Não foi possível atualizar a assinatura.');
    } finally {
      setSalvando(false);
    }
  };

  // Função para ver logs
  const handleVerLogs = async (assinatura) => {
    const id = assinatura.id || assinatura.session_id;
    if (!id) {
      modal.error('Erro', 'ID da assinatura não encontrado.');
      return;
    }
    try {
      const response = await superadminAPI.logsAssinatura(id);
      setLogsAssinatura(response.data.logs || []);
      setAssinaturaSelecionada(assinatura);
      setModalMode('logs');
      setShowModal(true);
    } catch (err) {
      modal.error('Erro', 'Não foi possível carregar o histórico de alterações.');
    }
  };

  const handleRenovar = (assinatura) => {
    const id = assinatura.id || assinatura.session_id;
    if (!id) {
      modal.error('Erro', 'ID da assinatura não encontrado.');
      return;
    }
    setModalMode('renovar');
    setAssinaturaSelecionada(assinatura);
    setDiasRenovacao(30);
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.usuario_id) {
      modal.warning('Atenção', 'Selecione um usuário para a assinatura.');
      return;
    }
    
    try {
      const data = {
        ...formData,
        valor: formData.valor ? parseFloat(formData.valor) : null
      };
      
      await superadminAPI.criarAssinatura(data);
      modal.success('Assinatura Criada!', 'A nova assinatura foi registrada com sucesso.');
      setShowModal(false);
      carregarDados();
    } catch (err) {
      modal.error('Erro', err.response?.data?.detail || 'Não foi possível criar a assinatura.');
    }
  };

  const handleConfirmarRenovacao = async () => {
    const id = assinaturaSelecionada?.id || assinaturaSelecionada?.session_id;
    if (!id) {
      modal.error('Erro', 'ID da assinatura não encontrado.');
      return;
    }
    try {
      await superadminAPI.renovarAssinatura(id, diasRenovacao);
      modal.success('Assinatura Renovada!', `A assinatura foi renovada por ${diasRenovacao} dias.`);
      setShowModal(false);
      carregarDados();
    } catch (err) {
      modal.error('Erro', 'Não foi possível renovar a assinatura.');
    }
  };

  const handleCancelar = (assinatura) => {
    const id = assinatura.id || assinatura.session_id;
    if (!id) {
      modal.error('Erro', 'ID da assinatura não encontrado.');
      return;
    }

    modal.confirm(
      'Cancelar Assinatura',
      `Tem certeza que deseja cancelar a assinatura de "${assinatura.usuario?.nome}"? O usuário será rebaixado para o plano Trial.`,
      async () => {
        try {
          await superadminAPI.cancelarAssinatura(id);
          modal.success('Assinatura Cancelada', 'A assinatura foi cancelada com sucesso.');
          carregarDados();
        } catch (err) {
          modal.error('Erro', 'Não foi possível cancelar a assinatura.');
        }
      }
    );
  };

  const handleDeletar = (assinatura) => {
    const id = assinatura.id || assinatura.session_id;
    if (!id) {
      modal.error('Erro', 'ID da assinatura não encontrado.');
      return;
    }

    modal.confirm(
      'Excluir Assinatura',
      `Tem certeza que deseja EXCLUIR permanentemente a assinatura de "${assinatura.usuario?.nome}"? Esta ação não pode ser desfeita.`,
      async () => {
        try {
          await superadminAPI.deletarAssinatura(id);
          modal.success('Assinatura Excluída', 'A assinatura foi removida permanentemente.');
          carregarDados();
        } catch (err) {
          modal.error('Erro', 'Não foi possível excluir a assinatura.');
        }
      }
    );
  };

  const getStatusColor = (status) => {
    const cores = {
      ativa: 'bg-emerald-500/20 text-emerald-400',
      cancelada: 'bg-red-500/20 text-red-400',
      expirada: 'bg-amber-500/20 text-amber-400',
      pendente: 'bg-blue-500/20 text-blue-400'
    };
    return cores[status] || cores.pendente;
  };

  const getPlanoColor = (plano) => {
    const cores = {
      trial: 'bg-slate-500/20 text-slate-400',
      basico: 'bg-blue-500/20 text-blue-400',
      profissional: 'bg-purple-500/20 text-purple-400',
      enterprise: 'bg-amber-500/20 text-amber-400'
    };
    return cores[plano] || cores.trial;
  };

  const precosPadrão = {
    trial: 0,
    basico: 49,
    profissional: 99,
    enterprise: 199
  };

  if (loading && assinaturas.length === 0) return <Loading message="Carregando assinaturas..." />;

  return (
    <Layout>
      <div className="p-4 sm:p-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
              <CreditCard className="w-7 h-7 text-amber-500" />
              Gestão de Assinaturas
            </h1>
            <p className="text-muted-foreground mt-1">
              {total} assinatura(s) no sistema
            </p>
          </div>
          <Button
            onClick={handleCriar}
            variant="primary"
            className="mt-4 sm:mt-0"
          >
            <Plus className="w-4 h-4 mr-2" />
            Nova Assinatura
          </Button>
        </div>

        {/* Cards de Resumo */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-card rounded-xl border border-border p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total</p>
                <p className="text-2xl font-bold text-foreground">{total}</p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                <CreditCard className="w-5 h-5 text-primary" />
              </div>
            </div>
          </div>
          <div className="bg-card rounded-xl border border-border p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Ativas</p>
                <p className="text-2xl font-bold text-emerald-500">
                  {assinaturas.filter(a => a.status === 'ativa').length}
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-emerald-500" />
              </div>
            </div>
          </div>
          <div className="bg-card rounded-xl border border-border p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Canceladas</p>
                <p className="text-2xl font-bold text-red-500">
                  {assinaturas.filter(a => a.status === 'cancelada').length}
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-red-500/20 flex items-center justify-center">
                <XCircle className="w-5 h-5 text-red-500" />
              </div>
            </div>
          </div>
          <div className="bg-card rounded-xl border border-border p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Receita Est.</p>
                <p className="text-2xl font-bold text-amber-500">
                  {formatarMoeda(assinaturas.filter(a => a.status === 'ativa').reduce((sum, a) => sum + (a.valor || 0), 0))}
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
                <DollarSign className="w-5 h-5 text-amber-500" />
              </div>
            </div>
          </div>
        </div>

        {/* Filtros */}
        <div className="bg-card rounded-xl border border-border p-4 mb-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="lg:col-span-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Buscar por usuário..."
                  value={filtros.busca}
                  onChange={(e) => setFiltros(prev => ({ ...prev, busca: e.target.value }))}
                  className="w-full pl-10 pr-4 py-2 bg-background border border-border rounded-lg text-foreground placeholder:text-muted-foreground"
                />
              </div>
            </div>
            <select
              value={filtros.status}
              onChange={(e) => setFiltros(prev => ({ ...prev, status: e.target.value }))}
              className="px-3 py-2 bg-background border border-border rounded-lg text-foreground"
            >
              <option value="">Todos os status</option>
              <option value="ativa">Ativas</option>
              <option value="cancelada">Canceladas</option>
              <option value="expirada">Expiradas</option>
            </select>
            <select
              value={filtros.plano}
              onChange={(e) => setFiltros(prev => ({ ...prev, plano: e.target.value }))}
              className="px-3 py-2 bg-background border border-border rounded-lg text-foreground"
            >
              <option value="">Todos os planos</option>
              <option value="basico">Básico</option>
              <option value="profissional">Profissional</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>
        </div>

        {/* Lista de Assinaturas */}
        <div className="bg-card rounded-xl border border-border overflow-hidden">
          {/* Versão Desktop - Tabela */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted/50 border-b border-border">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Usuário</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Plano</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Valor</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Validade</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {assinaturas.map((assinatura) => (
                  <motion.tr
                    key={assinatura.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="hover:bg-muted/50"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
                          <User className="w-5 h-5 text-primary" />
                        </div>
                        <div>
                          <p className="font-medium text-foreground">{assinatura.usuario?.nome || 'N/A'}</p>
                          <p className="text-sm text-muted-foreground">{assinatura.usuario?.email || '-'}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${getPlanoColor(assinatura.plano)}`}>
                        {assinatura.plano?.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(assinatura.status)}`}>
                        {assinatura.status?.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-foreground font-medium">
                      {formatarMoeda(assinatura.valor || 0)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">
                          {formatarData(assinatura.data_fim)}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <button className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition outline-none">
                              <MoreVertical className="w-5 h-5" />
                            </button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-48">
                            <DropdownMenuItem onClick={() => handleVisualizar(assinatura)}>
                              <Eye className="w-4 h-4 mr-2" />
                              Visualizar
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleEditar(assinatura)}>
                              <Edit className="w-4 h-4 mr-2" />
                              Editar
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleVerLogs(assinatura)}>
                              <History className="w-4 h-4 mr-2" />
                              Histórico
                            </DropdownMenuItem>
                            
                            <DropdownMenuSeparator />
                            
                            {assinatura.status === 'ativa' && (
                              <>
                                <DropdownMenuItem onClick={() => handleRenovar(assinatura)}>
                                  <RotateCcw className="w-4 h-4 mr-2 text-emerald-500" />
                                  Renovar
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => handleCancelar(assinatura)}>
                                  <XCircle className="w-4 h-4 mr-2 text-amber-500" />
                                  Cancelar
                                </DropdownMenuItem>
                              </>
                            )}
                            
                            {assinatura.status === 'cancelada' && (
                              <DropdownMenuItem onClick={() => handleRenovar(assinatura)}>
                                <RefreshCw className="w-4 h-4 mr-2 text-emerald-500" />
                                Reativar
                              </DropdownMenuItem>
                            )}

                            <DropdownMenuSeparator />
                            
                            <DropdownMenuItem 
                              onClick={() => handleDeletar(assinatura)}
                              className="text-red-500 focus:text-red-500"
                            >
                              <Trash2 className="w-4 h-4 mr-2" />
                              Excluir
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Versão Mobile - Cards */}
          <div className="md:hidden divide-y divide-border">
            {assinaturas.map((assinatura) => (
              <motion.div
                key={assinatura.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="p-4"
              >
                <div className="flex items-start gap-3 mb-3">
                  <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center">
                    <User className="w-6 h-6 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-foreground truncate">{assinatura.usuario?.nome || 'N/A'}</p>
                    <p className="text-sm text-muted-foreground truncate">{assinatura.usuario?.email || '-'}</p>
                    <div className="flex items-center gap-2 mt-1.5">
                      <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${getPlanoColor(assinatura.plano)}`}>
                        {assinatura.plano?.toUpperCase()}
                      </span>
                      <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${getStatusColor(assinatura.status)}`}>
                        {assinatura.status?.toUpperCase()}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="space-y-2 text-sm mb-3">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Valor:</span>
                    <span className="text-foreground font-semibold">{formatarMoeda(assinatura.valor || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Validade:</span>
                    <div className="flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-muted-foreground" />
                      <span className="text-foreground">{formatarData(assinatura.data_fim)}</span>
                    </div>
                  </div>
                </div>

                <div className="flex gap-2">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <button className="flex-1 inline-flex items-center justify-center gap-2 px-3 py-2 text-muted-foreground hover:text-foreground bg-muted hover:bg-muted/80 rounded-lg transition text-sm outline-none">
                        <MoreVertical className="w-4 h-4" />
                        Ações
                      </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-48">
                      <DropdownMenuItem onClick={() => handleVisualizar(assinatura)}>
                        <Eye className="w-4 h-4 mr-2" />
                        Visualizar
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleEditar(assinatura)}>
                        <Edit className="w-4 h-4 mr-2" />
                        Editar
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleVerLogs(assinatura)}>
                        <History className="w-4 h-4 mr-2" />
                        Histórico
                      </DropdownMenuItem>
                      
                      <DropdownMenuSeparator />
                      
                      {assinatura.status === 'ativa' && (
                        <>
                          <DropdownMenuItem onClick={() => handleRenovar(assinatura)}>
                            <RotateCcw className="w-4 h-4 mr-2 text-emerald-500" />
                            Renovar
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleCancelar(assinatura)}>
                            <XCircle className="w-4 h-4 mr-2 text-amber-500" />
                            Cancelar
                          </DropdownMenuItem>
                        </>
                      )}
                      
                      {assinatura.status === 'cancelada' && (
                        <DropdownMenuItem onClick={() => handleRenovar(assinatura)}>
                          <RefreshCw className="w-4 h-4 mr-2 text-emerald-500" />
                          Reativar
                        </DropdownMenuItem>
                      )}

                      <DropdownMenuSeparator />
                      
                      <DropdownMenuItem 
                        onClick={() => handleDeletar(assinatura)}
                        className="text-red-500 focus:text-red-500"
                      >
                        <Trash2 className="w-4 h-4 mr-2" />
                        Excluir
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </motion.div>
            ))}
          </div>
          
          {assinaturas.length === 0 && (
            <div className="p-8 text-center text-muted-foreground">
              <CreditCard className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Nenhuma assinatura encontrada</p>
            </div>
          )}
        </div>
      </div>

      {/* Modal */}
      <AnimatePresence>
        {showModal && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
              onClick={() => setShowModal(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="fixed inset-0 flex items-center justify-center z-50 p-4"
            >
              <div className="bg-card rounded-xl border border-border shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
                <div className="p-6 border-b border-border flex items-center justify-between">
                  <h2 className="text-xl font-bold text-foreground">
                    {modalMode === 'criar' && 'Nova Assinatura'}
                    {modalMode === 'visualizar' && 'Detalhes da Assinatura'}
                    {modalMode === 'renovar' && 'Renovar Assinatura'}
                    {modalMode === 'editar' && 'Editar Assinatura'}
                    {modalMode === 'logs' && 'Histórico de Alterações'}
                  </h2>
                  <button
                    onClick={() => setShowModal(false)}
                    className="p-1 text-muted-foreground hover:text-foreground transition"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {/* MODO EDITAR */}
                {modalMode === 'editar' && assinaturaSelecionada ? (
                  <div className="p-6 space-y-4">
                    <div className="flex items-center gap-4 pb-4 border-b border-border">
                      <div className="w-14 h-14 rounded-full bg-primary/20 flex items-center justify-center">
                        <User className="w-7 h-7 text-primary" />
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-foreground">
                          {assinaturaSelecionada.usuario?.nome}
                        </h3>
                        <p className="text-muted-foreground">
                          {assinaturaSelecionada.usuario?.email}
                        </p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1">
                          Plano
                        </label>
                        <select
                          value={editForm.plano}
                          onChange={(e) => setEditForm(prev => ({ ...prev, plano: e.target.value }))}
                          className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                        >
                          <option value="trial">Trial</option>
                          <option value="basico">Básico</option>
                          <option value="profissional">Profissional</option>
                          <option value="enterprise">Enterprise</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1">
                          Status
                        </label>
                        <select
                          value={editForm.status}
                          onChange={(e) => setEditForm(prev => ({ ...prev, status: e.target.value }))}
                          className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                        >
                          <option value="ativa">Ativa</option>
                          <option value="cancelada">Cancelada</option>
                          <option value="expirada">Expirada</option>
                        </select>
                      </div>
                    </div>

                    <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
                      <h4 className="font-semibold text-amber-500 mb-3 flex items-center gap-2">
                        <Calendar className="w-4 h-4" />
                        Data de Expiração
                      </h4>
                      <div className="space-y-3">
                        <div>
                          <label className="block text-sm font-medium text-foreground mb-1">
                            Nova Data de Vencimento
                          </label>
                          <input
                            type="date"
                            value={editForm.data_expiracao}
                            onChange={(e) => setEditForm(prev => ({ ...prev, data_expiracao: e.target.value, dias_extras: '' }))}
                            className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                          />
                          <p className="text-xs text-muted-foreground mt-1">
                            Data atual: {formatarData(assinaturaSelecionada.data_expiracao || assinaturaSelecionada.data_fim)}
                          </p>
                        </div>
                        
                        <div className="text-center text-muted-foreground text-sm">ou</div>
                        
                        <div>
                          <label className="block text-sm font-medium text-foreground mb-1 flex items-center gap-2">
                            <PlusCircle className="w-4 h-4 text-emerald-500" />
                            Adicionar Dias Extras
                          </label>
                          <div className="flex gap-2">
                            <input
                              type="number"
                              min="0"
                              placeholder="Quantidade de dias"
                              value={editForm.dias_extras}
                              onChange={(e) => setEditForm(prev => ({ ...prev, dias_extras: e.target.value, data_expiracao: '' }))}
                              className="flex-1 px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                            />
                            <div className="flex gap-1">
                              {[7, 30, 90].map(dias => (
                                <button
                                  key={dias}
                                  type="button"
                                  onClick={() => setEditForm(prev => ({ ...prev, dias_extras: dias.toString(), data_expiracao: '' }))}
                                  className={`px-3 py-2 rounded-lg text-sm transition ${
                                    editForm.dias_extras === dias.toString() 
                                      ? 'bg-emerald-500 text-white' 
                                      : 'bg-muted hover:bg-muted/80'
                                  }`}
                                >
                                  +{dias}
                                </button>
                              ))}
                            </div>
                          </div>
                          
                          {/* Prévia da nova data */}
                          {editForm.dias_extras && parseInt(editForm.dias_extras) > 0 && (
                            <div className="mt-2 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
                              <p className="text-sm text-emerald-400 flex items-center gap-2">
                                <Calendar className="w-4 h-4" />
                                <span>
                                  Nova data de expiração: <strong>
                                    {(() => {
                                      const dataAtualStr = assinaturaSelecionada?.data_expiracao || assinaturaSelecionada?.data_fim;
                                      let dataBase = dataAtualStr ? new Date(dataAtualStr) : new Date();
                                      // Se a data já passou, começar de hoje
                                      if (dataBase < new Date()) {
                                        dataBase = new Date();
                                      }
                                      const novaData = new Date(dataBase);
                                      novaData.setDate(novaData.getDate() + parseInt(editForm.dias_extras));
                                      return novaData.toLocaleDateString('pt-BR');
                                    })()}
                                  </strong>
                                </span>
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-foreground mb-1">
                        Valor (R$)
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={editForm.valor}
                        onChange={(e) => setEditForm(prev => ({ ...prev, valor: e.target.value }))}
                        className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-foreground mb-1">
                        Observações
                      </label>
                      <textarea
                        rows={3}
                        value={editForm.observacoes}
                        onChange={(e) => setEditForm(prev => ({ ...prev, observacoes: e.target.value }))}
                        className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground resize-none"
                        placeholder="Motivo da alteração, observações..."
                      />
                    </div>

                    <div className="flex gap-3 pt-4">
                      <Button
                        onClick={() => setShowModal(false)}
                        variant="secondary"
                        className="flex-1"
                        disabled={salvando}
                      >
                        Cancelar
                      </Button>
                      <Button
                        onClick={handleSalvarEdicao}
                        variant="primary"
                        className="flex-1"
                        disabled={salvando}
                      >
                        {salvando ? (
                          <>
                            <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                            Salvando...
                          </>
                        ) : (
                          <>
                            <Save className="w-4 h-4 mr-2" />
                            Salvar Alterações
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                ) : modalMode === 'logs' && assinaturaSelecionada ? (
                  /* MODO LOGS */
                  <div className="p-6 space-y-4">
                    <div className="flex items-center gap-4 pb-4 border-b border-border">
                      <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                        <History className="w-5 h-5 text-blue-500" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-foreground">
                          {assinaturaSelecionada.usuario?.nome}
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          Histórico de alterações da assinatura
                        </p>
                      </div>
                    </div>

                    {logsAssinatura.length === 0 ? (
                      <div className="text-center py-8 text-muted-foreground">
                        <History className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>Nenhuma alteração registrada</p>
                      </div>
                    ) : (
                      <div className="space-y-3 max-h-96 overflow-y-auto">
                        {logsAssinatura.map((log) => (
                          <div key={log.id} className="bg-muted/50 rounded-lg p-4">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs text-muted-foreground">
                                {formatarData(log.data_alteracao, true)}
                              </span>
                              <span className="text-xs bg-blue-500/20 text-blue-500 px-2 py-0.5 rounded-full">
                                Por: {log.admin_nome || log.admin_email}
                              </span>
                            </div>
                            <div className="space-y-1">
                              {log.alteracoes?.map((alt, idx) => (
                                <div key={idx} className="text-sm">
                                  <span className="text-foreground">{alt.descricao}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="flex gap-3 pt-4">
                      <Button
                        onClick={() => setShowModal(false)}
                        variant="secondary"
                        className="flex-1"
                      >
                        Fechar
                      </Button>
                      <Button
                        onClick={() => handleEditar(assinaturaSelecionada)}
                        variant="primary"
                        className="flex-1"
                      >
                        <Edit className="w-4 h-4 mr-2" />
                        Editar Assinatura
                      </Button>
                    </div>
                  </div>
                ) : modalMode === 'visualizar' && assinaturaSelecionada ? (
                  <div className="p-6 space-y-4">
                    <div className="flex items-center gap-4 pb-4 border-b border-border">
                      <div className="w-14 h-14 rounded-full bg-primary/20 flex items-center justify-center">
                        <User className="w-7 h-7 text-primary" />
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-foreground">
                          {assinaturaSelecionada.usuario?.nome}
                        </h3>
                        <p className="text-muted-foreground">
                          {assinaturaSelecionada.usuario?.email}
                        </p>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-muted-foreground uppercase">Plano</p>
                        <p className="font-medium text-foreground">{assinaturaSelecionada.plano?.toUpperCase()}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground uppercase">Status</p>
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(assinaturaSelecionada.status)}`}>
                          {assinaturaSelecionada.status?.toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground uppercase">Valor</p>
                        <p className="font-medium text-foreground">{formatarMoeda(assinaturaSelecionada.valor || 0)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground uppercase">Dias de Validade</p>
                        <p className="font-medium text-foreground">{assinaturaSelecionada.dias_validade} dias</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground uppercase">Início</p>
                        <p className="font-medium text-foreground">{formatarData(assinaturaSelecionada.data_inicio)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground uppercase">Fim</p>
                        <p className="font-medium text-foreground">{formatarData(assinaturaSelecionada.data_fim)}</p>
                      </div>
                    </div>

                    {assinaturaSelecionada.observacoes && (
                      <div className="pt-4 border-t border-border">
                        <p className="text-xs text-muted-foreground uppercase mb-1">Observações</p>
                        <p className="text-foreground">{assinaturaSelecionada.observacoes}</p>
                      </div>
                    )}

                    {assinaturaSelecionada.criado_por && (
                      <div className="pt-4 border-t border-border text-sm text-muted-foreground">
                        Criado por: {assinaturaSelecionada.criado_por}
                      </div>
                    )}

                    <div className="flex gap-3 pt-4 border-t border-border">
                      <Button
                        onClick={() => setShowModal(false)}
                        variant="secondary"
                        className="flex-1"
                      >
                        Fechar
                      </Button>
                      <Button
                        onClick={() => handleEditar(assinaturaSelecionada)}
                        variant="primary"
                        className="flex-1"
                      >
                        <Edit className="w-4 h-4 mr-2" />
                        Editar
                      </Button>
                    </div>
                  </div>
                ) : modalMode === 'renovar' ? (
                  <div className="p-6 space-y-4">
                    <p className="text-muted-foreground">
                      Renovar assinatura de <strong>{assinaturaSelecionada?.usuario?.nome}</strong>
                    </p>
                    <div>
                      <label className="block text-sm font-medium text-foreground mb-1">
                        Dias de Renovação
                      </label>
                      <select
                        value={diasRenovacao}
                        onChange={(e) => setDiasRenovacao(parseInt(e.target.value))}
                        className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                      >
                        <option value={7}>7 dias</option>
                        <option value={15}>15 dias</option>
                        <option value={30}>30 dias (1 mês)</option>
                        <option value={60}>60 dias (2 meses)</option>
                        <option value={90}>90 dias (3 meses)</option>
                        <option value={180}>180 dias (6 meses)</option>
                        <option value={365}>365 dias (1 ano)</option>
                      </select>
                    </div>
                    <div className="flex gap-3 pt-4">
                      <Button
                        onClick={() => setShowModal(false)}
                        variant="secondary"
                        className="flex-1"
                      >
                        Cancelar
                      </Button>
                      <Button
                        onClick={handleConfirmarRenovacao}
                        variant="primary"
                        className="flex-1"
                      >
                        Confirmar Renovação
                      </Button>
                    </div>
                  </div>
                ) : (
                  <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    <div>
                      <label 
                        id="usuario-label" 
                        className="block text-sm font-medium text-foreground mb-1"
                      >
                        Usuário *
                      </label>
                      
                      {/* Usuário selecionado */}
                      {usuarioSelecionado && (
                        <div 
                          className="flex items-center justify-between p-3 mb-2 bg-primary/10 border border-primary/30 rounded-lg"
                          data-testid="usuario-selecionado"
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                              <User className="w-4 h-4 text-primary" />
                            </div>
                            <div>
                              <p className="text-sm font-medium text-foreground">{usuarioSelecionado.nome}</p>
                              <p className="text-xs text-muted-foreground">{usuarioSelecionado.email}</p>
                            </div>
                          </div>
                          <button
                            type="button"
                            onClick={() => setFormData(prev => ({ ...prev, usuario_id: '' }))}
                            className="p-1 text-muted-foreground hover:text-foreground transition"
                            aria-label="Remover usuário selecionado"
                            data-testid="remover-usuario-btn"
                          >
                            <XCircle className="w-5 h-5" />
                          </button>
                        </div>
                      )}
                      
                      {/* Campo de pesquisa */}
                      <div className="relative">
                        <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
                          <Search className="w-4 h-4 text-muted-foreground" aria-hidden="true" />
                        </div>
                        <input
                          ref={searchInputRef}
                          type="text"
                          value={buscaUsuario}
                          onChange={(e) => setBuscaUsuario(e.target.value)}
                          onKeyDown={handleKeyDown}
                          placeholder="Pesquisar usuário..."
                          className="w-full pl-10 pr-10 py-2.5 bg-background border border-border rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition"
                          aria-labelledby="usuario-label"
                          aria-describedby="usuario-hint"
                          aria-expanded={buscaUsuario.length > 0 || !formData.usuario_id}
                          aria-controls="usuarios-listbox"
                          aria-activedescendant={usuarioSelecionadoIndex >= 0 ? `usuario-option-${usuarioSelecionadoIndex}` : undefined}
                          role="combobox"
                          aria-autocomplete="list"
                          data-testid="pesquisa-usuario-input"
                        />
                        {buscaUsuario && (
                          <button
                            type="button"
                            onClick={limparBuscaUsuario}
                            className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground transition rounded"
                            aria-label="Limpar pesquisa"
                            data-testid="limpar-pesquisa-btn"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                      <p id="usuario-hint" className="sr-only">
                        Digite para pesquisar usuários. Use as setas para navegar e Enter para selecionar.
                      </p>
                      
                      {/* Lista de usuários rolável */}
                      <div 
                        ref={listRef}
                        id="usuarios-listbox"
                        role="listbox"
                        aria-labelledby="usuario-label"
                        className="mt-2 max-h-48 overflow-y-auto border border-border rounded-lg bg-background"
                        data-testid="usuarios-lista"
                      >
                        {usuariosFiltrados.length === 0 ? (
                          <div 
                            className="p-4 text-center text-muted-foreground"
                            data-testid="nenhum-resultado"
                          >
                            <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
                            <p className="text-sm">Nenhum resultado encontrado</p>
                            {buscaUsuarioDebounced && (
                              <p className="text-xs mt-1">
                                Tente buscar por outro nome ou e-mail
                              </p>
                            )}
                          </div>
                        ) : (
                          usuariosFiltrados.map((u, index) => (
                            <div
                              key={u.id}
                              id={`usuario-option-${index}`}
                              role="option"
                              aria-selected={formData.usuario_id === u.id}
                              tabIndex={-1}
                              onClick={() => handleSelecionarUsuario(u)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                  e.preventDefault();
                                  handleSelecionarUsuario(u);
                                }
                              }}
                              className={`
                                flex items-center gap-3 p-3 cursor-pointer transition-colors
                                ${formData.usuario_id === u.id 
                                  ? 'bg-primary/20 border-l-2 border-primary' 
                                  : 'hover:bg-muted/50 border-l-2 border-transparent'
                                }
                                ${index === usuarioSelecionadoIndex ? 'bg-muted' : ''}
                                ${index !== usuariosFiltrados.length - 1 ? 'border-b border-border' : ''}
                              `}
                              data-testid={`usuario-item-${u.id}`}
                            >
                              <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                                <User className="w-4 h-4 text-primary" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-foreground truncate">
                                  {u.nome}
                                </p>
                                <p className="text-xs text-muted-foreground truncate">
                                  {u.email}
                                </p>
                              </div>
                              <span className={`px-2 py-0.5 text-xs font-medium rounded-full flex-shrink-0 ${getPlanoColor(u.plano)}`}>
                                {u.plano?.toUpperCase()}
                              </span>
                              {formData.usuario_id === u.id && (
                                <CheckCircle className="w-4 h-4 text-primary flex-shrink-0" />
                              )}
                            </div>
                          ))
                        )}
                      </div>
                      
                      {/* Contador de resultados */}
                      {buscaUsuarioDebounced && usuariosFiltrados.length > 0 && (
                        <p className="mt-1 text-xs text-muted-foreground" aria-live="polite">
                          {usuariosFiltrados.length} usuário(s) encontrado(s)
                        </p>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1">Plano</label>
                        <select
                          value={formData.plano}
                          onChange={(e) => {
                            const plano = e.target.value;
                            setFormData(prev => ({ 
                              ...prev, 
                              plano,
                              valor: precosPadrão[plano] || ''
                            }));
                          }}
                          className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                        >
                          <option value="basico">Básico - R$ 49/mês</option>
                          <option value="profissional">Profissional - R$ 99/mês</option>
                          <option value="enterprise">Enterprise - R$ 199/mês</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1">Validade</label>
                        <select
                          value={formData.dias_validade}
                          onChange={(e) => setFormData(prev => ({ ...prev, dias_validade: parseInt(e.target.value) }))}
                          className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                        >
                          <option value={7}>7 dias</option>
                          <option value={15}>15 dias</option>
                          <option value={30}>30 dias</option>
                          <option value={60}>60 dias</option>
                          <option value={90}>90 dias</option>
                          <option value={180}>180 dias</option>
                          <option value={365}>365 dias</option>
                        </select>
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-foreground mb-1">
                        Valor (deixe em branco para usar o padrão)
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        value={formData.valor}
                        onChange={(e) => setFormData(prev => ({ ...prev, valor: e.target.value }))}
                        placeholder={`Padrão: R$ ${precosPadrão[formData.plano]}`}
                        className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-foreground mb-1">Observações</label>
                      <textarea
                        value={formData.observacoes}
                        onChange={(e) => setFormData(prev => ({ ...prev, observacoes: e.target.value }))}
                        placeholder="Observações internas..."
                        className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground h-20 resize-none"
                      />
                    </div>
                    <div className="flex gap-3 pt-4">
                      <Button
                        type="button"
                        onClick={() => setShowModal(false)}
                        variant="secondary"
                        className="flex-1"
                      >
                        Cancelar
                      </Button>
                      <Button type="submit" variant="primary" className="flex-1">
                        Criar Assinatura
                      </Button>
                    </div>
                  </form>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </Layout>
  );
};

export default AdminAssinaturas;
