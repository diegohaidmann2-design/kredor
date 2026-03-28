import React, { useState, useRef } from 'react';
import { cn } from '../lib/utils';

const Button = ({
  children,
  type = 'button',
  variant = 'primary',
  disabled = false,
  className = '',
  onClick,
  testId,
  preventDoubleClick = false, // Proteção DESATIVADA por padrão (usar loading manual)
  doubleClickDelay = 1000, // 1 segundo de delay padrão
  loading = false // Estado de loading externo
}) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const timeoutRef = useRef(null);

  const handleClick = async (e) => {
    // Se proteção está ativada e já está processando, ignora
    if (preventDoubleClick && isProcessing) {
      e.preventDefault();
      return;
    }

    // Marca como processando
    if (preventDoubleClick) {
      setIsProcessing(true);
    }

    // Executa o onClick original
    if (onClick) {
      try {
        await onClick(e);
      } catch (error) {
        console.error('Erro no onClick:', error);
      }
    }

    // Aguarda o delay antes de permitir novo clique
    if (preventDoubleClick) {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      
      timeoutRef.current = setTimeout(() => {
        setIsProcessing(false);
      }, doubleClickDelay);
    }
  };

  const baseClasses = 'inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed';
  
  const variants = {
    primary: 'bg-primary text-primary-foreground hover:bg-primary/90 shadow-glow',
    secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
    danger: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
    outline: 'border border-border bg-transparent text-foreground hover:bg-accent',
    ghost: 'bg-transparent text-foreground hover:bg-accent',
    success: 'bg-primary text-primary-foreground hover:bg-primary/90',
  };

  const isDisabled = disabled || loading || (preventDoubleClick && isProcessing);

  return (
    <button
      type={type}
      disabled={isDisabled}
      onClick={handleClick}
      className={cn(baseClasses, variants[variant], className)}
      data-testid={testId}
    >
      {loading || isProcessing ? (
        <>
          <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {children}
        </>
      ) : (
        children
      )}
    </button>
  );
};

export default Button;
