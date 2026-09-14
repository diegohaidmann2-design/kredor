import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import Button from '../components/Button';
import { useModal } from '../components/Modal';
import { superadminAPI } from '../api/api';
import { formatarData } from '../utils/formatters';
import {
  Users,
  UserPlus,
  Search,
  Filter,
  Edit,
  Trash2,
  Shield,
  Mail,
  Key,
  Check,
  X,
  RefreshCw,
  Crown,
  User,
  MoreVertical,
  Eye,
  Ban,
  CheckCircle,
  Clock
} from 'lucide-react';
import { toast } from '../hooks/use-toast';

const AdminUsuarios = () => {
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState('criar'); // criar, editar, visualizar
  const [usuarioSelecionado, setUsuarioSelecionado] = useState(null);
  const [showResetSenha, setShowResetSenha] = useState(false);
  const [novaSenha, setNovaSenha] = useState('');
  const modal = useModal();
  
  // Filtros
  const [filtros, setFiltros] = useState({
    perfil: '',
    plano: '',
    ativo: '',
    busca: ''
  });
  
  // Formulário
  const [formData, setFormData] = useState({
    nome: '',
    email: '',
    senha: '',
    perfil: 'usuario',
    plano: 'trial',
    ativo: true
  });

  const carregarUsuarios = useCallback(async () => {
    try {
      setLoading(true);
      const params = {};
      if (filtros.perfil) params.perfil = filtros.perfil;
      if (filtros.plano) params.plano = filtros.plano;
      if (filtros.ativo !== '') params.ativo = filtros.ativo === 'true';
      if (filtros.busca) params.busca = filtros.busca;
      
      const response = await superadminAPI.listarUsuarios(params);
      setUsuarios(response.data.usuarios);
      setTotal(response.data.total);
    } catch (err) {
      toast({ title: 'Erro', description: "Não foi possível carregar usuários.", variant: 'destructive' });
      console.error('Erro ao carregar usuários:', err);
    } finally {
      setLoading(false);
    }
  }, [filtros]);

  useEffect(() => {
    carregarUsuarios();
  }, [carregarUsuarios]);

  const handleCriar = () => {
    setModalMode('criar');
    setFormData({
      nome: '',
      email: '',
      senha: '',
      perfil: 'usuario',
      plano: 'trial',
      ativo: true
    });
    setShowModal(true);
  };

  const handleEditar = (usuario) => {
    setModalMode('editar');
    setUsuarioSelecionado(usuario);
    setFormData({
      nome: usuario.nome,
      email: usuario.email,
      senha: '',
      perfil: usuario.perfil,
      plano: usuario.plano,
      ativo: usuario.ativo
    });
    setShowModal(true);
  };

  const handleVisualizar = async (usuario) => {
    try {
      const response = await superadminAPI.obterUsuario(usuario.id);
      setModalMode('visualizar');
      setUsuarioSelecionado(response.data);
      setShowModal(true);
    } catch (err) {
      modal.error('Erro', 'Não foi possível carregar os detalhes do usuário.');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      if (modalMode === 'criar') {
        await superadminAPI.criarUsuario(formData);
        modal.success('Usuário Criado!', 'O novo usuário foi criado com sucesso.');
      } else {
        const updateData = { ...formData };
        if (!updateData.senha) delete updateData.senha;
        await superadminAPI.atualizarUsuario(usuarioSelecionado.id, updateData);
        modal.success('Usuário Atualizado!', 'Os dados do usuário foram atualizados.');
      }
      setShowModal(false);
      carregarUsuarios();
    } catch (err) {
      modal.error('Erro', err.response?.data?.detail || 'Não foi possível salvar o usuário.');
    }
  };

  const handleDeletar = (usuario) => {
    modal.confirm(
      'Excluir Usuário',
      `Tem certeza que deseja desativar o usuário "${usuario.nome}"? Os dados serão mantidos mas o acesso será bloqueado.`,
      async () => {
        try {
          await superadminAPI.deletarUsuario(usuario.id, false);
          modal.success('Usuário Desativado', 'O usuário foi desativado com sucesso.');
          carregarUsuarios();
        } catch (err) {
          modal.error('Erro', err.response?.data?.detail || 'Não foi possível desativar o usuário.');
        }
      }
    );
  };

  const handleDeletarPermanente = (usuario) => {
    modal.confirm(
      '⚠️ Excluir Permanentemente',
      `ATENÇÃO: Esta ação é IRREVERSÍVEL! Todos os dados do usuário "${usuario.nome}" serão deletados permanentemente, incluindo clientes, empréstimos e pagamentos.`,
      async () => {
        try {
          await superadminAPI.deletarUsuario(usuario.id, true);
          modal.success('Usuário Deletado', 'O usuário e todos os dados foram removidos permanentemente.');
          carregarUsuarios();
        } catch (err) {
          modal.error('Erro', err.response?.data?.detail || 'Não foi possível deletar o usuário.');
        }
      }
    );
  };

  const handleAtivar = async (usuario) => {
    try {
      await superadminAPI.ativarUsuario(usuario.id);
      modal.success('Usuário Ativado', 'O usuário foi reativado com sucesso.');
      carregarUsuarios();
    } catch (err) {
      modal.error('Erro', 'Não foi possível ativar o usuário.');
    }
  };

  const handleResetarSenha = async () => {
    if (!novaSenha || novaSenha.length < 8) {
      modal.warning('Senha Inválida', 'A nova senha deve ter pelo menos 8 caracteres, com letras e números.');
      return;
    }
    
    try {
      await superadminAPI.resetarSenhaUsuario(usuarioSelecionado.id, novaSenha);
      modal.success('Senha Resetada', 'A nova senha foi definida com sucesso.');
      setShowResetSenha(false);
      setNovaSenha('');
    } catch (err) {
      modal.error('Erro', 'Não foi possível resetar a senha.');
    }
  };

  const handleVerificarEmail = async (usuario) => {
    if (usuario.email_verificado) {
      modal.info('Email Já Verificado', 'O email deste usuário já está verificado.');
      return;
    }

    modal.confirm(
      'Verificar Email',
      `Deseja marcar o email "${usuario.email}" como verificado manualmente?`,
      async () => {
        try {
          const response = await superadminAPI.verificarEmailUsuario(usuario.id);
          
          if (response.data.ja_verificado) {
            modal.info('Email Verificado', 'O email já estava verificado.');
          } else {
            modal.success('Email Verificado!', 'O email foi marcado como verificado com sucesso.');
          }
          
          carregarUsuarios();
        } catch (err) {
          modal.error('Erro', 'Não foi possível verificar o email.');
        }
      }
    );
  };

  const handleDesativar2FA = (usuario) => {
    if (!usuario.two_factor_enabled) {
      modal.info('2FA Inativo', 'O 2FA já está desativado para este usuário.');
      return;
    }

    modal.confirm(
      '🔐 Desativar Autenticação 2FA',
      `Tem certeza que deseja desativar o 2FA para o usuário "${usuario.nome}"?\n\nEsta ação deve ser usada apenas quando o usuário perdeu acesso ao email e não consegue fazer login.\n\nTodos os códigos 2FA pendentes serão invalidados.`,
      async () => {
        try {
          const response = await superadminAPI.desativar2FAUsuario(usuario.id);
          modal.success(
            '2FA Desativado!', 
            `O 2FA foi desativado com sucesso para ${response.data.usuario_nome}. O usuário agora pode fazer login sem código de verificação.`
          );
          carregarUsuarios();
        } catch (err) {
          const errorMsg = err.response?.data?.detail || 'Não foi possível desativar o 2FA.';
          modal.error('Erro', errorMsg);
        }
      }
    );
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

  const getPerfilIcon = (perfil) => {
    return perfil === 'admin' ? Crown : User;
  };

  if (loading && usuarios.length === 0) return <Loading message="Carregando usuários..." />;

  return (
    <Layout>
      <div className="p-4 sm:p-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
              <Users className="w-7 h-7 text-amber-500" />
              Gestão de Usuários
            </h1>
            <p className="text-muted-foreground mt-1">
              {total} usuário(s) cadastrado(s) no sistema
            </p>
          </div>
          <Button
            onClick={handleCriar}
            variant="primary"
            className="mt-4 sm:mt-0"
          >
            <UserPlus className="w-4 h-4 mr-2" />
            Novo Usuário
          </Button>
        </div>

        {/* Filtros */}
        <div className="bg-card rounded-xl border border-border p-4 mb-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="lg:col-span-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Buscar por nome ou email..."
                  value={filtros.busca}
                  onChange={(e) => setFiltros(prev => ({ ...prev, busca: e.target.value }))}
                  className="w-full pl-10 pr-4 py-2 bg-background border border-border rounded-lg text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent"
                />
              </div>
            </div>
            <select
              value={filtros.perfil}
              onChange={(e) => setFiltros(prev => ({ ...prev, perfil: e.target.value }))}
              className="px-3 py-2 bg-background border border-border rounded-lg text-foreground"
            >
              <option value="">Todos os perfis</option>
              <option value="admin">Administrador</option>
              <option value="usuario">Usuário</option>
            </select>
            <select
              value={filtros.plano}
              onChange={(e) => setFiltros(prev => ({ ...prev, plano: e.target.value }))}
              className="px-3 py-2 bg-background border border-border rounded-lg text-foreground"
            >
              <option value="">Todos os planos</option>
              <option value="trial">Trial</option>
              <option value="basico">Básico</option>
              <option value="profissional">Profissional</option>
              <option value="enterprise">Enterprise</option>
            </select>
            <select
              value={filtros.ativo}
              onChange={(e) => setFiltros(prev => ({ ...prev, ativo: e.target.value }))}
              className="px-3 py-2 bg-background border border-border rounded-lg text-foreground"
            >
              <option value="">Todos os status</option>
              <option value="true">Ativos</option>
              <option value="false">Inativos</option>
            </select>
          </div>
        </div>

        {/* Lista de Usuários */}
        <div className="bg-card rounded-xl border border-border overflow-hidden">
          {/* Desktop: Table */}
          <div className="hidden lg:block overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted/50 border-b border-border">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Usuário</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Perfil</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Plano</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Email</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">2FA</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Criado em</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground uppercase">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {usuarios.map((usuario) => {
                  const PerfilIcon = getPerfilIcon(usuario.perfil);
                  return (
                    <motion.tr
                      key={usuario.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="hover:bg-muted/50"
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                            usuario.perfil === 'admin' ? 'bg-amber-500/20' : 'bg-primary/20'
                          }`}>
                            <span className={`font-semibold ${usuario.perfil === 'admin' ? 'text-amber-500' : 'text-primary'}`}>
                              {usuario.nome?.charAt(0)?.toUpperCase()}
                            </span>
                          </div>
                          <div className="min-w-0">
                            <p className="font-medium text-foreground truncate">{usuario.nome}</p>
                            <p className="text-sm text-muted-foreground truncate">{usuario.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1.5">
                          <PerfilIcon className={`w-4 h-4 ${usuario.perfil === 'admin' ? 'text-amber-500' : 'text-muted-foreground'}`} />
                          <span className={`text-sm ${usuario.perfil === 'admin' ? 'text-amber-500 font-medium' : 'text-muted-foreground'}`}>
                            {usuario.perfil === 'admin' ? 'Admin' : 'Usuário'}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                          !usuario.plano_ativo && usuario.payment_status === 'pending' 
                            ? 'bg-amber-500/20 text-amber-400' 
                            : usuario.plano_ativo 
                              ? getPlanoColor(usuario.plano) 
                              : 'bg-gray-500/20 text-gray-400'
                        }`}>
                          {!usuario.plano_ativo && usuario.payment_status === 'pending' 
                            ? `${(usuario.plano_pendente || usuario.plano)?.toUpperCase()} (Pgto pendente)` 
                            : usuario.plano?.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {usuario.plano_ativo ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-emerald-500/20 text-emerald-400">
                            <CheckCircle className="w-3 h-3" />
                            Ativo
                          </span>
                        ) : !usuario.plano_ativo && usuario.payment_status === 'pending' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-amber-500/20 text-amber-400">
                            <Clock className="w-3 h-3" />
                            Aguardando Pgto
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-red-500/20 text-red-400">
                            <Ban className="w-3 h-3" />
                            Inativo
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {usuario.email_verificado ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-emerald-500/20 text-emerald-400">
                            <Mail className="w-3 h-3" />
                            Verificado
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-amber-500/20 text-amber-400">
                            <Mail className="w-3 h-3" />
                            Pendente
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {usuario.two_factor_enabled ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-blue-500/20 text-blue-400">
                            <Shield className="w-3 h-3" />
                            Ativo
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-gray-500/20 text-gray-400">
                            <Shield className="w-3 h-3" />
                            Inativo
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground whitespace-nowrap">
                        {formatarData(usuario.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <button onClick={() => handleVisualizar(usuario)} className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition" title="Visualizar"><Eye className="w-4 h-4" /></button>
                          <button onClick={() => handleEditar(usuario)} className="p-2 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded-lg transition" title="Editar"><Edit className="w-4 h-4" /></button>
                          {!usuario.email_verificado && (
                            <button onClick={() => handleVerificarEmail(usuario)} className="p-2 text-muted-foreground hover:text-blue-500 hover:bg-blue-500/10 rounded-lg transition" title="Verificar Email"><Mail className="w-4 h-4" /></button>
                          )}
                          {usuario.two_factor_enabled && (
                            <button onClick={() => handleDesativar2FA(usuario)} className="p-2 text-muted-foreground hover:text-orange-500 hover:bg-orange-500/10 rounded-lg transition" title="Desativar 2FA"><Shield className="w-4 h-4" /></button>
                          )}
                          {usuario.ativo ? (
                            <button onClick={() => handleDeletar(usuario)} className="p-2 text-muted-foreground hover:text-amber-500 hover:bg-amber-500/10 rounded-lg transition" title="Desativar"><Ban className="w-4 h-4" /></button>
                          ) : (
                            <button onClick={() => handleAtivar(usuario)} className="p-2 text-muted-foreground hover:text-emerald-500 hover:bg-emerald-500/10 rounded-lg transition" title="Ativar"><CheckCircle className="w-4 h-4" /></button>
                          )}
                          <button onClick={() => handleDeletarPermanente(usuario)} className="p-2 text-muted-foreground hover:text-red-500 hover:bg-red-500/10 rounded-lg transition" title="Excluir Permanentemente"><Trash2 className="w-4 h-4" /></button>
                        </div>
                      </td>
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Mobile/Tablet: Cards */}
          <div className="lg:hidden divide-y divide-border">
            {usuarios.map((usuario) => {
              const PerfilIcon = getPerfilIcon(usuario.perfil);
              return (
                <motion.div
                  key={usuario.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="p-4 hover:bg-muted/30 transition"
                >
                  {/* Header: Avatar + Nome + Ações */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <div className={`w-11 h-11 rounded-full flex items-center justify-center flex-shrink-0 ${
                        usuario.perfil === 'admin' ? 'bg-amber-500/20' : 'bg-primary/20'
                      }`}>
                        <span className={`text-lg font-semibold ${usuario.perfil === 'admin' ? 'text-amber-500' : 'text-primary'}`}>
                          {usuario.nome?.charAt(0)?.toUpperCase()}
                        </span>
                      </div>
                      <div className="min-w-0">
                        <p className="font-semibold text-foreground truncate text-sm">{usuario.nome}</p>
                        <p className="text-xs text-muted-foreground truncate">{usuario.email}</p>
                      </div>
                    </div>
                    {/* Ações compactas mobile */}
                    <div className="flex items-center gap-0.5 flex-shrink-0">
                      <button onClick={() => handleVisualizar(usuario)} className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted rounded-md transition" title="Visualizar"><Eye className="w-4 h-4" /></button>
                      <button onClick={() => handleEditar(usuario)} className="p-1.5 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded-md transition" title="Editar"><Edit className="w-4 h-4" /></button>
                      {usuario.ativo ? (
                        <button onClick={() => handleDeletar(usuario)} className="p-1.5 text-muted-foreground hover:text-amber-500 hover:bg-amber-500/10 rounded-md transition" title="Desativar"><Ban className="w-4 h-4" /></button>
                      ) : (
                        <button onClick={() => handleAtivar(usuario)} className="p-1.5 text-muted-foreground hover:text-emerald-500 hover:bg-emerald-500/10 rounded-md transition" title="Ativar"><CheckCircle className="w-4 h-4" /></button>
                      )}
                      <button onClick={() => handleDeletarPermanente(usuario)} className="p-1.5 text-muted-foreground hover:text-red-500 hover:bg-red-500/10 rounded-md transition" title="Excluir"><Trash2 className="w-4 h-4" /></button>
                    </div>
                  </div>

                  {/* Badges row */}
                  <div className="flex flex-wrap items-center gap-1.5 mt-3">
                    {/* Perfil */}
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium rounded-full ${
                      usuario.perfil === 'admin' ? 'bg-amber-500/20 text-amber-400' : 'bg-muted text-muted-foreground'
                    }`}>
                      <PerfilIcon className="w-3 h-3" />
                      {usuario.perfil === 'admin' ? 'Admin' : 'Usuário'}
                    </span>

                    {/* Plano */}
                    <span className={`px-2 py-0.5 text-[11px] font-medium rounded-full ${
                      !usuario.plano_ativo && usuario.payment_status === 'pending' 
                        ? 'bg-amber-500/20 text-amber-400' 
                        : usuario.plano_ativo 
                          ? getPlanoColor(usuario.plano) 
                          : 'bg-gray-500/20 text-gray-400'
                    }`}>
                      {!usuario.plano_ativo && usuario.payment_status === 'pending' 
                        ? `${(usuario.plano_pendente || usuario.plano)?.toUpperCase()} (Pgto pendente)` 
                        : usuario.plano?.toUpperCase()}
                    </span>

                    {/* Status */}
                    {usuario.plano_ativo ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium rounded-full bg-emerald-500/20 text-emerald-400">
                        <CheckCircle className="w-3 h-3" />Ativo
                      </span>
                    ) : !usuario.plano_ativo && usuario.payment_status === 'pending' ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium rounded-full bg-amber-500/20 text-amber-400">
                        <Clock className="w-3 h-3" />Aguardando
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium rounded-full bg-red-500/20 text-red-400">
                        <Ban className="w-3 h-3" />Inativo
                      </span>
                    )}

                    {/* Email */}
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium rounded-full ${
                      usuario.email_verificado ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
                    }`}>
                      <Mail className="w-3 h-3" />
                      {usuario.email_verificado ? 'Email OK' : 'Email Pend.'}
                    </span>

                    {/* 2FA */}
                    {usuario.two_factor_enabled && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium rounded-full bg-blue-500/20 text-blue-400">
                        <Shield className="w-3 h-3" />2FA
                      </span>
                    )}

                    {/* Data */}
                    <span className="text-[11px] text-muted-foreground ml-auto">
                      {formatarData(usuario.created_at)}
                    </span>
                  </div>

                  {/* Ações extras mobile (email verif, 2FA) */}
                  {(!usuario.email_verificado || usuario.two_factor_enabled) && (
                    <div className="flex gap-2 mt-2.5 pt-2.5 border-t border-border/50">
                      {!usuario.email_verificado && (
                        <button onClick={() => handleVerificarEmail(usuario)} className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 rounded-md transition">
                          <Mail className="w-3.5 h-3.5" />Verificar Email
                        </button>
                      )}
                      {usuario.two_factor_enabled && (
                        <button onClick={() => handleDesativar2FA(usuario)} className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-orange-400 bg-orange-500/10 hover:bg-orange-500/20 rounded-md transition">
                          <Shield className="w-3.5 h-3.5" />Desativar 2FA
                        </button>
                      )}
                    </div>
                  )}
                </motion.div>
              );
            })}
          </div>
          
          {usuarios.length === 0 && (
            <div className="p-8 text-center text-muted-foreground">
              <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>Nenhum usuário encontrado</p>
            </div>
          )}
        </div>
      </div>

      {/* Modal Criar/Editar/Visualizar */}
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
                    {modalMode === 'criar' && 'Novo Usuário'}
                    {modalMode === 'editar' && 'Editar Usuário'}
                    {modalMode === 'visualizar' && 'Detalhes do Usuário'}
                  </h2>
                  <button
                    onClick={() => setShowModal(false)}
                    className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition"
                    title="Fechar"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {modalMode === 'visualizar' && usuarioSelecionado ? (
                  <div className="p-6 space-y-4">
                    <div className="flex items-center gap-4">
                      <div className={`w-16 h-16 rounded-full flex items-center justify-center ${
                        usuarioSelecionado.perfil === 'admin' ? 'bg-amber-500/20' : 'bg-primary/20'
                      }`}>
                        <span className={`text-2xl font-bold ${usuarioSelecionado.perfil === 'admin' ? 'text-amber-500' : 'text-primary'}`}>
                          {usuarioSelecionado.nome?.charAt(0)?.toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-foreground">{usuarioSelecionado.nome}</h3>
                        <p className="text-muted-foreground">{usuarioSelecionado.email}</p>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border">
                      <div>
                        <p className="text-xs text-muted-foreground uppercase">Perfil</p>
                        <p className="font-medium text-foreground">{usuarioSelecionado.perfil === 'admin' ? '👑 Admin' : 'Usuário'}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground uppercase">Plano</p>
                        <p className="font-medium text-foreground">{usuarioSelecionado.plano?.toUpperCase()}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground uppercase">Status</p>
                        <p className={`font-medium ${usuarioSelecionado.ativo ? 'text-emerald-500' : 'text-red-500'}`}>
                          {usuarioSelecionado.ativo ? 'Ativo' : 'Inativo'}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground uppercase">Criado em</p>
                        <p className="font-medium text-foreground">{formatarData(usuarioSelecionado.created_at)}</p>
                      </div>
                    </div>

                    {usuarioSelecionado.stats && (
                      <div className="pt-4 border-t border-border">
                        <p className="text-sm font-semibold text-foreground mb-3">Estatísticas</p>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="bg-muted/50 rounded-lg p-3 text-center">
                            <p className="text-2xl font-bold text-primary">{usuarioSelecionado.stats.clientes}</p>
                            <p className="text-xs text-muted-foreground">Clientes</p>
                          </div>
                          <div className="bg-muted/50 rounded-lg p-3 text-center">
                            <p className="text-2xl font-bold text-primary">{usuarioSelecionado.stats.emprestimos}</p>
                            <p className="text-xs text-muted-foreground">Empréstimos</p>
                          </div>
                          <div className="bg-muted/50 rounded-lg p-3 text-center">
                            <p className="text-2xl font-bold text-primary">{usuarioSelecionado.stats.emprestimos_ativos}</p>
                            <p className="text-xs text-muted-foreground">Emp. Ativos</p>
                          </div>
                          <div className="bg-muted/50 rounded-lg p-3 text-center">
                            <p className="text-2xl font-bold text-primary">{usuarioSelecionado.stats.pagamentos}</p>
                            <p className="text-xs text-muted-foreground">Pagamentos</p>
                          </div>
                        </div>
                      </div>
                    )}

                    <div className="flex gap-3 pt-4">
                      <Button
                        onClick={() => {
                          setShowResetSenha(true);
                        }}
                        variant="secondary"
                        className="flex-1"
                      >
                        <Key className="w-4 h-4 mr-2" />
                        Resetar Senha
                      </Button>
                      <Button
                        onClick={() => handleEditar(usuarioSelecionado)}
                        variant="primary"
                        className="flex-1"
                      >
                        <Edit className="w-4 h-4 mr-2" />
                        Editar
                      </Button>
                    </div>
                  </div>
                ) : (
                  <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-foreground mb-1">Nome</label>
                      <input
                        type="text"
                        value={formData.nome}
                        onChange={(e) => setFormData(prev => ({ ...prev, nome: e.target.value }))}
                        className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-foreground mb-1">Email</label>
                      <input
                        type="email"
                        value={formData.email}
                        onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                        className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-foreground mb-1">
                        Senha {modalMode === 'editar' && '(deixe em branco para manter)'}
                      </label>
                      <input
                        type="password"
                        value={formData.senha}
                        onChange={(e) => setFormData(prev => ({ ...prev, senha: e.target.value }))}
                        className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                        required={modalMode === 'criar'}
                        minLength={8}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1">Perfil</label>
                        <select
                          value={formData.perfil}
                          onChange={(e) => setFormData(prev => ({ ...prev, perfil: e.target.value }))}
                          className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                        >
                          <option value="usuario">Usuário</option>
                          <option value="admin">Administrador</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1">Plano</label>
                        <select
                          value={formData.plano}
                          onChange={(e) => setFormData(prev => ({ ...prev, plano: e.target.value }))}
                          className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                        >
                          <option value="trial">Trial</option>
                          <option value="basico">Básico</option>
                          <option value="profissional">Profissional</option>
                          <option value="enterprise">Enterprise</option>
                        </select>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id="ativo"
                        checked={formData.ativo}
                        onChange={(e) => setFormData(prev => ({ ...prev, ativo: e.target.checked }))}
                        className="w-4 h-4 rounded border-border"
                      />
                      <label htmlFor="ativo" className="text-sm text-foreground">Usuário ativo</label>
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
                        {modalMode === 'criar' ? 'Criar Usuário' : 'Salvar Alterações'}
                      </Button>
                    </div>
                  </form>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Modal Reset Senha */}
      <AnimatePresence>
        {showResetSenha && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60]"
              onClick={() => setShowResetSenha(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="fixed inset-0 flex items-center justify-center z-[60] p-4"
            >
              <div className="bg-card rounded-xl border border-border shadow-xl w-full max-w-sm p-6">
                <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                  <Key className="w-5 h-5 text-amber-500" />
                  Resetar Senha
                </h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Digite a nova senha para o usuário <strong>{usuarioSelecionado?.nome}</strong>
                </p>
                <input
                  type="password"
                  value={novaSenha}
                  onChange={(e) => setNovaSenha(e.target.value)}
                  placeholder="Nova senha (min. 8, com letras e números)"
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground mb-4"
                  minLength={8}
                />
                <div className="flex gap-3">
                  <Button
                    onClick={() => {
                      setShowResetSenha(false);
                      setNovaSenha('');
                    }}
                    variant="secondary"
                    className="flex-1"
                  >
                    Cancelar
                  </Button>
                  <Button onClick={handleResetarSenha} variant="primary" className="flex-1">
                    Confirmar
                  </Button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </Layout>
  );
};

export default AdminUsuarios;
