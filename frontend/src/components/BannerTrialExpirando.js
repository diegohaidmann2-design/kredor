import React from 'react';
import { Clock, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from './ui/button';

const BannerTrialExpirando = ({ diasRestantes }) => {
  const urgente = diasRestantes <= 1;

  return (
    <div className={`${
      urgente 
        ? 'bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500' 
        : 'bg-orange-50 dark:bg-orange-900/20 border-l-4 border-orange-400'
    } p-4 mb-6`}>
      <div className="flex items-start gap-3">
        <Clock className={`w-5 h-5 ${
          urgente ? 'text-red-600 dark:text-red-400' : 'text-orange-600 dark:text-orange-400'
        } mt-0.5 flex-shrink-0`} />
        
        <div className="flex-1">
          <h3 className={`font-semibold ${
            urgente ? 'text-red-800 dark:text-red-200' : 'text-orange-800 dark:text-orange-200'
          } mb-1`}>
            {urgente ? '⚠️ Seu trial acaba hoje!' : `Seu trial acaba em ${diasRestantes} ${diasRestantes === 1 ? 'dia' : 'dias'}`}
          </h3>
          <p className={`text-sm ${
            urgente ? 'text-red-700 dark:text-red-300' : 'text-orange-700 dark:text-orange-300'
          } mb-3`}>
            {urgente 
              ? 'Não perca acesso! Assine agora para continuar usando o Gestor Cred e manter todos os seus dados.' 
              : 'Assine um plano para continuar usando todas as funcionalidades sem interrupção.'
            }
          </p>
          
          <Link to="/assinatura">
            <Button
              size="sm"
              className={urgente ? 'bg-red-600 hover:bg-red-700' : 'bg-orange-600 hover:bg-orange-700'}
            >
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
