import React from 'react';
import { Plus } from 'lucide-react';
import { Button } from './ui/button';

const Header = ({ title, subtitle, action }) => {
  return (
    <div className="sticky top-0 z-30 bg-background/80 backdrop-blur-xl border-b border-border px-4 sm:px-6 py-3 sm:py-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4">
        <div className="min-w-0">
          <h1 className="text-xl sm:text-2xl font-display font-bold text-foreground tracking-tight truncate">
            {title}
          </h1>
          {subtitle && (
            <p className="text-xs sm:text-sm text-muted-foreground mt-0.5 sm:mt-1 truncate">{subtitle}</p>
          )}
        </div>
        {action && (
          <>
            {/* Se action é um componente React, renderize diretamente */}
            {React.isValidElement(action) ? (
              action
            ) : (
              /* Senão, renderize como objeto com label e onClick */
              <Button 
                onClick={action.onClick}
                className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-glow w-full sm:w-auto"
                size="sm"
              >
                <Plus className="w-4 h-4 mr-2" />
                <span className="truncate">{action.label}</span>
              </Button>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default Header;
