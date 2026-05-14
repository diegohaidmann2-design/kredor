import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Target, Eye, Heart, Users, Award, TrendingUp } from 'lucide-react';
import Footer from '../components/Footer';
import { configuracoesAPI } from '../api/api';

const Sobre = () => {
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

  const values = [
    { icon: Target, title: 'Missão', description: 'Simplificar a gestão de empréstimos, oferecendo uma ferramenta completa e acessível para profissionais do setor financeiro.' },
    { icon: Eye, title: 'Visão', description: 'Ser a plataforma líder em gestão de empréstimos no Brasil, reconhecida pela excelência e inovação.' },
    { icon: Heart, title: 'Valores', description: 'Transparência, segurança, inovação e compromisso com o sucesso dos nossos clientes.' }
  ];

  const stats = [
    { icon: Users, value: '500+', label: 'Usuários Ativos' },
    { icon: TrendingUp, value: 'R$ 50M+', label: 'Gerenciados' },
    { icon: Award, value: '99.9%', label: 'Uptime' }
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
      <section className="container mx-auto px-4 py-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center max-w-3xl mx-auto"
        >
          <h1 className="text-3xl md:text-5xl font-display font-bold mb-6">
            Sobre o <span className="text-primary">Gestor Cred</span>
          </h1>
          <p className={`text-lg ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
            Nascemos da necessidade de simplificar a gestão de empréstimos. Nossa plataforma foi desenvolvida por profissionais do setor financeiro que entendiam as dores do dia a dia.
          </p>
        </motion.div>
      </section>

      {/* Story */}
      <section className={`py-16 ${isDark ? 'bg-slate-900/50' : 'bg-slate-50'}`}>
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
            >
              <h2 className="text-2xl md:text-3xl font-display font-bold mb-6 text-center">Nossa História</h2>
              <div className={`space-y-4 text-lg ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>
                <p>
                  O Gestor Cred surgiu em 2024, quando um grupo de desenvolvedores e profissionais do mercado financeiro percebeu que a maioria das soluções existentes eram complexas demais ou não atendiam às necessidades reais do mercado brasileiro.
                </p>
                <p>
                  Decidimos criar uma plataforma que fosse ao mesmo tempo poderosa e simples de usar. Uma ferramenta que permitisse a qualquer pessoa gerenciar seus empréstimos de forma profissional, sem precisar de conhecimentos técnicos avançados.
                </p>
                <p>
                  Hoje, o Gestor Cred ajuda centenas de profissionais a gerenciar milhões de reais em empréstimos, com segurança, praticidade e conformidade legal.
                </p>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Values */}
      <section className="container mx-auto px-4 py-16">
        <h2 className="text-2xl md:text-3xl font-display font-bold mb-12 text-center">Nossos Pilares</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {values.map((item, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
              className={`p-6 rounded-2xl text-center ${isDark ? 'bg-slate-800/50 border border-slate-700' : 'bg-white border border-slate-200 shadow-lg'}`}
            >
              <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                <item.icon className="w-7 h-7 text-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-3">{item.title}</h3>
              <p className={isDark ? 'text-slate-400' : 'text-slate-600'}>{item.description}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Stats */}
      <section className={`py-16 ${isDark ? 'bg-slate-900/50' : 'bg-slate-50'}`}>
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            {stats.map((stat, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="text-center"
              >
                <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                  <stat.icon className="w-7 h-7 text-primary" />
                </div>
                <p className="text-3xl md:text-4xl font-display font-bold text-primary mb-1">{stat.value}</p>
                <p className={isDark ? 'text-slate-400' : 'text-slate-600'}>{stat.label}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <Footer config={config} isDark={isDark} />
    </div>
  );
};

export default Sobre;
