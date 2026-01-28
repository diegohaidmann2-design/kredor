import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useModal } from '../components/Modal';
import { motion } from 'framer-motion';
import {
  Shield,
  Mail,
  RefreshCw,
  ArrowLeft,
  Clock,
  AlertCircle
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { authAPI } from '../api/api';

const Verify2FA = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const modal = useModal();

  const email = location.state?.email || '';
  const [code, setCode] = useState(['', '', '', '', '', '']);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState('');
  const [countdown, setCountdown] = useState(600); // 10 minutos em segundos
  const [canResend, setCanResend] = useState(false);
  const [resendCountdown, setResendCountdown] = useState(60); // 1 minuto para reenvio

  const inputRefs = useRef([]);

  // Redirecionar se não tiver email
  useEffect(() => {
    if (!email) {
      navigate('/login');
    }
  }, [email, navigate]);

  // Countdown do código (10 minutos)
  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          setError('Código expirado. Solicite um novo código.');
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // Countdown para reenvio (1 minuto)
  useEffect(() => {
    if (resendCountdown > 0) {
      const timer = setInterval(() => {
        setResendCountdown((prev) => {
          if (prev <= 1) {
            setCanResend(true);
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);

      return () => clearInterval(timer);
    }
  }, [resendCountdown]);

  const handleChange = (index, value) => {
    // Permitir apenas números
    if (value && !/^\d$/.test(value)) return;

    const newCode = [...code];
    newCode[index] = value;
    setCode(newCode);
    setError('');

    // Mover para o próximo input automaticamente
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // Auto-submit quando todos os 6 dígitos forem preenchidos
    if (newCode.every(digit => digit !== '') && index === 5) {
      handleSubmit(newCode.join(''));
    }
  };

  const handleKeyDown = (index, e) => {
    // Backspace - voltar para input anterior
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').trim();

    // Verificar se são 6 dígitos
    if (/^\d{6}$/.test(pastedData)) {
      const newCode = pastedData.split('');
      setCode(newCode);
      setError('');

      // Focar no último input
      inputRefs.current[5]?.focus();

      // Auto-submit
      handleSubmit(pastedData);
    }
  };

  const handleSubmit = async (codeString) => {
    const finalCode = codeString || code.join('');

    if (finalCode.length !== 6) {
      setError('Por favor, digite o código completo de 6 dígitos');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await authAPI.verify2FA({
        email,
        codigo: finalCode
      });

      // Login bem-sucedido
      if (response.data.access_token) {
        // Salvar token
        localStorage.setItem('token', response.data.access_token);
        if (response.data.refresh_token) {
          localStorage.setItem('refresh_token', response.data.refresh_token);
        }

        // Atualizar usuário no contexto
        setUser(response.data.usuario);

        // Redirecionar para dashboard
        navigate('/');
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Código inválido. Tente novamente.';
      setError(errorMsg);

      // Limpar código em caso de erro
      setCode(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (!canResend) return;

    setResending(true);
    setError('');

    try {
      await authAPI.resend2FA({ email });

      modal.success(
        'Código Reenviado',
        'Um novo código foi enviado para seu email.'
      );

      // Resetar countdowns
      setCountdown(600); // 10 minutos
      setResendCountdown(60); // 1 minuto
      setCanResend(false);

      // Limpar código atual
      setCode(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Erro ao reenviar código. Tente novamente.';
      setError(errorMsg);
    } finally {
      setResending(false);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-blue-50 dark:from-gray-900 dark:via-gray-800 dark:to-purple-900 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: "spring" }}
            className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-purple-500 to-blue-600 rounded-full mb-4"
          >
            <Shield className="w-8 h-8 text-white" />
          </motion.div>

          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Verificação de Dois Fatores
          </h1>

          <p className="text-gray-600 dark:text-gray-400">
            Digite o código de 6 dígitos enviado para
          </p>
          <p className="text-purple-600 dark:text-purple-400 font-medium flex items-center justify-center gap-2 mt-1">
            <Mail className="w-4 h-4" />
            {email}
          </p>
        </div>

        {/* Card principal */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8"
        >
          {/* Countdown */}
          <div className="flex items-center justify-center gap-2 mb-6 text-sm">
            <Clock className="w-4 h-4 text-gray-500" />
            <span className="text-gray-600 dark:text-gray-400">
              Código expira em:{' '}
              <span className={`font-mono font-bold ${countdown < 60 ? 'text-red-500' : 'text-purple-600 dark:text-purple-400'}`}>
                {formatTime(countdown)}
              </span>
            </span>
          </div>

          {/* Input de código */}
          <div className="flex justify-center gap-2 mb-6">
            {code.map((digit, index) => (
              <input
                key={index}
                ref={(el) => (inputRefs.current[index] = el)}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={digit}
                onChange={(e) => handleChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                onPaste={index === 0 ? handlePaste : undefined}
                className={`w-12 h-14 text-center text-2xl font-bold border-2 rounded-lg transition-all
                  ${error
                    ? 'border-red-500 bg-red-50 dark:bg-red-900/20'
                    : 'border-gray-300 dark:border-gray-600 focus:border-purple-500 dark:focus:border-purple-400'
                  }
                  bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                  focus:outline-none focus:ring-2 focus:ring-purple-500/20
                  disabled:opacity-50 disabled:cursor-not-allowed
                `}
                disabled={loading || countdown === 0}
                autoFocus={index === 0}
              />
            ))}
          </div>

          {/* Mensagem de erro */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-start gap-2 p-3 mb-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
            >
              <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-red-700 dark:text-red-400">{error}</p>
            </motion.div>
          )}

          {/* Botão de verificar */}
          <Button
            onClick={() => handleSubmit()}
            disabled={loading || code.some(d => d === '') || countdown === 0}
            className="w-full mb-4"
          >
            {loading ? 'Verificando...' : 'Verificar Código'}
          </Button>

          {/* Botão de reenviar */}
          <div className="text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              Não recebeu o código?
            </p>
            <Button
              variant="ghost"
              onClick={handleResend}
              disabled={!canResend || resending}
              className="text-purple-600 dark:text-purple-400 hover:text-purple-700 dark:hover:text-purple-300"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${resending ? 'animate-spin' : ''}`} />
              {resending
                ? 'Reenviando...'
                : canResend
                  ? 'Reenviar Código'
                  : `Reenviar em ${resendCountdown}s`
              }
            </Button>
          </div>

          {/* Dicas de segurança */}
          <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 font-semibold">
              💡 Dicas de Segurança:
            </p>
            <ul className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
              <li>• Nunca compartilhe este código com ninguém</li>
              <li>• Você tem 3 tentativas para inserir o código correto</li>
              <li>• O código é válido por 10 minutos</li>
            </ul>
          </div>
        </motion.div>

        {/* Voltar ao login */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="text-center mt-6"
        >
          <Button
            variant="ghost"
            onClick={() => navigate('/login')}
            className="text-gray-600 dark:text-gray-400"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Voltar ao Login
          </Button>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default Verify2FA;
