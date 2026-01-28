/**
 * Utilitários de Timezone - São Paulo/Brasil
 * 
 * Todas as datas do backend vêm em UTC.
 * Este módulo converte para o fuso de São Paulo na exibição.
 */

import { format, parseISO } from 'date-fns';
import { toZonedTime, fromZonedTime } from 'date-fns-tz';
import { ptBR } from 'date-fns/locale';

const TIMEZONE_SP = 'America/Sao_Paulo';

/**
 * Converte datetime UTC (do backend) para São Paulo
 * @param {string|Date} dateString - Data em UTC (ISO string ou Date object)
 * @returns {Date} Data no fuso de São Paulo
 */
export const toSaoPaulo = (dateString) => {
  if (!dateString) return null;
  
  const date = typeof dateString === 'string' ? parseISO(dateString) : dateString;
  return toZonedTime(date, TIMEZONE_SP);
};

/**
 * Formata data no padrão brasileiro
 * @param {string|Date} dateString - Data em UTC
 * @param {boolean} includeTime - Incluir hora (padrão: true)
 * @returns {string} Data formatada (ex: "21/01/2026 13:30")
 */
export const formatDateBR = (dateString, includeTime = true) => {
  if (!dateString) return '-';
  
  try {
    const date = toSaoPaulo(dateString);
    const pattern = includeTime ? 'dd/MM/yyyy HH:mm' : 'dd/MM/yyyy';
    
    return format(date, pattern, { locale: ptBR });
  } catch (error) {
    console.error('Erro ao formatar data:', error);
    return '-';
  }
};

/**
 * Formata data por extenso
 * @param {string|Date} dateString - Data em UTC
 * @returns {string} Data formatada (ex: "21 de janeiro de 2026")
 */
export const formatDateLong = (dateString) => {
  if (!dateString) return '-';
  
  try {
    const date = toSaoPaulo(dateString);
    return format(date, "dd 'de' MMMM 'de' yyyy", { locale: ptBR });
  } catch (error) {
    console.error('Erro ao formatar data por extenso:', error);
    return '-';
  }
};

/**
 * Formata data e hora com segundos
 * @param {string|Date} dateString - Data em UTC
 * @returns {string} Data formatada (ex: "21/01/2026 13:30:45")
 */
export const formatDateTimeFull = (dateString) => {
  if (!dateString) return '-';
  
  try {
    const date = toSaoPaulo(dateString);
    return format(date, 'dd/MM/yyyy HH:mm:ss', { locale: ptBR });
  } catch (error) {
    console.error('Erro ao formatar data completa:', error);
    return '-';
  }
};

/**
 * Formata apenas a hora
 * @param {string|Date} dateString - Data em UTC
 * @returns {string} Hora formatada (ex: "13:30")
 */
export const formatTime = (dateString) => {
  if (!dateString) return '-';
  
  try {
    const date = toSaoPaulo(dateString);
    return format(date, 'HH:mm', { locale: ptBR });
  } catch (error) {
    console.error('Erro ao formatar hora:', error);
    return '-';
  }
};

/**
 * Formata data relativa (ex: "há 2 dias", "em 3 horas")
 * Requer date-fns/formatDistanceToNow
 */
export const formatDateRelative = (dateString) => {
  if (!dateString) return '-';
  
  try {
    const { formatDistanceToNow } = require('date-fns');
    const date = toSaoPaulo(dateString);
    return formatDistanceToNow(date, { addSuffix: true, locale: ptBR });
  } catch (error) {
    console.error('Erro ao formatar data relativa:', error);
    return '-';
  }
};

/**
 * Converte input do usuário (São Paulo) para UTC (para enviar ao backend)
 * @param {Date} date - Data no fuso de São Paulo
 * @returns {Date} Data em UTC
 */
export const toUTC = (date) => {
  if (!date) return null;
  return fromZonedTime(date, TIMEZONE_SP);
};

/**
 * Data e hora atual em São Paulo
 * @returns {Date} Data atual no fuso de São Paulo
 */
export const nowSP = () => {
  return toZonedTime(new Date(), TIMEZONE_SP);
};

/**
 * Data e hora atual em UTC
 * @returns {Date} Data atual em UTC
 */
export const nowUTC = () => {
  return new Date();
};

/**
 * Obtém informações sobre o fuso horário
 * @returns {Object} Informações do timezone
 */
export const getTimezoneInfo = () => {
  const now = new Date();
  const nowSP = toSaoPaulo(now);
  const offset = nowSP.getTimezoneOffset() / -60;
  
  return {
    timezone: TIMEZONE_SP,
    offsetHours: offset,
    offsetStr: offset >= 0 ? `+${offset}:00` : `${offset}:00`,
    currentTime: formatDateBR(now),
    userTimezone: Intl.DateTimeFormat().resolvedOptions().timeZone
  };
};

/**
 * Verifica se uma data é hoje (no fuso de SP)
 * @param {string|Date} dateString - Data a verificar
 * @returns {boolean} True se é hoje
 */
export const isToday = (dateString) => {
  if (!dateString) return false;
  
  try {
    const date = toSaoPaulo(dateString);
    const today = nowSP();
    
    return (
      date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear()
    );
  } catch (error) {
    return false;
  }
};

export default {
  toSaoPaulo,
  formatDateBR,
  formatDateLong,
  formatDateTimeFull,
  formatTime,
  formatDateRelative,
  toUTC,
  nowSP,
  nowUTC,
  getTimezoneInfo,
  isToday,
  TIMEZONE_SP
};
