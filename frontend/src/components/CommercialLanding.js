import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, ArrowLeft, ChevronRight, ShieldCheck } from 'lucide-react';
import { Button } from './ui/button';
import Footer from './Footer';
import { configuracoesAPI } from '../api/api';
import logomark from '../assets/logomark.png';
import useSeo from '../hooks/useSeo';

/**
 * Layout reutilizável para as landing pages comerciais (site público).
 * O conteúdo é único por página; apenas a estrutura visual é compartilhada.
 */
const CommercialLanding = ({
  seo,
  eyebrow,
  h1,
  subtitle,
  heroBullets = [],
  blocks = [],
  diffTitle = 'O que o GestorCred tem que os concorrentes simples não têm',
  differentials = [],
  faq = [],
  related = [],
  ctaTitle = 'Comece a organizar sua carteira de crédito hoje',
  ctaText = 'Teste grátis por 7 dias. Sem cartão de crédito.',
  children,
}) => {
  const [config, setConfig] = useState({ nome_empresa: 'GestorCred' });
  const [isDark, setIsDark] = useState(true);

  useSeo({ title: seo?.title, description: seo?.description, path: seo?.path });

  useEffect(() => {
    (async () => {
      try {
        const res = await configuracoesAPI.obterLanding();
        setConfig((c) => ({ ...c, ...res.data }));
      } catch (e) {}
    })();
    setIsDark(localStorage.getItem('sgej-theme') !== 'light');
    window.scrollTo(0, 0);
  }, []);

  const cardBg = isDark ? 'bg-slate-800/50 border-slate-700' : 'bg-white border-slate-200';

  return (
    <div className={`min-h-screen transition-colors duration-300 ${isDark ? 'bg-slate-950 text-white' : 'bg-white text-slate-900'}`}>
      {/* Header */}
      <header className={`sticky top-0 z-40 backdrop-blur-xl border-b ${isDark ? 'bg-slate-950/80 border-slate-800' : 'bg-white/80 border-slate-200'}`}>
        <nav className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3" data-testid="landing-brand">
            <img src={logomark} alt="GestorCred - sistema de gestão de empréstimos" className="w-9 h-9 object-contain" />
            <span className="text-lg font-display font-bold">
              <span className="text-primary">Gestor</span>
              <span className={isDark ? 'text-white' : 'text-slate-900'}>Cred</span>
            </span>
          </Link>
          <div className="hidden md:flex items-center gap-6 text-sm">
            <Link to="/como-funciona" className={isDark ? 'text-slate-300 hover:text-white' : 'text-slate-600 hover:text-slate-900'}>Como funciona</Link>
            <Link to="/precos" className={isDark ? 'text-slate-300 hover:text-white' : 'text-slate-600 hover:text-slate-900'}>Preços</Link>
            <Link to="/faq" className={isDark ? 'text-slate-300 hover:text-white' : 'text-slate-600 hover:text-slate-900'}>FAQ</Link>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/login" className={`text-sm font-medium ${isDark ? 'text-slate-300 hover:text-white' : 'text-slate-600 hover:text-slate-900'}`} data-testid="landing-login">Entrar</Link>
            <Link to="/login">
              <Button size="sm" className="bg-primary hover:bg-primary/90 text-white" data-testid="landing-cta-top">Teste grátis</Button>
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero */}
      <section className="container mx-auto px-4 pt-16 pb-12 max-w-4xl">
        <Link to="/" className={`inline-flex items-center gap-1 text-sm mb-6 ${isDark ? 'text-slate-400 hover:text-white' : 'text-slate-500 hover:text-slate-900'}`}>
          <ArrowLeft className="w-4 h-4" /> Voltar para a home
        </Link>
        {eyebrow && (
          <span className="inline-block mb-4 text-xs font-semibold tracking-wide uppercase text-primary bg-primary/10 border border-primary/20 rounded-full px-3 py-1">
            {eyebrow}
          </span>
        )}
        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-3xl md:text-5xl font-display font-bold leading-tight mb-5"
          data-testid="landing-h1"
        >
          {h1}
        </motion.h1>
        <p className={`text-lg md:text-xl mb-6 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>{subtitle}</p>
        {heroBullets.length > 0 && (
          <ul className="grid sm:grid-cols-2 gap-2 mb-8">
            {heroBullets.map((b, i) => (
              <li key={i} className={`flex items-start gap-2 text-sm ${isDark ? 'text-slate-300' : 'text-slate-700'}`}>
                <ChevronRight className="w-4 h-4 mt-0.5 text-primary shrink-0" /> {b}
              </li>
            ))}
          </ul>
        )}
        <div className="flex flex-col sm:flex-row gap-3">
          <Link to="/login">
            <Button size="lg" className="bg-primary hover:bg-primary/90 text-white shadow-glow px-8" data-testid="landing-cta-hero">
              Começar teste grátis <ArrowRight className="ml-2 w-5 h-5" />
            </Button>
          </Link>
          <Link to="/como-funciona">
            <Button size="lg" variant="outline">Ver como funciona</Button>
          </Link>
        </div>
      </section>

      {/* Custom children (ex.: calculadora, tabela de planos) */}
      {children && (
        <section className="container mx-auto px-4 py-6 max-w-4xl">
          {typeof children === 'function' ? children({ config, isDark }) : children}
        </section>
      )}

      {/* Blocks / conteúdo */}
      {blocks.length > 0 && (
        <section className="container mx-auto px-4 py-10 max-w-4xl">
          <div className="grid md:grid-cols-2 gap-6">
            {blocks.map((b, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                className={`rounded-xl border p-6 ${cardBg}`}
              >
                {b.icon && <b.icon className="w-8 h-8 text-primary mb-3" />}
                <h2 className="text-lg font-display font-semibold mb-2">{b.title}</h2>
                <p className={`text-sm leading-relaxed ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>{b.text}</p>
              </motion.div>
            ))}
          </div>
        </section>
      )}

      {/* Diferenciais */}
      {differentials.length > 0 && (
        <section className={`py-12 ${isDark ? 'bg-slate-900/50' : 'bg-slate-50'}`}>
          <div className="container mx-auto px-4 max-w-4xl">
            <h2 className="text-2xl md:text-3xl font-display font-bold mb-8 text-center">{diffTitle}</h2>
            <div className="grid sm:grid-cols-2 gap-5">
              {differentials.map((d, i) => (
                <div key={i} className={`rounded-lg border p-5 ${cardBg}`}>
                  <h3 className="font-semibold mb-1 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-primary" /> {d.title}
                  </h3>
                  <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>{d.text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* FAQ */}
      {faq.length > 0 && (
        <section className="container mx-auto px-4 py-12 max-w-3xl">
          <h2 className="text-2xl md:text-3xl font-display font-bold mb-6">Perguntas frequentes</h2>
          <div className="space-y-4">
            {faq.map((f, i) => (
              <div key={i} className={`rounded-lg border p-5 ${cardBg}`}>
                <h3 className="font-semibold mb-2">{f.q}</h3>
                <p className={`text-sm ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>{f.a}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Links internos relacionados */}
      {related.length > 0 && (
        <section className="container mx-auto px-4 pb-12 max-w-4xl">
          <h2 className="text-sm font-semibold uppercase tracking-wide mb-4 text-primary">Explore também</h2>
          <div className="flex flex-wrap gap-3">
            {related.map((r, i) => (
              <Link
                key={i}
                to={r.to}
                className={`inline-flex items-center gap-1 text-sm rounded-full border px-4 py-2 transition ${isDark ? 'border-slate-700 text-slate-300 hover:border-primary hover:text-white' : 'border-slate-300 text-slate-700 hover:border-primary'}`}
              >
                {r.label} <ChevronRight className="w-3 h-3" />
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* CTA final */}
      <section className="container mx-auto px-4 py-14 max-w-3xl text-center">
        <div className="rounded-2xl border border-primary/30 bg-primary/10 p-8">
          <h2 className="text-2xl md:text-3xl font-display font-bold mb-3">{ctaTitle}</h2>
          <p className={`mb-6 ${isDark ? 'text-slate-300' : 'text-slate-600'}`}>{ctaText}</p>
          <Link to="/login">
            <Button size="lg" className="bg-primary hover:bg-primary/90 text-white px-8" data-testid="landing-cta-final">
              Criar minha conta grátis <ArrowRight className="ml-2 w-5 h-5" />
            </Button>
          </Link>
          <p className={`text-xs mt-4 ${isDark ? 'text-slate-500' : 'text-slate-500'}`}>
            O GestorCred é um software de gestão. Não concede empréstimos nem realiza operações de crédito.
          </p>
        </div>
      </section>

      <Footer config={config} isDark={isDark} />
    </div>
  );
};

export default CommercialLanding;
