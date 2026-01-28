import React from 'react';
import { cn } from '../lib/utils';

const Button = ({
  children,
  type = 'button',
  variant = 'primary',
  disabled = false,
  className = '',
  onClick,
  testId
}) => {
  const baseClasses = 'inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed';
  
  const variants = {
    primary: 'bg-primary text-primary-foreground hover:bg-primary/90 shadow-glow',
    secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
    danger: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
    outline: 'border border-border bg-transparent text-foreground hover:bg-accent',
    ghost: 'bg-transparent text-foreground hover:bg-accent',
    success: 'bg-primary text-primary-foreground hover:bg-primary/90',
  };

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={cn(baseClasses, variants[variant], className)}
      data-testid={testId}
    >
      {children}
    </button>
  );
};

export default Button;
