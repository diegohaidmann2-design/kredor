import React from 'react';
import { Clock, AlertTriangle, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from './ui/button';

const BannerTrialExpirando = ({ diasRestantes }) => {
  const urgente = diasRestantes <= 1;
  const Icon = urgente ? AlertTriangle : Clock;

  return (
    <div
      className={`rounded-xl ring-1 ring-inset p-5 mb-6 ${
        urgente
          ? 'bg-rose-500/10 ring-rose-500/20'
          : 'bg-amber-500/10 ring-amber-500/20'
      }`}
      data-testid="banner-trial-expirando"
    >
      <div className="flex items-start gap-3">
        <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${urgente ? 'text-rose-500' : 'text-amber-500'}`} strokeWidth={1.5} />

        <div className="flex-1">
          <h3 className={`font-cabinet font-bold mb-1 ${urgente ? 'text-rose-500' : 'text-amber-500'}`}>
            {urgente ? 'Seu trial acaba hoje' : `Seu trial acaba em ${diasRestantes} ${diasRestantes === 1 ? 'dia' : 'dias'}`}
          </h3>
          <p className="text-sm text-muted-foreground mb-3">
            {urgente
              ? 'Não perca acesso! Assine agora para continuar usando o Kredor e manter todos os seus dados.'
              : 'Assine um plano para continuar usando todas as funcionalidades sem interrupção.'}
          </p>

          <Link to="/assinatura">
            <Button size="sm" className={urgente ? 'bg-rose-600 hover:bg-rose-700' : 'bg-amber-600 hover:bg-amber-700'}>
              Ver Planos
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default BannerTrialExpirando;
