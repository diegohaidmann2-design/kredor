import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import Button from '../components/Button';
import { useModal } from '../components/Modal';
import { emprestimosAPI, clientesAPI, contratosAPI } from '../api/api';
import { formatarMoeda, formatarData } from '../utils/formatters';
import { toast } from '../hooks/use-toast';
import { FileText, ShieldCheck, PenLine, Check, ArrowRight } from 'lucide-react';

const Contratos = () => {
  const [emprestimos, setEmprestimos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [gerando, setGerando] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [emprestimoSelecionado, setEmprestimoSelecionado] = useState(null);
  const [templateSelecionado, setTemplateSelecionado] = useState('padrao');
  const [clausulasAdicionais, setClausulasAdicionais] = useState('');
  const [filtroStatus, setFiltroStatus] = useState('');
  const [modalTipo, setModalTipo] = useState('emprestimo'); // 'emprestimo' ou 'template'
  const modal = useModal();

  const carregarEmprestimos = useCallback(async () => {
    try {
      setLoading(true);
      const response = await emprestimosAPI.listar();
      // A API agora retorna {items: [...], pagination: {...}}
      const empData = response.data.items || response.data;
      const emprestimosComCliente = await Promise.all(
        empData.map(async (emp) => {
          try {
            const cliente = await clientesAPI.obter(emp.cliente_id);
            return { ...emp, cliente_nome: cliente.data.nome, cliente_cpf: cliente.data.cpf_cnpj };
          } catch {
            return { ...emp, cliente_nome: 'Cliente não encontrado', cliente_cpf: '-' };
          }
        })
      );
      setEmprestimos(emprestimosComCliente);
    } catch (err) {
      toast({ title: 'Erro', description: "Não foi possível carregar empréstimos.", variant: 'destructive' });
      console.error('Erro ao carregar empréstimos:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    carregarEmprestimos();
  }, [carregarEmprestimos]);

  const abrirModalTemplate = (template, emprestimo = null) => {
    setTemplateSelecionado(template);
    setModalTipo('template');
    setEmprestimoSelecionado(emprestimo);
    setClausulasAdicionais('');
    setShowModal(true);
  };

  const abrirModalContrato = async (emprestimo) => {
    setEmprestimoSelecionado(emprestimo);
    setTemplateSelecionado('padrao');
    setClausulasAdicionais('');
    setModalTipo('emprestimo');
    setShowModal(true);
  };

  const selecionarEmprestimoNoModal = (emprestimo) => {
    setEmprestimoSelecionado(emprestimo);
  };

  const gerarContrato = async () => {
    if (!emprestimoSelecionado) {
      modal.warning('Empréstimo não selecionado', 'Por favor, selecione um empréstimo para gerar o contrato.');
      return;
    }

    try {
      setGerando(emprestimoSelecionado.id);

      const payload = {
        emprestimo_id: emprestimoSelecionado.id,
        template: templateSelecionado
      };

      if (templateSelecionado === 'personalizado' && clausulasAdicionais.trim()) {
        payload.clausulas_adicionais = clausulasAdicionais;
      }

      const response = await contratosAPI.gerar(payload);

      // Download do PDF
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `contrato_${templateSelecionado}_${emprestimoSelecionado.cliente_nome.replace(/\s+/g, '_')}_${emprestimoSelecionado.id.substring(0, 8)}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      setShowModal(false);
      modal.success('Contrato Gerado!', 'O contrato foi gerado e o download iniciou automaticamente.');
    } catch (err) {
      console.error('Erro ao gerar contrato:', err);
      if (err.response && err.response.status === 403) {
        modal.warning(
          'Funcionalidade indisponível no seu plano',
          'A geração de contratos em PDF é um recurso exclusivo dos planos pagos. Atualize seu plano para ter acesso a este e outros recursos avançados.'
        );
      } else {
        modal.error('Erro ao gerar contrato', 'Não foi possível gerar o contrato. Tente novamente.');
      }
    } finally {
      setGerando(null);
    }
  };

  const gerarContratoRapido = async (emprestimo, template = 'padrao') => {
    try {
      setGerando(emprestimo.id);

      const response = await contratosAPI.gerar({
        emprestimo_id: emprestimo.id,
        template: template
      });

      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `contrato_${template}_${emprestimo.cliente_nome.replace(/\s+/g, '_')}_${emprestimo.id.substring(0, 8)}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      modal.success('Contrato Gerado!', 'O download do contrato PDF iniciou automaticamente.');
    } catch (err) {
      console.error('Erro ao gerar contrato:', err);
      if (err.response && err.response.status === 403) {
        modal.warning(
          'Funcionalidade indisponível no seu plano',
          'A geração de contratos em PDF é um recurso exclusivo dos planos pagos. Atualize seu plano para desbloquear.'
        );
      } else {
        modal.error('Erro ao gerar contrato', 'Não foi possível gerar o contrato. Tente novamente.');
      }
    } finally {
      setGerando(null);
    }
  };

  const emprestimosFiltrados = emprestimos.filter(emp => {
    if (!filtroStatus) return true;
    return emp.status === filtroStatus;
  });

  const getMetodoNome = (metodo) => {
    const nomes = {
      'simples': 'Juros Simples',
      'composto': 'Juros Compostos',
      'price': 'Tabela Price',
      'sac': 'SAC'
    };
    return nomes[metodo] || metodo;
  };

  const getTemplateNome = (template) => {
    const nomes = {
      'padrao': 'Contrato Padrão',
      'garantia': 'Contrato com Garantia',
      'personalizado': 'Contrato Personalizado'
    };
    return nomes[template] || template;
  };

  if (loading) return <Loading message="Carregando empréstimos..." />;

  return (
    <Layout>
      <div className="container mx-auto px-4 sm:px-6 py-8 font-satoshi">
        <div className="mb-8">
          <h1 className="font-cabinet font-black text-3xl sm:text-4xl tracking-tighter text-foreground" data-testid="contratos-title">
            Contratos
          </h1>
          <p className="text-muted-foreground mt-1.5">Gere contratos profissionais em PDF para seus empréstimos</p>
        </div>

        {/* Templates */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {/* Template Padrão */}
          <div
            onClick={() => abrirModalTemplate('padrao')}
            className="bg-card rounded-xl ring-1 ring-emerald-500/30 hover:ring-emerald-500 p-6 cursor-pointer transition-all duration-200 hover:-translate-y-px group"
          >
            <div className="flex items-center justify-between mb-4">
              <span className="flex items-center justify-center w-11 h-11 rounded-md bg-emerald-500/10 text-emerald-400"><FileText className="w-5 h-5" strokeWidth={1.5} /></span>
              <span className="inline-flex items-center rounded-md ring-1 ring-inset ring-emerald-500/20 bg-emerald-500/10 text-emerald-500 text-xs font-medium uppercase tracking-wider px-2 py-0.5">Modelo Padrão</span>
            </div>
            <h3 className="font-cabinet font-bold text-lg mb-2 text-foreground group-hover:text-primary transition-colors">Contrato Padrão</h3>
            <p className="text-sm text-muted-foreground mb-4">Modelo básico com todas as cláusulas essenciais de empréstimo</p>
            <ul className="text-sm text-muted-foreground mb-4 space-y-1.5">
              <li className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-500 shrink-0" strokeWidth={2} /> Dados das partes</li>
              <li className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-500 shrink-0" strokeWidth={2} /> Condições do empréstimo</li>
              <li className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-500 shrink-0" strokeWidth={2} /> Tabela de parcelas</li>
              <li className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-500 shrink-0" strokeWidth={2} /> Multa e juros de mora</li>
            </ul>
            <div className="inline-flex items-center gap-1.5 text-xs text-primary font-medium opacity-0 group-hover:opacity-100 transition-opacity">
              Clique para selecionar <ArrowRight className="w-3.5 h-3.5" strokeWidth={1.5} />
            </div>
          </div>

          {/* Template Garantia */}
          <div
            onClick={() => abrirModalTemplate('garantia')}
            className="bg-card rounded-xl ring-1 ring-border hover:ring-emerald-500 p-6 cursor-pointer transition-all duration-200 hover:-translate-y-px group"
          >
            <span className="flex items-center justify-center w-11 h-11 rounded-md bg-muted text-muted-foreground mb-4"><ShieldCheck className="w-5 h-5" strokeWidth={1.5} /></span>
            <h3 className="font-cabinet font-bold text-lg mb-2 text-foreground group-hover:text-primary transition-colors">Contrato com Garantia</h3>
            <p className="text-sm text-muted-foreground mb-4">Inclui cláusulas específicas para garantias oferecidas</p>
            <ul className="text-sm text-muted-foreground mb-4 space-y-1.5">
              <li className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-500 shrink-0" strokeWidth={2} /> Tudo do padrão</li>
              <li className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-500 shrink-0" strokeWidth={2} /> Cláusula de garantia</li>
              <li className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-500 shrink-0" strokeWidth={2} /> Execução da garantia</li>
            </ul>
            <div className="inline-flex items-center gap-1.5 text-xs text-primary font-medium opacity-0 group-hover:opacity-100 transition-opacity">
              Clique para selecionar <ArrowRight className="w-3.5 h-3.5" strokeWidth={1.5} />
            </div>
          </div>

          {/* Template Personalizado */}
          <div
            onClick={() => abrirModalTemplate('personalizado')}
            className="bg-card rounded-xl ring-1 ring-border hover:ring-emerald-500 p-6 cursor-pointer transition-all duration-200 hover:-translate-y-px group"
          >
            <span className="flex items-center justify-center w-11 h-11 rounded-md bg-muted text-muted-foreground mb-4"><PenLine className="w-5 h-5" strokeWidth={1.5} /></span>
            <h3 className="font-cabinet font-bold text-lg mb-2 text-foreground group-hover:text-primary transition-colors">Personalizado</h3>
            <p className="text-sm text-muted-foreground mb-4">Crie seu próprio modelo de contrato</p>
            <ul className="text-sm text-muted-foreground mb-4 space-y-1.5">
              <li className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-500 shrink-0" strokeWidth={2} /> Tudo do padrão</li>
              <li className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-500 shrink-0" strokeWidth={2} /> Cláusulas especiais</li>
              <li className="flex items-center gap-2"><Check className="w-4 h-4 text-emerald-500 shrink-0" strokeWidth={2} /> Flexibilidade total</li>
            </ul>
            <div className="inline-flex items-center gap-1.5 text-xs text-primary font-medium opacity-0 group-hover:opacity-100 transition-opacity">
              Clique para selecionar <ArrowRight className="w-3.5 h-3.5" strokeWidth={1.5} />
            </div>
          </div>
        </div>

        {/* Filtros */}
        <div className="bg-card rounded-lg shadow-md p-4 mb-6">
          <div className="flex flex-wrap items-center gap-4">
            <span className="text-sm font-medium text-foreground">Filtrar por status:</span>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setFiltroStatus('')}
                className={`px-3 py-1 rounded-full text-sm transition ${filtroStatus === '' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-muted/80'
                  }`}
              >
                Todos ({emprestimos.length})
              </button>
              <button
                onClick={() => setFiltroStatus('ativo')}
                className={`px-3 py-1 rounded-full text-sm transition ${filtroStatus === 'ativo' ? 'bg-green-600 text-white' : 'bg-muted text-muted-foreground hover:bg-muted/80'
                  }`}
              >
                Ativos ({emprestimos.filter(e => e.status === 'ativo').length})
              </button>
              <button
                onClick={() => setFiltroStatus('quitado')}
                className={`px-3 py-1 rounded-full text-sm transition ${filtroStatus === 'quitado' ? 'bg-blue-600 text-white' : 'bg-muted text-muted-foreground hover:bg-muted/80'
                  }`}
              >
                Quitados ({emprestimos.filter(e => e.status === 'quitado').length})
              </button>
            </div>
          </div>
        </div>

        {/* Lista de Empréstimos */}
        <div className="bg-card rounded-lg shadow-md overflow-hidden">
          <div className="px-4 md:px-6 py-4 border-b border-border bg-muted/50">
            <h2 className="text-xl font-bold text-foreground">Gerar Contrato por Empréstimo</h2>
            <p className="text-sm text-muted-foreground">Selecione um empréstimo para gerar o contrato em PDF</p>
          </div>

          {emprestimosFiltrados.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              <p>Nenhum empréstimo encontrado</p>
            </div>
          ) : (
            <>
              {/* Versão Desktop - Tabela */}
              <div className="hidden md:block overflow-x-auto">
                <table className="min-w-full divide-y divide-border">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Cliente</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Valor</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Método</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Data</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="bg-card divide-y divide-border">
                    {emprestimosFiltrados.map((emp) => (
                      <tr key={emp.id} className="hover:bg-muted/50">
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-foreground">{emp.cliente_nome}</div>
                          <div className="text-xs text-muted-foreground">{emp.cliente_cpf}</div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-foreground">{formatarMoeda(emp.valor_principal)}</div>
                          <div className="text-xs text-muted-foreground">{emp.prazo_meses}x de {formatarMoeda(emp.valor_total_com_juros / emp.prazo_meses)}</div>
                        </td>
                        <td className="px-6 py-4 text-sm text-muted-foreground">
                          {getMetodoNome(emp.metodo_calculo)}
                        </td>
                        <td className="px-6 py-4">
                          <span className={`px-2 py-1 text-xs font-semibold rounded-full ${emp.status === 'ativo' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
                              emp.status === 'quitado' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400' :
                                'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400'
                            }`}>
                            {emp.status?.toUpperCase()}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm text-muted-foreground">
                          {formatarData(emp.data_inicio)}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex space-x-2">
                            <button
                              onClick={() => gerarContratoRapido(emp, 'padrao')}
                              disabled={gerando === emp.id}
                              className="inline-flex items-center px-3 py-1 bg-primary hover:bg-primary/90 text-primary-foreground text-sm rounded transition disabled:opacity-50"
                              data-testid={`gerar-contrato-${emp.id}`}
                            >
                              {gerando === emp.id ? (
                                <>
                                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                  </svg>
                                  Gerando...
                                </>
                              ) : (
                                <>
                                  <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M6 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0015.414 6L12 2.586A2 2 0 0010.586 2H6zm5 6a1 1 0 10-2 0v3.586l-1.293-1.293a1 1 0 10-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 11.586V8z" clipRule="evenodd" />
                                  </svg>
                                  PDF
                                </>
                              )}
                            </button>
                            <button
                              onClick={() => abrirModalTemplate('', emp)}
                              className="inline-flex items-center px-3 py-1 bg-muted hover:bg-muted/80 text-foreground text-sm rounded transition"
                            >
                              <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                              </svg>
                              Escolher
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Versão Mobile - Cards */}
              <div className="md:hidden divide-y divide-border">
                {emprestimosFiltrados.map((emp) => (
                  <div key={emp.id} className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-semibold text-foreground text-base">{emp.cliente_nome}</h3>
                        <p className="text-xs text-muted-foreground mt-0.5">{emp.cliente_cpf}</p>
                        <span className={`inline-flex mt-2 px-2 py-0.5 text-xs font-semibold rounded-full ${emp.status === 'ativo' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
                            emp.status === 'quitado' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400' :
                              'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400'
                          }`}>
                          {emp.status?.toUpperCase()}
                        </span>
                      </div>
                    </div>

                    <div className="space-y-2 text-sm mb-3">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Valor:</span>
                        <div className="text-right">
                          <div className="font-medium text-foreground">{formatarMoeda(emp.valor_principal)}</div>
                          <div className="text-xs text-muted-foreground">{emp.prazo_meses}x de {formatarMoeda(emp.valor_total_com_juros / emp.prazo_meses)}</div>
                        </div>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Método:</span>
                        <span className="text-foreground">{getMetodoNome(emp.metodo_calculo)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Data:</span>
                        <span className="text-foreground">{formatarData(emp.data_inicio)}</span>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <button
                        onClick={() => gerarContratoRapido(emp, 'padrao')}
                        disabled={gerando === emp.id}
                        className="inline-flex items-center justify-center px-3 py-2 bg-primary hover:bg-primary/90 text-primary-foreground text-sm rounded transition disabled:opacity-50"
                        data-testid={`gerar-contrato-${emp.id}`}
                      >
                        {gerando === emp.id ? (
                          <>
                            <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Gerando...
                          </>
                        ) : (
                          <>
                            <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M6 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0015.414 6L12 2.586A2 2 0 0010.586 2H6zm5 6a1 1 0 10-2 0v3.586l-1.293-1.293a1 1 0 10-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 11.586V8z" clipRule="evenodd" />
                            </svg>
                            PDF
                          </>
                        )}
                      </button>
                      <button
                        onClick={() => abrirModalTemplate('', emp)}
                        className="inline-flex items-center justify-center px-3 py-2 bg-muted hover:bg-muted/80 text-foreground text-sm rounded transition"
                      >
                        <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                        </svg>
                        Escolher
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Info box */}
        <div className="mt-6 bg-primary/10 border border-primary/20 rounded-lg p-4">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-primary mr-3 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
            <div>
              <h4 className="font-semibold text-primary">Dica</h4>
              <p className="text-sm text-foreground/80">
                O contrato gerado inclui todas as informações do empréstimo, dados do cliente, tabela de parcelas e cláusulas padrão.
                Recomendamos imprimir em 2 vias para assinatura de ambas as partes.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Modal de Opções */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-card rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h2 className="text-2xl font-bold text-foreground">
                    {modalTipo === 'template' ? getTemplateNome(templateSelecionado) : 'Gerar Contrato'}
                  </h2>
                  <p className="text-muted-foreground">
                    {emprestimoSelecionado ? emprestimoSelecionado.cliente_nome : 'Selecione um empréstimo'}
                  </p>
                </div>
                <button
                  onClick={() => setShowModal(false)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>

              {/* Se veio pelo card de template, mostrar lista de empréstimos para selecionar */}
              {modalTipo === 'template' && (
                <div className="mb-6">
                  <h3 className="font-semibold text-foreground mb-3">Selecione o Empréstimo</h3>
                  {emprestimos.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <p>Nenhum empréstimo cadastrado.</p>
                      <p className="text-sm mt-2">Cadastre um empréstimo primeiro para gerar contratos.</p>
                    </div>
                  ) : (
                    <div className="max-h-48 overflow-y-auto border border-border rounded-lg">
                      {emprestimos.map((emp) => (
                        <div
                          key={emp.id}
                          onClick={() => selecionarEmprestimoNoModal(emp)}
                          className={`p-3 cursor-pointer border-b border-border last:border-b-0 transition ${emprestimoSelecionado?.id === emp.id
                              ? 'bg-primary/10 border-l-4 border-l-primary'
                              : 'hover:bg-muted/50'
                            }`}
                        >
                          <div className="flex justify-between items-center">
                            <div>
                              <div className="font-medium text-foreground">{emp.cliente_nome}</div>
                              <div className="text-xs text-muted-foreground">{emp.cliente_cpf}</div>
                            </div>
                            <div className="text-right">
                              <div className="font-medium text-foreground">{formatarMoeda(emp.valor_principal)}</div>
                              <div className="text-xs text-muted-foreground">{emp.prazo_meses}x</div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Resumo do Empréstimo (se selecionado) */}
              {emprestimoSelecionado && (
                <div className="bg-muted/50 rounded-lg p-4 mb-6">
                  <h3 className="font-semibold text-foreground mb-3">Resumo do Empréstimo</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Valor Principal:</span>
                      <span className="ml-2 font-medium text-foreground">{formatarMoeda(emprestimoSelecionado.valor_principal)}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Prazo:</span>
                      <span className="ml-2 font-medium text-foreground">{emprestimoSelecionado.prazo_meses} meses</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Taxa:</span>
                      <span className="ml-2 font-medium text-foreground">{emprestimoSelecionado.taxa_juros_mensal}% a.m.</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Total:</span>
                      <span className="ml-2 font-medium text-foreground">{formatarMoeda(emprestimoSelecionado.valor_total_com_juros)}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Seleção de Template (se veio pelo botão Opções) */}
              {modalTipo === 'emprestimo' && (
                <div className="mb-6">
                  <h3 className="font-semibold text-foreground mb-3">Selecione o Template</h3>
                  <div className="grid grid-cols-3 gap-4">
                    <button
                      onClick={() => setTemplateSelecionado('padrao')}
                      className={`p-4 border-2 rounded-lg text-left transition ${templateSelecionado === 'padrao'
                          ? 'border-primary bg-primary/10'
                          : 'border-border hover:border-muted-foreground'
                        }`}
                    >
                      <FileText className="w-6 h-6 text-emerald-400 mb-2" strokeWidth={1.5} />
                      <div className="font-medium text-foreground">Padrão</div>
                      <div className="text-xs text-muted-foreground">Cláusulas essenciais</div>
                    </button>
                    <button
                      onClick={() => setTemplateSelecionado('garantia')}
                      className={`p-4 border-2 rounded-lg text-left transition ${templateSelecionado === 'garantia'
                          ? 'border-primary bg-primary/10'
                          : 'border-border hover:border-muted-foreground'
                        }`}
                    >
                      <ShieldCheck className="w-6 h-6 text-emerald-400 mb-2" strokeWidth={1.5} />
                      <div className="font-medium text-foreground">Garantia</div>
                      <div className="text-xs text-muted-foreground">Com cláusula de garantia</div>
                    </button>
                    <button
                      onClick={() => setTemplateSelecionado('personalizado')}
                      className={`p-4 border-2 rounded-lg text-left transition ${templateSelecionado === 'personalizado'
                          ? 'border-primary bg-primary/10'
                          : 'border-border hover:border-muted-foreground'
                        }`}
                    >
                      <PenLine className="w-6 h-6 text-emerald-400 mb-2" strokeWidth={1.5} />
                      <div className="font-medium text-foreground">Personalizado</div>
                      <div className="text-xs text-muted-foreground">Cláusulas especiais</div>
                    </button>
                  </div>
                </div>
              )}

              {/* Campo de cláusulas adicionais (para template personalizado) */}
              {templateSelecionado === 'personalizado' && (
                <div className="mb-6">
                  <h3 className="font-semibold text-foreground mb-3">Cláusulas Especiais (opcional)</h3>
                  <textarea
                    value={clausulasAdicionais}
                    onChange={(e) => setClausulasAdicionais(e.target.value)}
                    placeholder="Digite aqui as cláusulas especiais que deseja incluir no contrato..."
                    className="w-full h-32 px-3 py-2 border border-border rounded-lg bg-background text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    As cláusulas digitadas serão incluídas no contrato após as cláusulas padrão.
                  </p>
                </div>
              )}

              {/* Info do template selecionado */}
              <div className="bg-muted/30 rounded-lg p-4 mb-6">
                <div className="flex items-start">
                  <div className="mr-3 shrink-0">
                    {templateSelecionado === 'padrao' && <FileText className="w-6 h-6 text-emerald-400" strokeWidth={1.5} />}
                    {templateSelecionado === 'garantia' && <ShieldCheck className="w-6 h-6 text-emerald-400" strokeWidth={1.5} />}
                    {templateSelecionado === 'personalizado' && <PenLine className="w-6 h-6 text-emerald-400" strokeWidth={1.5} />}
                  </div>
                  <div>
                    <h4 className="font-semibold text-foreground">{getTemplateNome(templateSelecionado)}</h4>
                    <p className="text-sm text-muted-foreground">
                      {templateSelecionado === 'padrao' && 'Modelo básico com dados das partes, condições do empréstimo, tabela de parcelas e cláusulas de mora.'}
                      {templateSelecionado === 'garantia' && 'Inclui tudo do padrão mais cláusulas específicas de garantia e execução da garantia.'}
                      {templateSelecionado === 'personalizado' && 'Modelo flexível com espaço para cláusulas especiais definidas por você.'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Botões */}
              <div className="flex justify-end space-x-3 pt-4 border-t border-border">
                <Button
                  onClick={() => setShowModal(false)}
                  variant="secondary"
                >
                  Cancelar
                </Button>
                <Button
                  onClick={gerarContrato}
                  variant="primary"
                  disabled={gerando || !emprestimoSelecionado}
                  testId="confirmar-gerar-contrato"
                >
                  {gerando ? 'Gerando...' : 'Gerar Contrato PDF'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

export default Contratos;
