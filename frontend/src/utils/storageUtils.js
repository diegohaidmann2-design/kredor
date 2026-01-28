/**
 * Storage Utils - Sistema de armazenamento seguro com criptografia
 * Usa AES-256 para proteger dados sensíveis no localStorage
 */
import CryptoJS from 'crypto-js';

// Chave de criptografia (em produção, use variável de ambiente)
const ENCRYPTION_KEY = process.env.REACT_APP_STORAGE_KEY || 'jurofacil-secure-key-2026';

// Prefixos para organização
const DRAFT_PREFIX = 'draft_';
const TIMESTAMP_PREFIX = 'timestamp_';

/**
 * Criptografa dados usando AES-256
 */
const encrypt = (data) => {
  try {
    const jsonString = JSON.stringify(data);
    return CryptoJS.AES.encrypt(jsonString, ENCRYPTION_KEY).toString();
  } catch (error) {
    console.error('Erro ao criptografar:', error);
    return null;
  }
};

/**
 * Descriptografa dados
 */
const decrypt = (encryptedData) => {
  try {
    const bytes = CryptoJS.AES.decrypt(encryptedData, ENCRYPTION_KEY);
    const decryptedString = bytes.toString(CryptoJS.enc.Utf8);
    return JSON.parse(decryptedString);
  } catch (error) {
    console.error('Erro ao descriptografar:', error);
    return null;
  }
};

/**
 * Sanitiza dados para evitar XSS
 */
const sanitize = (data) => {
  if (typeof data === 'string') {
    return data.replace(/[<>]/g, '');
  }
  if (typeof data === 'object' && data !== null) {
    const sanitized = {};
    Object.keys(data).forEach(key => {
      sanitized[key] = sanitize(data[key]);
    });
    return sanitized;
  }
  return data;
};

/**
 * Verifica se localStorage está disponível
 */
const isLocalStorageAvailable = () => {
  try {
    const test = '__storage_test__';
    localStorage.setItem(test, test);
    localStorage.removeItem(test);
    return true;
  } catch (e) {
    return false;
  }
};

/**
 * Salva rascunho criptografado
 */
export const saveDraft = (key, data, encrypt_data = true) => {
  if (!isLocalStorageAvailable()) {
    console.warn('localStorage não disponível');
    return false;
  }

  try {
    const sanitizedData = sanitize(data);
    const dataToStore = encrypt_data ? encrypt(sanitizedData) : JSON.stringify(sanitizedData);
    
    if (!dataToStore) {
      throw new Error('Falha ao processar dados');
    }

    localStorage.setItem(`${DRAFT_PREFIX}${key}`, dataToStore);
    localStorage.setItem(`${TIMESTAMP_PREFIX}${key}`, new Date().toISOString());
    return true;
  } catch (error) {
    console.error('Erro ao salvar rascunho:', error);
    
    // Se localStorage está cheio, limpar rascunhos antigos
    if (error.name === 'QuotaExceededError') {
      clearOldDrafts();
      // Tentar novamente
      try {
        const sanitizedData = sanitize(data);
        const dataToStore = encrypt_data ? encrypt(sanitizedData) : JSON.stringify(sanitizedData);
        localStorage.setItem(`${DRAFT_PREFIX}${key}`, dataToStore);
        localStorage.setItem(`${TIMESTAMP_PREFIX}${key}`, new Date().toISOString());
        return true;
      } catch (retryError) {
        console.error('Erro ao salvar após limpeza:', retryError);
        return false;
      }
    }
    return false;
  }
};

/**
 * Recupera rascunho descriptografado
 */
export const getDraft = (key, decrypt_data = true) => {
  if (!isLocalStorageAvailable()) {
    return null;
  }

  try {
    const stored = localStorage.getItem(`${DRAFT_PREFIX}${key}`);
    if (!stored) return null;

    const data = decrypt_data ? decrypt(stored) : JSON.parse(stored);
    
    // Validar integridade dos dados
    if (!data || typeof data !== 'object') {
      console.warn('Dados corrompidos detectados');
      removeDraft(key);
      return null;
    }

    return data;
  } catch (error) {
    console.error('Erro ao recuperar rascunho:', error);
    // Se dados estão corrompidos, remove
    removeDraft(key);
    return null;
  }
};

/**
 * Verifica se existe rascunho
 */
export const hasDraft = (key) => {
  if (!isLocalStorageAvailable()) return false;
  return localStorage.getItem(`${DRAFT_PREFIX}${key}`) !== null;
};

/**
 * Remove rascunho específico
 */
export const removeDraft = (key) => {
  if (!isLocalStorageAvailable()) return;
  
  try {
    localStorage.removeItem(`${DRAFT_PREFIX}${key}`);
    localStorage.removeItem(`${TIMESTAMP_PREFIX}${key}`);
  } catch (error) {
    console.error('Erro ao remover rascunho:', error);
  }
};

/**
 * Obtém timestamp do rascunho
 */
export const getDraftTimestamp = (key) => {
  if (!isLocalStorageAvailable()) return null;
  
  const timestamp = localStorage.getItem(`${TIMESTAMP_PREFIX}${key}`);
  return timestamp ? new Date(timestamp) : null;
};

/**
 * Limpa rascunhos antigos (mais de 24h)
 */
export const clearOldDrafts = (maxAgeHours = 24) => {
  if (!isLocalStorageAvailable()) return 0;

  let cleaned = 0;
  const now = new Date();
  const maxAge = maxAgeHours * 60 * 60 * 1000; // em ms

  try {
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith(TIMESTAMP_PREFIX)) {
        const draftKey = key.replace(TIMESTAMP_PREFIX, '');
        const timestamp = new Date(localStorage.getItem(key));
        
        if (now - timestamp > maxAge) {
          removeDraft(draftKey);
          cleaned++;
        }
      }
    });
  } catch (error) {
    console.error('Erro ao limpar rascunhos antigos:', error);
  }

  return cleaned;
};

/**
 * Lista todos os rascunhos disponíveis
 */
export const listDrafts = () => {
  if (!isLocalStorageAvailable()) return [];

  const drafts = [];
  
  try {
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith(DRAFT_PREFIX)) {
        const draftKey = key.replace(DRAFT_PREFIX, '');
        const timestamp = getDraftTimestamp(draftKey);
        drafts.push({
          key: draftKey,
          timestamp,
          age: timestamp ? new Date() - timestamp : null
        });
      }
    });
  } catch (error) {
    console.error('Erro ao listar rascunhos:', error);
  }

  return drafts;
};

/**
 * Formata tempo relativo (ex: "há 5 minutos")
 */
export const formatRelativeTime = (date) => {
  if (!date) return '';
  
  const now = new Date();
  const diff = now - date;
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (seconds < 60) return 'agora mesmo';
  if (minutes < 60) return `há ${minutes} minuto${minutes > 1 ? 's' : ''}`;
  if (hours < 24) return `há ${hours} hora${hours > 1 ? 's' : ''}`;
  return `há ${days} dia${days > 1 ? 's' : ''}`;
};

export default {
  saveDraft,
  getDraft,
  hasDraft,
  removeDraft,
  getDraftTimestamp,
  clearOldDrafts,
  listDrafts,
  formatRelativeTime
};
