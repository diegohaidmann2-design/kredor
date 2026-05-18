import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import ErrorMessage from '../components/ErrorMessage';
import Button from '../components/Button';
import { useModal } from '../components/Modal';
import { emprestimosAPI, clientesAPI } from '../api/api';
import { formatarMoeda, formatarData, getStatusColor, getStatusLabel, getMetodoCalculoLabel } from '../utils/formatters';
import { Eye, DollarSign, Trash2, MoreVertical, Plus, Search, Filter, Pencil } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import useAutosave, { useUnsavedChangesWarning } from '../hooks/useAutosave';
import DraftRecovery, { SaveStatusBadge } from '../components/DraftRecovery';
import { getDraftTimestamp } from '../utils/storageUtils';
import NovoEmprestimoModal from '../components/emprestimos/NovoEmprestimoModal';
import EditarEmprestimoModal from '../components/emprestimos/EditarEmprestimoModal';
import DetalhesEmprestimoModal from '../components/emprestimos/DetalhesEmprestimoModal';
import LixeiraEmprestimos from '../components/emprestimos/LixeiraEmprestimos';

const Emprestimos = ({ somenteQuitados = false }) => {
  const [emprestimos, setEmprestimos] = useState([]);
  const [emprestimosFiltrados, setEmprestimosFiltrados] = useState([]);
  const [termoBusca, setTermoBusca] = useState('');
  const [clientes, setClientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showNovoEmprestimo, setShowNovoEmprestimo] = useState(false);
  const [showEditarEmprestimo, setShowEditarEmprestimo] = useState(false);
  const [showDetalhes, setShowDetalhes] = useState(false);
  const [showLixeira, setShowLixeira] = useState(false);
  const [showDraftRecovery, setShowDraftRecovery] = useState(false);
  const [showProrrogarModal, setShowProrrogarModal] = useState(false);
  const [periodosProrrogacao, setPeriodosProrrogacao] = useState(1);
  const [emprestimoSelecionado, setEmprestimoSelecionado] = useState(null);
  const buttonRefs = useRef({});
  const modal = useModal();
  const [formData, setFormData] = useState({
    cliente_id: '',
    valor_principal: '',
    taxa_juros_mensal: '',
    prazo_meses: '',
    metodo_calculo: 'tabela_price',
    periodo_carencia_meses: 0,
    taxa_multa_atraso: 2.0,
    taxa_juros_mora_diario: 0.033,
    periodicidade: 'mensal',
    taxa_juros_semanal: '',
    prazo_semanas: '',
    data_inicio: new Date().toISOString().split('T')[0],
    dia_vencimento: null
  });
  const navigate = useNavigate();
  const user = { role: 'admin', is_owner: true }; // Mock user for testing purposes

  // Sistema de autosave
  const autosave = useAutosave('emprestimo', formData, {
    enabled: showNovoEmprestimo,
    delay: 3000,
    encrypt: false,
  });

  // Aviso ao sair com dados não salvos
  useUnsavedChangesWarning(
    showNovoEmprestimo && autosave.hasUnsavedChanges,
    'Você tem um empréstimo em andamento. Deseja realmente sair?'
  );

  useEffect(() => {
    carregarDados();
  }, [somenteQuitados]); // ✅ Recarregar quando mudar entre ativos/quitados

  // Função para normalizar strings (remove acentos e case)
  const normalizeString = (str) => {
    if (!str || typeof str !== 'string') return '';
    return str
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();
  };

  // Aplicar filtro sempre que emprestimos ou termoBusca mudarem
  useEffect(() => {
    if (!termoBusca.trim()) {
      setEmprestimosFiltrados([...emprestimos]);
      return;
    }

    const termoNormalizado = normalizeString(termoBusca);
    const termoApenasNumeros = termoBusca.replace(/\D/g, '');
    
    const filtrados = emprestimos.filter(emprestimo => {
      // Buscar por nome do cliente
      const clienteNome = getClienteNome(emprestimo.cliente_id);
      const nomeNorm = normalizeString(clienteNome);
      
      // Buscar por valor (apenas números)
      const valorStr = emprestimo.valor_principal.toString().replace(/\D/g, '');
      
      // Buscar por status
      const statusNorm = normalizeString(getStatusLabel(emprestimo.status));
      
      // Buscar por método de cálculo
      const metodoNorm = normalizeString(getMetodoCalculoLabel(emprestimo.metodo_calculo));
      
      const matchNome = nomeNorm.includes(termoNormalizado);
      const matchValor = termoApenasNumeros && valorStr.includes(termoApenasNumeros);
      const matchStatus = statusNorm.includes(termoNormalizado);
      const matchMetodo = metodoNorm.includes(termoNormalizado);
      
      return matchNome || matchValor || matchStatus || matchMetodo;
    });

    setEmprestimosFiltrados([...filtrados]);
  }, [emprestimos, termoBusca, clientes]);

  // Verificar rascunho ao abrir modal
  useEffect(() => {
    if (showNovoEmprestimo && autosave.exists()) {
      setShowDraftRecovery(true);
    }
  }, [showNovoEmprestimo]);

  const carregarDados = async () => {
    try {
      setLoading(true);
      setError('');
      
      // ✅ Chamar API com filtro correto baseado na prop somenteQuitados
      const params = somenteQuitados 
        ? { status: 'quitado' } 
        : { excluir_quitados: true };
      
      const [emprestimosRes, clientesRes] = await Promise.all([
        emprestimosAPI.listar(params),
        clientesAPI.listar()
      ]);
      // A API agora retorna {items: [...], pagination: {...}}
      const empData = emprestimosRes.data;
      const cliData = clientesRes.data;
      const emprestimosData = empData.items || empData;
      setEmprestimos(emprestimosData);
      setEmprestimosFiltrados(emprestimosData); // Inicializa com todos os empréstimos
      setClientes(cliData.items || cliData);
    } catch (err) {
      console.error('Erro ao carregar dados:', err);
      setError('Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
  };

  // Função de busca de empréstimos
  const handleBusca = (termo) => {
    setTermoBusca(termo);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  // Funções de recuperação de rascunho
  const handleRecoverDraft = () => {
    const draft = autosave.restore();
    if (draft) {
      setFormData(draft);
      setShowDraftRecovery(false);
      modal.success('Rascunho Recuperado!', 'Seus dados foram restaurados.');
    }
  };

  const handleDiscardDraft = () => {
    autosave.clear();
    setShowDraftRecovery(false);
  };

  const handleClearDraft = () => {
    if (window.confirm('Deseja limpar o rascunho salvo?')) {
      autosave.clear();
      modal.success('Rascunho Limpo', 'O rascunho foi removido.');
    }
  };

  const resetForm = () => {
    setFormData({
      cliente_id: '',
      valor_principal: '',
      taxa_juros_mensal: '',
      prazo_meses: '',
      metodo_calculo: 'tabela_price',
      periodo_carencia_meses: 0,
      taxa_multa_atraso: 2.0,
      taxa_juros_mora_diario: 0.033,
      data_inicio: new Date().toISOString().split('T')[0]
    });
  };

  const getClienteNome = (clienteId) => {
    const cliente = clientes.find(c => c.id === clienteId);
    return cliente ? cliente.nome : 'N/A';
  };

  const handleExcluir = (emprestimo) => {
    modal.confirm(
      'Excluir Empréstimo',
      `Tem certeza que deseja excluir o empréstimo de ${getClienteNome(emprestimo.cliente_id)}? Esta ação não pode ser desfeita.`,
      async () => {
        try {
          await emprestimosAPI.deletar(emprestimo.id);
          modal.success('Empréstimo Excluído', 'O empréstimo foi excluído com sucesso.');
          carregarDados();
        } catch (err) {
          modal.error('Erro', err.response?.data?.detail || 'Não foi possível excluir o empréstimo.');
        }
      }
    );
  };

  const handleQuitarEmprestimoAberto = async (emprestimo) => {
    modal.confirm(
      'Quitar Empréstimo Aberto',
      `Deseja gerar a parcela final para quitar o empréstimo de ${getClienteNome(emprestimo.cliente_id)}? Será gerada uma parcela com o capital + juros.`,
      async () => {
        try {
          const response = await emprestimosAPI.quitarAberto(emprestimo.id);
          modal.success(
            'Parcela Final Gerada!',
            `Parcela #${response.data.parcela_numero} gerada com sucesso. Valor total: R$ ${response.data.valor_total.toFixed(2)}`
          );
          carregarDados();
        } catch (err) {
          modal.error('Erro', err.response?.data?.detail || 'Não foi possível gerar a parcela final.');
        }
      }
    );
  };

  const handleRegistrarPagamento = (emprestimoId) => {
    navigate(`/emprestimos/${emprestimoId}`);
  };

  const handleAbrirProrrogacao = (emprestimo) => {
    // Validar se empréstimo pode ser prorrogado
    if (emprestimo.metodo_calculo !== 'apenas_juros') {
      modal.info('Prorrogação Não Disponível', 'Apenas empréstimos com método "Apenas Juros" podem ser prorrogados.');
      return;
    }
    
    if (emprestimo.status !== 'ativo' && emprestimo.status !== 'inadimplente') {
      modal.info('Prorrogação Não Disponível', 'Apenas empréstimos ativos ou inadimplentes podem ser prorrogados.');
      return;
    }
    
    setEmprestimoSelecionado(emprestimo);
    setPeriodosProrrogacao(1);
    setShowProrrogarModal(true);
    setMenuAberto(null);
  };

  const handleProrrogar = async () => {
    if (!emprestimoSelecionado) return;
    
    if (periodosProrrogacao < 1) {
      modal.error('Erro', 'Quantidade de períodos deve ser maior que zero.');
      return;
    }
    
    try {
      const response = await emprestimosAPI.prorrogar(emprestimoSelecionado.id, periodosProrrogacao);
      
      setShowProrrogarModal(false);
      modal.success(
        'Empréstimo Prorrogado!',
        `${response.data.mensagem}. ${response.data.novas_parcelas_criadas.length} novas parcelas foram criadas.`
      );
      
      // Recarregar dados
      await carregarDados();
    } catch (err) {
      modal.error('Erro ao Prorrogar', err.response?.data?.detail || 'Não foi possível prorrogar o empréstimo. Tente novamente.');
    }
  };

  // Componente reutilizável do Dropdown Menu de Ações
  const renderAcoesMenu = (emprestimo) => (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition"
          title="Mais ações"
        >
          <MoreVertical className="w-4 h-4" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuItem
          onClick={() => {
            setEmprestimoSelecionado(emprestimo);
            setShowEditarEmprestimo(true);
          }}
          className="flex items-center gap-3 cursor-pointer"
        >
          <Pencil className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium">Editar Empréstimo</span>
        </DropdownMenuItem>
        
        <DropdownMenuItem
          onClick={() => {
            setEmprestimoSelecionado(emprestimo);
            setShowDetalhes(true);
          }}
          className="flex items-center gap-3 cursor-pointer"
        >
          <Eye className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium">Ver Detalhes</span>
        </DropdownMenuItem>
        
        <DropdownMenuItem
          onClick={() => handleRegistrarPagamento(emprestimo.id)}
          className="flex items-center gap-3 cursor-pointer bg-emerald-50/50 dark:bg-emerald-900/10 hover:bg-emerald-50 dark:hover:bg-emerald-900/20"
        >
          <DollarSign className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          <span className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">Registrar Pagamento</span>
        </DropdownMenuItem>
        
        {/* Botão de Prorrogação (só aparece para empréstimos apenas_juros) */}
        {emprestimo.metodo_calculo === 'apenas_juros' && 
         (emprestimo.status === 'ativo' || emprestimo.status === 'inadimplente') && (
          <DropdownMenuItem
            onClick={() => handleAbrirProrrogacao(emprestimo)}
            className="flex items-center gap-3 cursor-pointer hover:bg-primary/10"
            data-testid="btn-prorrogar-menu"
          >
            <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm font-medium">Prorrogar Empréstimo</span>
          </DropdownMenuItem>
        )}
        
        <DropdownMenuItem
          onClick={async () => {
            try {
              const response = await emprestimosAPI.compartilharPDF(emprestimo.id);
              const blob = new Blob([response.data], { type: 'application/pdf' });
              const url = window.URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `emprestimo_${emprestimo.id.substring(0,8)}.pdf`;
              document.body.appendChild(a);
              a.click();
              window.URL.revokeObjectURL(url);
              document.body.removeChild(a);
            } catch (err) {
              console.error('Erro ao gerar PDF:', err);
              alert('Erro ao gerar PDF. Tente novamente.');
            }
          }}
          className="flex items-center gap-3 cursor-pointer"
        >
          <svg className="w-4 h-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
          </svg>
          <span className="text-sm font-medium">Compartilhar PDF</span>
        </DropdownMenuItem>
        
        {emprestimo.sem_prazo && emprestimo.status === 'ativo' && (
          <DropdownMenuItem
            onClick={() => handleQuitarEmprestimoAberto(emprestimo)}
            className="flex items-center gap-3 cursor-pointer border-t"
          >
            <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm font-medium text-emerald-600">Quitar Empréstimo</span>
          </DropdownMenuItem>
        )}
        
        <DropdownMenuItem
          onClick={() => handleExcluir(emprestimo)}
          className="flex items-center gap-3 cursor-pointer hover:bg-destructive/10"
        >
          <Trash2 className="w-4 h-4 text-destructive" />
          <span className="text-sm font-medium text-destructive">Excluir</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );

  if (loading) return <Loading message="Carregando empréstimos..." />;

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-foreground" data-testid="emprestimos-title">
              {somenteQuitados ? 'Empréstimos Quitados' : 'Empréstimos Ativos'}
            </h1>
            <p className="text-muted-foreground mt-1 text-sm sm:base">
              {somenteQuitados ? 'Empréstimos que já foram totalmente pagos' : 'Gerencie empréstimos em andamento'}
            </p>
          </div>

          <div className="grid grid-cols-2 sm:flex gap-2 w-full sm:w-auto">
            {(user?.role === 'admin' || user?.is_owner) && (
              <Button
                variant="outline"
                className="gap-2 text-red-600 border-red-200 hover:bg-red-50 dark:hover:bg-red-900/20 text-xs sm:text-sm px-2 sm:px-4"
                onClick={() => setShowLixeira(true)}
              >
                <Trash2 className="h-4 w-4" />
                Lixeira
              </Button>
            )}

            <Button 
              onClick={() => setShowNovoEmprestimo(true)} 
              className="gap-2 text-xs sm:text-sm px-2 sm:px-4"
            >
              <Plus className="h-4 w-4" />
              Novo Empréstimo
            </Button>
          </div>
        </div>

        {/* Filtros e Busca */}
        {error && <ErrorMessage message={error} onRetry={carregarDados} />}

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
              placeholder="Buscar por cliente, valor, status ou método..."
              className="w-full pl-10 pr-4 py-2.5 bg-background border border-input rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition"
              data-testid="buscar-emprestimo-input"
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
              {emprestimosFiltrados.length === 0 
                ? 'Nenhum empréstimo encontrado' 
                : `${emprestimosFiltrados.length} empréstimo${emprestimosFiltrados.length !== 1 ? 's' : ''} encontrado${emprestimosFiltrados.length !== 1 ? 's' : ''}`
              }
            </p>
          )}
        </div>

        <div className="bg-card rounded-lg border border-border overflow-hidden" data-testid="emprestimos-table-container">
          {emprestimosFiltrados.length === 0 ? (
            <div className="p-8 text-center" data-testid="sem-emprestimos-message">
              <p className="text-muted-foreground">
                {termoBusca ? 'Nenhum empréstimo encontrado com os critérios de busca' : 'Nenhum empréstimo registrado'}
              </p>
            </div>
          ) : (
            <>
              {/* Versão Desktop - Tabela */}
              <div className="hidden md:block overflow-x-auto">
                <table className="min-w-full divide-y divide-border">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Cliente
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Valor Principal
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Total com Juros
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Taxa/Prazo
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Método
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Data Início
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                        Ações
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border" data-testid="emprestimos-table-body">
                    {emprestimosFiltrados.map((emprestimo) => (
                      <tr key={emprestimo.id} data-testid={`emprestimo-row-${emprestimo.id}`} className="hover:bg-muted/50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-foreground">
                            {getClienteNome(emprestimo.cliente_id)}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                          {formatarMoeda(emprestimo.valor_principal)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {emprestimo.sem_prazo ? (
                            <div className="flex flex-col">
                              <span className="text-sm font-semibold text-amber-600">
                                {formatarMoeda(emprestimo.valor_total_com_juros || emprestimo.valor_principal)} ⚡
                              </span>
                              <span className="text-xs text-muted-foreground">
                                Acumulado
                              </span>
                            </div>
                          ) : (
                            <span className="text-sm font-semibold text-emerald-500">
                              {formatarMoeda(emprestimo.valor_total_com_juros)}
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                          {emprestimo.sem_prazo ? (
                            <span className="inline-flex items-center gap-1">
                              <span>🔄</span>
                              <span className="font-medium text-amber-600">Aberto</span>
                            </span>
                          ) : (
                            `${emprestimo.taxa_juros_mensal}% / ${emprestimo.prazo_meses}m`
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                          {getMetodoCalculoLabel(emprestimo.metodo_calculo)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                          {formatarData(emprestimo.data_inicio)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(emprestimo.status)}`}>
                            {getStatusLabel(emprestimo.status)}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            {/* Botão de Pagamento Rápido — oculto para quitados */}
                            {emprestimo.status !== 'quitado' && (
                              <button
                                onClick={() => handleRegistrarPagamento(emprestimo.id)}
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium rounded-md transition-colors shadow-sm"
                                title="Registrar Pagamento"
                                data-testid={`btn-pagar-${emprestimo.id}`}
                              >
                                <DollarSign className="w-4 h-4" />
                                <span className="hidden sm:inline">Pagar</span>
                              </button>
                            )}

                            {/* Menu de Ações */}
                            {renderAcoesMenu(emprestimo)}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Versão Mobile - Cards */}
              <div className="md:hidden divide-y divide-border">
                {emprestimosFiltrados.map((emprestimo) => (
                  <div key={emprestimo.id} className="p-4 hover:bg-muted/50 transition-colors">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-semibold text-foreground text-base">
                          {getClienteNome(emprestimo.cliente_id)}
                        </h3>
                        <span className={`inline-flex mt-1 px-2 py-0.5 text-xs font-semibold rounded-full ${getStatusColor(emprestimo.status)}`}>
                          {getStatusLabel(emprestimo.status)}
                        </span>
                      </div>
                      <div className="flex gap-2">
                        {/* Botão de Pagamento Mobile — oculto para quitados */}
                        {emprestimo.status !== 'quitado' && (
                          <button
                            onClick={() => handleRegistrarPagamento(emprestimo.id)}
                            className="p-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg transition"
                            title="Registrar Pagamento"
                          >
                            <DollarSign className="w-4 h-4" />
                          </button>
                        )}
                        {renderAcoesMenu(emprestimo)}
                      </div>
                    </div>

                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Valor Principal:</span>
                        <span className="font-medium text-foreground">{formatarMoeda(emprestimo.valor_principal)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Total com Juros:</span>
                        {emprestimo.sem_prazo ? (
                          <div className="flex flex-col items-end">
                            <span className="font-semibold text-amber-600">
                              {formatarMoeda(emprestimo.valor_total_com_juros || emprestimo.valor_principal)} ⚡
                            </span>
                            <span className="text-xs text-muted-foreground">Acumulado</span>
                          </div>
                        ) : (
                          <span className="font-semibold text-emerald-500">{formatarMoeda(emprestimo.valor_total_com_juros)}</span>
                        )}
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Taxa/Prazo:</span>
                        {emprestimo.sem_prazo ? (
                          <span className="inline-flex items-center gap-1">
                            <span>🔄</span>
                            <span className="font-medium text-amber-600">Aberto</span>
                          </span>
                        ) : (
                          <span className="text-foreground">{emprestimo.taxa_juros_mensal}% / {emprestimo.prazo_meses}m</span>
                        )}
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Método:</span>
                        <span className="text-foreground">{getMetodoCalculoLabel(emprestimo.metodo_calculo)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Data Início:</span>
                        <span className="text-foreground">{formatarData(emprestimo.data_inicio)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Modal de Criação */}
      <NovoEmprestimoModal
        open={showNovoEmprestimo}
        onOpenChange={setShowNovoEmprestimo}
        onSuccess={carregarDados}
        clientes={clientes}
        formData={formData}
        setFormData={setFormData}
        resetForm={resetForm}
        autosave={autosave}
        showDraftRecovery={showDraftRecovery}
        setShowDraftRecovery={setShowDraftRecovery}
        handleRecoverDraft={handleRecoverDraft}
        handleDiscardDraft={handleDiscardDraft}
        handleClearDraft={handleClearDraft}
      />

      {/* Modal de Recuperação de Rascunho */}
      <DraftRecovery
        isOpen={showDraftRecovery}
        onRecover={handleRecoverDraft}
        onDiscard={handleDiscardDraft}
        draftTimestamp={getDraftTimestamp('emprestimo')}
        title="Rascunho de Empréstimo Encontrado"
        description="Encontramos um empréstimo que você estava criando."
      />
      {emprestimoSelecionado && (
        <EditarEmprestimoModal
          open={showEditarEmprestimo}
          onOpenChange={setShowEditarEmprestimo}
          emprestimo={emprestimoSelecionado}
          onSuccess={carregarDados}
          clientes={clientes}
        />
      )}

      {emprestimoSelecionado && (
        <DetalhesEmprestimoModal
          open={showDetalhes}
          onOpenChange={setShowDetalhes}
          emprestimo={emprestimoSelecionado}
          onUpdate={carregarDados}
        />
      )}

      <LixeiraEmprestimos
        open={showLixeira}
        onOpenChange={setShowLixeira}
        onRestored={carregarDados}
      />

      {/* Modal de Prorrogação */}
      {showProrrogarModal && emprestimoSelecionado && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" data-testid="prorrogar-modal">
          <div className="bg-card rounded-lg border border-border shadow-xl max-w-md w-full">
            <div className="p-6">
              <h2 className="text-2xl font-bold text-foreground mb-4">
                Prorrogar Empréstimo
              </h2>
              
              <div className="mb-4 p-3 bg-muted/50 rounded-lg border border-border">
                <p className="text-sm text-muted-foreground mb-1">
                  <strong>Cliente:</strong> {getClienteNome(emprestimoSelecionado.cliente_id)}
                </p>
                <p className="text-sm text-muted-foreground">
                  <strong>Valor:</strong> {formatarMoeda(emprestimoSelecionado.valor_principal)}
                </p>
              </div>
              
              <div className="mb-6 p-4 bg-primary/10 rounded-lg border border-primary/20">
                <p className="text-sm text-muted-foreground mb-2">
                  <strong>Como funciona:</strong>
                </p>
                <p className="text-sm text-muted-foreground mb-2">
                  • A última parcela (com capital) vira parcela de juros
                </p>
                <p className="text-sm text-muted-foreground mb-2">
                  • Novas parcelas de juros são criadas
                </p>
                <p className="text-sm text-muted-foreground">
                  • Nova última parcela com capital é criada
                </p>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-foreground mb-2">
                  Quantidade de {emprestimoSelecionado.periodicidade === 'semanal' ? 'semanas' : 'meses'} <span className="text-destructive">*</span>
                </label>
                <input
                  type="number"
                  value={periodosProrrogacao}
                  onChange={(e) => setPeriodosProrrogacao(parseInt(e.target.value) || 1)}
                  required
                  min="1"
                  max="12"
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  data-testid="input-periodos-prorrogacao"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Prorrogar por quantos {emprestimoSelecionado.periodicidade === 'semanal' ? 'semanas' : 'meses'}?
                </p>
              </div>

              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowProrrogarModal(false)}
                  className="flex-1"
                >
                  Cancelar
                </Button>
                <Button
                  onClick={handleProrrogar}
                  className="flex-1"
                  data-testid="confirmar-prorrogacao-btn"
                >
                  Confirmar Prorrogação
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

export default Emprestimos;
