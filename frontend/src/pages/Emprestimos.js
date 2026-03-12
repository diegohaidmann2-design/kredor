import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { createPortal } from 'react-dom';
import { motion } from 'framer-motion';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import ErrorMessage from '../components/ErrorMessage';
import Button from '../components/Button';
import { useModal } from '../components/Modal';
import { emprestimosAPI, clientesAPI } from '../api/api';
import { formatarMoeda, formatarData, getStatusColor, getStatusLabel, getMetodoCalculoLabel } from '../utils/formatters';
import { Eye, DollarSign, Trash2, MoreVertical, Plus, Search, Filter, Pencil } from 'lucide-react';
import useAutosave, { useUnsavedChangesWarning } from '../hooks/useAutosave';
import DraftRecovery, { SaveStatusBadge } from '../components/DraftRecovery';
import { getDraftTimestamp } from '../utils/storageUtils';
import NovoEmprestimoModal from '../components/emprestimos/NovoEmprestimoModal';
import EditarEmprestimoModal from '../components/emprestimos/EditarEmprestimoModal';
import DetalhesEmprestimoModal from '../components/emprestimos/DetalhesEmprestimoModal';
import LixeiraEmprestimos from '../components/emprestimos/LixeiraEmprestimos';

const Emprestimos = () => {
  const [emprestimos, setEmprestimos] = useState([]);
  const [clientes, setClientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showNovoEmprestimo, setShowNovoEmprestimo] = useState(false);
  const [showEditarEmprestimo, setShowEditarEmprestimo] = useState(false);
  const [showDetalhes, setShowDetalhes] = useState(false);
  const [showLixeira, setShowLixeira] = useState(false);
  const [showDraftRecovery, setShowDraftRecovery] = useState(false);
  const [emprestimoSelecionado, setEmprestimoSelecionado] = useState(null);
  const [menuAberto, setMenuAberto] = useState(null);
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 });
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
    data_inicio: new Date().toISOString().split('T')[0], // Default hoje
    dia_vencimento: null // null = usar dia da data_inicio, ou especificar 1-31
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
  }, []);

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
      const [emprestimosRes, clientesRes] = await Promise.all([
        emprestimosAPI.listar(),
        clientesAPI.listar()
      ]);
      // A API agora retorna {items: [...], pagination: {...}}
      const empData = emprestimosRes.data;
      const cliData = clientesRes.data;
      setEmprestimos(empData.items || empData);
      setClientes(cliData.items || cliData);
    } catch (err) {
      console.error('Erro ao carregar dados:', err);
      setError('Erro ao carregar dados');
    } finally {
      setLoading(false);
    }
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

  const handleRegistrarPagamento = (emprestimoId) => {
    navigate(`/emprestimos/${emprestimoId}`);
  };

  const handleMenuClick = (emprestimoId, event) => {
    if (menuAberto === emprestimoId) {
      setMenuAberto(null);
      return;
    }

    const button = event.currentTarget;
    const rect = button.getBoundingClientRect();

    // Altura estimada do menu (3 itens * ~40px + padding)
    const MENU_HEIGHT = 150;
    const spaceBelow = window.innerHeight - rect.bottom;

    // Se não houver espaço suficiente abaixo, mostre acima
    const showAbove = spaceBelow < MENU_HEIGHT;

    // Mobile adjustment: Ensure menu doesn't go off-screen right
    let leftPos = rect.right - 192; // Default align right (menu width is w-48 = 12rem = 192px)
    
    // Se o menu sair pela esquerda, alinhe à esquerda do botão
    if (leftPos < 10) {
      leftPos = rect.left;
    }
    
    // Se ainda assim sair pela direita (em telas muito pequenas), alinhe com uma margem
    if (leftPos + 192 > window.innerWidth) {
      leftPos = window.innerWidth - 202; // 192px + 10px margin
    }

    setMenuPosition({
      top: showAbove ? rect.top - 150 : rect.bottom + 4,
      left: Math.max(10, leftPos),
      placement: showAbove ? 'top' : 'bottom'
    });

    setMenuAberto(emprestimoId);
  };

  if (loading) return <Loading message="Carregando empréstimos..." />;

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-foreground" data-testid="emprestimos-title">Empréstimos</h1>
            <p className="text-muted-foreground mt-1 text-sm sm:base">Gerencie todos os empréstimos</p>
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

        <div className="bg-card rounded-lg border border-border overflow-hidden" data-testid="emprestimos-table-container">
          {emprestimos.length === 0 ? (
            <div className="p-8 text-center" data-testid="sem-emprestimos-message">
              <p className="text-muted-foreground">Nenhum empréstimo registrado</p>
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
                    {emprestimos.map((emprestimo) => (
                      <tr key={emprestimo.id} data-testid={`emprestimo-row-${emprestimo.id}`} className="hover:bg-muted/50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-foreground">
                            {getClienteNome(emprestimo.cliente_id)}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                          {formatarMoeda(emprestimo.valor_principal)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-emerald-500">
                          {formatarMoeda(emprestimo.valor_total_com_juros)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                          {emprestimo.taxa_juros_mensal}% / {emprestimo.prazo_meses}m
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
                          <button
                            onClick={(e) => handleMenuClick(emprestimo.id, e)}
                            className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition"
                            title="Mais ações"
                          >
                            <MoreVertical className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Versão Mobile - Cards */}
              <div className="md:hidden divide-y divide-border">
                {emprestimos.map((emprestimo) => (
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
                      <button
                        onClick={(e) => handleMenuClick(emprestimo.id, e)}
                        className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition"
                        title="Mais ações"
                      >
                        <MoreVertical className="w-4 h-4" />
                      </button>
                    </div>

                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Valor Principal:</span>
                        <span className="font-medium text-foreground">{formatarMoeda(emprestimo.valor_principal)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Total com Juros:</span>
                        <span className="font-semibold text-emerald-500">{formatarMoeda(emprestimo.valor_total_com_juros)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Taxa/Prazo:</span>
                        <span className="text-foreground">{emprestimo.taxa_juros_mensal}% / {emprestimo.prazo_meses}m</span>
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

      {/* Menu Dropdown com Portal */}
      {menuAberto && createPortal(
        <>
          <div
            className="fixed inset-0 z-[100]"
            onClick={() => setMenuAberto(null)}
          />
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              position: 'fixed',
              top: `${menuPosition.top}px`,
              left: `${menuPosition.left}px`,
            }}
            className="w-48 bg-card border border-border rounded-lg shadow-lg z-[101] overflow-hidden"
          >
            <button
              onClick={() => {
                const emprestimo = emprestimos.find(e => e.id === menuAberto);
                if (emprestimo) {
                  setEmprestimoSelecionado(emprestimo);
                  setShowEditarEmprestimo(true);
                }
                setMenuAberto(null);
              }}
              className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-accent transition-colors"
            >
              <Pencil className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">Editar Empréstimo</span>
            </button>
            <button
              onClick={() => {
                const emprestimo = emprestimos.find(e => e.id === menuAberto);
                if (emprestimo) {
                  setEmprestimoSelecionado(emprestimo);
                  setShowDetalhes(true);
                }
                setMenuAberto(null);
              }}
              className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-accent transition-colors"
            >
              <Eye className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">Ver Detalhes</span>
            </button>
            <button
              onClick={() => {
                handleRegistrarPagamento(menuAberto);
                setMenuAberto(null);
              }}
              className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-accent transition-colors"
            >
              <DollarSign className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium text-foreground">Registrar Pagamento</span>
            </button>
            <button
              onClick={() => {
                const emprestimo = emprestimos.find(e => e.id === menuAberto);
                if (emprestimo) handleExcluir(emprestimo);
                setMenuAberto(null);
              }}
              className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-destructive/10 transition-colors"
            >
              <Trash2 className="w-4 h-4 text-destructive" />
              <span className="text-sm font-medium text-destructive">Excluir</span>
            </button>
          </motion.div>
        </>,
        document.body
      )}

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
    </Layout>
  );
};

export default Emprestimos;
