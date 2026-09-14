import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth, MOTIVO_LOGOUT_KEY } from '../context/AuthContext';
import { useModal } from '../components/Modal';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Eye,
  EyeOff,
  Mail,
  Lock,
  LogIn,
  UserPlus,
  User
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';

const floatingElements = [
  { size: 250, x: "5%", y: "30%", delay: 0 },
  { size: 180, x: "85%", y: "50%", delay: 0.8 },
  { size: 120, x: "75%", y: "15%", delay: 0.3 },
  { size: 90, x: "15%", y: "75%", delay: 1.2 },
];

const Login = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    senha: '',
    nome: '',
    confirmarSenha: ''
  });
  const [error, setError] = useState('');
  // Motivo de um logout involuntário (ex.: a conta foi acessada em outro dispositivo), gravado
  // pelo AuthContext antes do redirecionamento. Mostrado uma vez e apagado.
  const [avisoSessao, setAvisoSessao] = useState(() => {
    try {
      const motivo = localStorage.getItem(MOTIVO_LOGOUT_KEY);
      if (motivo) localStorage.removeItem(MOTIVO_LOGOUT_KEY);
      return motivo || '';
    } catch (e) {
      return '';   // silencioso: sem armazenamento, apenas não há aviso a mostrar.
    }
  });
  const [loading, setLoading] = useState(false);

  // Cloudflare Turnstile (proteção anti-bot no cadastro)
  const TURNSTILE_SITE_KEY = process.env.REACT_APP_TURNSTILE_SITE_KEY;
  const turnstileRef = useRef(null);
  const turnstileWidgetId = useRef(null);
  const [turnstileToken, setTurnstileToken] = useState('');

  // Renderiza o widget UMA única vez quando o script do Turnstile estiver pronto.
  // O container permanece montado em ambas as abas (login/registro).
  useEffect(() => {
    if (!TURNSTILE_SITE_KEY) return undefined;
    let cancelled = false;
    const timer = setInterval(() => {
      if (cancelled) return;
      if (window.turnstile && turnstileRef.current && turnstileWidgetId.current === null) {
        clearInterval(timer);
        turnstileWidgetId.current = window.turnstile.render(turnstileRef.current, {
          sitekey: TURNSTILE_SITE_KEY,
          theme: 'dark',
          callback: (token) => { setTurnstileToken(token); setError(''); },
          'expired-callback': () => setTurnstileToken(''),
          'error-callback': () => setTurnstileToken(''),
        });
      }
    }, 100);
    return () => {
      cancelled = true;
      clearInterval(timer);
      if (turnstileWidgetId.current !== null && window.turnstile) {
        try { window.turnstile.remove(turnstileWidgetId.current); } catch (e) { /* noop */ }
      }
      turnstileWidgetId.current = null;
      setTurnstileToken('');
    };
  }, [TURNSTILE_SITE_KEY]);

  // Ao alternar entre Login e Cadastro, recarrega (reset) o desafio sem destruir o widget.
  useEffect(() => {
    setTurnstileToken('');
    if (turnstileWidgetId.current !== null && window.turnstile) {
      try { window.turnstile.reset(turnstileWidgetId.current); } catch (e) { /* noop */ }
    }
  }, [isLogin]);

  const resetTurnstile = () => {
    setTurnstileToken('');
    if (turnstileWidgetId.current !== null && window.turnstile) {
      try { window.turnstile.reset(turnstileWidgetId.current); } catch (e) { /* noop */ }
    }
  };

  const { login, registro } = useAuth();
  const navigate = useNavigate();
  const modal = useModal();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (isLogin) {
        if (TURNSTILE_SITE_KEY && !turnstileToken) {
          setError('Complete a verificação de segurança antes de entrar.');
          setLoading(false);
          return;
        }
        const result = await login(formData.email, formData.senha, turnstileToken);

        if (result.success) {
          // Verificar se requer 2FA
          if (result.requires_2fa) {
            navigate('/verify-2fa', { state: { email: result.email } });
          } else {
            // Login normal - redirecionar para dashboard
            navigate('/');
          }
        } else {
          resetTurnstile();
          modal.error('Erro no Login', result.error || 'Credenciais inválidas. Verifique seu email e senha.');
        }
      } else {
        // Validações do registro
        if (formData.senha.length < 8) {
          setError('A senha deve ter pelo menos 8 caracteres, com letras e números');
          setLoading(false);
          return;
        }

        if (formData.senha !== formData.confirmarSenha) {
          setError('As senhas não coincidem');
          setLoading(false);
          return;
        }

        if (TURNSTILE_SITE_KEY && !turnstileToken) {
          setError('Complete a verificação de segurança antes de criar a conta.');
          setLoading(false);
          return;
        }

        const result = await registro({ ...formData, turnstile_token: turnstileToken });
        if (result.success) {
          setError('');
          // Redirecionar para página de verificação de email
          modal.success(
            'Conta Criada com Sucesso!',
            'Enviamos um email de verificação para ' + formData.email + '. Por favor, verifique sua caixa de entrada.',
            {
              confirmText: 'Verificar Email',
              onConfirm: () => {
                navigate(`/verificar-email?email=${encodeURIComponent(formData.email)}`);
              }
            }
          );
        } else {
          resetTurnstile();
          modal.error('Erro no Registro', result.error || 'Não foi possível criar sua conta. Tente novamente.');
        }
      }
    } catch (err) {
      modal.error('Erro', 'Erro ao processar solicitação. Tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-emerald-950 flex items-center justify-center p-4 overflow-hidden relative">
      {/* Animated background elements */}
      {floatingElements.map((el, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full bg-gradient-to-br from-emerald-500/10 to-green-500/5 blur-3xl"
          style={{
            width: el.size,
            height: el.size,
            left: el.x,
            top: el.y,
          }}
          animate={{
            x: [0, 20, -20, 0],
            y: [0, -20, 20, 0],
            scale: [1, 1.1, 0.95, 1],
          }}
          transition={{
            duration: 12,
            delay: el.delay,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
      ))}

      {/* Grid pattern overlay */}
      <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0wIDBoNjB2NjBIMHoiLz48cGF0aCBkPSJNMzAgMzBtLTEgMGExIDEgMCAxIDAgMiAwYTEgMSAwIDEgMCAtMiAwIiBmaWxsPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMDMpIi8+PC9nPjwvc3ZnPg==')] opacity-50" />

      <motion.div
        className="relative z-10 w-full max-w-md"
        initial="hidden"
        animate="visible"
        variants={containerVariants}
      >
        {/* Back button */}
        <motion.div variants={itemVariants} className="mb-8">
          <Link to="/">
            <button className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors" data-testid="link-back-home">
              <ArrowLeft className="w-4 h-4" />
              Voltar para o início
            </button>
          </Link>
        </motion.div>

        {/* Form Card */}
        <motion.div
          className="bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 rounded-3xl p-8 shadow-2xl shadow-emerald-500/10"
          variants={itemVariants}
          data-testid="login-container"
        >
          {/* Header */}
          <div className="text-center mb-8">
            <motion.div
              className="inline-flex items-center justify-center w-16 h-16 bg-white rounded-2xl mb-4 shadow-lg shadow-emerald-500/30 p-2"
              whileHover={{ scale: 1.05, rotate: -5 }}
              whileTap={{ scale: 0.95 }}
              animate={{
                boxShadow: [
                  "0 10px 40px -10px rgba(16, 185, 129, 0.3)",
                  "0 10px 60px -10px rgba(16, 185, 129, 0.5)",
                  "0 10px 40px -10px rgba(16, 185, 129, 0.3)",
                ]
              }}
              transition={{
                boxShadow: { duration: 2, repeat: Infinity, ease: "easeInOut" }
              }}
            >
              <img src="/logomark.png" alt="Kredor" className="w-full h-full object-contain" />
            </motion.div>
            <h1 className="text-3xl font-bold text-white mb-2" data-testid="app-title">
              <span className="text-emerald-400">Kredor</span>
            </h1>
            <p className="text-slate-400">Sistema de Gestão de Empréstimos</p>
          </div>

          {/* Tabs */}
          <div className="flex mb-6 bg-slate-900/50 rounded-xl p-1">
            <button
              onClick={() => { setIsLogin(true); setError(''); }}
              className={`flex-1 py-2.5 text-center font-medium rounded-lg transition-all ${isLogin
                  ? 'bg-emerald-500 text-white shadow-lg'
                  : 'text-slate-400 hover:text-white'
                }`}
              data-testid="tab-login"
            >
              <span className="flex items-center justify-center gap-2">
                <LogIn className="w-4 h-4" />
                Login
              </span>
            </button>
            <button
              onClick={() => { setIsLogin(false); setError(''); }}
              className={`flex-1 py-2.5 text-center font-medium rounded-lg transition-all ${!isLogin
                  ? 'bg-emerald-500 text-white shadow-lg'
                  : 'text-slate-400 hover:text-white'
                }`}
              data-testid="tab-registro"
            >
              <span className="flex items-center justify-center gap-2">
                <UserPlus className="w-4 h-4" />
                Registro
              </span>
            </button>
          </div>

          {/* Aviso de sessão encerrada por outro acesso — informação, não erro de digitação */}
          {avisoSessao && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-4 p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-300 text-sm"
              data-testid="aviso-sessao-encerrada"
            >
              {avisoSessao}
              <button
                type="button"
                onClick={() => setAvisoSessao('')}
                className="ml-2 font-medium text-emerald-400 underline hover:no-underline hover:text-emerald-300"
              >
                entendi
              </button>
            </motion.div>
          )}

          {/* Error Message */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm"
            >
              {error}
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Nome (registro only) */}
            {!isLogin && (
              <motion.div
                className="space-y-2"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
              >
                <Label htmlFor="nome" className="text-slate-300">Nome Completo</Label>
                <div className="relative group">
                  <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 group-focus-within:text-emerald-400 transition-colors" />
                  <Input
                    id="nome"
                    name="nome"
                    type="text"
                    placeholder="Digite seu nome"
                    className="pl-12 h-12 bg-slate-900/50 border-slate-700 focus:border-emerald-500 rounded-xl text-white placeholder:text-slate-500"
                    value={formData.nome}
                    onChange={handleChange}
                    required={!isLogin}
                    data-testid="input-nome"
                    autoComplete="name"
                  />
                </div>
              </motion.div>
            )}

            {/* Email */}
            <motion.div
              className="space-y-2"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 }}
            >
              <Label htmlFor="email" className="text-slate-300">E-mail</Label>
              <div className="relative group">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 group-focus-within:text-emerald-400 transition-colors" />
                <Input
                  id="email"
                  name="email"
                  type="email"
                  placeholder="seu@email.com"
                  className="pl-12 h-12 bg-slate-900/50 border-slate-700 focus:border-emerald-500 rounded-xl text-white placeholder:text-slate-500"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  data-testid="input-email"
                  autoComplete="email"
                />
              </div>
            </motion.div>

            {/* Password */}
            <motion.div
              className="space-y-2"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
            >
              <Label htmlFor="senha" className="text-slate-300">Senha</Label>
              <div className="relative group">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 group-focus-within:text-emerald-400 transition-colors" />
                <Input
                  id="senha"
                  name="senha"
                  type={showPassword ? "text" : "password"}
                  placeholder="********"
                  className="pl-12 pr-12 h-12 bg-slate-900/50 border-slate-700 focus:border-emerald-500 rounded-xl text-white placeholder:text-slate-500"
                  value={formData.senha}
                  onChange={handleChange}
                  required
                  data-testid="input-senha"
                  autoComplete={isLogin ? "current-password" : "new-password"}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </motion.div>

            {/* Confirmar Senha (registro only) */}
            {!isLogin && (
              <motion.div
                className="space-y-2"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Label htmlFor="confirmarSenha" className="text-slate-300">Confirmar Senha</Label>
                <div className="relative group">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 group-focus-within:text-emerald-400 transition-colors" />
                  <Input
                    id="confirmarSenha"
                    name="confirmarSenha"
                    type={showConfirmPassword ? "text" : "password"}
                    placeholder="********"
                    className="pl-12 pr-12 h-12 bg-slate-900/50 border-slate-700 focus:border-emerald-500 rounded-xl text-white placeholder:text-slate-500"
                    value={formData.confirmarSenha}
                    onChange={handleChange}
                    required={!isLogin}
                    data-testid="input-confirmar-senha"
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white transition-colors"
                  >
                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </motion.div>
            )}

            {/* Nota: Perfil é definido automaticamente como "usuario" no backend */}
            {/* Apenas admins existentes podem promover outros usuários */}

            {/* Cloudflare Turnstile — proteção anti-bot (login e cadastro) */}
            {TURNSTILE_SITE_KEY && (
              <div className="flex justify-center" data-testid="turnstile-widget">
                <div ref={turnstileRef} />
              </div>
            )}

            {/* Submit Button */}
            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <Button
                type="submit"
                disabled={loading}
                className="w-full h-12 bg-gradient-to-r from-emerald-500 to-green-500 hover:from-emerald-600 hover:to-green-600 text-white font-semibold rounded-xl shadow-lg shadow-emerald-500/30 transition-all duration-300 disabled:opacity-70"
                data-testid="submit-button"
              >
                {loading ? (
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Processando...
                  </div>
                ) : (
                  <div className="flex items-center justify-center gap-2">
                    {isLogin ? <LogIn className="w-5 h-5" /> : <UserPlus className="w-5 h-5" />}
                    {isLogin ? 'Entrar' : 'Registrar'}
                  </div>
                )}
              </Button>
            </motion.div>
          </form>

          {/* Footer */}
          {isLogin && (
            <motion.div
              className="mt-6 text-center"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              <p className="text-slate-400">
                Primeira vez?{" "}
                <button
                  onClick={() => setIsLogin(false)}
                  className="text-emerald-400 hover:text-emerald-300 font-medium"
                  data-testid="link-to-registro"
                >
                  Crie uma conta
                </button>
              </p>
            </motion.div>
          )}
        </motion.div>

        <motion.div
          className="mt-6 text-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7 }}
        >
          <p className="text-xs text-slate-500">
            © 2025 Kredor - Todos os direitos reservados
          </p>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default Login;
