import React from 'react';
import { Link } from 'react-router-dom';
import { Lock, ArrowRight, CheckCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';

const AssinaturaExpirada = ({ tipo = 'trial', dataExpiracao }) => {
  const isTrial = tipo === 'trial';

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900 flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl">
        <CardContent className="p-8">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-red-100 dark:bg-red-900/20 mb-4">
              <Lock className="w-10 h-10 text-red-600 dark:text-red-400" />
            </div>
            
            <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">
              {isTrial ? 'Seu período de testes expirou' : 'Sua assinatura expirou'}
            </h1>
            
            <p className="text-lg text-slate-600 dark:text-slate-400 mb-1">
              {isTrial 
                ? `O trial gratuito de 7 dias terminou em ${dataExpiracao || 'hoje'}.`
                : `Sua assinatura venceu em ${dataExpiracao || 'hoje'}.`
              }
            </p>
            
            <p className="text-slate-600 dark:text-slate-400">
              Mas não se preocupe! Seus dados estão <strong className="text-green-600 dark:text-green-400">100% seguros</strong>.
            </p>
          </div>

          <div className="bg-slate-50 dark:bg-slate-800 rounded-lg p-6 mb-6">
            <h3 className="font-semibold text-slate-900 dark:text-white mb-3">
              💚 Seus dados estão protegidos
            </h3>
            <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
              <li className="flex items-start gap-2">
                <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                <span>Todos os clientes cadastrados</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                <span>Histórico completo de empréstimos</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                <span>Todos os pagamentos registrados</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                <span>Relatórios e documentos gerados</span>
              </li>
            </ul>
          </div>

          <div className="border-t border-slate-200 dark:border-slate-700 pt-6">
            <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
              Escolha um plano para reativar sua conta:
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="border border-slate-200 dark:border-slate-700 rounded-lg p-4 text-center">
                <h4 className="font-semibold mb-1">Básico</h4>
                <p className="text-2xl font-bold text-primary mb-1">R$ 97</p>
                <p className="text-xs text-slate-500 mb-2">/mês</p>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Até 50 clientes
                </p>
              </div>
              
              <div className="border-2 border-primary rounded-lg p-4 text-center relative">
                <span className="absolute -top-3 left-1/2 transform -translate-x-1/2 bg-primary text-white text-xs px-3 py-1 rounded-full">
                  Popular
                </span>
                <h4 className="font-semibold mb-1">Profissional</h4>
                <p className="text-2xl font-bold text-primary mb-1">R$ 197</p>
                <p className="text-xs text-slate-500 mb-2">/mês</p>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Até 200 clientes
                </p>
              </div>
              
              <div className="border border-slate-200 dark:border-slate-700 rounded-lg p-4 text-center">
                <h4 className="font-semibold mb-1">Enterprise</h4>
                <p className="text-2xl font-bold text-primary mb-1">R$ 497</p>
                <p className="text-xs text-slate-500 mb-2">/mês</p>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Ilimitado
                </p>
              </div>
            </div>

            <Link to="/assinatura">
              <Button className="w-full bg-primary hover:bg-primary/90 text-white text-lg py-6">
                Ver Todos os Planos e Reativar
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </Link>

            <p className="text-center text-xs text-slate-500 mt-4">
              Ao reativar, você terá acesso imediato a todos os seus dados.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AssinaturaExpirada;
