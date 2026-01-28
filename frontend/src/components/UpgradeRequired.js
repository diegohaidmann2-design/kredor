import React from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Componente para exibir mensagem quando recurso não está disponível no plano
 */
const UpgradeRequired = ({ 
  recurso = "Este recurso",
  mensagem = null,
  planoRecomendado = "Básico"
}) => {
  const navigate = useNavigate();

  return (
    <div className="bg-card border border-border rounded-xl p-8 text-center max-w-lg mx-auto">
      {/* Ícone de cadeado */}
      <div className="w-20 h-20 mx-auto mb-6 bg-amber-500/20 rounded-full flex items-center justify-center">
        <svg className="w-10 h-10 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
      </div>

      {/* Título */}
      <h2 className="text-xl font-bold text-foreground mb-2">
        Recurso Premium
      </h2>

      {/* Mensagem */}
      <p className="text-muted-foreground mb-6">
        {mensagem || `${recurso} não está disponível no seu plano atual. Faça upgrade para desbloquear este recurso.`}
      </p>

      {/* Benefícios do upgrade */}
      <div className="bg-muted/50 rounded-lg p-4 mb-6 text-left">
        <p className="text-sm font-medium text-foreground mb-3">
          Com o plano {planoRecomendado} você terá:
        </p>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li className="flex items-center gap-2">
            <svg className="w-4 h-4 text-emerald-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
            </svg>
            Mais clientes e empréstimos
          </li>
          <li className="flex items-center gap-2">
            <svg className="w-4 h-4 text-emerald-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
            </svg>
            Exportação de dados em massa
          </li>
          <li className="flex items-center gap-2">
            <svg className="w-4 h-4 text-emerald-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
            </svg>
            Contratos em PDF
          </li>
          <li className="flex items-center gap-2">
            <svg className="w-4 h-4 text-emerald-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
            </svg>
            Notificações por email
          </li>
        </ul>
      </div>

      {/* Botões */}
      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        <button
          onClick={() => navigate('/assinatura')}
          className="px-6 py-3 bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white font-medium rounded-lg transition-all shadow-lg shadow-purple-500/25 hover:shadow-purple-500/40"
        >
          <span className="flex items-center justify-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
            </svg>
            Ver Planos
          </span>
        </button>
        <button
          onClick={() => navigate(-1)}
          className="px-6 py-3 bg-muted hover:bg-muted/80 text-foreground font-medium rounded-lg transition-colors"
        >
          Voltar
        </button>
      </div>
    </div>
  );
};

export default UpgradeRequired;
