import React from 'react';
import { cn } from '../lib/utils';

const Input = ({
  label,
  type = 'text',
  name,
  value,
  onChange,
  placeholder,
  required = false,
  disabled = false,
  className = '',
  error,
  testId
}) => {
  return (
    <div className="space-y-2 mb-4">
      {label && (
        <label className="block text-sm font-medium text-foreground">
          {label}
          {required && <span className="text-destructive ml-1">*</span>}
        </label>
      )}
      <input
        type={type}
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        disabled={disabled}
        className={cn(
          'w-full px-4 py-2.5 rounded-xl border bg-background text-foreground placeholder:text-muted-foreground transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary',
          error ? 'border-destructive' : 'border-input',
          disabled && 'opacity-50 cursor-not-allowed',
          className
        )}
        data-testid={testId}
      />
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
    </div>
  );
};

export default Input;
