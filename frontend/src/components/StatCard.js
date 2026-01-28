import React from 'react';
import { Card, CardContent } from './ui/card';

const StatCard = ({ title, value, color = 'primary', subtitle, icon, testId }) => {
  const colorClasses = {
    blue: 'text-blue-400',
    green: 'text-primary',
    red: 'text-destructive',
    yellow: 'text-warning',
    purple: 'text-purple-400',
    indigo: 'text-indigo-400',
    primary: 'text-primary'
  };

  const bgClasses = {
    blue: 'bg-blue-500/10',
    green: 'bg-primary/10',
    red: 'bg-destructive/10',
    yellow: 'bg-warning/10',
    purple: 'bg-purple-500/10',
    indigo: 'bg-indigo-500/10',
    primary: 'bg-primary/10'
  };

  return (
    <Card 
      className="overflow-hidden transition-all duration-300 hover:shadow-lg hover:shadow-primary/5"
      data-testid={testId}
    >
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className={`text-2xl font-display font-bold tracking-tight ${colorClasses[color] || colorClasses.primary}`}>
              {value}
            </p>
            {subtitle && (
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            )}
          </div>
          {icon && (
            <div className={`p-3 rounded-xl ${bgClasses[color] || bgClasses.primary} ${colorClasses[color] || colorClasses.primary}`}>
              {icon}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default StatCard;
