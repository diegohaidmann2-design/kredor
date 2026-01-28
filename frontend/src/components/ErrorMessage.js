import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from './ui/button';

const ErrorMessage = ({ message, onRetry }) => {
  return (
    <div className="p-4 bg-destructive/10 border border-destructive/20 rounded-xl flex items-center gap-3">
      <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0" />
      <span className="text-destructive flex-1">{message}</span>
      {onRetry && (
        <Button 
          variant="outline" 
          size="sm" 
          onClick={onRetry}
          className="border-destructive/20 text-destructive hover:bg-destructive/10"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Tentar novamente
        </Button>
      )}
    </div>
  );
};

export default ErrorMessage;
