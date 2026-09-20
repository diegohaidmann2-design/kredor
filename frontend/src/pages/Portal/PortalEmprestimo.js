import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { portalAPI } from '../../api/api';
import { toast } from '../../hooks/use-toast';

const PortalEmprestimo = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [emprestimo, setEmprestimo] = useState(null);
  const [parcelas, setParcelas] = useState([]);
  const [pagamentos, setPagamentos] = useState([]);
  const [activeTab, setActiveTab] = useState('parcelas');

  useEffect(() => {
    carregarDados();
  }, [id]);

  const carregarDados = async () => {
    setLoading(true);
    try {
      const [empRes, pagRes] = await Promise.all([
        portalAPI.emprestimo(id),
        portalAPI.historicoPagamentos(id)
      ]);

      setEmprestimo(empRes.data.emprestimo);
      setParcelas(empRes.data.parcelas || []);
      setPagamentos(pagRes.data.pagamentos || []);
    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível carregar empréstimo.", variant: 'destructive' });
      console.error('Erro ao carregar empréstimo:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor || 0);
  };

  const formatarData = (data) => {
    if (!data) return '-';
    return new Date(data).toLocaleDateString('pt-BR');
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-emerald-200 rounded-full animate-spin border-t-emerald-600"></div>
        </div>
        <p className="mt-4 text-slate-600 font-medium">Carregando empréstimo...</p>
      </div>
    );
  }

  if (!emprestimo) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center">
        <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-slate-600 mb-4">Empréstimo não encontrado.</p>
        <button
          onClick={() => navigate('/portal/app/dashboard')}
          className="text-emerald-600 hover:text-emerald-700 font-medium"
        >
          ← Voltar ao início
        </button>
      </div>
    );
  }

  const parcelasPagas = parcelas.filter(p => p.status === 'pago').length;
  const progressoParcelas = parcelas.length > 0 ? (parcelasPagas / parcelas.length) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Botão Voltar */}
      <button
        onClick={() => navigate('/portal/app/dashboard')}
        className="flex items-center gap-2 text-slate-600 hover:text-emerald-600 font-medium transition"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Voltar para Meus Empréstimos
      </button>

      {/* Header do Empréstimo */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="bg-gradient-to-r from-emerald-600 to-emerald-600 px-5 sm:px-6 py-5">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h2 className="text-xl sm:text-2xl font-bold text-white">Detalhes do Empréstimo</h2>
              <p className="text-emerald-100 text-sm mt-1 capitalize">{emprestimo.metodo_calculo?.replace('_', ' ')}</p>
            </div>
            <span className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold ${
              emprestimo.status === 'ativo' 
                ? 'bg-emerald-500 text-white' 
                : emprestimo.status === 'quitado' 
                ? 'bg-slate-400 text-white'
                : 'bg-slate-200 text-slate-700'
            }`}>
              <span className="w-2 h-2 rounded-full bg-current"></span>
              {emprestimo.status === 'ativo' ? 'Ativo' : emprestimo.status === 'quitado' ? 'Quitado' : emprestimo.status}
            </span>
          </div>
        </div>
        
        {/* Progresso */}
        <div className="px-5 sm:px-6 py-4 bg-slate-50 border-b border-slate-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-600">Progresso do Pagamento</span>
            <span className="text-sm font-bold text-slate-800">{parcelasPagas}/{parcelas.length} parcelas</span>
          </div>
          <div className="w-full bg-slate-200 rounded-full h-3">
            <div 
              className="bg-gradient-to-r from-emerald-500 to-emerald-400 h-3 rounded-full transition-all duration-500"
              style={{ width: `${progressoParcelas}%` }}
            ></div>
          </div>
        </div>

        {/* Informações */}
        <div className="p-5 sm:p-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 sm:gap-6">
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-sm text-slate-500 font-medium">Valor Principal</p>
              <p className="text-lg sm:text-xl font-bold text-slate-800 mt-1">
                {formatarMoeda(emprestimo.valor_principal)}
              </p>
            </div>
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-sm text-slate-500 font-medium">Valor Total</p>
              <p className="text-lg sm:text-xl font-bold text-slate-800 mt-1">
                {formatarMoeda(emprestimo.valor_total_com_juros)}
              </p>
            </div>
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-sm text-slate-500 font-medium">Taxa de Juros</p>
              <p className="text-lg sm:text-xl font-bold text-slate-800 mt-1">
                {emprestimo.taxa_juros_mensal}% <span className="text-sm font-normal text-slate-500">a.m.</span>
              </p>
            </div>
            <div className="bg-slate-50 rounded-xl p-4">
              <p className="text-sm text-slate-500 font-medium">Parcelas</p>
              <p className="text-lg sm:text-xl font-bold text-slate-800 mt-1">
                {emprestimo.prazo_meses}x
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
            <div className="flex items-center gap-3 p-4 bg-slate-50 rounded-xl">
              <div className="bg-emerald-100 p-2 rounded-lg">
                <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <div>
                <p className="text-sm text-slate-500">Data do Empréstimo</p>
                <p className="font-semibold text-slate-800">{formatarData(emprestimo.created_at)}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 p-4 bg-slate-50 rounded-xl">
              <div className="bg-emerald-100 p-2 rounded-lg">
                <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              </div>
              <div>
                <p className="text-sm text-slate-500">Método de Cálculo</p>
                <p className="font-semibold text-slate-800 capitalize">{emprestimo.metodo_calculo?.replace('_', ' ')}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="border-b border-slate-200">
          <nav className="flex">
            <button
              onClick={() => setActiveTab('parcelas')}
              className={`flex-1 sm:flex-none py-4 px-6 text-sm font-medium transition-all border-b-2 ${
                activeTab === 'parcelas'
                  ? 'border-emerald-600 text-emerald-600 bg-emerald-50/50'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50'
              }`}
            >
              <span className="flex items-center justify-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                Parcelas ({parcelas.length})
              </span>
            </button>
            <button
              onClick={() => setActiveTab('pagamentos')}
              className={`flex-1 sm:flex-none py-4 px-6 text-sm font-medium transition-all border-b-2 ${
                activeTab === 'pagamentos'
                  ? 'border-emerald-600 text-emerald-600 bg-emerald-50/50'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50'
              }`}
            >
              <span className="flex items-center justify-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                Histórico ({pagamentos.length})
              </span>
            </button>
          </nav>
        </div>

        {/* Conteúdo das Tabs */}
        <div className="p-4 sm:p-6">
          {activeTab === 'parcelas' && (
            <div className="space-y-3">
              {parcelas.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-slate-500">Nenhuma parcela encontrada.</p>
                </div>
              ) : (
                parcelas.map((parcela) => (
                  <div
                    key={parcela.id}
                    className={`rounded-xl p-4 border-2 transition ${
                      parcela.status === 'pago' 
                        ? 'border-emerald-200 bg-emerald-50' 
                        : parcela.dias_atraso > 0 
                        ? 'border-red-200 bg-red-50' 
                        : 'border-slate-200 bg-white hover:border-slate-300'
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                      <div className="flex-1">
                        <div className="flex flex-wrap items-center gap-2 mb-2">
                          <span className="font-bold text-slate-800">Parcela {parcela.numero_parcela}</span>
                          <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                            parcela.status === 'pago' 
                              ? 'bg-emerald-200 text-emerald-800' 
                              : parcela.dias_atraso > 0 
                              ? 'bg-red-200 text-red-800' 
                              : 'bg-amber-200 text-amber-800'
                          }`}>
                            {parcela.status === 'pago' 
                              ? '✓ Paga' 
                              : parcela.dias_atraso > 0 
                              ? `Atrasada (${parcela.dias_atraso}d)` 
                              : 'Pendente'}
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-600">
                          <span>Vencimento: <strong>{formatarData(parcela.data_vencimento)}</strong></span>
                          {parcela.data_pagamento && (
                            <span>Pago em: <strong>{formatarData(parcela.data_pagamento)}</strong></span>
                          )}
                        </div>
                      </div>
                      <div className="text-left sm:text-right">
                        <p className="text-xs text-slate-500 mb-1">Valor</p>
                        <p className="text-xl sm:text-2xl font-bold text-slate-800">
                          {formatarMoeda(parcela.valor_total)}
                        </p>
                        {parcela.valor_pago > 0 && parcela.status === 'pago' && (
                          <p className="text-sm text-emerald-600 font-medium">
                            Pago: {formatarMoeda(parcela.valor_pago)}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'pagamentos' && (
            <div className="space-y-3">
              {pagamentos.length === 0 ? (
                <div className="text-center py-8">
                  <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-3">
                    <svg className="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                    </svg>
                  </div>
                  <p className="text-slate-500">Nenhum pagamento registrado.</p>
                </div>
              ) : (
                pagamentos.map((pag) => (
                  <div key={pag.id} className="border border-slate-200 rounded-xl p-4 bg-white hover:border-slate-300 transition">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <div className="w-8 h-8 bg-emerald-100 rounded-full flex items-center justify-center">
                            <svg className="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          </div>
                          <p className="font-semibold text-slate-800">Pagamento - Parcela {pag.numero_parcela}</p>
                        </div>
                        <p className="text-sm text-slate-500 ml-10">Data: {formatarData(pag.data_pagamento)}</p>
                        {pag.observacoes && (
                          <p className="text-sm text-slate-400 ml-10 mt-1">{pag.observacoes}</p>
                        )}
                      </div>
                      <p className="text-xl sm:text-2xl font-bold text-emerald-600">
                        {formatarMoeda(pag.valor_pago)}
                      </p>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PortalEmprestimo;
