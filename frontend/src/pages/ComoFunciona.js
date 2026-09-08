import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, ArrowRight, UserPlus, Wallet, Calculator, FileText, Bell, BarChart3, CheckCircle } from 'lucide-react';
import Footer from '../components/Footer';
import { configuracoesAPI } from '../api/api';
import { Button } from '../components/ui/button';

const ComoFunciona = () => {
  const [config, setConfig] = useState({});
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    const loadConfig = async () => {
      try {
        const res = await configuracoesAPI.obterLanding();
        setConfig(res.data);
      } catch (e) {}
    };
    loadConfig();
    setIsDark(localStorage.getItem('sgej-theme') !== 'light');
  }, []);

  const steps = [
    {
      icon: UserPlus,
      step: '01',
      title: 'Cadastre seus Clientes',
      description: 'Adicione seus clientes com dados completos: nome, CPF/CNPJ, telefone, email e endereço. O sistema valida automaticamente os documentos.',
      features: ['Validação de CPF/CNPJ', 'Busca automática de CEP', 'Histórico de empréstimos']
    },
    {
      icon: Calculator,
      step: '02',
      title: 'Simule o Empréstimo',
      description: 'Use nosso simulador para calcular parcelas com diferentes métodos: Juros Simples, Compostos, Tabela Price ou SAC.',
      features: ['4 métodos de cálculo', 'Visualização de parcelas', 'Comparativo de opções']
    },
    {
      icon: Wallet,
      step: '03',
      title: 'Registre o Empréstimo',
      description: 'Formalize o empréstimo com todos os dados: valor, taxa de juros, prazo, data de início e método de cálculo escolhido.',
      features: ['Geração automática de parcelas', 'Definição de garantias', 'Observações personalizadas']
    },
    {
      icon: FileText,
      step: '04',
      title: 'Gere Contratos',
      description: 'Crie contratos profissionais em PDF com todos os dados do empréstimo, prontos para assinatura.',
      features: ['Modelo profissional', 'Dados preenchidos', 'Download em PDF']
    },
    {
      icon: Bell,
      step: '05',
      title: 'Acompanhe Pagamentos',
      description: 'Registre pagamentos, acompanhe parcelas em aberto e receba notificações de vencimentos próximos.',
      features: ['Registro de pagamentos', 'Alertas de vencimento', 'Controle de atrasos']
    },
    {
      icon: BarChart3,
      step: '06',
      title: 'Analise Relatórios',
      description: 'Visualize dashboards completos com métricas do seu negócio: capital emprestado, juros, inadimplência e mais.',
      features: ['Dashboard executivo', 'Exportação Excel/PDF', 'Gráficos interativos']
    }
  ];

  return (
    <div className={`min-h-screen ${isDark ? 'bg-slate-950 text-white' : 'bg-white text-slate-900'}`}>
      {/* Header */}
      <header className={`sticky top-0 z-40 backdrop-blur-xl border-b ${isDark ? 'bg-slate-950/80 border-slate-800' : 'bg-white/80 border-slate-200'}`}>
        <nav className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-emerald-600 flex items-center justify-center">
              <span className="text-lg font-display font-bold text-white">GC</span>
            </div>
            <span className="text-xl font-display font-bold">
              <span className="text-primary">Gestor</span>Cred
            </span>
          </Link>
          <Link to="/" className={`flex items-center gap-2 text-sm ${isDark ? 'text-slate-400 hover:text-white' : 'text-slate-600 hover:text-slate-900'}`}>
            <ArrowLeft className="w-4 h-4" />
            Voltar
          </Link>
        </nav>
      </header>

      {/* Hero */}
      <section className="container mx-auto px-4 py-16 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <h1 className="text-3xl md:text-5xl font-display font-bold mb-6">
            Como o <span className="text-primary">GestorCred</span> Funciona?
          </h1>
          <p className={`text-lg md:text-xl max-w-2xl mx-auto ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
            Em apenas 6 passos simples, você terá controle total sobre seus empréstimos. Veja como é fácil!
          </p>
        </motion.div>
      </section>

      {/* Steps */}
      <section className="container mx-auto px-4 pb-16">
        <div className="max-w-5xl mx-auto">
          {steps.map((step, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: index % 2 === 0 ? -30 : 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
              className={`flex flex-col md:flex-row items-center gap-8 mb-16 ${index % 2 === 1 ? 'md:flex-row-reverse' : ''}`}
            >
              {/* Icon */}
              <div className="flex-shrink-0">
                <div className="relative">
                  <div className={`w-24 h-24 rounded-2xl flex items-center justify-center ${isDark ? 'bg-slate-800' : 'bg-slate-100'}`}>
                    <step.icon className="w-12 h-12 text-primary" />
                  </div>
                  <div className="absolute -top-3 -right-3 w-10 h-10 rounded-full bg-primary flex items-center justify-center">
                    <span className="text-white font-bold text-sm">{step.step}</span>
                  </div>
                </div>
              </div>

              {/* Content */}
              <div className="flex-1 text-center md:text-left">
                <h3 className="text-2xl font-display font-bold mb-3">{step.title}</h3>
                <p className={`mb-4 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
                  {step.description}
                </p>
                <ul className="flex flex-wrap justify-center md:justify-start gap-2">
                  {step.features.map((feature, i) => (
                    <li key={i} className={`flex items-center gap-1 text-sm px-3 py-1 rounded-full ${isDark ? 'bg-primary/10 text-primary' : 'bg-primary/10 text-primary'}`}>
                      <CheckCircle className="w-3 h-3" />
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className={`py-16 ${isDark ? 'bg-slate-900/50' : 'bg-slate-50'}`}>
        <div className="container mx-auto px-4 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-2xl md:text-3xl font-display font-bold mb-4">Pronto para Começar?</h2>
            <p className={`mb-8 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
              Experimente grátis por 7 dias. Sem cartão de crédito.
            </p>
            <Link to="/login">
              <Button size="lg" className="bg-primary hover:bg-primary/90 text-white shadow-glow">
                Criar Conta Grátis
                <ArrowRight className="ml-2 w-5 h-5" />
              </Button>
            </Link>
          </motion.div>
        </div>
      </section>

      <Footer config={config} isDark={isDark} />
    </div>
  );
};

export default ComoFunciona;
