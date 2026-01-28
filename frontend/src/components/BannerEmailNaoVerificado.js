import React, { useState } from 'react';
import { AlertCircle, X, Mail } from 'lucide-react';
import { Button } from './ui/button';

const BannerEmailNaoVerificado = ({ onReenviar }) => {
  const [reenvando, setReenviando] = useState(false);
  const [fechado, setFechado] = useState(false);
  const [mensagem, setMensagem] = useState('');

  const handleReenviar = async () => {
    setReenviando(true);
    setMensagem('');
    
    try {
      await onReenviar();
      setMensagem('Email reenviado com sucesso! Verifique sua caixa de entrada.');
    } catch (err) {
      setMensagem('Erro ao reenviar. Tente novamente.');
    } finally {
      setReenviando(false);
    }
  };

  if (fechado) return null;

  return (
    <div className="bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-400 p-4 mb-6 relative">
      <button
        onClick={() => setFechado(true)}
        className="absolute top-2 right-2 text-yellow-600 hover:text-yellow-800 dark:text-yellow-400"
      >
        <X className="w-5 h-5" />
      </button>

      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5 flex-shrink-0" />
        
        <div className="flex-1">
          <h3 className="font-semibold text-yellow-800 dark:text-yellow-200 mb-1">
            Confirme seu email
          </h3>
          <p className="text-sm text-yellow-700 dark:text-yellow-300 mb-3">
            Enviamos um email de confirmação para você. Por favor, verifique sua caixa de entrada e confirme seu email para aproveitar todos os recursos.
          </p>
          
          <Button
            size="sm"
            variant="outline"
            onClick={handleReenviar}
            disabled={reenvando}
            className="border-yellow-600 text-yellow-700 hover:bg-yellow-100 dark:border-yellow-400 dark:text-yellow-300"
          >
            {reenvando ? (
              <>
                <Mail className="w-4 h-4 mr-2 animate-pulse" />
                Reenviando...
              </>
            ) : (
              <>
                <Mail className="w-4 h-4 mr-2" />
                Reenviar Email
              </>
            )}
          </Button>

          {mensagem && (
            <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-2">
              {mensagem}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default BannerEmailNaoVerificado;
