import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { configuracoesAPI } from '../api/api';
import { useTheme } from '../context/ThemeContext';
import {
  Wallet,
  Users,
  Calculator,
  FileText,
  Shield,
  TrendingUp,
  CheckCircle,
  ArrowRight,
  Star,
  Zap,
  Clock,
  BarChart3,
  MessageCircle,
  Sun,
  Moon,
  Menu,
  X,
  Search,
  Bot,
  Gauge,
  UserCheck,
  Repeat,
  CalendarClock,
  ScrollText,
  Smartphone,
  QrCode,
  Play,
  Gift,
  Rocket
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import Footer from '../components/Footer';
import DemoShowcase from '../components/DemoShowcase';
import Testimonials from '../components/Testimonials';
import JsonLd from '../components/JsonLd';
import { organizationSchema, websiteSchema, softwareApplicationSchema, faqPageSchema } from '../lib/seoSchema';
import logomark from '../assets/logomark.png';
import { toast } from '../hooks/use-toast';

const LandingPage = () => {
  const { theme, toggleTheme, isDark } = useTheme();
  const navigate = useNavigate();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [config, setConfig] = useState({
    whatsapp_numero: '',
    whatsapp_mensagem: 'Olá! Gostaria de saber mais sobre o Kredor.',
    nome_empresa: 'Kredor',
    slogan: 'Sistema de Gestão de Empréstimos',
    descricao: 'Gerencie seus empréstimos de forma simples e profissional',
    plano_trial_dias: 7,
    plano_basico_preco: 97.0,
    plano_basico_clientes: 50,
    plano_basico_emprestimos: 100,
    plano_profissional_preco: 197.0,
    plano_profissional_clientes: 200,
    plano_profissional_emprestimos: 500,
    plano_enterprise_preco: 497.0,
    plano_enterprise_clientes: -1,
    plano_enterprise_emprestimos: -1
  });

  useEffect(() => {
    const carregarConfig = async () => {
      try {
        const response = await configuracoesAPI.obterLanding();
        setConfig(prev => ({ ...prev, ...response.data }));
      } catch (err) {
        toast({ title: 'Erro', description: "Não foi possível carregar configurações.", variant: 'destructive' });
        console.error('Erro ao carregar configurações:', err);
      }
    };
    carregarConfig();
  }, []);

  const formatarPreco = (valor) => {
    return valor.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  };

  const formatarLimite = (valor) => {
    return valor === -1 ? 'Ilimitado' : valor.toString();
  };

  const whatsappLink = config.whatsapp_numero
    ? `https://wa.me/55${config.whatsapp_numero.replace(/\D/g, '')}?text=${encodeURIComponent(config.whatsapp_mensagem || 'Olá! Gostaria de saber mais sobre o Kredor.')}`
    : '#';

  const features = [
    { icon: Users, title: 'Gestão de Clientes', desc: 'Cadastro completo com CPF/CNPJ, histórico, score e status', novo: false },
    { icon: Wallet, title: 'Controle de Empréstimos', desc: '4 métodos de cálculo: Simples, Composto, Price e SAC', novo: false },
    { icon: QrCode, title: 'Cobrança PIX Automática', desc: 'Gere PIX dinâmico e baixe pagamentos em tempo real', novo: false },
    { icon: MessageCircle, title: 'Régua de Cobrança WhatsApp', desc: 'Lembretes e cobranças automáticas com proteção anti-spam', novo: true },
    { icon: Search, title: 'Consulta de CPF', desc: 'Consulte CPF e valide os dados dos clientes na plataforma', novo: true },
    { icon: Bot, title: 'Assistente com IA', desc: 'Tire dúvidas e receba insights do seu negócio com IA', novo: true },
    { icon: UserCheck, title: 'Portal do Cliente', desc: 'Seu cliente acompanha parcelas e paga sozinho pelo PIX', novo: true },
    { icon: Gauge, title: 'Score de Crédito', desc: 'Análise automática de risco e classificação de clientes', novo: true },
    { icon: Repeat, title: 'Juros de Mora Automáticos', desc: 'Multa e juros aplicados sozinhos em parcelas atrasadas', novo: true },
    { icon: ScrollText, title: 'Contratos Digitais', desc: 'Gere contratos (CCB) e recibos em PDF automaticamente', novo: false },
    { icon: BarChart3, title: 'Dashboard e Relatórios', desc: 'Métricas em tempo real e exportação em PDF/Excel', novo: false },
    { icon: Shield, title: 'Segurança e Equipe', desc: 'Login 2FA, criptografia e multiusuário com permissões', novo: true },
  ];

  const benefits = [
    'Recebe mais rápido — PIX dinâmico com baixa automática',
    'Cobra sozinho — régua no WhatsApp reduz a inadimplência',
    'Aprova com segurança — análise de CPF e score antes de liberar',
    'Opera formalizado — contratos digitais (CCB) e recibos em PDF',
    'Controla de qualquer lugar — dashboard em tempo real e backup em nuvem'
  ];

  const homeFaqs = [
    { q: 'O que é o Kredor?', a: 'O Kredor é um software de gestão de empréstimos para credores particulares: você cadastra clientes, controla parcelas e juros, cobra automaticamente no PIX e WhatsApp, gera contratos (CCB) e acompanha tudo em um só lugar.' },
    { q: 'O Kredor empresta dinheiro?', a: 'Não. O Kredor é uma ferramenta de gestão e cobrança. Quem empresta é você; o sistema organiza sua carteira, automatiza a cobrança e reduz a inadimplência.' },
    { q: 'Preciso instalar algo ou ter cartão para testar?', a: 'Não. É 100% online e o teste grátis de 7 dias não pede cartão de crédito. Você cria a conta e começa a usar na hora, no computador ou no celular.' },
    { q: 'Como funciona a cobrança automática no PIX e WhatsApp?', a: 'Você configura uma régua de cobrança e o sistema envia lembretes e avisos sozinho, já com o PIX dentro da mensagem. Quando o cliente paga, a baixa é automática.' },
    { q: 'Quais métodos de cálculo de juros o Kredor suporta?', a: 'Juros simples, juros compostos, Tabela Price e SAC. Você simula e compara antes de registrar o empréstimo.' },
    { q: 'Meus dados e os dos meus clientes estão seguros?', a: 'Sim. Usamos criptografia em trânsito, hash de senhas, backups e controles de acesso, seguindo as boas práticas da LGPD.' },
  ];

  return (
    <div className={`min-h-screen transition-colors duration-300 ${isDark ? 'bg-slate-950 text-white' : 'bg-white text-slate-900'}`}>
      {/* SEO Hidden Headings (SR-Only) */}
      <div className="sr-only">
        <h2>Software para controle de crédito, consulta de CPF e portal do cliente</h2>
        <h3>Como automatizar a régua de cobrança com PIX dinâmico e WhatsApp</h3>
        <p>O Kredor é uma plataforma para gestão de empréstimos particulares e microcrédito: cobrança automatizada via PIX e WhatsApp, consulta de CPF para validar dados de clientes, score de crédito, contratos digitais (CCB), portal do cliente e assistente com inteligência artificial. Ideal para credores, fintechs e escritórios de cobrança.</p>
      </div>

      {/* WhatsApp Floating Button */}
      {config.whatsapp_numero && (
        <motion.a
          href={whatsappLink}
          target="_blank"
          rel="noopener noreferrer"
          className="fixed bottom-6 right-6 z-50 bg-green-500 hover:bg-green-600 text-white p-4 rounded-full shadow-2xl shadow-green-500/30"
          aria-label="Falar com suporte no WhatsApp sobre sistema de gestão de empréstimos e cobranças"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          animate={{ y: [0, -10, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
          data-testid="whatsapp-button"
        >
          <MessageCircle className="w-7 h-7" />
        </motion.a>
      )}

      {/* Header */}
      <header className={`fixed top-0 left-0 right-0 z-40 backdrop-blur-xl border-b ${isDark ? 'bg-slate-950/80 border-slate-800' : 'bg-white/80 border-slate-200'}`}>
        <nav className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src={logomark} alt="Kredor - sistema de gestão de empréstimos" className="w-10 h-10 object-contain" data-testid="brand-logo" />
            <span className="text-xl font-display font-bold">
              <span className="text-primary">Kredor</span>
            </span>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            <a href="#funcionalidades" className={`text-sm font-medium transition ${isDark ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900'}`}>Funcionalidades</a>
            <a href="#demo" className={`text-sm font-medium transition ${isDark ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900'}`}>Demo</a>
            <a href="#planos" className={`text-sm font-medium transition ${isDark ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900'}`}>Planos</a>
            <a href="#beneficios" className={`text-sm font-medium transition ${isDark ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900'}`}>Benefícios</a>
          </div>

          <div className="flex items-center gap-2">
            {/* Theme Toggle - Desktop Only */}
            <button
              onClick={toggleTheme}
              className={`hidden md:block p-2 rounded-lg transition ${isDark ? 'text-slate-400 hover:text-white hover:bg-slate-800' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'}`}
            >
              {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>

            {/* Login Button - Always Visible */}
            <Link to="/login" className={`text-sm md:text-base font-medium transition px-3 py-2 rounded-lg ${isDark ? 'text-slate-300 hover:text-white hover:bg-slate-800' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'}`}>
              Entrar
            </Link>

            {/* CTA - Desktop Only */}
            <Link to="/login" className="hidden md:block">
              <Button className="bg-primary hover:bg-primary/90 text-white shadow-glow" data-testid="cta-header">
                Começar Grátis
              </Button>
            </Link>

            {/* Mobile Menu Toggle */}
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className={`md:hidden p-2 rounded-lg transition ${isDark ? 'text-slate-400 hover:text-white hover:bg-slate-800' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'}`}
            >
              {isMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </nav>

        {/* Mobile Menu Drawer */}
        <motion.div
          initial={false}
          animate={isMenuOpen ? { height: 'auto', opacity: 1 } : { height: 0, opacity: 0 }}
          className="md:hidden overflow-hidden bg-inherit border-t border-slate-800"
        >
          <div className="px-4 py-6 space-y-4 flex flex-col">
            <a href="#funcionalidades" onClick={() => setIsMenuOpen(false)} className="text-lg font-medium py-2">Funcionalidades</a>
            <a href="#demo" onClick={() => setIsMenuOpen(false)} className="text-lg font-medium py-2">Demo</a>
            <a href="#planos" onClick={() => setIsMenuOpen(false)} className="text-lg font-medium py-2">Planos</a>
            <a href="#beneficios" onClick={() => setIsMenuOpen(false)} className="text-lg font-medium py-2">Benefícios</a>
            
            <div className="pt-4 border-t border-slate-800 flex flex-col gap-4">
              <Link to="/login" onClick={() => setIsMenuOpen(false)}>
                <Button className="w-full bg-primary hover:bg-primary/90 text-white shadow-glow py-6 text-lg">
                  Começar Grátis
                </Button>
              </Link>
              
              <button
                onClick={() => { toggleTheme(); setIsMenuOpen(false); }}
                className={`flex items-center justify-between w-full p-4 rounded-xl border ${isDark ? 'border-slate-800 bg-slate-900 text-slate-300' : 'border-slate-200 bg-slate-50 text-slate-600'}`}
              >
                <span className="font-medium">Alternar Tema</span>
                {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
              </button>
            </div>
          </div>
        </motion.div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 overflow-hidden">
        {/* Background Effects */}
        <div className="absolute inset-0 overflow-hidden">
          <div className={`absolute top-1/4 left-1/4 w-96 h-96 rounded-full blur-3xl ${isDark ? 'bg-primary/10' : 'bg-primary/5'}`} />
          <div className={`absolute bottom-1/4 right-1/4 w-96 h-96 rounded-full blur-3xl ${isDark ? 'bg-emerald-500/10' : 'bg-emerald-500/5'}`} />
        </div>

        <div className="container mx-auto px-4 relative z-10">
          <motion.div
            className="text-center max-w-4xl mx-auto"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <Badge className="mb-6 bg-primary/10 text-primary border-primary/20">
              <Gift className="w-3 h-3 mr-1" />
              {config.plano_trial_dias} dias grátis · sem cartão
            </Badge>

            <h1 className="text-4xl md:text-6xl font-display font-bold mb-6 leading-tight">
              Gestão de empréstimos e
              <span className="text-gradient"> cobrança automática no PIX e WhatsApp</span>
            </h1>

            <p className={`text-lg md:text-xl mb-8 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
              Organize sua carteira de crédito, cobre no automático e reduza a inadimplência. Chega de caderninho e planilha — controle tudo em um só lugar, com segurança.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/login">
                <Button size="lg" className="bg-primary hover:bg-primary/90 text-white shadow-glow text-lg px-8">
                  Começar grátis
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </Link>
              <a href="#demo">
                <Button size="lg" variant="outline" className={`text-lg px-8 ${isDark ? 'border-slate-700 hover:bg-slate-800' : ''}`}>
                  <Play className="mr-2 w-5 h-5" />
                  Ver demonstração
                </Button>
              </a>
            </div>

            <div className={`mt-6 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`} data-testid="hero-microcopy">
              <span className="flex items-center gap-1.5"><CheckCircle className="w-4 h-4 text-primary" /> 7 dias grátis</span>
              <span className="flex items-center gap-1.5"><CheckCircle className="w-4 h-4 text-primary" /> Sem cartão de crédito</span>
              <span className="flex items-center gap-1.5"><CheckCircle className="w-4 h-4 text-primary" /> Configure em minutos</span>
            </div>

            <div className="mt-12 flex items-center justify-center gap-8">
              <div className="text-center">
                <p className="text-3xl font-display font-bold text-primary">500+</p>
                <p className={`text-sm ${isDark ? 'text-slate-500' : 'text-slate-600'}`}>credores usando</p>
              </div>
              <div className={`h-12 w-px ${isDark ? 'bg-slate-800' : 'bg-slate-200'}`} />
              <div className="text-center">
                <p className="text-3xl font-display font-bold text-primary">R$ 50M+</p>
                <p className={`text-sm ${isDark ? 'text-slate-500' : 'text-slate-600'}`}>em carteira gerenciada</p>
              </div>
              <div className={`h-12 w-px ${isDark ? 'bg-slate-800' : 'bg-slate-200'}`} />
              <div className="text-center">
                <p className="text-3xl font-display font-bold text-primary">99,9%</p>
                <p className={`text-sm ${isDark ? 'text-slate-500' : 'text-slate-600'}`}>de disponibilidade</p>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* SEO Optimized Section - Solutions */}
      <section className={`py-12 border-y ${isDark ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="text-center md:text-left">
              <h3 className="text-primary font-bold mb-2 text-lg">Cobrança PIX automática</h3>
              <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                Gere <strong>PIX dinâmico</strong> e dê baixa dos pagamentos em tempo real, sem conferência manual.
              </p>
            </div>
            <div className="text-center md:text-left">
              <h3 className="text-primary font-bold mb-2 text-lg">Régua de cobrança no WhatsApp</h3>
              <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                Lembretes e avisos enviados sozinhos, com o PIX dentro da mensagem. Recupere crédito sem ligar para ninguém.
              </p>
            </div>
            <div className="text-center md:text-left">
              <h3 className="text-primary font-bold mb-2 text-lg">Análise de crédito com CPF</h3>
              <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                Valide os dados do cliente e avalie o risco antes de aprovar — com tratamento de dados conforme a LGPD.
              </p>
            </div>
            <div className="text-center md:text-left">
              <h3 className="text-primary font-bold mb-2 text-lg">Portal do cliente</h3>
              <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                Seu cliente consulta parcelas e paga sozinho, 24h. Menos ligação, menos atrito, mais recebimento.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Para quem é */}
      <section className={`py-14 ${isDark ? 'bg-slate-900/40' : 'bg-white'}`}>
        <div className="container mx-auto px-4 text-center">
          <p className={`text-sm font-semibold uppercase tracking-wider mb-6 ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>
            Feito para quem trabalha com crédito e cansou da planilha
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3" data-testid="para-quem-e">
            {['Credores particulares', 'Microcrédito', 'Financiamento pessoal', 'Escritórios de cobrança', 'Gestão de carteira de recebíveis'].map((p, i) => (
              <span
                key={i}
                className={`px-4 py-2 rounded-full text-sm font-medium border ${isDark ? 'bg-slate-800/60 border-slate-700 text-slate-200' : 'bg-slate-50 border-slate-200 text-slate-700'}`}
              >
                {p}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Demo Showcase Section */}
      <DemoShowcase isDark={isDark} />

      {/* Testimonials Section */}
      <Testimonials isDark={isDark} />

      {/* Features Section */}
      <section id="funcionalidades" className={`py-20 ${isDark ? 'bg-slate-900/50' : 'bg-slate-50'}`}>
        <div className="container mx-auto px-4">
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl md:text-4xl font-display font-bold mb-4">Tudo que você precisa para profissionalizar sua operação</h2>
            <p className={`text-lg ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>Da aprovação ao recebimento — automatize cobrança, controle parcelas e reduza a inadimplência.</p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className={`h-full transition-all duration-300 hover:shadow-lg hover:shadow-primary/5 ${isDark ? 'bg-slate-800/50 border-slate-700' : 'bg-white'}`}>
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                        <feature.icon className="w-6 h-6 text-primary" />
                      </div>
                      {feature.novo && (
                        <Badge className="bg-primary/10 text-primary border-primary/20 text-[10px] uppercase tracking-wide" data-testid={`feature-novo-${index}`}>
                          Novo
                        </Badge>
                      )}
                    </div>
                    <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
                    <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>{feature.desc}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="planos" className="py-20">
        <div className="container mx-auto px-4">
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl md:text-4xl font-display font-bold mb-4">Planos e Preços</h2>
            <p className={`text-lg ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>Escolha o plano ideal para seu negócio</p>
          </motion.div>

          {/* Banner de Teste Grátis */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
            className="max-w-3xl mx-auto mb-12"
          >
            <div className={`relative overflow-hidden rounded-2xl ${isDark
                ? 'bg-gradient-to-r from-emerald-900/30 via-emerald-800/30 to-teal-900/30'
                : 'bg-gradient-to-r from-emerald-50 via-teal-50 to-cyan-50'
              } border ${isDark ? 'border-emerald-700/30' : 'border-emerald-200'} p-8 md:p-10`}>
              {/* Efeito de brilho animado */}
              <motion.div
                animate={{
                  x: [-100, 300],
                  opacity: [0, 0.3, 0]
                }}
                transition={{
                  duration: 3,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
                className="absolute top-0 left-0 w-32 h-full bg-gradient-to-r from-transparent via-white to-transparent opacity-20 blur-xl"
              />

              <div className="relative z-10 text-center">
                <motion.div
                  initial={{ y: -10 }}
                  animate={{ y: 0 }}
                  transition={{ duration: 0.5 }}
                  className="mb-4"
                >
                  <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-600 dark:text-emerald-400 text-sm font-semibold">
                    <Gift className="w-4 h-4" />
                    100% GRÁTIS POR 7 DIAS
                  </span>
                </motion.div>

                <h3 className={`text-2xl md:text-3xl font-display font-bold mb-3 ${isDark ? 'text-white' : 'text-slate-900'
                  }`}>
                  Teste Sem Compromisso!
                </h3>

                <p className={`text-base md:text-lg mb-6 max-w-2xl mx-auto ${isDark ? 'text-slate-300' : 'text-slate-700'
                  }`}>
                  Experimente todas as funcionalidades por <strong className="text-emerald-600 dark:text-emerald-400">7 dias grátis</strong>. Sem cartão de crédito, sem complicação!
                </p>

                <motion.div
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <button
                    onClick={() => navigate('/login')}
                    className="inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all duration-300"
                  >
                    <Rocket className="w-5 h-5" />
                    Começar Teste Grátis Agora
                    <ArrowRight className="w-5 h-5" />
                  </button>
                </motion.div>

                <p className={`text-xs mt-4 ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>
                  ✓ Sem cartão de crédito • ✓ Cancele quando quiser • ✓ Acesso completo
                </p>
              </div>
            </div>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {/* Básico */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
            >
              <Card className={`h-full ${isDark ? 'bg-slate-800/50 border-slate-700' : 'bg-white'}`}>
                <CardHeader className="text-center pb-4">
                  <CardTitle className="text-xl">Básico</CardTitle>
                  <div className="mt-4">
                    <span className="text-4xl font-display font-bold">{formatarPreco(config.plano_basico_preco)}</span>
                    <span className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>/mês</span>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <ul className="space-y-3">
                    <li className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-primary" />
                      <span>Até {formatarLimite(config.plano_basico_clientes)} clientes</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-primary" />
                      <span>Até {formatarLimite(config.plano_basico_emprestimos)} empréstimos</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-primary" />
                      <span>Relatórios básicos</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-primary" />
                      <span>Suporte por email</span>
                    </li>
                  </ul>
                  <Link to="/checkout-transparente/basico" className="block">
                    <Button variant="outline" className="w-full mt-4">Assinar Agora</Button>
                  </Link>
                </CardContent>
              </Card>
            </motion.div>

            {/* Profissional */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
            >
              <Card className="h-full border-primary bg-gradient-to-b from-primary/10 to-transparent relative overflow-hidden">
                <div className="absolute top-0 right-0 bg-primary text-white text-xs px-3 py-1 rounded-bl-lg font-medium">
                  Popular
                </div>
                <CardHeader className="text-center pb-4">
                  <CardTitle className="text-xl">Profissional</CardTitle>
                  <div className="mt-4">
                    <span className="text-4xl font-display font-bold text-primary">{formatarPreco(config.plano_profissional_preco)}</span>
                    <span className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>/mês</span>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <ul className="space-y-3">
                    <li className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-primary" />
                      <span>Até {formatarLimite(config.plano_profissional_clientes)} clientes</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-primary" />
                      <span>Até {formatarLimite(config.plano_profissional_emprestimos)} empréstimos</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-primary" />
                      <span>Relatórios avançados</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-primary" />
                      <span>Assistente IA</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-primary" />
                      <span>Suporte prioritário</span>
                    </li>
                  </ul>
                  <Link to="/checkout-transparente/profissional" className="block">
                    <Button className="w-full mt-4 bg-primary hover:bg-primary/90 shadow-glow">Assinar Agora</Button>
                  </Link>
                </CardContent>
              </Card>
            </motion.div>

            {/* Enterprise */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
            >
              <Card className={`h-full ${isDark ? 'bg-slate-800/50 border-slate-700' : 'bg-white'}`}>
                <CardHeader className="text-center pb-4">
                  <CardTitle className="text-xl">Enterprise</CardTitle>
                  <div className="mt-4">
                    <span className="text-4xl font-display font-bold">{formatarPreco(config.plano_enterprise_preco)}</span>
                    <span className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>/mês</span>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <ul className="space-y-3">
                    <li className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-primary" />
                      <span>Clientes ilimitados</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-primary" />
                      <span>Empréstimos ilimitados</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-primary" />
                      <span>API personalizada</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-primary" />
                      <span>Multi-usuários</span>
                    </li>
                    <li className="flex items-center gap-2">
                      <CheckCircle className="w-5 h-5 text-primary" />
                      <span>Suporte 24/7</span>
                    </li>
                  </ul>
                  <Link to="/checkout-transparente/enterprise" className="block">
                    <Button variant="outline" className="w-full mt-4">Falar com Vendas</Button>
                  </Link>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section id="beneficios" className={`py-20 ${isDark ? 'bg-slate-900/50' : 'bg-slate-50'}`}>
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              <h2 className="text-3xl md:text-4xl font-display font-bold mb-6">
                Menos planilha, menos calote, mais controle
              </h2>
              <p className={`text-lg mb-8 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                O Kredor foi feito para quem empresta e precisa receber. Você acompanha a carteira inteira em tempo real, cobra no automático e recebe via PIX — com contratos digitais (CCB) e dados criptografados para operar de forma profissional e segura.
              </p>
              <ul className="space-y-4">
                {benefits.map((benefit, index) => (
                  <motion.li
                    key={index}
                    className="flex items-center gap-3"
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: index * 0.1 }}
                  >
                    <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center">
                      <CheckCircle className="w-4 h-4 text-primary" />
                    </div>
                    <span>{benefit}</span>
                  </motion.li>
                ))}
              </ul>
            </motion.div>

            <motion.div
              className="relative"
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              <div className={`rounded-2xl p-8 ${isDark ? 'bg-slate-800' : 'bg-white shadow-xl'}`}>
                <div className="flex items-center gap-4 mb-6">
                  <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                    <TrendingUp className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <p className="font-semibold">Resultados que você sente</p>
                    <div className="flex items-center gap-1">
                      {[1, 2, 3, 4, 5].map(i => (
                        <Star key={i} className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                      ))}
                      <span className={`text-sm ml-2 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>4.9/5 de avaliação</span>
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { v: '-32%', l: 'de inadimplência' },
                    { v: '+2,5h', l: 'economizadas por dia' },
                    { v: 'PIX', l: 'com baixa automática' },
                    { v: '24h', l: 'portal do cliente no ar' },
                  ].map((m, i) => (
                    <div key={i} className={`rounded-xl p-4 ${isDark ? 'bg-slate-900/60' : 'bg-slate-50'}`}>
                      <p className="text-2xl font-display font-bold text-primary">{m.v}</p>
                      <p className={`text-xs ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>{m.l}</p>
                    </div>
                  ))}
                </div>
                <p className={`mt-6 text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                  Menos planilha, menos calote e mais controle da sua carteira de crédito.
                </p>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <motion.div
            className={`rounded-3xl p-12 text-center relative overflow-hidden ${isDark ? 'bg-gradient-to-br from-primary/20 to-emerald-500/10' : 'bg-gradient-to-br from-primary/10 to-emerald-500/5'}`}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <div className="relative z-10">
              <h2 className="text-3xl md:text-4xl font-display font-bold mb-4">
                Comece a profissionalizar sua carteira hoje
              </h2>
              <p className={`text-lg mb-8 max-w-2xl mx-auto ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
                7 dias grátis, sem cartão de crédito. Configure em minutos e veja a diferença já na primeira cobrança.
              </p>
              <Link to="/login">
                <Button size="lg" className="bg-primary hover:bg-primary/90 text-white shadow-glow text-lg px-8">
                  Criar conta grátis
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>


      {/* FAQ Section */}
      <section id="faq" className={`py-20 ${isDark ? 'bg-slate-900/50' : 'bg-slate-50'}`}>
        <div className="container mx-auto px-4 max-w-3xl">
          <motion.div
            className="text-center mb-12"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl md:text-4xl font-display font-bold mb-4">Perguntas frequentes</h2>
            <p className={`text-lg ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>Tudo que você precisa saber antes de começar</p>
          </motion.div>
          <div className="space-y-4" data-testid="home-faq">
            {homeFaqs.map((f, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                className={`rounded-xl border p-6 ${isDark ? 'bg-slate-800/50 border-slate-700' : 'bg-white border-slate-200'}`}
              >
                <h3 className="font-semibold mb-2">{f.q}</h3>
                <p className={`text-sm leading-relaxed ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>{f.a}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* SEO structured data (JSON-LD) */}
      <JsonLd id="home-organization" data={organizationSchema()} />
      <JsonLd id="home-website" data={websiteSchema()} />
      <JsonLd id="home-software" data={softwareApplicationSchema(config)} />
      <JsonLd id="home-faq" data={faqPageSchema(homeFaqs)} />

      {/* Footer */}
      <Footer config={config} isDark={isDark} />
    </div>
  );
};

export default LandingPage;
