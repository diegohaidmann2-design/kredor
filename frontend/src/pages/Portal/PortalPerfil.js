import React, { useState, useEffect } from 'react';
import { usePortal } from '../../context/PortalContext';
import { portalAPI } from '../../api/api';
import { toast } from '../../hooks/use-toast';

// Componente de Input de Código com Toggle de Visibilidade
const CodigoInput = ({ value, onChange, placeholder, label }) => {
  const [showCodigo, setShowCodigo] = useState(false);
  
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-2">
        {label}
      </label>
      <div className="relative">
        <input
          type={showCodigo ? "text" : "password"}
          inputMode="numeric"
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className="w-full px-4 py-3 pr-12 border border-slate-300 rounded-xl focus:ring-2 focus:ring-ring focus:border-transparent text-center text-2xl tracking-[0.5em] font-mono bg-white text-slate-800 placeholder-slate-400"
          maxLength={6}
        />
        <button
          type="button"
          onClick={() => setShowCodigo(!showCodigo)}
          className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-slate-400 hover:text-slate-600 transition-colors"
          title={showCodigo ? "Ocultar código" : "Mostrar código"}
        >
          {showCodigo ? (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          )}
        </button>
      </div>
    </div>
  );
};

const PortalPerfil = () => {
  const { alterarCodigo } = usePortal();
  const [loading, setLoading] = useState(true);
  const [perfil, setPerfil] = useState(null);
  const [showAlterarCodigo, setShowAlterarCodigo] = useState(false);
  const [codigoAtual, setCodigoAtual] = useState('');
  const [codigoNovo, setCodigoNovo] = useState('');
  const [codigoNovoConfirmacao, setCodigoNovoConfirmacao] = useState('');
  const [message, setMessage] = useState({ type: '', text: '' });

  useEffect(() => {
    carregarPerfil();
  }, []);

  const carregarPerfil = async () => {
    setLoading(true);
    try {
      const response = await portalAPI.meuPerfil();
      setPerfil(response.data);
    } catch (error) {
      toast({ title: 'Erro', description: "Não foi possível carregar perfil.", variant: 'destructive' });
      console.error('Erro ao carregar perfil:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAlterarCodigo = async (e) => {
    e.preventDefault();
    setMessage({ type: '', text: '' });

    if (!codigoAtual || !codigoNovo || !codigoNovoConfirmacao) {
      setMessage({ type: 'error', text: 'Preencha todos os campos' });
      return;
    }

    if (codigoNovo.length !== 6 || codigoNovoConfirmacao.length !== 6) {
      setMessage({ type: 'error', text: 'Os códigos devem ter 6 dígitos' });
      return;
    }

    if (codigoNovo !== codigoNovoConfirmacao) {
      setMessage({ type: 'error', text: 'Os códigos novos não conferem' });
      return;
    }

    const result = await alterarCodigo(codigoAtual, codigoNovo, codigoNovoConfirmacao);
    
    if (result.success) {
      setMessage({ type: 'success', text: result.message });
      setCodigoAtual('');
      setCodigoNovo('');
      setCodigoNovoConfirmacao('');
      setShowAlterarCodigo(false);
    } else {
      setMessage({ type: 'error', text: result.message });
    }
  };

  const formatarMoeda = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(valor || 0);
  };

  const formatarCpf = (cpf) => {
    if (!cpf) return '-';
    const numeros = cpf.replace(/\D/g, '');
    if (numeros.length === 11) {
      return numeros.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
    }
    if (numeros.length === 14) {
      return numeros.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
    }
    return cpf;
  };

  const formatarTelefone = (tel) => {
    if (!tel) return '-';
    const numeros = tel.replace(/\D/g, '');
    if (numeros.length === 11) {
      return numeros.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3');
    }
    if (numeros.length === 10) {
      return numeros.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3');
    }
    return tel;
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh]">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-emerald-200 rounded-full animate-spin border-t-emerald-600"></div>
        </div>
        <p className="mt-4 text-slate-600 font-medium">Carregando perfil...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-br from-slate-700 to-slate-800 rounded-2xl p-6 sm:p-8 text-white shadow-lg">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="w-16 h-16 sm:w-20 sm:h-20 bg-white/10 rounded-full flex items-center justify-center">
            <svg className="w-8 h-8 sm:w-10 sm:h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <div>
            <h2 className="text-2xl sm:text-3xl font-bold">Meu Perfil</h2>
            <p className="text-slate-300 mt-1">Visualize e gerencie suas informações</p>
          </div>
        </div>
      </div>

      {/* Mensagem */}
      {message.text && (
        <div className={`rounded-xl p-4 flex items-center gap-3 ${
          message.type === 'success' 
            ? 'bg-emerald-50 border border-emerald-200 text-emerald-700' 
            : 'bg-red-50 border border-red-200 text-red-700'
        }`}>
          {message.type === 'success' ? (
            <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ) : (
            <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )}
          <span className="font-medium">{message.text}</span>
        </div>
      )}

      {/* Informações Pessoais */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-5 sm:px-6 py-4 border-b border-slate-200 bg-slate-50">
          <h3 className="font-bold text-slate-800 flex items-center gap-2">
            <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c1.306 0 2.417.835 2.83 2M9 14a3.001 3.001 0 00-2.83 2M15 11h3m-3 4h2" />
            </svg>
            Informações Pessoais
          </h3>
        </div>
        <div className="p-5 sm:p-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div className="space-y-1">
              <p className="text-sm text-slate-500 font-medium">Nome Completo</p>
              <p className="text-lg font-semibold text-slate-800">{perfil?.nome}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-slate-500 font-medium">CPF/CNPJ</p>
              <p className="text-lg font-semibold text-slate-800 font-mono">{formatarCpf(perfil?.cpf_cnpj)}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-slate-500 font-medium">Telefone</p>
              <p className="text-lg font-semibold text-slate-800">{formatarTelefone(perfil?.telefone)}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-slate-500 font-medium">Email</p>
              <p className="text-lg font-semibold text-slate-800">{perfil?.email || 'Não cadastrado'}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-slate-500 font-medium">Status</p>
              <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold ${
                perfil?.status === 'ativo' 
                  ? 'bg-emerald-100 text-emerald-700' 
                  : 'bg-slate-100 text-slate-700'
              }`}>
                <span className={`w-2 h-2 rounded-full ${perfil?.status === 'ativo' ? 'bg-emerald-500' : 'bg-slate-400'}`}></span>
                {perfil?.status === 'ativo' ? 'Ativo' : perfil?.status}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Resumo Financeiro */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-5 sm:px-6 py-4 border-b border-slate-200 bg-slate-50">
          <h3 className="font-bold text-slate-800 flex items-center gap-2">
            <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            Resumo Financeiro
          </h3>
        </div>
        <div className="p-5 sm:p-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 rounded-xl p-5 border border-emerald-200">
              <div className="flex items-center gap-3">
                <div className="bg-emerald-500 p-2 rounded-lg">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-emerald-600 font-medium">Total de Empréstimos</p>
                  <p className="text-3xl font-bold text-emerald-800">{perfil?.total_emprestimos || 0}</p>
                </div>
              </div>
            </div>
            <div className="bg-gradient-to-br from-emerald-50 to-emerald-100 rounded-xl p-5 border border-emerald-200">
              <div className="flex items-center gap-3">
                <div className="bg-emerald-500 p-2 rounded-lg">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-emerald-600 font-medium">Empréstimos Ativos</p>
                  <p className="text-3xl font-bold text-emerald-800">{perfil?.emprestimos_ativos || 0}</p>
                </div>
              </div>
            </div>
            <div className="bg-gradient-to-br from-red-50 to-red-100 rounded-xl p-5 border border-red-200">
              <div className="flex items-center gap-3">
                <div className="bg-red-500 p-2 rounded-lg">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm text-red-600 font-medium">Total Devido</p>
                  <p className="text-2xl sm:text-3xl font-bold text-red-800">{formatarMoeda(perfil?.total_devido)}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Segurança */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="px-5 sm:px-6 py-4 border-b border-slate-200 bg-slate-50">
          <h3 className="font-bold text-slate-800 flex items-center gap-2">
            <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            Segurança
          </h3>
        </div>
        <div className="p-5 sm:p-6">
          {!showAlterarCodigo ? (
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 p-4 bg-slate-50 rounded-xl">
              <div>
                <p className="font-medium text-slate-800">Código de Acesso</p>
                <p className="text-sm text-slate-500">Use o código de 6 dígitos para acessar o portal</p>
              </div>
              <button
                onClick={() => setShowAlterarCodigo(true)}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2.5 px-5 rounded-xl transition flex items-center gap-2 justify-center"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                </svg>
                Alterar Código
              </button>
            </div>
          ) : (
            <form onSubmit={handleAlterarCodigo} className="space-y-5 max-w-md">
              <CodigoInput
                label="Código Atual"
                value={codigoAtual}
                onChange={(e) => setCodigoAtual(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
              />

              <CodigoInput
                label="Novo Código"
                value={codigoNovo}
                onChange={(e) => setCodigoNovo(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
              />

              <CodigoInput
                label="Confirmar Novo Código"
                value={codigoNovoConfirmacao}
                onChange={(e) => setCodigoNovoConfirmacao(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
              />

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowAlterarCodigo(false);
                    setCodigoAtual('');
                    setCodigoNovo('');
                    setCodigoNovoConfirmacao('');
                    setMessage({ type: '', text: '' });
                  }}
                  className="flex-1 bg-slate-200 hover:bg-slate-300 text-slate-700 font-semibold py-3 px-4 rounded-xl transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-3 px-4 rounded-xl transition"
                >
                  Confirmar
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default PortalPerfil;
