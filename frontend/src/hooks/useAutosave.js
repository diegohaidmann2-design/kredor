/**
 * useAutosave Hook - Sistema de autosave inteligente com debounce
 * Salva automaticamente dados do formulário no localStorage
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { saveDraft, getDraft, removeDraft, hasDraft, getDraftTimestamp } from '../utils/storageUtils';

/**
 * Hook de autosave
 * @param {string} key - Chave única para identificar o rascunho
 * @param {object} data - Dados a serem salvos
 * @param {object} options - Opções de configuração
 * @returns {object} - Estado e funções de controle
 */
export const useAutosave = (key, data, options = {}) => {
  const {
    enabled = true,
    delay = 3000, // 3 segundos de debounce
    encrypt = true,
    onSave = null,
    onRestore = null,
    skipEmpty = true // Não salva se dados estão vazios
  } = options;

  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const timeoutRef = useRef(null);
  const previousDataRef = useRef(null);

  /**
   * Verifica se dados estão vazios
   */
  const isDataEmpty = useCallback((obj) => {
    if (!obj || typeof obj !== 'object') return true;
    
    return Object.values(obj).every(value => {
      if (value === null || value === undefined || value === '') return true;
      if (typeof value === 'object') return isDataEmpty(value);
      return false;
    });
  }, []);

  /**
   * Salva rascunho com debounce
   */
  const saveWithDebounce = useCallback(() => {
    if (!enabled || !key) return;

    // Limpar timeout anterior
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Verificar se dados mudaram
    const dataString = JSON.stringify(data);
    if (dataString === previousDataRef.current) {
      return;
    }

    previousDataRef.current = dataString;
    setHasUnsavedChanges(true);

    // Não salvar se dados estão vazios
    if (skipEmpty && isDataEmpty(data)) {
      return;
    }

    // Criar novo timeout
    timeoutRef.current = setTimeout(() => {
      setIsSaving(true);

      try {
        const success = saveDraft(key, data, encrypt);
        
        if (success) {
          const now = new Date();
          setLastSaved(now);
          setHasUnsavedChanges(false);
          
          if (onSave) {
            onSave(data, now);
          }
        }
      } catch (error) {
        console.error('Erro ao salvar rascunho:', error);
      } finally {
        setIsSaving(false);
      }
    }, delay);
  }, [enabled, key, data, delay, encrypt, onSave, skipEmpty, isDataEmpty]);

  /**
   * Efeito de autosave
   */
  useEffect(() => {
    saveWithDebounce();

    // Cleanup
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [saveWithDebounce]);

  /**
   * Restaura rascunho salvo
   */
  const restore = useCallback(() => {
    if (!key) return null;

    try {
      const draft = getDraft(key, encrypt);
      
      if (draft) {
        const timestamp = getDraftTimestamp(key);
        setLastSaved(timestamp);
        
        if (onRestore) {
          onRestore(draft, timestamp);
        }
        
        return draft;
      }
      
      return null;
    } catch (error) {
      console.error('Erro ao restaurar rascunho:', error);
      return null;
    }
  }, [key, encrypt, onRestore]);

  /**
   * Limpa rascunho
   */
  const clear = useCallback(() => {
    if (!key) return;
    
    try {
      removeDraft(key);
      setLastSaved(null);
      setHasUnsavedChanges(false);
      previousDataRef.current = null;
    } catch (error) {
      console.error('Erro ao limpar rascunho:', error);
    }
  }, [key]);

  /**
   * Verifica se existe rascunho
   */
  const exists = useCallback(() => {
    if (!key) return false;
    return hasDraft(key);
  }, [key]);

  /**
   * Salva imediatamente (sem debounce)
   */
  const saveNow = useCallback(() => {
    if (!enabled || !key) return false;

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    if (skipEmpty && isDataEmpty(data)) {
      return false;
    }

    setIsSaving(true);

    try {
      const success = saveDraft(key, data, encrypt);
      
      if (success) {
        const now = new Date();
        setLastSaved(now);
        setHasUnsavedChanges(false);
        
        if (onSave) {
          onSave(data, now);
        }
      }
      
      return success;
    } catch (error) {
      console.error('Erro ao salvar imediatamente:', error);
      return false;
    } finally {
      setIsSaving(false);
    }
  }, [enabled, key, data, encrypt, onSave, skipEmpty, isDataEmpty]);

  return {
    isSaving,
    lastSaved,
    hasUnsavedChanges,
    restore,
    clear,
    exists,
    saveNow
  };
};

/**
 * Hook para aviso de saída com dados não salvos
 */
export const useUnsavedChangesWarning = (hasUnsavedChanges, message = 'Você tem alterações não salvas. Deseja realmente sair?') => {
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = message;
        return message;
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [hasUnsavedChanges, message]);
};

export default useAutosave;
