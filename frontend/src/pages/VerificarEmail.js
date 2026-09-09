import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mail,
  CheckCircle,
  XCircle,
  RefreshCw,
  ArrowRight,
  Loader2
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { authAPI } from '../api/api';

const VerificarEmail = () => {
  const { token } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState(token ? 'verifying' : 'pending'); // pending, verifying, success, error, resent
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const pollingIntervalRef = useRef(null);

  const email = searchParams.get('email');

  // Quando status mudar para success, fazer logout para forçar reautenticação
  useEffect(() => {
    if (status === 'success') {
      // Limpar token para forçar novo login com dados atualizados
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
    }
  }, [status]);

  const verificacaoIniciada = useRef(false);

  // Efeito 1: Disparar verificação do token (Apenas UMA vez na montagem ou troca de token)
  useEffect(() => {
    if (token) {
      // Se já iniciou verificação para este token específico, ignora
      if (verificacaoIniciada.current) return;

      verificacaoIniciada.current = true;
      verificarToken();
    }
  }, [token]);

  // Efeito 2: Gerenciar polling quando status é pending
  useEffect(() => {
    if (email && status === 'pending') {
      iniciarPolling();
    }

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [email, status]);

  const iniciarPolling = () => {
    // Limpar polling anterior se existir
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }

    // Verificar status a cada 3 segundos
    pollingIntervalRef.current = setInterval(async () => {
      try {
        const response = await authAPI.verificarStatusEmail(email);
        const data = response.data;

        if (data.verificado) {
          // Email foi verificado!
          clearInterval(pollingIntervalRef.current);
          setStatus('success');
          setMessage('Email verificado com sucesso! Você já pode fazer login.');

          // Limpar storage e forçar reload para atualizar contexto
          setTimeout(() => {
            // Usar window.location para forçar reload completo
            window.location.href = '/login';
          }, 3000);
        }
      } catch (error) {
        console.error('Erro ao verificar status do email:', error);
      }
    }, 3000); // Verificar a cada 3 segundos
  };

  const verificarToken = async () => {
    setStatus('verifying');
    try {
      await authAPI.verificarEmail(token);
      setStatus('success');
      setMessage('Email verificado com sucesso! Você já pode fazer login.');
    } catch (error) {
      const msg = error.response?.data?.detail || 'Token inválido ou expirado.';
      setStatus('error');
      setMessage(msg);
    }
  };

  const reenviarEmail = async () => {
    setLoading(true);
    try {
      await authAPI.reenviarVerificacao(email);
      setStatus('resent');
      setTimeout(() => setStatus('pending'), 3000);
    } catch (error) {
      const msg = error.response?.data?.detail || 'Erro ao reenviar email';
      alert(msg);
    } finally {
      setLoading(false);
    }
  };

  const renderContent = () => {
    switch (status) {
      case 'verifying':
        return (
          <motion.div
            key="verifying"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="text-center"
          >
            <div className="relative mb-6">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                className="w-24 h-24 mx-auto rounded-full border-4 border-emerald-500/30 border-t-emerald-500"
              />
              <Mail className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-10 h-10 text-emerald-400" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Verificando...</h2>
            <p className="text-slate-400">Aguarde enquanto verificamos seu email.</p>
          </motion.div>
        );

      case 'success':
        return (
          <motion.div
            key="success"
            initial={{ opacity: 0, scale: 0.8, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.5, type: "spring", bounce: 0.4 }}
            className="text-center"
          >
            {/* Confetti Effect */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: [0, 1, 0] }}
              transition={{ duration: 1.5, times: [0, 0.5, 1] }}
              className="absolute inset-0 flex items-center justify-center pointer-events-none"
            >
              <div className="relative w-full h-full">
                {[...Array(12)].map((_, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, scale: 0, x: 0, y: 0 }}
                    animate={{
                      opacity: [0, 1, 0],
                      scale: [0, 1, 0.5],
                      x: [0, (Math.random() - 0.5) * 200],
                      y: [0, (Math.random() - 0.5) * 200],
                    }}
                    transition={{
                      duration: 1.2,
                      delay: i * 0.05,
                      ease: "easeOut"
                    }}
                    className="absolute top-1/2 left-1/2 w-2 h-2 rounded-full"
                    style={{
                      backgroundColor: ['#10b981', '#34d399', '#6ee7b7'][i % 3]
                    }}
                  />
                ))}
              </div>
            </motion.div>

            <motion.div
              initial={{ scale: 0, rotate: -180 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{
                type: "spring",
                damping: 12,
                stiffness: 200,
                delay: 0.2
              }}
              className="relative w-28 h-28 mx-auto mb-6"
            >
              {/* Animated rings */}
              <motion.div
                animate={{
                  scale: [1, 1.3, 1],
                  opacity: [0.5, 0, 0.5]
                }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                className="absolute inset-0 bg-emerald-500/30 rounded-full"
              />
              <motion.div
                animate={{
                  scale: [1, 1.5, 1],
                  opacity: [0.3, 0, 0.3]
                }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut", delay: 0.3 }}
                className="absolute inset-0 bg-emerald-500/20 rounded-full"
              />

              {/* Main icon container */}
              <div className="absolute inset-0 bg-gradient-to-br from-emerald-500 to-green-600 rounded-full flex items-center justify-center shadow-2xl shadow-emerald-500/50">
                <motion.div
                  initial={{ scale: 0, rotate: -90 }}
                  animate={{ scale: 1, rotate: 0 }}
                  transition={{
                    type: "spring",
                    damping: 10,
                    stiffness: 200,
                    delay: 0.4
                  }}
                >
                  <CheckCircle className="w-16 h-16 text-white" strokeWidth={2.5} />
                </motion.div>
              </div>
            </motion.div>

            <motion.h2
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              className="text-3xl font-bold text-white mb-3"
            >
              🎉 Email Verificado!
            </motion.h2>

            <motion.p
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="text-slate-300 mb-2"
            >
              {message}
            </motion.p>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.7 }}
              className="mb-8"
            >
              <p className="text-emerald-400 text-sm font-medium">
                Redirecionando para o login...
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 }}
            >
              <Button
                onClick={() => window.location.href = '/login'}
                className="bg-gradient-to-r from-emerald-500 to-green-500 hover:from-emerald-600 hover:to-green-600 text-white px-8 py-3 rounded-xl shadow-lg shadow-emerald-500/30 transition-all transform hover:scale-105"
              >
                Ir para Login Agora
                <ArrowRight className="ml-2 w-5 h-5" />
              </Button>
            </motion.div>
          </motion.div>
        );

      case 'error':
        return (
          <motion.div
            key="error"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="text-center"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", damping: 15, stiffness: 200 }}
              className="w-24 h-24 mx-auto mb-6 bg-red-500/20 rounded-full flex items-center justify-center"
            >
              <XCircle className="w-14 h-14 text-red-400" />
            </motion.div>
            <h2 className="text-2xl font-bold text-white mb-2">Erro na Verificação</h2>
            <p className="text-slate-400 mb-8">{message}</p>
            <div className="flex gap-4 justify-center">
              <Button
                onClick={() => navigate('/login')}
                variant="outline"
                className="border-slate-600 text-slate-300 hover:bg-slate-800 px-6 py-3 rounded-xl"
              >
                Voltar ao Login
              </Button>
            </div>
          </motion.div>
        );

      case 'resent':
        return (
          <motion.div
            key="resent"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="text-center"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", damping: 15, stiffness: 200 }}
              className="w-24 h-24 mx-auto mb-6 bg-blue-500/20 rounded-full flex items-center justify-center"
            >
              <Mail className="w-14 h-14 text-blue-400" />
            </motion.div>
            <h2 className="text-2xl font-bold text-white mb-2">Email Reenviado!</h2>
            <p className="text-slate-400 mb-4">Verifique sua caixa de entrada.</p>
            <p className="text-slate-500 text-sm">Não esqueça de verificar a pasta de spam.</p>
          </motion.div>
        );

      default: // pending - aguardando verificação
        return (
          <motion.div
            key="pending"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="text-center"
          >
            <motion.div
              animate={{ y: [0, -10, 0] }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              className="w-24 h-24 mx-auto mb-6 bg-amber-500/20 rounded-full flex items-center justify-center relative"
            >
              <Mail className="w-14 h-14 text-amber-400" />
              <motion.div
                animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                className="absolute inset-0 rounded-full border-2 border-amber-400/50"
              />
            </motion.div>
            <h2 className="text-2xl font-bold text-white mb-4">Verifique seu Email</h2>
            <p className="text-slate-400 mb-2">
              Enviamos um link de verificação para:
            </p>
            {email && (
              <p className="text-emerald-400 font-semibold text-lg mb-6">{email}</p>
            )}
            <div className="bg-slate-800/50 rounded-xl p-4 mb-6 text-left">
              <p className="text-slate-300 text-sm mb-2">
                📧 Clique no link enviado para seu email
              </p>
              <p className="text-slate-300 text-sm mb-2">
                ⏱️ O link expira em 24 horas
              </p>
              <p className="text-slate-300 text-sm">
                📁 Verifique também a pasta de spam
              </p>
            </div>

            {/* Indicador de Polling */}
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-3 mb-6">
              <div className="flex items-center justify-center gap-2 text-blue-400">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                >
                  <RefreshCw className="w-4 h-4" />
                </motion.div>
                <span className="text-sm font-medium">Verificando automaticamente...</span>
              </div>
              <p className="text-blue-300 text-xs mt-1">
                Esta página atualizará assim que seu email for verificado
              </p>
            </div>

            {/* Aviso de bloqueio para TRIAL */}
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 mb-6">
              <p className="text-amber-400 text-sm font-medium mb-2">
                🔒 Verificação Obrigatória
              </p>
              <p className="text-amber-300 text-xs">
                Você precisa verificar seu email para acessar o sistema. Não conseguiu receber? Use o botão abaixo para reenviar.
              </p>
            </div>

            <div className="flex flex-col gap-3">
              <Button
                onClick={reenviarEmail}
                disabled={loading}
                className="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-3 rounded-xl transition flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Reenviando...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4" />
                    Reenviar Email de Verificação
                  </>
                )}
              </Button>
            </div>
          </motion.div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center p-4">
      {/* Background effects */}
      <div className="absolute inset-0 overflow-hidden">
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.1, 0.2, 0.1]
          }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
          className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl"
        />
        <motion.div
          animate={{
            scale: [1.2, 1, 1.2],
            opacity: [0.1, 0.15, 0.1]
          }}
          transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
          className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl"
        />
      </div>

      {/* Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative w-full max-w-md"
      >
        <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-800 rounded-2xl p-8 shadow-2xl">
          {/* Logo */}
          <Link to="/" className="flex items-center justify-center gap-2 mb-8 group">
            <div className="w-12 h-12 bg-gradient-to-br from-emerald-400 to-green-500 rounded-xl flex items-center justify-center shadow-lg shadow-emerald-500/30 group-hover:scale-105 transition-transform">
              <span className="text-white font-bold text-xl">GC</span>
            </div>
            <span className="text-2xl font-bold">
              <span className="text-emerald-400">Kredor</span>
            </span>
          </Link>

          <AnimatePresence mode="wait">
            {renderContent()}
          </AnimatePresence>

        </div>
      </motion.div>
    </div>
  );
};

export default VerificarEmail;
