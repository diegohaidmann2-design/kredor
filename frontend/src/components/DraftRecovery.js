/**
 * DraftRecovery - Componente de recuperação de rascunhos
 * Modal que aparece quando detecta rascunho salvo
 */
import React from 'react';
import { formatRelativeTime } from '../utils/storageUtils';

const DraftRecovery = ({ 
  isOpen, 
  onRecover, 
  onDiscard, 
  draftTimestamp,
  title = 'Rascunho Encontrado',
  description = 'Encontramos um rascunho salvo anteriormente.'
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onDiscard}
      />
      
      {/* Modal */}
      <div className="relative bg-card rounded-lg shadow-xl max-w-md w-full border border-border animate-in fade-in zoom-in duration-200">
        {/* Header */}
        <div className="p-6 border-b border-border">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-blue-500/10 flex items-center justify-center">
              <svg className="w-6 h-6 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-foreground">
                {title}
              </h3>
              <p className="text-sm text-muted-foreground mt-1">
                {description}
              </p>
              {draftTimestamp && (
                <p className="text-xs text-muted-foreground mt-2">
                  <span className="inline-flex items-center gap-1">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Salvo {formatRelativeTime(draftTimestamp)}
                  </span>
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="p-6">
          <div className="bg-blue-500/5 border border-blue-500/20 rounded-lg p-4 mb-4">
            <div className="flex gap-2">
              <svg className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="text-sm text-foreground">
                <p className="font-medium mb-1">O que você deseja fazer?</p>
                <ul className="text-muted-foreground space-y-1 text-xs">
                  <li>• <strong>Recuperar:</strong> Continua de onde parou</li>
                  <li>• <strong>Descartar:</strong> Começa um novo formulário</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={onDiscard}
              className="flex-1 px-4 py-2.5 bg-background border border-border text-foreground rounded-lg hover:bg-muted/50 transition font-medium"
            >
              Descartar
            </button>
            <button
              onClick={onRecover}
              className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium flex items-center justify-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Recuperar Dados
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Badge de status de salvamento
 */
export const SaveStatusBadge = ({ 
  isSaving, 
  lastSaved, 
  hasUnsavedChanges,
  onClearDraft 
}) => {
  if (isSaving) {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-500/10 border border-blue-500/20 rounded-full text-xs text-blue-600">
        <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600"></div>
        <span>Salvando...</span>
      </div>
    );
  }

  if (lastSaved) {
    return (
      <div className="inline-flex items-center gap-2">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-green-500/10 border border-green-500/20 rounded-full text-xs text-green-600">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span>Salvo {formatRelativeTime(lastSaved)}</span>
        </div>
        {onClearDraft && (
          <button
            onClick={onClearDraft}
            className="text-xs text-muted-foreground hover:text-foreground transition"
            title="Limpar rascunho"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        )}
      </div>
    );
  }

  if (hasUnsavedChanges) {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-yellow-500/10 border border-yellow-500/20 rounded-full text-xs text-yellow-600">
        <div className="w-2 h-2 rounded-full bg-yellow-600 animate-pulse"></div>
        <span>Alterações não salvas</span>
      </div>
    );
  }

  return null;
};

export default DraftRecovery;
