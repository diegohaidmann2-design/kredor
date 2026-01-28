import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import Button from '../components/Button';
import Loading from '../components/Loading';
import UpgradeRequired from '../components/UpgradeRequired';
import { exportacaoAPI } from '../api/api';

const Exportacao = () => {
  const [loading, setLoading] = useState(false);
  const [loadingResumo, setLoadingResumo] = useState(true);
  const [resumo, setResumo] = useState(null);
  const [semPermissao, setSemPermissao] = useState(false);
  const [mensagemPermissao, setMensagemPermissao] = useState('');
  const [entidades, setEntidades] = useState({
    clientes: true,
    emprestimos: true,
    pagamentos: true,
    parcelas: false
  });
  const [formato, setFormato] = useState('csv');
  const [dataInicio, setDataInicio] = useState('');
  const [dataFim, setDataFim] = useState('');
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    carregarResumo();
  }, []);

  const carregarResumo = async () => {
    try {
      setLoadingResumo(true);
      const response = await exportacaoAPI.resumo();
      setResumo(response.data);
      
      // Verificar se tem permissão para exportar
      if (response.data.pode_exportar === false) {
        setSemPermissao(true);
        setMensagemPermissao(response.data.mensagem_permissao || 'Você não tem permissão para exportar dados.');
      } else {
        setSemPermissao(false);
      }
    } catch (err) {
      console.error('Erro ao carregar resumo:', err);
      if (err.response?.status === 403) {
        setSemPermissao(true);
        setMensagemPermissao(err.response?.data?.detail || 'Você não tem permissão para acessar este recurso.');
      }
    } finally {
      setLoadingResumo(false);
    }
  };

  const handleEntidadeChange = (entidade) => {
    setEntidades(prev => ({
      ...prev,
      [entidade]: !prev[entidade]
    }));
  };

  const handleExportar = async () => {
    const entidadesSelecionadas = Object.entries(entidades)
      .filter(([_, selected]) => selected)
      .map(([key]) => key);

    if (entidadesSelecionadas.length === 0) {
      setError('Selecione pelo menos uma entidade para exportar');
      return;
    }

    try {
      setLoading(true);
      setError('');
      setSuccess('');

      const response = await exportacaoAPI.exportar({
        entidades: entidadesSelecionadas,
        formato,
        data_inicio: dataInicio || null,
        data_fim: dataFim || null
      });

      // Criar blob a partir do arraybuffer
      const blob = new Blob([response.data], { 
        type: formato === 'json' 
          ? 'application/json' 
          : entidadesSelecionadas.length === 1 
            ? 'text/csv' 
            : 'application/zip'
      });
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      
      const ext = formato === 'json' ? 'json' : entidadesSelecionadas.length === 1 ? 'csv' : 'zip';
      a.download = `exportacao_${new Date().toISOString().slice(0, 10)}.${ext}`;
      
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      setSuccess('Exportação realizada com sucesso!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      // Tratar erro 403 de permissão
      if (err.response?.status === 403) {
        const mensagem = err.response?.data?.detail || 'Você não tem permissão para exportar dados.';
        setSemPermissao(true);
        setMensagemPermissao(mensagem);
      } else {
        const mensagemErro = err.response?.data?.detail || 'Erro ao exportar dados. Tente novamente.';
        setError(mensagemErro);
      }
    } finally {
      setLoading(false);
    }
  };

  // Se não tiver permissão, mostrar tela de upgrade
  if (semPermissao) {
    return (
      <Layout>
        <div className="container mx-auto px-4 py-8">
          <UpgradeRequired 
            recurso="Exportação de Dados"
            mensagem={mensagemPermissao}
            planoRecomendado="Básico"
          />
        </div>
      </Layout>
    );
  }

  // Loading inicial
  if (loadingResumo) {
    return (
      <Layout>
        <div className="container mx-auto px-4 py-8">
          <Loading message="Carregando..." />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground" data-testid="exportacao-title">
            Exportação de Dados
          </h1>
          <p className="text-muted-foreground mt-1">Exporte seus dados em massa para CSV ou JSON</p>
        </div>

        {success && (
          <div className="mb-6 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-4 py-3 rounded-lg flex items-center">
            <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
            </svg>
            {success}
          </div>
        )}

        {error && (
          <div className="mb-6 bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Resumo dos Dados */}
          <div className="lg:col-span-1">
            <div className="bg-card rounded-lg border border-border p-6" data-testid="resumo-dados">
              <h2 className="text-lg font-bold text-foreground mb-4">Resumo dos Dados</h2>
              
              {resumo ? (
                <div className="space-y-4">
                  <div className="flex justify-between items-center p-3 bg-blue-500/10 rounded-lg">
                    <span className="text-foreground">Clientes</span>
                    <span className="font-bold text-blue-400">{resumo.clientes}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-emerald-500/10 rounded-lg">
                    <span className="text-foreground">Empréstimos</span>
                    <span className="font-bold text-emerald-400">{resumo.emprestimos}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-purple-500/10 rounded-lg">
                    <span className="text-foreground">Pagamentos</span>
                    <span className="font-bold text-purple-400">{resumo.pagamentos}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-amber-500/10 rounded-lg">
                    <span className="text-foreground">Parcelas</span>
                    <span className="font-bold text-amber-400">{resumo.parcelas}</span>
                  </div>
                </div>
              ) : (
                <Loading message="Carregando..." />
              )}
            </div>
          </div>

          {/* Opções de Exportação */}
          <div className="lg:col-span-2">
            <div className="bg-card rounded-lg border border-border p-6" data-testid="opcoes-exportacao">
              <h2 className="text-lg font-bold text-foreground mb-4">Opções de Exportação</h2>

              {/* Entidades */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-foreground mb-3">
                  Selecione os dados para exportar:
                </label>
                <div className="grid grid-cols-2 gap-4">
                  {Object.entries(entidades).map(([key, checked]) => (
                    <label key={key} className="flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => handleEntidadeChange(key)}
                        className="w-5 h-5 text-primary border-border rounded focus:ring-primary bg-background"
                        data-testid={`checkbox-${key}`}
                      />
                      <span className="ml-2 text-foreground capitalize">{key}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Formato */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-foreground mb-3">
                  Formato do arquivo:
                </label>
                <div className="flex gap-4">
                  <label className={`flex-1 p-4 border-2 rounded-lg cursor-pointer transition ${formato === 'csv' ? 'border-primary bg-primary/10' : 'border-border hover:border-muted-foreground'}`}>
                    <input
                      type="radio"
                      value="csv"
                      checked={formato === 'csv'}
                      onChange={(e) => setFormato(e.target.value)}
                      className="sr-only"
                    />
                    <div className="flex items-center">
                      <svg className="w-8 h-8 text-emerald-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <div>
                        <p className="font-medium text-foreground">CSV</p>
                        <p className="text-xs text-muted-foreground">Excel, Google Sheets</p>
                      </div>
                    </div>
                  </label>

                  <label className={`flex-1 p-4 border-2 rounded-lg cursor-pointer transition ${formato === 'json' ? 'border-primary bg-primary/10' : 'border-border hover:border-muted-foreground'}`}>
                    <input
                      type="radio"
                      value="json"
                      checked={formato === 'json'}
                      onChange={(e) => setFormato(e.target.value)}
                      className="sr-only"
                    />
                    <div className="flex items-center">
                      <svg className="w-8 h-8 text-blue-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                      </svg>
                      <div>
                        <p className="font-medium text-foreground">JSON</p>
                        <p className="text-xs text-muted-foreground">Integrações, APIs</p>
                      </div>
                    </div>
                  </label>
                </div>
              </div>

              {/* Filtro de Data */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-foreground mb-3">
                  Período (opcional):
                </label>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">Data Início</label>
                    <input
                      type="date"
                      value={dataInicio}
                      onChange={(e) => setDataInicio(e.target.value)}
                      className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                      data-testid="input-data-inicio"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">Data Fim</label>
                    <input
                      type="date"
                      value={dataFim}
                      onChange={(e) => setDataFim(e.target.value)}
                      className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                      data-testid="input-data-fim"
                    />
                  </div>
                </div>
              </div>

              {/* Botão Exportar */}
              <Button
                onClick={handleExportar}
                variant="primary"
                className="w-full py-3"
                disabled={loading}
                data-testid="btn-exportar"
              >
                {loading ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Exportando...
                  </span>
                ) : (
                  <span className="flex items-center justify-center">
                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Exportar Dados
                  </span>
                )}
              </Button>

              {/* Info */}
              <div className="mt-4 bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                <p className="text-sm text-blue-400">
                  <strong>Dica:</strong> Se selecionar múltiplas entidades com formato CSV, será gerado um arquivo ZIP contendo um CSV para cada entidade.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Exportacao;
