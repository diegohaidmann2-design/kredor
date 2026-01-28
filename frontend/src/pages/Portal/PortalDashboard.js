import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

const PortalDashboard = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [perfil, setPerfil] = useState(null);
  const [emprestimos, setEmprestimos] = useState([]);
  const [proximasParcelas, setProximasParcelas] = useState([]);

  useEffect(() => {
    carregarDados();
  }, []);

  const carregarDados = async () => {
    setLoading(true);
    try {
      const [perfilRes, emprestimosRes, parcelasRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/portal/meu-perfil`),
        axios.get(`${BACKEND_URL}/api/portal/emprestimos`),
        axios.get(`${BACKEND_URL}/api/portal/proximas-parcelas`)
      ]);

      setPerfil(perfilRes.data);
      setEmprestimos(emprestimosRes.data.emprestimos || []);
      setProximasParcelas(parcelasRes.data.parcelas || []);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
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

  const getUrgenciaStyle = (urgencia) => {
    switch (urgencia) {
      case 'atrasada':
        return 'bg-red-100 text-red-700 border-red-200';
      case 'urgente':
        return 'bg-amber-100 text-amber-700 border-amber-200';
      case 'proxima':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const getUrgenciaTexto = (urgencia) => {
    switch (urgencia) {
      case 'atrasada': return 'Atrasada';
      case 'urgente': return 'Urgente';
      case 'proxima': return 'Próxima';
      default: return 'Normal';
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-blue-200 rounded-full animate-spin border-t-blue-600"></div>
        </div>
        <p className="mt-4 text-slate-600 font-medium">Carregando seus dados...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Bem-vindo */}
      <div className="bg-gradient-to-br from-blue-600 to-indigo-700 rounded-2xl p-6 sm:p-8 text-white shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <p className="text-blue-100 text-sm mb-1">Bem-vindo(a) de volta,</p>
            <h2 className="text-2xl sm:text-3xl font-bold">
              {perfil?.nome?.split(' ')[0]}! 👋
            </h2>
            <p className="text-blue-100 mt-2 text-sm sm:text-base">
              Acompanhe seus empréstimos e parcelas de forma simples.
            </p>
          </div>
          <div className="hidden sm:block">
            <div className="w-20 h-20 bg-white/10 rounded-full flex items-center justify-center">
              <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* Cards de Resumo */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl p-5 shadow-sm border border-slate-200 hover:shadow-md transition">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500 font-medium">Total de Empréstimos</p>
              <p className="text-3xl font-bold text-slate-800 mt-2">
                {perfil?.total_emprestimos || 0}
              </p>
            </div>
            <div className="bg-blue-50 p-3 rounded-xl">
              <svg className="w-7 h-7 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-5 shadow-sm border border-slate-200 hover:shadow-md transition">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500 font-medium">Empréstimos Ativos</p>
              <p className="text-3xl font-bold text-emerald-600 mt-2">
                {perfil?.emprestimos_ativos || 0}
              </p>
            </div>
            <div className="bg-emerald-50 p-3 rounded-xl">
              <svg className="w-7 h-7 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl p-5 shadow-sm border border-slate-200 hover:shadow-md transition">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-500 font-medium">Total Devido</p>
              <p className="text-2xl sm:text-3xl font-bold text-red-600 mt-2">
                {formatarMoeda(perfil?.total_devido)}
              </p>
            </div>
            <div className="bg-red-50 p-3 rounded-xl">
              <svg className="w-7 h-7 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* Próxima Parcela Destaque */}
      {perfil?.proxima_parcela && (
        <div className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-2xl p-5 sm:p-6 border border-amber-200 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <div className="bg-amber-500 p-2 rounded-lg">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-amber-800">Próxima Parcela</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-white/70 rounded-xl p-4">
              <p className="text-sm text-amber-700">Parcela</p>
              <p className="text-2xl font-bold text-slate-800">#{perfil.proxima_parcela.numero}</p>
            </div>
            <div className="bg-white/70 rounded-xl p-4">
              <p className="text-sm text-amber-700">Valor</p>
              <p className="text-2xl font-bold text-slate-800">{formatarMoeda(perfil.proxima_parcela.valor)}</p>
            </div>
            <div className="bg-white/70 rounded-xl p-4">
              <p className="text-sm text-amber-700">Vencimento</p>
              <p className="text-xl sm:text-2xl font-bold text-slate-800">{formatarData(perfil.proxima_parcela.data_vencimento)}</p>
              {perfil.proxima_parcela.dias_ate_vencimento !== null && (
                <p className={`text-sm mt-1 font-medium ${
                  perfil.proxima_parcela.dias_ate_vencimento > 7 ? 'text-emerald-600' :
                  perfil.proxima_parcela.dias_ate_vencimento > 0 ? 'text-amber-600' : 'text-red-600'
                }`}>
                  {perfil.proxima_parcela.dias_ate_vencimento > 0
                    ? `Faltam ${perfil.proxima_parcela.dias_ate_vencimento} dias`
                    : perfil.proxima_parcela.dias_ate_vencimento === 0
                    ? '⚠️ Vence hoje!'
                    : `⚠️ Atrasada há ${Math.abs(perfil.proxima_parcela.dias_ate_vencimento)} dias`
                  }
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Próximas Parcelas Lista */}
      {proximasParcelas.length > 0 && (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-5 sm:px-6 py-4 border-b border-slate-200 bg-slate-50">
            <h3 className="font-bold text-slate-800 flex items-center gap-2">
              <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              Próximas Parcelas
            </h3>
          </div>
          <div className="divide-y divide-slate-100">
            {proximasParcelas.map((parcela, index) => (
              <div key={index} className="p-4 sm:p-5 hover:bg-slate-50 transition">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div className="flex items-start sm:items-center gap-3">
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getUrgenciaStyle(parcela.urgencia)}`}>
                      {getUrgenciaTexto(parcela.urgencia)}
                    </span>
                    <div>
                      <p className="font-semibold text-slate-800">Parcela {parcela.numero_parcela}</p>
                      <p className="text-sm text-slate-500">
                        Vencimento: {formatarData(parcela.data_vencimento)}
                        {parcela.dias_ate_vencimento !== undefined && (
                          <span className="ml-2 text-slate-400">
                            ({parcela.dias_ate_vencimento > 0 ? `${parcela.dias_ate_vencimento}d` : 'vencida'})
                          </span>
                        )}
                      </p>
                    </div>
                  </div>
                  <p className="text-xl font-bold text-slate-800">
                    {formatarMoeda(parcela.valor_total)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Lista de Empréstimos */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-5 sm:px-6 py-4 border-b border-slate-200 bg-slate-50">
          <h3 className="font-bold text-slate-800 flex items-center gap-2">
            <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            Meus Empréstimos
          </h3>
        </div>
        
        {emprestimos.length === 0 ? (
          <div className="p-8 text-center">
            <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
              </svg>
            </div>
            <p className="text-slate-500">Você ainda não possui empréstimos cadastrados.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {emprestimos.map((emp) => (
              <div
                key={emp.id}
                className="p-4 sm:p-5 hover:bg-blue-50/50 transition cursor-pointer group"
                onClick={() => navigate(`/portal/app/emprestimo/${emp.id}`)}
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        emp.status === 'ativo' ? 'bg-emerald-100 text-emerald-700' :
                        emp.status === 'quitado' ? 'bg-blue-100 text-blue-700' :
                        'bg-slate-100 text-slate-700'
                      }`}>
                        {emp.status === 'ativo' ? 'Ativo' : emp.status === 'quitado' ? 'Quitado' : emp.status}
                      </span>
                      <span className="text-slate-600 font-medium text-sm capitalize">
                        {emp.metodo_calculo?.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-600">
                      <span>Valor: <strong className="text-slate-800">{formatarMoeda(emp.valor_principal)}</strong></span>
                      <span>Total: <strong className="text-slate-800">{formatarMoeda(emp.valor_total_com_juros)}</strong></span>
                      <span>Parcelas: <strong className="text-slate-800">{emp.resumo_parcelas?.pagas || 0}/{emp.resumo_parcelas?.total || 0}</strong></span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">Criado em: {formatarData(emp.created_at)}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <p className="text-xs text-slate-500">Restante</p>
                      <p className="text-xl font-bold text-red-600">
                        {formatarMoeda(emp.resumo_parcelas?.valor_restante)}
                      </p>
                    </div>
                    <svg className="w-5 h-5 text-slate-400 group-hover:text-blue-600 transition hidden sm:block" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default PortalDashboard;
