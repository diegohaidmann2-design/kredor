import React, { useState } from 'react';
import Layout from '../components/Layout';
import Button from '../components/Button';
import { useModal } from '../components/Modal';
import { relatoriosAPI } from '../api/api';
import { toast } from '../hooks/use-toast';

const Relatorios = () => {
  const [tipoRelatorio, setTipoRelatorio] = useState('emprestimos');
  const [formato, setFormato] = useState('pdf');
  const [periodo, setPeriodo] = useState('mes');
  const [dataInicio, setDataInicio] = useState('');
  const [dataFim, setDataFim] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const modal = useModal();

  const handleGerar = async () => {
    try {
      setLoading(true);
      setError('');
      
      const data = {
        tipo: tipoRelatorio,
        formato: formato,
        periodo: periodo,
        data_inicio: periodo === 'personalizado' ? dataInicio : null,
        data_fim: periodo === 'personalizado' ? dataFim : null
      };

      const response = await relatoriosAPI.gerar(data);
      
      const blob = new Blob([response.data], {
        type: formato === 'pdf' 
          ? 'application/pdf' 
          : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `relatorio_${tipoRelatorio}_${new Date().toISOString().split('T')[0]}.${formato === 'pdf' ? 'pdf' : 'xlsx'}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      modal.success('Relatório Gerado!', 'O download do relatório iniciou automaticamente.');
      
    } catch (err) {
      toast({ title: 'Erro', description: "Não foi possível gerar relatório.", variant: 'destructive' });
      console.error('Erro ao gerar relatório:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Erro ao gerar relatório. Tente novamente.';
      modal.error('Erro ao gerar relatório', typeof errorMsg === 'string' ? errorMsg : 'Erro ao gerar relatório');
    } finally {
      setLoading(false);
    }
  };

  const handleRelatorioRapido = async (tipo) => {
    setTipoRelatorio(tipo);
    setPeriodo('mes');
    setFormato('pdf');
    
    try {
      setLoading(true);
      setError('');
      
      const response = await relatoriosAPI.gerar({
        tipo: tipo,
        formato: 'pdf',
        periodo: 'mes'
      });
      
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `relatorio_${tipo}_${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
    } catch (err) {
      toast({ title: 'Erro', description: "Não foi possível gerar relatório.", variant: 'destructive' });
      console.error('Erro ao gerar relatório:', err);
      const errorMsg = err.response?.data?.detail || 'Erro ao gerar relatório. Tente novamente.';
      setError(typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground" data-testid="relatorios-title">
            Relatórios
          </h1>
          <p className="text-muted-foreground mt-1">Gere relatórios personalizados em PDF ou Excel</p>
        </div>

        {error && (
          <div className="mb-6 bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg" data-testid="error-message">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Configuração */}
          <div className="bg-card rounded-lg border border-border p-6" data-testid="config-relatorio">
            <h2 className="text-xl font-bold text-foreground mb-6">Configurar Relatório</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Tipo de Relatório
                </label>
                <select
                  value={tipoRelatorio}
                  onChange={(e) => setTipoRelatorio(e.target.value)}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  data-testid="select-tipo-relatorio"
                >
                  <option value="emprestimos">Empréstimos</option>
                  <option value="pagamentos">Pagamentos</option>
                  <option value="clientes">Clientes</option>
                  <option value="inadimplencia">Inadimplência</option>
                  <option value="fluxo_caixa">Fluxo de Caixa</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Formato
                </label>
                <div className="flex space-x-4">
                  <label className="flex items-center cursor-pointer">
                    <input
                      type="radio"
                      name="formato"
                      value="pdf"
                      checked={formato === 'pdf'}
                      onChange={(e) => setFormato(e.target.value)}
                      className="mr-2"
                      data-testid="formato-pdf"
                    />
                    <span className="flex items-center text-foreground">
                      <svg className="w-5 h-5 mr-1 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                      </svg>
                      PDF
                    </span>
                  </label>
                  <label className="flex items-center cursor-pointer">
                    <input
                      type="radio"
                      name="formato"
                      value="excel"
                      checked={formato === 'excel'}
                      onChange={(e) => setFormato(e.target.value)}
                      className="mr-2"
                      data-testid="formato-excel"
                    />
                    <span className="flex items-center text-foreground">
                      <svg className="w-5 h-5 mr-1 text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                      </svg>
                      Excel
                    </span>
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Período
                </label>
                <select
                  value={periodo}
                  onChange={(e) => setPeriodo(e.target.value)}
                  className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  data-testid="select-periodo"
                >
                  <option value="hoje">Hoje</option>
                  <option value="semana">Última Semana</option>
                  <option value="mes">Último Mês</option>
                  <option value="trimestre">Último Trimestre</option>
                  <option value="ano">Último Ano</option>
                  <option value="personalizado">Personalizado</option>
                </select>
              </div>

              {periodo === 'personalizado' && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Data Início
                    </label>
                    <input
                      type="date"
                      value={dataInicio}
                      onChange={(e) => setDataInicio(e.target.value)}
                      className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                      data-testid="input-data-inicio"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Data Fim
                    </label>
                    <input
                      type="date"
                      value={dataFim}
                      onChange={(e) => setDataFim(e.target.value)}
                      className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                      data-testid="input-data-fim"
                    />
                  </div>
                </div>
              )}

              <div className="pt-4">
                <Button
                  onClick={handleGerar}
                  variant="primary"
                  className="w-full"
                  testId="gerar-relatorio-button"
                  disabled={loading}
                >
                  {loading ? (
                    <span className="flex items-center justify-center">
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Gerando...
                    </span>
                  ) : (
                    `Gerar Relatório (${formato.toUpperCase()})`
                  )}
                </Button>
              </div>
            </div>
          </div>

          {/* Relatórios Rápidos */}
          <div className="space-y-4">
            <div className="bg-card rounded-lg border border-border p-6" data-testid="relatorios-rapidos">
              <h2 className="text-xl font-bold text-foreground mb-4">Relatórios Rápidos</h2>
              <p className="text-sm text-muted-foreground mb-4">Clique para gerar PDF do mês atual</p>
              <div className="space-y-3">
                <button 
                  onClick={() => handleRelatorioRapido('fluxo_caixa')}
                  disabled={loading}
                  className="w-full text-left px-4 py-3 bg-muted/50 hover:bg-muted rounded-lg transition disabled:opacity-50"
                  data-testid="rapido-fluxo-caixa"
                >
                  <div className="flex items-center">
                    <span className="text-2xl mr-3">📊</span>
                    <div>
                      <div className="font-medium text-foreground">Fluxo de Caixa</div>
                      <div className="text-xs text-muted-foreground">Entradas e saídas do período</div>
                    </div>
                  </div>
                </button>
                <button 
                  onClick={() => handleRelatorioRapido('inadimplencia')}
                  disabled={loading}
                  className="w-full text-left px-4 py-3 bg-muted/50 hover:bg-muted rounded-lg transition disabled:opacity-50"
                  data-testid="rapido-inadimplencia"
                >
                  <div className="flex items-center">
                    <span className="text-2xl mr-3">⚠️</span>
                    <div>
                      <div className="font-medium text-foreground">Clientes Inadimplentes</div>
                      <div className="text-xs text-muted-foreground">Lista de devedores em atraso</div>
                    </div>
                  </div>
                </button>
                <button 
                  onClick={() => handleRelatorioRapido('pagamentos')}
                  disabled={loading}
                  className="w-full text-left px-4 py-3 bg-muted/50 hover:bg-muted rounded-lg transition disabled:opacity-50"
                  data-testid="rapido-pagamentos"
                >
                  <div className="flex items-center">
                    <span className="text-2xl mr-3">💰</span>
                    <div>
                      <div className="font-medium text-foreground">Receitas do Mês</div>
                      <div className="text-xs text-muted-foreground">Pagamentos recebidos</div>
                    </div>
                  </div>
                </button>
                <button 
                  onClick={() => handleRelatorioRapido('emprestimos')}
                  disabled={loading}
                  className="w-full text-left px-4 py-3 bg-muted/50 hover:bg-muted rounded-lg transition disabled:opacity-50"
                  data-testid="rapido-emprestimos"
                >
                  <div className="flex items-center">
                    <span className="text-2xl mr-3">📋</span>
                    <div>
                      <div className="font-medium text-foreground">Empréstimos Ativos</div>
                      <div className="text-xs text-muted-foreground">Todos os empréstimos cadastrados</div>
                    </div>
                  </div>
                </button>
              </div>
            </div>

            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
              <h3 className="font-semibold text-blue-400 mb-2 flex items-center">
                <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
                Dica
              </h3>
              <p className="text-sm text-blue-400/80">
                Os relatórios em PDF são ideais para impressão e compartilhamento. 
                Use Excel para análises mais detalhadas com filtros e gráficos.
              </p>
            </div>

            {/* Tipos de Relatório */}
            <div className="bg-card rounded-lg border border-border p-6">
              <h2 className="text-lg font-bold text-foreground mb-3">Tipos de Relatório</h2>
              <div className="space-y-2 text-sm">
                <div className="flex items-start">
                  <span className="text-blue-500 font-bold mr-2">•</span>
                  <div className="text-foreground"><strong>Empréstimos:</strong> Lista completa de todos os empréstimos</div>
                </div>
                <div className="flex items-start">
                  <span className="text-emerald-500 font-bold mr-2">•</span>
                  <div className="text-foreground"><strong>Pagamentos:</strong> Histórico de pagamentos recebidos</div>
                </div>
                <div className="flex items-start">
                  <span className="text-purple-500 font-bold mr-2">•</span>
                  <div className="text-foreground"><strong>Clientes:</strong> Cadastro completo de clientes</div>
                </div>
                <div className="flex items-start">
                  <span className="text-red-500 font-bold mr-2">•</span>
                  <div className="text-foreground"><strong>Inadimplência:</strong> Parcelas em atraso</div>
                </div>
                <div className="flex items-start">
                  <span className="text-amber-500 font-bold mr-2">•</span>
                  <div className="text-foreground"><strong>Fluxo de Caixa:</strong> Resumo de entradas e saídas</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Relatorios;
