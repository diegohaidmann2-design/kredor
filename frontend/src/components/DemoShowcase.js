import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  Wallet,
  Search,
  Calculator,
  FileBarChart,
  Play,
  ShieldCheck,
  ArrowUpRight,
  Star,
  Video
} from 'lucide-react';

import imgDashboard from '../assets/demo/dashboard.jpg';
import imgEmprestimos from '../assets/demo/emprestimos.jpg';
import imgConsultas from '../assets/demo/consultas.jpg';
import imgSimulacao from '../assets/demo/simulacao.jpg';
import imgRelatorios from '../assets/demo/relatorios.jpg';

/**
 * ▶️ VÍDEO DE DEMONSTRAÇÃO
 * Cole aqui o link do seu vídeo do YouTube ou Vimeo (ex.: https://www.youtube.com/watch?v=XXXX
 * ou https://vimeo.com/123456789). Deixe vazio ('') para exibir apenas o tour interativo.
 */
const VIDEO_DEMO_URL = '';

const toEmbedUrl = (url) => {
  if (!url) return null;
  const yt = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([\w-]{11})/);
  if (yt) return `https://www.youtube.com/embed/${yt[1]}?autoplay=1&rel=0`;
  const vm = url.match(/vimeo\.com\/(?:video\/)?(\d+)/);
  if (vm) return `https://player.vimeo.com/video/${vm[1]}?autoplay=1`;
  return url;
};

const TABS = [
  { id: 'dashboard', label: 'Dashboard', desc: 'Visão geral da carteira em tempo real', icon: LayoutDashboard, img: imgDashboard },
  { id: 'emprestimos', label: 'Empréstimos', desc: 'Controle de contratos, juros e status', icon: Wallet, img: imgEmprestimos },
  { id: 'consultas', label: 'Consulta de CPF', desc: 'Análise e score de crédito', icon: Search, img: imgConsultas },
  { id: 'simulacao', label: 'Simulação', desc: 'Simule valores, prazos e frequência', icon: Calculator, img: imgSimulacao },
  { id: 'relatorios', label: 'Relatórios', desc: 'Gere relatórios em PDF e Excel', icon: FileBarChart, img: imgRelatorios },
];

const AUTOPLAY_MS = 4600;

const DemoShowcase = ({ isDark = true }) => {
  const [active, setActive] = useState(0);
  const [mode, setMode] = useState('tour');
  const [paused, setPaused] = useState(false);
  const timer = useRef(null);
  const embed = toEmbedUrl(VIDEO_DEMO_URL);

  useEffect(() => {
    if (mode !== 'tour' || paused) return;
    timer.current = setTimeout(() => setActive((p) => (p + 1) % TABS.length), AUTOPLAY_MS);
    return () => clearTimeout(timer.current);
  }, [active, paused, mode]);

  const softText = isDark ? 'text-slate-400' : 'text-slate-500';
  const current = TABS[active];

  return (
    <section id="demo" className={`py-20 ${isDark ? 'bg-slate-950' : 'bg-white'}`}>
      <div className="container mx-auto px-4">
        <motion.div className="text-center mb-10" initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold mb-4">
            <Play className="w-3 h-3" /> Demonstração
          </span>
          <h2 className="text-3xl md:text-4xl font-display font-bold mb-3">Veja o Kredor por dentro</h2>
          <p className={`text-lg ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
            Telas reais: dashboard, contratos, análise de crédito, simulação e relatórios
          </p>
        </motion.div>

        {/* Mode toggle */}
        <div className="flex justify-center mb-6">
          <div className={`inline-flex p-1 rounded-xl ${isDark ? 'bg-slate-900 border border-slate-800' : 'bg-slate-100'}`}>
            <button onClick={() => setMode('tour')} data-testid="demo-mode-tour"
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition ${mode === 'tour' ? 'bg-primary text-white shadow' : (isDark ? 'text-slate-400' : 'text-slate-600')}`}>
              <LayoutDashboard className="w-4 h-4" /> Tour interativo
            </button>
            <button onClick={() => setMode('video')} data-testid="demo-mode-video"
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition ${mode === 'video' ? 'bg-primary text-white shadow' : (isDark ? 'text-slate-400' : 'text-slate-600')}`}>
              <Video className="w-4 h-4" /> Vídeo
            </button>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-6 max-w-6xl mx-auto items-start">
          {/* Tab list */}
          {mode === 'tour' && (
            <div className="lg:col-span-1 space-y-2 order-2 lg:order-1">
              {TABS.map((t, i) => (
                <button key={t.id} onClick={() => setActive(i)}
                  data-testid={`demo-tab-${t.id}`}
                  onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}
                  className={`w-full text-left flex items-start gap-3 px-4 py-3 rounded-xl border transition-all ${active === i
                    ? 'border-primary/50 bg-primary/10'
                    : `${isDark ? 'border-slate-800 hover:border-slate-700' : 'border-slate-200 hover:border-slate-300'}`}`}>
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${active === i ? 'bg-primary text-white' : (isDark ? 'bg-slate-800 text-slate-400' : 'bg-slate-100 text-slate-500')}`}>
                    <t.icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-semibold ${active === i ? 'text-primary' : ''}`}>{t.label}</p>
                    <p className={`text-xs truncate ${softText}`}>{t.desc}</p>
                  </div>
                  {active === i && (
                    <motion.span className="w-1.5 h-1.5 rounded-full bg-primary mt-2"
                      animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.5, repeat: Infinity }} />
                  )}
                </button>
              ))}
            </div>
          )}

          {/* Window frame */}
          <div className={`${mode === 'tour' ? 'lg:col-span-2' : 'lg:col-span-3'} order-1 lg:order-2`}
            onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}>
            <div className={`rounded-2xl border overflow-hidden shadow-2xl ${isDark ? 'border-slate-800 shadow-primary/5' : 'border-slate-200 shadow-slate-300/40'}`}>
              {/* Top bar */}
              <div className={`flex items-center gap-2 px-4 py-3 ${isDark ? 'bg-slate-900 border-b border-slate-800' : 'bg-slate-100 border-b border-slate-200'}`}>
                <span className="w-3 h-3 rounded-full bg-red-400/80" />
                <span className="w-3 h-3 rounded-full bg-amber-400/80" />
                <span className="w-3 h-3 rounded-full bg-emerald-400/80" />
                <div className={`ml-3 flex-1 text-center text-[11px] rounded-md py-1 ${isDark ? 'bg-slate-800 text-slate-500' : 'bg-white text-slate-400'}`}>
                  app.kredor.com.br/{current.id}
                </div>
              </div>
              {/* Body */}
              <div className={`${isDark ? 'bg-slate-950' : 'bg-slate-100'}`}>
                {mode === 'tour' ? (
                  <div className="relative w-full overflow-hidden" style={{ aspectRatio: '1600 / 955' }}>
                    <AnimatePresence mode="wait">
                      <motion.img key={current.id} src={current.img}
                        alt={`Tela ${current.label} do Kredor`}
                        data-testid={`demo-screen-${current.id}`}
                        className="absolute inset-0 w-full h-full object-cover object-top"
                        initial={{ opacity: 0, scale: 1.02 }} animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0 }} transition={{ duration: 0.5 }} />
                    </AnimatePresence>
                  </div>
                ) : embed ? (
                  <div className="relative w-full" style={{ paddingTop: '56.25%' }}>
                    <iframe title="Demonstração Kredor" src={embed}
                      className="absolute inset-0 w-full h-full"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                      allowFullScreen data-testid="demo-video-iframe" />
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center text-center py-16 px-6" data-testid="demo-video-placeholder">
                    <motion.div className="w-16 h-16 rounded-full bg-primary/15 flex items-center justify-center mb-4"
                      animate={{ scale: [1, 1.08, 1] }} transition={{ duration: 1.8, repeat: Infinity }}>
                      <Play className="w-7 h-7 text-primary ml-1" />
                    </motion.div>
                    <p className="font-semibold mb-1">Vídeo em breve</p>
                    <p className={`text-sm max-w-sm ${softText}`}>
                      Grave um vídeo do sistema e cole o link do YouTube/Vimeo em
                      <code className="mx-1 px-1.5 py-0.5 rounded bg-primary/10 text-primary">VIDEO_DEMO_URL</code>
                      para exibi-lo aqui. Enquanto isso, confira o tour com telas reais.
                    </p>
                    <button onClick={() => setMode('tour')}
                      className="mt-4 text-sm font-medium text-primary hover:underline">
                      Ver tour interativo →
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Progress dots (mobile-friendly) */}
            {mode === 'tour' && (
              <div className="flex items-center justify-center gap-2 mt-4 lg:hidden">
                {TABS.map((t, i) => (
                  <button key={t.id} onClick={() => setActive(i)} aria-label={t.label}
                    className={`h-1.5 rounded-full transition-all ${active === i ? 'w-6 bg-primary' : 'w-2 bg-slate-500/40'}`} />
                ))}
              </div>
            )}

            {/* Trust row */}
            <div className={`flex flex-wrap items-center justify-center gap-x-6 gap-y-2 mt-5 text-xs ${softText}`}>
              <span className="flex items-center gap-1.5"><ShieldCheck className="w-4 h-4 text-emerald-400" /> Dados criptografados</span>
              <span className="flex items-center gap-1.5"><ArrowUpRight className="w-4 h-4 text-emerald-400" /> Baixa automática de PIX</span>
              <span className="flex items-center gap-1.5"><Star className="w-4 h-4 text-amber-400" /> 4.9/5 de avaliação</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default DemoShowcase;
