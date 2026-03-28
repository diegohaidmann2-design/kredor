import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import Header from '../components/Header';
import Loading from '../components/Loading';
import ErrorMessage from '../components/ErrorMessage';
import Button from '../components/Button';
import { useModal } from '../components/Modal';
import { useToast } from '../hooks/use-toast';
import { clientesAPI } from '../api/api';
import { formatarCpfCnpj, formatarTelefone } from '../utils/formatters';
import {
  validarCpfCnpj,
  validarEmail,
  validarTelefone,
  validarCep,
  validarCampoObrigatorio,
  mascaraCpfCnpj,
  mascaraTelefone,
  mascaraCep
} from '../utils/validators';
import { getStatusColor, getStatusLabel, formatarErroAPI } from '../utils/formatters';
import useAutosave, { useUnsavedChangesWarning } from '../hooks/useAutosave';
import DraftRecovery, { SaveStatusBadge } from '../components/DraftRecovery';
import { getDraftTimestamp } from '../utils/storageUtils';

const Clientes = () => {
  const [clientes, setClientes] = useState([]);
  const [clientesFiltrados, setClientesFiltrados] = useState([]);
  const [termoBusca, setTermoBusca] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false); // Estado de submissão
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [showDetalhesModal, setShowDetalhesModal] = useState(false);
  const [clienteSelecionado, setClienteSelecionado] = useState(null);
  const [editando, setEditando] = useState(null);
  const [formErrors, setFormErrors] = useState({});
  const [showDraftRecovery, setShowDraftRecovery] = useState(false);
  const [enderecoOpcional, setEnderecoOpcional] = useState(false);
  const [cpfOpcional, setCpfOpcional] = useState(false);
  const { toast } = useToast();
  const modal = useModal();
  const [formData, setFormData] = useState({
    nome: '',
    cpf_cnpj: '',
    telefone: '',
    email: '',
    endereco: {
      rua: '',
      numero: '',
      bairro: '',
      cidade: '',
      estado: '',
      cep: ''
    },
    dados_bancarios: {
      banco: '',
      agencia: '',
      conta: '',
      tipo_conta: 'corrente'
    }
  });

  // Sistema de autosave
  const autosave = useAutosave('cliente', formData, {
    enabled: showModal && !editando, // Só salva em modo de criação
    delay: 3000,
    encrypt: true,
    onSave: (data, timestamp) => {
      // Rascunho salvo automaticamente
    }
  });

  // Aviso ao sair com dados não salvos
  useUnsavedChangesWarning(
    showModal && autosave.hasUnsavedChanges,
    'Você tem um formulário em andamento. Deseja realmente sair?'
  );

  useEffect(() => {
    carregarClientes();
  }, []);

  // Função para normalizar strings (remove acentos e case)
  const normalizeString = (str) => {
    if (!str || typeof str !== 'string') return '';
    return str
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();
  };

  // Aplicar filtro sempre que clientes ou termoBusca mudarem
  useEffect(() => {
    if (!termoBusca.trim()) {
      setClientesFiltrados([...clientes]);
      return;
    }

    const termoNormalizado = normalizeString(termoBusca);
    const termoApenasNumeros = termoBusca.replace(/\D/g, '');
    
    const filtrados = clientes.filter(cliente => {
      const nomeNorm = normalizeString(cliente.nome);
      const cpfNorm = (cliente.cpf_cnpj || '').replace(/\D/g, '');
      const telNorm = (cliente.telefone || '').replace(/\D/g, '');
      const emailNorm = normalizeString(cliente.email);
      
      const matchNome = nomeNorm.includes(termoNormalizado);
      const matchCpf = termoApenasNumeros && cpfNorm.includes(termoApenasNumeros);
      const matchTel = termoApenasNumeros && telNorm.includes(termoApenasNumeros);
      const matchEmail = emailNorm.includes(termoNormalizado);
      
      return matchNome || matchCpf || matchTel || matchEmail;
    });

    setClientesFiltrados([...filtrados]);
  }, [clientes, termoBusca]);

  // Verificar rascunho ao abrir modal
  useEffect(() => {
    if (showModal && !editando && autosave.exists()) {
      setShowDraftRecovery(true);
    }
  }, [showModal, editando]);

  const carregarClientes = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await clientesAPI.listar();
      // A API agora retorna {items: [...], pagination: {...}}
      const data = response.data;
      const clientesData = data.items || data;
      setClientes(clientesData);  // Suporte para ambos os formatos
      setClientesFiltrados(clientesData); // Inicializa com todos os clientes
    } catch (err) {
      console.error('Erro ao carregar clientes:', err);
      setError('Erro ao carregar clientes');
    } finally {
      setLoading(false);
    }
  };

  // Função de busca de clientes
  const handleBusca = (termo) => {
    setTermoBusca(termo);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;

    // Limpa o erro do campo quando o usuário começa a digitar
    if (formErrors[name]) {
      setFormErrors(prev => ({ ...prev, [name]: '' }));
    }

    if (name.startsWith('endereco.')) {
      const field = name.split('.')[1];
      setFormData({
        ...formData,
        endereco: { ...formData.endereco, [field]: value }
      });
    } else if (name.startsWith('dados_bancarios.')) {
      const field = name.split('.')[1];
      setFormData({
        ...formData,
        dados_bancarios: { ...formData.dados_bancarios, [field]: value }
      });
    } else {
      setFormData({ ...formData, [name]: value });
    }
  };

  // Handler específico para CPF/CNPJ com máscara
  const handleCpfCnpjChange = (e) => {
    const valorComMascara = mascaraCpfCnpj(e.target.value);
    setFormData({ ...formData, cpf_cnpj: valorComMascara });

    // Limpa o erro quando o usuário digita
    if (formErrors.cpf_cnpj) {
      setFormErrors(prev => ({ ...prev, cpf_cnpj: '' }));
    }
  };

  // Handler específico para Telefone com máscara
  const handleTelefoneChange = (e) => {
    const valorComMascara = mascaraTelefone(e.target.value);
    setFormData({ ...formData, telefone: valorComMascara });

    // Limpa o erro quando o usuário digita
    if (formErrors.telefone) {
      setFormErrors(prev => ({ ...prev, telefone: '' }));
    }
  };

  // Handler específico para Email com validação
  const handleEmailChange = (e) => {
    setFormData({ ...formData, email: e.target.value });

    // Limpa o erro quando o usuário digita
    if (formErrors.email) {
      setFormErrors(prev => ({ ...prev, email: '' }));
    }
  };

  // Validação do formulário antes de enviar
  const validarFormulario = () => {
    const erros = {};

    // Validar nome
    if (!validarCampoObrigatorio(formData.nome)) {
      erros.nome = 'Nome é obrigatório';
    }

    // Validar CPF/CNPJ (apenas se não for opcional)
    if (!cpfOpcional) {
      if (!validarCampoObrigatorio(formData.cpf_cnpj)) {
        erros.cpf_cnpj = 'CPF/CNPJ é obrigatório';
      } else if (!validarCpfCnpj(formData.cpf_cnpj)) {
        erros.cpf_cnpj = 'CPF/CNPJ inválido';
      }
    }

    // Validar Telefone
    if (!validarCampoObrigatorio(formData.telefone)) {
      erros.telefone = 'Telefone é obrigatório';
    } else if (!validarTelefone(formData.telefone)) {
      erros.telefone = 'Telefone inválido (mínimo 10 dígitos)';
    }

    // Validar Email
    if (!validarCampoObrigatorio(formData.email)) {
      erros.email = 'Email é obrigatório';
    } else if (!validarEmail(formData.email)) {
      erros.email = 'Email inválido';
    }

    // Validar Endereço apenas se não for opcional
    if (!enderecoOpcional) {
      // Validar CEP
      if (!validarCampoObrigatorio(formData.endereco.cep)) {
        erros['endereco.cep'] = 'CEP é obrigatório';
      } else if (!validarCep(formData.endereco.cep)) {
        erros['endereco.cep'] = 'CEP inválido';
      }

      // Validar campos de endereço obrigatórios
      if (!validarCampoObrigatorio(formData.endereco.rua)) {
        erros['endereco.rua'] = 'Rua é obrigatória';
      }
      if (!validarCampoObrigatorio(formData.endereco.numero)) {
        erros['endereco.numero'] = 'Número é obrigatório';
      }
      if (!validarCampoObrigatorio(formData.endereco.bairro)) {
        erros['endereco.bairro'] = 'Bairro é obrigatório';
      }
      if (!validarCampoObrigatorio(formData.endereco.cidade)) {
        erros['endereco.cidade'] = 'Cidade é obrigatória';
      }
      if (!validarCampoObrigatorio(formData.endereco.estado)) {
        erros['endereco.estado'] = 'Estado é obrigatório';
      }
    }

    setFormErrors(erros);
    return Object.keys(erros).length === 0;
  };

  const buscarCep = async (cep) => {
    // Remove caracteres não numéricos
    const cepLimpo = cep.replace(/\D/g, '');

    // Verifica se o CEP tem 8 dígitos
    if (cepLimpo.length !== 8) {
      return;
    }

    try {
      const response = await fetch(`https://viacep.com.br/ws/${cepLimpo}/json/`);
      const data = await response.json();

      if (data.erro) {
        modal.warning('CEP não encontrado', 'O CEP informado não foi encontrado. Verifique e tente novamente.');
        return;
      }

      // Preenche os campos automaticamente
      setFormData({
        ...formData,
        endereco: {
          ...formData.endereco,
          cep: cep,
          rua: data.logradouro || '',
          bairro: data.bairro || '',
          cidade: data.localidade || '',
          estado: data.uf || ''
        }
      });
    } catch (error) {
      console.error('Erro ao buscar CEP:', error);
      modal.error('Erro ao buscar CEP', 'Não foi possível buscar o endereço. Tente novamente.');
    }
  };

  const handleCepChange = (e) => {
    let cep = e.target.value;

    // Remove tudo que não é número
    cep = cep.replace(/\D/g, '');

    // Aplica a máscara 00000-000
    if (cep.length > 5) {
      cep = cep.replace(/(\d{5})(\d)/, '$1-$2');
    }

    // Limita a 9 caracteres (00000-000)
    cep = cep.substring(0, 9);

    // Atualiza o campo
    setFormData({
      ...formData,
      endereco: { ...formData.endereco, cep }
    });

    // Busca o CEP automaticamente quando tiver 8 dígitos (sem o hífen)
    const cepLimpo = cep.replace(/\D/g, '');
    if (cepLimpo.length === 8) {
      buscarCep(cep);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validar formulário antes de enviar
    if (!validarFormulario()) {
      return;
    }

    // Prevenir duplo submit
    if (submitting) {
      return;
    }

    setSubmitting(true);

    try {
      if (editando) {
        // Se for opcional, enviar como string vazia ou null (depende do backend, mas o modelo agora aceita null e o converter trata "")
        const dataToSend = { ...formData };
        if (cpfOpcional) dataToSend.cpf_cnpj = "";
        await clientesAPI.atualizar(editando, dataToSend);
      } else {
        const dataToSend = { ...formData };
        if (cpfOpcional) dataToSend.cpf_cnpj = "";
        await clientesAPI.criar(dataToSend);
        // Limpar rascunho após criação bem-sucedida
        autosave.clear();
      }

      setShowModal(false);
      resetForm();
      carregarClientes();
      modal.success(
        editando ? 'Cliente Atualizado!' : 'Cliente Cadastrado!',
        editando ? 'Os dados do cliente foram atualizados com sucesso.' : 'O cliente foi cadastrado com sucesso no sistema.'
      );
    } catch (err) {
      const errorMsg = formatarErroAPI(err, 'Não foi possível salvar o cliente. Tente novamente.');
      modal.error('Erro ao salvar', errorMsg);
    } finally {
      setSubmitting(false);
    }
  };

  // Funções de recuperação de rascunho
  const handleRecoverDraft = () => {
    const draft = autosave.restore();
    if (draft) {
      setFormData(draft);
      setShowDraftRecovery(false);
      modal.success('Rascunho Recuperado!', 'Seus dados foram restaurados com sucesso.');
    }
  };

  const handleDiscardDraft = () => {
    autosave.clear();
    setShowDraftRecovery(false);
  };

  const handleClearDraft = () => {
    if (window.confirm('Deseja limpar o rascunho salvo?')) {
      autosave.clear();
      modal.success('Rascunho Limpo', 'O rascunho foi removido com sucesso.');
    }
  };

  const handleEditar = (cliente) => {
    setEditando(cliente.id);
    setFormData({
      nome: cliente.nome,
      cpf_cnpj: cliente.cpf_cnpj,
      telefone: cliente.telefone,
      email: cliente.email,
      endereco: cliente.endereco,
      dados_bancarios: cliente.dados_bancarios || {
        banco: '',
        agencia: '',
        conta: '',
        tipo_conta: 'corrente'
      }
    });
    setEnderecoOpcional(!cliente.endereco || (typeof cliente.endereco === 'object' && !cliente.endereco.rua));
    setCpfOpcional(!cliente.cpf_cnpj);
    setShowModal(true);
  };

  const handleVerDetalhes = (cliente) => {
    setClienteSelecionado(cliente);
    setShowDetalhesModal(true);
  };

  const handleDeletar = async (id) => {
    modal.confirm(
      'Confirmar Exclusão',
      'Tem certeza que deseja deletar este cliente? Esta ação não pode ser desfeita.',
      async () => {
        try {
          await clientesAPI.deletar(id);
          carregarClientes();
          modal.success('Cliente Excluído', 'O cliente foi removido do sistema com sucesso.');
        } catch (err) {
          const errorMsg = formatarErroAPI(err, 'Não foi possível excluir o cliente. Tente novamente.');
          modal.error('Erro ao excluir', errorMsg);
        }
      }
    );
  };

  const handleBloquear = async (cliente) => {
    modal.confirm(
      'Bloquear Cliente',
      `Tem certeza que deseja bloquear "${cliente.nome}"? O cliente não poderá receber novos empréstimos.`,
      async () => {
        try {
          await clientesAPI.atualizar(cliente.id, { ...cliente, status: 'bloqueado' });
          carregarClientes();
          modal.success('Cliente Bloqueado', 'O cliente foi bloqueado com sucesso.');
        } catch (err) {
          const errorMsg = formatarErroAPI(err, 'Não foi possível bloquear o cliente.');
          modal.error('Erro ao bloquear', errorMsg);
        }
      }
    );
  };

  const handleDesbloquear = async (cliente) => {
    try {
      await clientesAPI.atualizar(cliente.id, { ...cliente, status: 'ativo' });
      carregarClientes();
      modal.success('Cliente Desbloqueado', 'O cliente foi reativado com sucesso.');
    } catch (err) {
      const errorMsg = formatarErroAPI(err, 'Não foi possível desbloquear o cliente.');
      modal.error('Erro ao desbloquear', errorMsg);
    }
  };

  const resetForm = () => {
    setEditando(null);
    setSubmitting(false); // Reset do estado de submitting
    setFormErrors({});
    setFormErrors({});
    setEnderecoOpcional(false);
    setCpfOpcional(false);
    setFormData({
      nome: '',
      cpf_cnpj: '',
      telefone: '',
      email: '',
      endereco: {
        rua: '',
        numero: '',
        bairro: '',
        cidade: '',
        estado: '',
        cep: ''
      },
      dados_bancarios: {
        banco: '',
        agencia: '',
        conta: '',
        tipo_conta: 'corrente'
      }
    });
  };

  if (loading) return <Loading message="Carregando clientes..." />;

  return (
    <Layout>
      <Header
        title="Clientes"
        subtitle="Gerencie seus clientes"
        action={{
          label: "Novo Cliente",
          onClick: () => {
            resetForm();
            setShowModal(true);
          }
        }}
      />

      <div className="p-4 sm:p-6">
        {error && <ErrorMessage message={error} onRetry={carregarClientes} />}

        {/* Campo de Busca */}
        <div className="mb-4">
          <div className="relative max-w-md">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg 
                className="h-5 w-5 text-muted-foreground" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" 
                />
              </svg>
            </div>
            <input
              type="text"
              value={termoBusca}
              onChange={(e) => handleBusca(e.target.value)}
              placeholder="Buscar por nome, CPF/CNPJ, telefone ou email..."
              className="w-full pl-10 pr-4 py-2.5 bg-background border border-input rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
              data-testid="buscar-cliente-input"
            />
            {termoBusca && (
              <button
                onClick={() => handleBusca('')}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-muted-foreground hover:text-foreground transition"
                title="Limpar busca"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
          {termoBusca && (
            <p className="text-sm text-muted-foreground mt-2">
              {clientesFiltrados.length === 0 
                ? 'Nenhum cliente encontrado' 
                : `${clientesFiltrados.length} cliente${clientesFiltrados.length !== 1 ? 's' : ''} encontrado${clientesFiltrados.length !== 1 ? 's' : ''}`
              }
            </p>
          )}
        </div>

        {/* Lista de Clientes */}
        <div className="bg-card rounded-xl border border-border overflow-hidden" data-testid="clientes-table-container">
          {clientesFiltrados.length === 0 ? (
            <div className="p-8 text-center" data-testid="sem-clientes-message">
              <p className="text-muted-foreground">
                {termoBusca ? 'Nenhum cliente encontrado com os critérios de busca' : 'Nenhum cliente cadastrado'}
              </p>
            </div>
          ) : (
            <>
              {/* Tabela Desktop */}
              <div className="hidden md:block overflow-x-auto">
                <table className="min-w-full divide-y divide-border">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Nome
                      </th>
                      <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        CPF/CNPJ
                      </th>
                      <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Telefone
                      </th>
                      <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider hidden lg:table-cell">
                        Email
                      </th>
                      <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider hidden xl:table-cell">
                        Código Portal
                      </th>
                      <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-4 lg:px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Ações
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border" data-testid="clientes-table-body">
                    {clientesFiltrados.map((cliente) => (
                      <tr key={cliente.id} className="hover:bg-muted/30 transition-colors" data-testid={`cliente-row-${cliente.id}`}>
                        <td className="px-4 lg:px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-foreground">{cliente.nome}</div>
                        </td>
                        <td className="px-4 lg:px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                          {formatarCpfCnpj(cliente.cpf_cnpj)}
                        </td>
                        <td className="px-4 lg:px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                          {formatarTelefone(cliente.telefone)}
                        </td>
                        <td className="px-4 lg:px-6 py-4 whitespace-nowrap text-sm text-muted-foreground hidden lg:table-cell">
                          {cliente.email}
                        </td>
                        <td className="px-4 lg:px-6 py-4 whitespace-nowrap text-sm text-muted-foreground hidden xl:table-cell">
                          {cliente.codigo_portal ? (
                            <div className="flex items-center gap-2">
                              <code className="px-2 py-1 bg-muted rounded font-mono text-xs">
                                {cliente.codigo_portal}
                              </code>
                              <button
                                onClick={() => {
                                  navigator.clipboard.writeText(cliente.codigo_portal);
                                  toast({
                                    title: "✅ Código Copiado!",
                                    description: `Código ${cliente.codigo_portal} copiado para a área de transferência.`,
                                    variant: "default",
                                  });
                                }}
                                className="p-1 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded transition"
                                title="Copiar código"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                </svg>
                              </button>
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground italic">Sem código</span>
                          )}
                        </td>
                        <td className="px-4 lg:px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full border ${getStatusColor(cliente.status)}`}>
                            {getStatusLabel(cliente.status)}
                          </span>
                        </td>
                        <td className="px-4 lg:px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              onClick={() => handleVerDetalhes(cliente)}
                              className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition"
                              title="Ver Detalhes"
                              data-testid={`ver-detalhes-${cliente.id}`}
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                              </svg>
                            </button>
                            <button
                              onClick={() => handleEditar(cliente)}
                              className="p-2 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded-lg transition"
                              title="Editar"
                              data-testid={`editar-cliente-${cliente.id}`}
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                              </svg>
                            </button>
                            {cliente.status === 'ativo' ? (
                              <button
                                onClick={() => handleBloquear(cliente)}
                                className="p-2 text-muted-foreground hover:text-amber-500 hover:bg-amber-500/10 rounded-lg transition"
                                title="Bloquear Cliente"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                                </svg>
                              </button>
                            ) : cliente.status === 'bloqueado' ? (
                              <button
                                onClick={() => handleDesbloquear(cliente)}
                                className="p-2 text-muted-foreground hover:text-emerald-500 hover:bg-emerald-500/10 rounded-lg transition"
                                title="Desbloquear Cliente"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                              </button>
                            ) : null}
                            <button
                              onClick={() => handleDeletar(cliente.id)}
                              className="p-2 text-muted-foreground hover:text-red-500 hover:bg-red-500/10 rounded-lg transition"
                              title="Excluir Cliente"
                              data-testid={`deletar-cliente-${cliente.id}`}
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Cards Mobile */}
              <div className="md:hidden divide-y divide-border">
                {clientesFiltrados.map((cliente) => (
                  <div key={cliente.id} className="p-4 hover:bg-muted/30 transition-colors" data-testid={`cliente-card-${cliente.id}`}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-foreground truncate">{cliente.nome}</p>
                        <p className="text-xs text-muted-foreground mt-1">{formatarCpfCnpj(cliente.cpf_cnpj)}</p>
                        <p className="text-xs text-muted-foreground">{formatarTelefone(cliente.telefone)}</p>
                        {cliente.codigo_portal && (
                          <div className="flex items-center gap-2 mt-2">
                            <span className="text-xs text-muted-foreground">Código Portal:</span>
                            <code className="px-2 py-1 bg-muted rounded font-mono text-xs">
                              {cliente.codigo_portal}
                            </code>
                            <button
                              onClick={() => {
                                navigator.clipboard.writeText(cliente.codigo_portal);
                                toast({
                                  title: "✅ Código Copiado!",
                                  description: `Código ${cliente.codigo_portal} copiado para a área de transferência.`,
                                  variant: "default",
                                });
                              }}
                              className="p-1 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded transition"
                              title="Copiar código"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                              </svg>
                            </button>
                          </div>
                        )}
                      </div>
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full border flex-shrink-0 ${getStatusColor(cliente.status)}`}>
                        {getStatusLabel(cliente.status)}
                      </span>
                    </div>
                    <div className="flex items-center justify-end gap-1 mt-3 pt-3 border-t border-border">
                      <button
                        onClick={() => handleVerDetalhes(cliente)}
                        className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition"
                        title="Ver Detalhes"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleEditar(cliente)}
                        className="p-2 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded-lg transition"
                        title="Editar"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      {cliente.status === 'ativo' ? (
                        <button
                          onClick={() => handleBloquear(cliente)}
                          className="p-2 text-muted-foreground hover:text-amber-500 hover:bg-amber-500/10 rounded-lg transition"
                          title="Bloquear"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                          </svg>
                        </button>
                      ) : cliente.status === 'bloqueado' ? (
                        <button
                          onClick={() => handleDesbloquear(cliente)}
                          className="p-2 text-muted-foreground hover:text-emerald-500 hover:bg-emerald-500/10 rounded-lg transition"
                          title="Desbloquear"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </button>
                      ) : null}
                      <button
                        onClick={() => handleDeletar(cliente.id)}
                        className="p-2 text-muted-foreground hover:text-red-500 hover:bg-red-500/10 rounded-lg transition"
                        title="Excluir"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Modal de Cadastro/Edição */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50" data-testid="cliente-modal">
          <div className="bg-card rounded-xl border border-border shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            <div className="p-4 sm:p-6">
              <div className="flex items-center justify-between mb-4 sm:mb-6">
                <h2 className="text-xl sm:text-2xl font-display font-bold text-foreground">
                  {editando ? 'Editar Cliente' : 'Novo Cliente'}
                </h2>
                {!editando && (
                  <SaveStatusBadge
                    isSaving={autosave.isSaving}
                    lastSaved={autosave.lastSaved}
                    hasUnsavedChanges={autosave.hasUnsavedChanges}
                    onClearDraft={handleClearDraft}
                  />
                )}
              </div>

              <form onSubmit={handleSubmit}>
                <div className="space-y-4">
                  {/* Dados Pessoais */}
                  <div className="border-b border-border pb-4">
                    <h3 className="font-semibold text-base sm:text-lg mb-3 text-foreground">Dados Pessoais</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1">
                          Nome Completo <span className="text-destructive">*</span>
                        </label>
                        <input
                          type="text"
                          name="nome"
                          value={formData.nome}
                          onChange={handleChange}
                          className={`w-full px-3 py-2 bg-background border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary ${formErrors.nome ? 'border-destructive' : 'border-input'
                            }`}
                          data-testid="input-nome"
                        />
                        {formErrors.nome && (
                          <p className="text-destructive text-xs mt-1" data-testid="erro-nome">{formErrors.nome}</p>
                        )}
                      </div>
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <label className="block text-sm font-medium text-foreground">
                            CPF/CNPJ {!cpfOpcional && <span className="text-destructive">*</span>}
                          </label>
                          <label className="flex items-center gap-1.5 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={cpfOpcional}
                              onChange={(e) => {
                                setCpfOpcional(e.target.checked);
                                if (e.target.checked) setFormErrors(prev => ({ ...prev, cpf_cnpj: '' }));
                              }}
                              className="w-3.5 h-3.5 rounded border-input text-primary focus:ring-primary/20 bg-background"
                            />
                            <span className="text-xs text-muted-foreground select-none">Não informar</span>
                          </label>
                        </div>
                        <input
                          type="text"
                          name="cpf_cnpj"
                          value={formData.cpf_cnpj}
                          onChange={handleCpfCnpjChange}
                          disabled={!!editando || cpfOpcional}
                          maxLength={18}
                          placeholder="000.000.000-00 ou 00.000.000/0000-00"
                          className={`w-full px-3 py-2 bg-background border rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary disabled:bg-muted disabled:cursor-not-allowed ${formErrors.cpf_cnpj ? 'border-destructive' : 'border-input'
                            }`}
                          data-testid="input-cpf-cnpj"
                        />
                        {formErrors.cpf_cnpj && (
                          <p className="text-destructive text-xs mt-1" data-testid="erro-cpf-cnpj">{formErrors.cpf_cnpj}</p>
                        )}
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1">
                          Telefone <span className="text-destructive">*</span>
                        </label>
                        <input
                          type="text"
                          name="telefone"
                          value={formData.telefone}
                          onChange={handleTelefoneChange}
                          maxLength={15}
                          placeholder="(00) 00000-0000"
                          className={`w-full px-3 py-2 bg-background border rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary ${formErrors.telefone ? 'border-destructive' : 'border-input'
                            }`}
                          data-testid="input-telefone"
                        />
                        {formErrors.telefone && (
                          <p className="text-destructive text-xs mt-1" data-testid="erro-telefone">{formErrors.telefone}</p>
                        )}
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1">
                          Email <span className="text-destructive">*</span>
                        </label>
                        <input
                          type="email"
                          name="email"
                          value={formData.email}
                          onChange={handleEmailChange}
                          placeholder="email@exemplo.com"
                          className={`w-full px-3 py-2 bg-background border rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary ${formErrors.email ? 'border-destructive' : 'border-input'
                            }`}
                          data-testid="input-email"
                        />
                        {formErrors.email && (
                          <p className="text-destructive text-xs mt-1" data-testid="erro-email">{formErrors.email}</p>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Endereço */}
                  <div className="border-b pb-4">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-semibold text-lg text-foreground">Endereço</h3>
                      <label className="flex items-center gap-2 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={enderecoOpcional}
                          onChange={(e) => {
                            setEnderecoOpcional(e.target.checked);
                            // Limpa erros de endereço quando marcado como opcional
                            if (e.target.checked) {
                              setFormErrors(prev => {
                                const newErrors = { ...prev };
                                Object.keys(newErrors).forEach(key => {
                                  if (key.startsWith('endereco.')) {
                                    delete newErrors[key];
                                  }
                                });
                                return newErrors;
                              });
                            }
                          }}
                          className="w-4 h-4 rounded border-border text-primary focus:ring-primary/20 bg-background"
                          data-testid="checkbox-endereco-opcional"
                        />
                        <span className="text-sm text-muted-foreground">
                          Cadastrar sem endereço
                        </span>
                      </label>
                    </div>

                    {enderecoOpcional && (
                      <div className="mb-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                        <p className="text-sm text-amber-600 dark:text-amber-400">
                          ⚠️ O endereço não será obrigatório para este cliente.
                        </p>
                      </div>
                    )}

                    <div className={`grid grid-cols-1 md:grid-cols-2 gap-4 ${enderecoOpcional ? 'opacity-60' : ''}`}>
                      <div className="md:col-span-2">
                        <label className="block text-sm font-medium text-foreground mb-1">
                          CEP {!enderecoOpcional && <span className="text-destructive">*</span>}
                        </label>
                        <input
                          type="text"
                          name="endereco.cep"
                          value={formData.endereco.cep}
                          onChange={handleCepChange}
                          placeholder="00000-000"
                          maxLength="9"
                          className={`w-full px-3 py-2 bg-background border rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary ${formErrors['endereco.cep'] ? 'border-destructive' : 'border-input'
                            }`}
                          data-testid="input-cep"
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          Digite o CEP para preencher automaticamente o endereço
                        </p>
                        {formErrors['endereco.cep'] && (
                          <p className="text-destructive text-xs mt-1" data-testid="erro-cep">{formErrors['endereco.cep']}</p>
                        )}
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1">
                          Rua {!enderecoOpcional && <span className="text-destructive">*</span>}
                        </label>
                        <input
                          type="text"
                          name="endereco.rua"
                          value={formData.endereco.rua}
                          onChange={handleChange}
                          className={`w-full px-3 py-2 bg-background border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary ${formErrors['endereco.rua'] ? 'border-destructive' : 'border-input'
                            }`}
                          data-testid="input-rua"
                        />
                        {formErrors['endereco.rua'] && (
                          <p className="text-destructive text-xs mt-1" data-testid="erro-rua">{formErrors['endereco.rua']}</p>
                        )}
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1">
                          Número {!enderecoOpcional && <span className="text-destructive">*</span>}
                        </label>
                        <input
                          type="text"
                          name="endereco.numero"
                          value={formData.endereco.numero}
                          onChange={handleChange}
                          className={`w-full px-3 py-2 bg-background border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary ${formErrors['endereco.numero'] ? 'border-destructive' : 'border-input'
                            }`}
                          data-testid="input-numero"
                        />
                        {formErrors['endereco.numero'] && (
                          <p className="text-destructive text-xs mt-1" data-testid="erro-numero">{formErrors['endereco.numero']}</p>
                        )}
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1">
                          Bairro {!enderecoOpcional && <span className="text-destructive">*</span>}
                        </label>
                        <input
                          type="text"
                          name="endereco.bairro"
                          value={formData.endereco.bairro}
                          onChange={handleChange}
                          className={`w-full px-3 py-2 bg-background border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary ${formErrors['endereco.bairro'] ? 'border-destructive' : 'border-input'
                            }`}
                          data-testid="input-bairro"
                        />
                        {formErrors['endereco.bairro'] && (
                          <p className="text-destructive text-xs mt-1" data-testid="erro-bairro">{formErrors['endereco.bairro']}</p>
                        )}
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1">
                          Cidade {!enderecoOpcional && <span className="text-destructive">*</span>}
                        </label>
                        <input
                          type="text"
                          name="endereco.cidade"
                          value={formData.endereco.cidade}
                          onChange={handleChange}
                          className={`w-full px-3 py-2 bg-background border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary ${formErrors['endereco.cidade'] ? 'border-destructive' : 'border-input'
                            }`}
                          data-testid="input-cidade"
                        />
                        {formErrors['endereco.cidade'] && (
                          <p className="text-destructive text-xs mt-1" data-testid="erro-cidade">{formErrors['endereco.cidade']}</p>
                        )}
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1">
                          Estado {!enderecoOpcional && <span className="text-destructive">*</span>}
                        </label>
                        <input
                          type="text"
                          name="endereco.estado"
                          value={formData.endereco.estado}
                          onChange={handleChange}
                          maxLength="2"
                          placeholder="SP"
                          className={`w-full px-3 py-2 bg-background border rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary ${formErrors['endereco.estado'] ? 'border-destructive' : 'border-input'
                            }`}
                          data-testid="input-estado"
                        />
                        {formErrors['endereco.estado'] && (
                          <p className="text-destructive text-xs mt-1" data-testid="erro-estado">{formErrors['endereco.estado']}</p>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Dados Bancários */}
                  <div>
                    <h3 className="font-semibold text-lg mb-3 text-foreground">Dados Bancários (Opcional)</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1">
                          Banco
                        </label>
                        <input
                          type="text"
                          name="dados_bancarios.banco"
                          value={formData.dados_bancarios.banco}
                          onChange={handleChange}
                          className="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                          data-testid="input-banco"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1">
                          Agência
                        </label>
                        <input
                          type="text"
                          name="dados_bancarios.agencia"
                          value={formData.dados_bancarios.agencia}
                          onChange={handleChange}
                          className="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                          data-testid="input-agencia"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1">
                          Conta
                        </label>
                        <input
                          type="text"
                          name="dados_bancarios.conta"
                          value={formData.dados_bancarios.conta}
                          onChange={handleChange}
                          className="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                          data-testid="input-conta"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-foreground mb-1">
                          Tipo de Conta
                        </label>
                        <select
                          name="dados_bancarios.tipo_conta"
                          value={formData.dados_bancarios.tipo_conta}
                          onChange={handleChange}
                          className="w-full px-3 py-2 bg-background border border-input rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                          data-testid="select-tipo-conta"
                        >
                          <option value="corrente">Corrente</option>
                          <option value="poupanca">Poupança</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end space-x-3 mt-6 pt-6 border-t">
                  <Button
                    type="button"
                    onClick={() => {
                      setShowModal(false);
                      resetForm();
                    }}
                    variant="secondary"
                    testId="cancelar-button"
                  >
                    Cancelar
                  </Button>
                  <Button 
                    type="submit" 
                    variant="primary" 
                    testId="salvar-cliente-button"
                    loading={submitting}
                    disabled={submitting}
                  >
                    {editando ? 'Salvar Alterações' : 'Cadastrar Cliente'}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Detalhes do Cliente */}
      {showDetalhesModal && clienteSelecionado && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50" onClick={() => setShowDetalhesModal(false)}>
          <div className="bg-card rounded-xl border border-border shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="p-4 sm:p-6">
              {/* Header */}
              <div className="flex items-start justify-between mb-6">
                <div>
                  <h2 className="text-xl sm:text-2xl font-display font-bold text-foreground">
                    Detalhes do Cliente
                  </h2>
                  <p className="text-sm text-muted-foreground mt-1">
                    Informações completas do cliente
                  </p>
                </div>
                <button
                  onClick={() => setShowDetalhesModal(false)}
                  className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Dados Pessoais */}
              <div className="space-y-6">
                <div className="border-b border-border pb-4">
                  <h3 className="font-semibold text-base mb-3 text-foreground flex items-center gap-2">
                    <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    Dados Pessoais
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Nome</p>
                      <p className="text-sm font-medium text-foreground">{clienteSelecionado.nome}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">CPF/CNPJ</p>
                      <p className="text-sm font-medium text-foreground">{formatarCpfCnpj(clienteSelecionado.cpf_cnpj)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Telefone</p>
                      <p className="text-sm font-medium text-foreground">{formatarTelefone(clienteSelecionado.telefone)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Email</p>
                      <p className="text-sm font-medium text-foreground">{clienteSelecionado.email || '-'}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Status</p>
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full border ${getStatusColor(clienteSelecionado.status)}`}>
                        {getStatusLabel(clienteSelecionado.status)}
                      </span>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground mb-1">Código Portal</p>
                      {clienteSelecionado.codigo_portal ? (
                        <div className="flex items-center gap-2">
                          <code className="px-2 py-1 bg-muted rounded font-mono text-sm">
                            {clienteSelecionado.codigo_portal}
                          </code>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(clienteSelecionado.codigo_portal);
                              toast({
                                title: "✅ Código Copiado!",
                                description: `Código ${clienteSelecionado.codigo_portal} copiado para a área de transferência.`,
                                variant: "default",
                              });
                            }}
                            className="p-1.5 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded transition"
                            title="Copiar código"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                          </button>
                          {clienteSelecionado.email && (
                            <button
                              onClick={async () => {
                                try {
                                  await clientesAPI.reenviarCodigoPortal(clienteSelecionado.id);
                                  toast({
                                    title: "✅ Email Enviado!",
                                    description: "Código enviado para o email do cliente com sucesso.",
                                    variant: "default",
                                  });
                                } catch (err) {
                                  toast({
                                    title: "❌ Erro",
                                    description: err.response?.data?.detail || err.message,
                                    variant: "destructive",
                                  });
                                }
                              }}
                              className="p-1.5 text-muted-foreground hover:text-blue-600 hover:bg-blue-50 rounded transition"
                              title="Reenviar código por email"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                              </svg>
                            </button>
                          )}
                        </div>
                      ) : (
                        <button
                          onClick={async () => {
                            try {
                              const response = await clientesAPI.gerarCodigoPortal(clienteSelecionado.id);
                              toast({
                                title: "✅ Código Gerado!",
                                description: `Código: ${response.data.codigo}${response.data.email_enviado ? '\nEmail enviado com sucesso!' : '\n(Cliente sem email cadastrado)'}`,
                                variant: "default",
                              });
                              // Recarregar clientes
                              carregarClientes();
                              setShowDetalhesModal(false);
                            } catch (err) {
                              toast({
                                title: "❌ Erro",
                                description: err.response?.data?.detail || err.message,
                                variant: "destructive",
                              });
                            }
                          }}
                          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded transition"
                        >
                          🔑 Gerar Código
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                {/* Endereço */}
                <div className="border-b border-border pb-4">
                  <h3 className="font-semibold text-base mb-3 text-foreground flex items-center gap-2">
                    <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    Endereço
                  </h3>
                  <div className="space-y-2">
                    <p className="text-sm text-foreground">
                      {clienteSelecionado.endereco.rua}, {clienteSelecionado.endereco.numero}
                      {clienteSelecionado.endereco.complemento && ` - ${clienteSelecionado.endereco.complemento}`}
                    </p>
                    <p className="text-sm text-foreground">
                      {clienteSelecionado.endereco.bairro}
                    </p>
                    <p className="text-sm text-foreground">
                      {clienteSelecionado.endereco.cidade} - {clienteSelecionado.endereco.estado}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      CEP: {clienteSelecionado.endereco.cep}
                    </p>
                  </div>
                </div>

                {/* Dados Bancários */}
                {clienteSelecionado.dados_bancarios && (clienteSelecionado.dados_bancarios.banco || clienteSelecionado.dados_bancarios.conta) && (
                  <div className="border-b border-border pb-4">
                    <h3 className="font-semibold text-base mb-3 text-foreground flex items-center gap-2">
                      <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                      </svg>
                      Dados Bancários
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">Banco</p>
                        <p className="text-sm font-medium text-foreground">{clienteSelecionado.dados_bancarios.banco || '-'}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">Tipo de Conta</p>
                        <p className="text-sm font-medium text-foreground capitalize">{clienteSelecionado.dados_bancarios.tipo_conta || '-'}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">Agência</p>
                        <p className="text-sm font-medium text-foreground">{clienteSelecionado.dados_bancarios.agencia || '-'}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground mb-1">Conta</p>
                        <p className="text-sm font-medium text-foreground">{clienteSelecionado.dados_bancarios.conta || '-'}</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Observações */}
                {clienteSelecionado.observacoes && (
                  <div>
                    <h3 className="font-semibold text-base mb-2 text-foreground flex items-center gap-2">
                      <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                      </svg>
                      Observações
                    </h3>
                    <p className="text-sm text-muted-foreground bg-muted/30 p-3 rounded-lg">
                      {clienteSelecionado.observacoes}
                    </p>
                  </div>
                )}
              </div>

              {/* Ações */}
              <div className="mt-6 pt-4 border-t border-border flex flex-col sm:flex-row gap-3">
                <Link
                  to={`/clientes/${clienteSelecionado.id}/emprestimos`}
                  className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition font-medium"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Ver Empréstimos
                </Link>
                <button
                  onClick={() => {
                    setShowDetalhesModal(false);
                    handleEditar(clienteSelecionado);
                  }}
                  className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-muted text-foreground rounded-lg hover:bg-muted/80 transition font-medium"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  Editar
                </button>
                <button
                  onClick={() => setShowDetalhesModal(false)}
                  className="sm:hidden px-4 py-2.5 bg-background border border-border text-foreground rounded-lg hover:bg-muted transition font-medium"
                >
                  Fechar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal de Recuperação de Rascunho */}
      <DraftRecovery
        isOpen={showDraftRecovery}
        onRecover={handleRecoverDraft}
        onDiscard={handleDiscardDraft}
        draftTimestamp={getDraftTimestamp('cliente')}
        title="Rascunho de Cliente Encontrado"
        description="Encontramos um cadastro de cliente que você estava preenchendo."
      />
    </Layout>
  );
};

export default Clientes;
