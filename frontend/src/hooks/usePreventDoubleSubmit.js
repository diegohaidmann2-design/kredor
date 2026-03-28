import { useState, useCallback, useRef } from 'react';

/**
 * Hook para prevenir duplo submit em formulários e ações
 * 
 * @param {number} delay - Tempo em ms para bloquear novos cliques (padrão: 2000ms)
 * @returns {object} - { isSubmitting, handleSubmit }
 */
export const usePreventDoubleSubmit = (delay = 2000) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const timeoutRef = useRef(null);

  const handleSubmit = useCallback(async (callback) => {
    // Se já está processando, ignora
    if (isSubmitting) {
      return;
    }

    setIsSubmitting(true);

    try {
      await callback();
    } catch (error) {
      throw error;
    } finally {
      // Aguarda o delay antes de permitir novo submit
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      
      timeoutRef.current = setTimeout(() => {
        setIsSubmitting(false);
      }, delay);
    }
  }, [isSubmitting, delay]);

  const reset = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setIsSubmitting(false);
  }, []);

  return { isSubmitting, handleSubmit, reset };
};

/**
 * Hook simples para prevenir cliques duplos em botões
 * 
 * @param {number} delay - Tempo em ms para bloquear novos cliques (padrão: 1000ms)
 * @returns {object} - { isClicking, handleClick }
 */
export const usePreventDoubleClick = (delay = 1000) => {
  const [isClicking, setIsClicking] = useState(false);
  const timeoutRef = useRef(null);

  const handleClick = useCallback((callback) => {
    if (isClicking) {
      return;
    }

    setIsClicking(true);

    // Executa o callback
    if (callback) {
      callback();
    }

    // Aguarda o delay antes de permitir novo clique
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    
    timeoutRef.current = setTimeout(() => {
      setIsClicking(false);
    }, delay);
  }, [isClicking, delay]);

  return { isClicking, handleClick };
};

export default usePreventDoubleSubmit;
