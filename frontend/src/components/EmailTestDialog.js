import React from 'react';

const EmailTestDialog = ({ isOpen, onClose, status, message, logs, email, onRetry }) => {
  if (!isOpen) return null;

  const isSuccess = status === 'success';
  const isError = status === 'error';
  const isLoading = status === 'loading';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-card w-full max-w-md rounded-lg shadow-xl border border-border p-6 animate-in fade-in zoom-in duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-foreground">Teste de Email</h3>
          {!isLoading && (
            <button 
              onClick={onClose}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Content */}
        <div className="flex flex-col items-center text-center py-4">
          
          {/* Status Icon */}
          {isLoading && (
            <div className="w-16 h-16 mb-4 rounded-full bg-blue-500/10 flex items-center justify-center animate-pulse">
              <svg className="w-8 h-8 text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
          )}

          {isSuccess && (
            <div className="w-16 h-16 mb-4 rounded-full bg-green-500/10 flex items-center justify-center">
              <svg className="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          )}

          {isError && (
            <div className="w-16 h-16 mb-4 rounded-full bg-red-500/10 flex items-center justify-center">
              <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
          )}

          {/* Message */}
          <h4 className={`text-lg font-medium mb-2 ${
            isSuccess ? 'text-green-500' : isError ? 'text-red-500' : 'text-foreground'
          }`}>
            {isLoading ? 'Enviando email...' : (isSuccess ? 'Email Enviado!' : 'Falha no Envio')}
          </h4>
          
          <p className="text-muted-foreground text-sm mb-6">
            {message}
          </p>

          {/* Dicas para Sucesso */}
          {isSuccess && (
            <div className="w-full bg-blue-500/5 border border-blue-500/10 rounded-lg p-3 mb-4 text-left">
              <h5 className="text-sm font-semibold text-blue-500 mb-2 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                Dicas Importantes:
              </h5>
              <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside pl-1">
                <li>Verifique a caixa de entrada de <strong>{email}</strong></li>
                <li>Verifique a pasta de <strong>SPAM/Lixo Eletrônico</strong></li>
                <li>O envio pode levar até 5 minutos</li>
              </ul>
            </div>
          )}
          
          {/* Logs / Detalhes (Opcional, escondido por padrão) */}
          {logs && logs.length > 0 && (
            <details className="w-full text-left mb-4 group">
              <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground transition-colors flex items-center gap-1 select-none">
                <svg className="w-4 h-4 transition-transform group-open:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
                Ver logs técnicos
              </summary>
              <div className="mt-2 bg-slate-950 text-slate-300 p-3 rounded text-xs font-mono h-32 overflow-y-auto border border-slate-800">
                {logs.map((log, index) => (
                  <div key={index} className="whitespace-pre-wrap mb-1 last:mb-0 border-b border-slate-900/50 pb-1 last:border-0 last:pb-0">
                    {log}
                  </div>
                ))}
              </div>
            </details>
          )}

        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-2 border-t border-border mt-2">
          {isLoading ? (
             <span className="text-xs text-muted-foreground self-center">Aguarde...</span>
          ) : (
            <>
              <button 
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-muted rounded-md transition-colors"
              >
                Fechar
              </button>
              {isError && (
                <button 
                  onClick={onRetry}
                  className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 rounded-md transition-colors shadow-sm"
                >
                  Tentar Novamente
                </button>
              )}
              {isSuccess && (
                <button 
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 rounded-md transition-colors shadow-sm"
                >
                  OK
                </button>
              )}
            </>
          )}
        </div>

      </div>
    </div>
  );
};

export default EmailTestDialog;