import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { equipeAPI } from '../api/equipe';
import { useToast } from '../hooks/use-toast';
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Loader2, CheckCircle, Lock, Eye, EyeOff, User } from 'lucide-react';
import { motion } from 'framer-motion';

const floatingElements = [
    { size: 250, x: "5%", y: "30%", delay: 0 },
    { size: 180, x: "85%", y: "50%", delay: 0.8 },
    { size: 120, x: "75%", y: "15%", delay: 0.3 },
    { size: 90, x: "15%", y: "75%", delay: 1.2 },
];

const AceitarConvite = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { toast } = useToast();
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [token, setToken] = useState('');

    // Form data
    const [formData, setFormData] = useState({
        senha: '',
        confirmarSenha: '',
        nome: ''
    });

    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);

    useEffect(() => {
        const pathParts = window.location.pathname.split('/');
        const tokenFromPath = pathParts[pathParts.length - 1];
        if (tokenFromPath && tokenFromPath !== 'aceitar-convite') {
            setToken(tokenFromPath);
        } else {
            toast({
                variant: "destructive",
                title: "Link inválido",
                description: "Token de convite não encontrado."
            });
        }
    }, [toast]);

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (formData.senha !== formData.confirmarSenha) {
            toast({
                variant: "destructive",
                title: "Senhas não conferem",
                description: "Por favor, digite a mesma senha nos dois campos."
            });
            return;
        }

        if (formData.senha.length < 6) {
            toast({
                variant: "destructive",
                title: "Senha muito curta",
                description: "A senha deve ter pelo menos 6 caracteres."
            });
            return;
        }

        setLoading(true);
        try {
            await equipeAPI.aceitarConvite({
                token: token,
                senha: formData.senha,
                nome: formData.nome || undefined
            });

            setSuccess(true);
            toast({
                title: "Conta ativada!",
                description: "Sua senha foi definida com sucesso."
            });

            setTimeout(() => {
                navigate('/login');
            }, 3000);

        } catch (error) {
            toast({
                variant: "destructive",
                title: "Erro ao ativar conta",
                description: error.response?.data?.detail || "Link inválido ou expirado."
            });
        } finally {
            setLoading(false);
        }
    };

    const containerVariants = {
        hidden: { opacity: 0 },
        visible: {
            opacity: 1,
            transition: { staggerChildren: 0.1, delayChildren: 0.2 }
        }
    };

    const itemVariants = {
        hidden: { opacity: 0, y: 20 },
        visible: { opacity: 1, y: 0 }
    };

    if (success) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-emerald-950 flex items-center justify-center p-4 overflow-hidden relative">
                {/* Background Pattern */}
                <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0wIDBoNjB2NjBIMHoiLz48cGF0aCBkPSJNMzAgMzBtLTEgMGExIDEgMCAxIDAgMiAwYTEgMSAwIDEgMCAtMiAwIiBmaWxsPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMDMpIi8+PC9nPjwvc3ZnPg==')] opacity-50" />

                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="max-w-md w-full space-y-8 text-center bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 p-8 rounded-3xl shadow-2xl shadow-emerald-500/10 relative z-10"
                >
                    <CheckCircle className="mx-auto h-20 w-20 text-emerald-500" />
                    <h2 className="mt-6 text-3xl font-bold text-white">Tudo pronto!</h2>
                    <p className="mt-2 text-slate-300">
                        Sua conta foi ativada com sucesso. Você será redirecionado para o login em instantes.
                    </p>
                    <Button onClick={() => navigate('/login')} className="w-full mt-6 bg-emerald-500 hover:bg-emerald-600 text-white font-semibold h-12 rounded-xl">
                        Ir para Login agora
                    </Button>
                </motion.div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-emerald-950 flex items-center justify-center p-4 overflow-hidden relative">
            {/* Animated background elements */}
            {floatingElements.map((el, i) => (
                <motion.div
                    key={i}
                    className="absolute rounded-full bg-gradient-to-br from-emerald-500/10 to-green-500/5 blur-3xl"
                    style={{ width: el.size, height: el.size, left: el.x, top: el.y }}
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
                <motion.div
                    className="bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 rounded-3xl p-8 shadow-2xl shadow-emerald-500/10"
                    variants={itemVariants}
                >
                    {/* Header Logo */}
                    <div className="text-center mb-8">
                        <motion.div
                            className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-emerald-400 to-green-500 rounded-2xl mb-4 shadow-lg shadow-emerald-500/30"
                            whileHover={{ scale: 1.05, rotate: -5 }}
                            animate={{
                                boxShadow: [
                                    "0 10px 40px -10px rgba(16, 185, 129, 0.3)",
                                    "0 10px 60px -10px rgba(16, 185, 129, 0.5)",
                                    "0 10px 40px -10px rgba(16, 185, 129, 0.3)",
                                ]
                            }}
                            transition={{ boxShadow: { duration: 2, repeat: Infinity, ease: "easeInOut" } }}
                        >
                            <span className="text-2xl font-display font-bold text-white">K</span>
                        </motion.div>
                        <h1 className="text-3xl font-bold text-white mb-2">
                            <span className="text-emerald-400">Kredor</span>
                        </h1>
                        <p className="text-slate-400">Bem-vindo à equipe!</p>
                    </div>

                    <form className="space-y-5" onSubmit={handleSubmit}>
                        <motion.div className="space-y-2" variants={itemVariants}>
                            <Label htmlFor="nome" className="text-slate-300">Seu Nome (Opcional)</Label>
                            <div className="relative group">
                                <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 group-focus-within:text-emerald-400 transition-colors" />
                                <Input
                                    id="nome"
                                    name="nome"
                                    type="text"
                                    value={formData.nome}
                                    onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                                    placeholder="Confirme seu nome completo"
                                    className="pl-12 h-12 bg-slate-900/50 border-slate-700 focus:border-emerald-500 rounded-xl text-white placeholder:text-slate-500"
                                />
                            </div>
                        </motion.div>

                        <motion.div className="space-y-2" variants={itemVariants}>
                            <Label htmlFor="password" className="text-slate-300">Nova Senha</Label>
                            <div className="relative group">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 group-focus-within:text-emerald-400 transition-colors" />
                                <Input
                                    id="password"
                                    name="password"
                                    type={showPassword ? "text" : "password"}
                                    required
                                    value={formData.senha}
                                    onChange={(e) => setFormData({ ...formData, senha: e.target.value })}
                                    placeholder="Mínimo 6 caracteres"
                                    className="pl-12 pr-12 h-12 bg-slate-900/50 border-slate-700 focus:border-emerald-500 rounded-xl text-white placeholder:text-slate-500"
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

                        <motion.div className="space-y-2" variants={itemVariants}>
                            <Label htmlFor="confirmPassword" className="text-slate-300">Confirmar Senha</Label>
                            <div className="relative group">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500 group-focus-within:text-emerald-400 transition-colors" />
                                <Input
                                    id="confirmPassword"
                                    name="confirmPassword"
                                    type={showConfirmPassword ? "text" : "password"}
                                    required
                                    value={formData.confirmarSenha}
                                    onChange={(e) => setFormData({ ...formData, confirmarSenha: e.target.value })}
                                    placeholder="Digite a senha novamente"
                                    className="pl-12 pr-12 h-12 bg-slate-900/50 border-slate-700 focus:border-emerald-500 rounded-xl text-white placeholder:text-slate-500"
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

                        <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} className="pt-4">
                            <Button
                                type="submit"
                                disabled={loading}
                                className="w-full h-12 bg-gradient-to-r from-emerald-500 to-green-500 hover:from-emerald-600 hover:to-green-600 text-white font-semibold rounded-xl shadow-lg shadow-emerald-500/30 transition-all duration-300"
                            >
                                {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                                Ativar Minha Conta
                            </Button>
                        </motion.div>
                    </form>
                </motion.div>

                {/* Footer */}
                <motion.div
                    className="mt-8 text-center"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.7 }}
                >
                    <p className="text-xs text-slate-600">
                        © 2025 Kredor - Todos os direitos reservados
                    </p>
                </motion.div>
            </motion.div>
        </div>
    );
};

export default AceitarConvite;
