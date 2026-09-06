import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  Wallet,
  QrCode,
  Search,
  UserCheck,
  Play,
  MessageCircle,
  TrendingUp,
  CheckCircle2,
  Clock,
  ArrowUpRight,
  ShieldCheck,
  Star,
  Video
} from 'lucide-react';

/**
 * ▶️ VÍDEO DE DEMONSTRAÇÃO
 * Cole aqui o link do seu vídeo do YouTube ou Vimeo (ex.: https://www.youtube.com/watch?v=XXXX
 * ou https://vimeo.com/123456789). Deixe vazio ('') para exibir apenas o tour interativo.
 */
const VIDEO_DEMO_URL = '';

const toEmbedUrl = (url) => {
  if (!url) return null;
  try {
    const yt = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([\w-]{11})/);
    if (yt) return `https://www.youtube.com/embed/${yt[1]}?autoplay=1&rel=0`;
    const vm = url.match(/vimeo\.com\/(?:video\/)?(\d+)/);
    if (vm) return `https://player.vimeo.com/video/${vm[1]}?autoplay=1`;
    return url;
  } catch {
    return url;
  }
};

const TABS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'emprestimos', label: 'Empréstimos', icon: Wallet },
  { id: 'cobranca', label: 'Cobrança PIX/WhatsApp', icon: QrCode },
  { id: 'consulta', label: 'Consulta de CPF', icon: Search },
  { id: 'portal', label: 'Portal do Cliente', icon: UserCheck },
];

const AUTOPLAY_MS = 4200;

const DemoShowcase = ({ isDark = true }) => {
  const [active, setActive] = useState(0);
  const [mode, setMode] = useState('tour'); // 'tour' | 'video'
  const [paused, setPaused] = useState(false);
  const timer = useRef(null);
  const embed = toEmbedUrl(VIDEO_DEMO_URL);

  useEffect(() => {
    if (mode !== 'tour' || paused) return;
    timer.current = setTimeout(() => setActive((p) => (p + 1) % TABS.length), AUTOPLAY_MS);
    return () => clearTimeout(timer.current);
  }, [active, paused, mode]);

  const surface = isDark ? 'bg-slate-900/70 border-slate-700/60' : 'bg-white border-slate-200';
  const soft = isDark ? 'bg-slate-800/70' : 'bg-slate-100';
  const softText = isDark ? 'text-slate-400' : 'text-slate-500';
  const line = isDark ? 'bg-slate-700/70' : 'bg-slate-200';

  const Bar = ({ w, delay = 0 }) => (
    <motion.div className={`h-2 rounded-full ${line}`} initial={{ width: 0 }}
      animate={{ width: w }} transition={{ duration: 0.5, delay }} />
  );

  const screens = {
    dashboard: (
      <div className="grid grid-cols-3 gap-3 h-full">
        {[
          { l: 'Total Emprestado', v: 'R$ 128.400', i: Wallet, c: 'text-emerald-400' },
          { l: 'A Receber', v: 'R$ 42.180', i: TrendingUp, c: 'text-sky-400' },
          { l: 'Inadimplência', v: '4,2%', i: Clock, c: 'text-amber-400' },
        ].map((s, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            className={`rounded-xl p-3 border ${surface}`}>
            <s.i className={`w-4 h-4 ${s.c}`} />
            <p className={`text-[10px] mt-2 ${softText}`}>{s.l}</p>
            <p className="text-sm md:text-base font-bold">{s.v}</p>
          </motion.div>
        ))}
        <motion.div className={`col-span-2 rounded-xl p-3 border ${surface}`}
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.25 }}>
          <p className={`text-[10px] mb-3 ${softText}`}>Recebimentos (últimos meses)</p>
          <div className="flex items-end gap-2 h-24">
            {[45, 62, 38, 78, 55, 90].map((h, i) => (
              <motion.div key={i} className="flex-1 rounded-t-md bg-gradient-to-t from-emerald-600 to-emerald-400"
                initial={{ height: 0 }} animate={{ height: `${h}%` }}
                transition={{ delay: 0.3 + i * 0.06, type: 'spring', stiffness: 120 }} />
            ))}
          </div>
        </motion.div>
        <motion.div className={`rounded-xl p-3 border ${surface} flex flex-col items-center justify-center`}
          initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.35 }}>
          <div className="relative w-16 h-16">
            <svg viewBox="0 0 36 36" className="w-16 h-16 -rotate-90">
              <circle cx="18" cy="18" r="15" fill="none" strokeWidth="4" className={isDark ? 'stroke-slate-700' : 'stroke-slate-200'} />
              <motion.circle cx="18" cy="18" r="15" fill="none" strokeWidth="4" strokeLinecap="round"
                className="stroke-emerald-400" strokeDasharray="94"
                initial={{ strokeDashoffset: 94 }} animate={{ strokeDashoffset: 20 }}
                transition={{ duration: 1, delay: 0.4 }} />
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-sm font-bold">78%</span>
          </div>
          <p className={`text-[10px] mt-2 ${softText}`}>Adimplência</p>
        </motion.div>
      </div>
    ),
    emprestimos: (
      <div className={`rounded-xl border ${surface} overflow-hidden`}>
        <div className={`px-3 py-2 text-[11px] font-semibold flex justify-between ${soft}`}>
          <span>Parcelas do Empréstimo #1042</span><span className={softText}>12x • Price</span>
        </div>
        {[
          { n: '01/12', v: 'R$ 1.240', s: 'Pago', c: 'text-emerald-400', bg: 'bg-emerald-400/10' },
          { n: '02/12', v: 'R$ 1.240', s: 'Pago', c: 'text-emerald-400', bg: 'bg-emerald-400/10' },
          { n: '03/12', v: 'R$ 1.240', s: 'Vence hoje', c: 'text-sky-400', bg: 'bg-sky-400/10' },
          { n: '04/12', v: 'R$ 1.240', s: 'Atrasada', c: 'text-amber-400', bg: 'bg-amber-400/10' },
          { n: '05/12', v: 'R$ 1.240', s: 'Pendente', c: softText, bg: soft },
        ].map((r, i) => (
          <motion.div key={i} initial={{ opacity: 0, x: -14 }} animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.08 }}
            className={`flex items-center justify-between px-3 py-2 text-xs border-t ${isDark ? 'border-slate-800' : 'border-slate-100'}`}>
            <span className={`w-10 ${softText}`}>{r.n}</span>
            <span className="font-semibold flex-1 ml-3">{r.v}</span>
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${r.bg} ${r.c}`}>{r.s}</span>
          </motion.div>
        ))}
      </div>
    ),
    cobranca: (
      <div className="grid grid-cols-5 gap-3 h-full">
        <div className={`col-span-3 rounded-xl border ${surface} p-3 flex flex-col`}>
          <div className="flex items-center gap-2 mb-3">
            <MessageCircle className="w-4 h-4 text-emerald-400" />
            <span className="text-[11px] font-semibold">Régua de cobrança • WhatsApp</span>
          </div>
          <div className="space-y-2 flex-1">
            {[
              'Olá João! Sua parcela de R$ 1.240 vence hoje. 😊',
              'Segue o PIX para pagamento rápido 👇',
            ].map((m, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 + i * 0.4 }}
                className="ml-auto max-w-[85%] bg-emerald-500/90 text-white text-[11px] rounded-2xl rounded-tr-sm px-3 py-2">
                {m}
              </motion.div>
            ))}
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.1 }}
              className={`max-w-[70%] text-[11px] rounded-2xl rounded-tl-sm px-3 py-2 ${soft}`}>
              Recebido! Pagamento confirmado ✅
            </motion.div>
          </div>
        </div>
        <motion.div className={`col-span-2 rounded-xl border ${surface} p-3 flex flex-col items-center justify-center`}
          initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.3 }}>
          <div className="p-2 rounded-lg bg-white">
            <QrCode className="w-16 h-16 text-slate-900" />
          </div>
          <p className="text-[11px] font-semibold mt-2">PIX Dinâmico</p>
          <p className={`text-[10px] ${softText}`}>R$ 1.240,00</p>
          <motion.span className="mt-2 flex items-center gap-1 text-[10px] text-emerald-400"
            animate={{ opacity: [0.4, 1, 0.4] }} transition={{ duration: 1.5, repeat: Infinity }}>
            <CheckCircle2 className="w-3 h-3" /> Baixa automática
          </motion.span>
        </motion.div>
      </div>
    ),
    consulta: (
      <div className="h-full flex flex-col gap-3">
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
          className={`flex items-center gap-2 rounded-xl border ${surface} px-3 py-2.5`}>
          <Search className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-mono tracking-wider">123.456.789-00</span>
          <span className="ml-auto text-[10px] px-2 py-0.5 rounded-md bg-emerald-500/15 text-emerald-400">Consultar</span>
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}
          className={`rounded-xl border ${surface} p-4 flex-1`}>
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-sm font-bold">João P. da Silva</p>
              <p className={`text-[10px] ${softText}`}>Situação: Regular • SP</p>
            </div>
            <div className="text-right">
              <p className={`text-[10px] ${softText}`}>Score</p>
              <p className="text-lg font-bold text-emerald-400">742</p>
            </div>
          </div>
          <div className="space-y-2">
            <div><p className={`text-[10px] mb-1 ${softText}`}>Dados cadastrais</p><Bar w="90%" /></div>
            <div><p className={`text-[10px] mb-1 ${softText}`}>Endereço confirmado</p><Bar w="70%" delay={0.1} /></div>
            <div><p className={`text-[10px] mb-1 ${softText}`}>Histórico de crédito</p><Bar w="55%" delay={0.2} /></div>
          </div>
        </motion.div>
      </div>
    ),
    portal: (
      <div className="h-full flex items-center justify-center">
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
          className={`w-56 rounded-2xl border ${surface} p-4`}>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
              <UserCheck className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <p className="text-xs font-semibold">Olá, Maria 👋</p>
              <p className={`text-[10px] ${softText}`}>Minhas parcelas</p>
            </div>
          </div>
          <div className={`rounded-xl p-3 mb-3 ${soft}`}>
            <p className={`text-[10px] ${softText}`}>Próxima parcela</p>
            <p className="text-lg font-bold">R$ 890,00</p>
            <p className="text-[10px] text-sky-400">Vence em 3 dias</p>
          </div>
          <motion.div whileHover={{ scale: 1.03 }}
            className="text-center text-xs font-semibold text-white bg-gradient-to-r from-emerald-500 to-teal-500 rounded-xl py-2.5 flex items-center justify-center gap-1">
            <QrCode className="w-4 h-4" /> Pagar com PIX
          </motion.div>
          <p className={`text-[9px] text-center mt-2 ${softText}`}>Autoatendimento 24h</p>
        </motion.div>
      </div>
    ),
  };

  const currentId = TABS[active].id;

  return (
    <section id="demo" className={`py-20 ${isDark ? 'bg-slate-950' : 'bg-white'}`}>
      <div className="container mx-auto px-4">
        <motion.div className="text-center mb-10" initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold mb-4">
            <Play className="w-3 h-3" /> Demonstração
          </span>
          <h2 className="text-3xl md:text-4xl font-display font-bold mb-3">Veja o GestorCred em ação</h2>
          <p className={`text-lg ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
            Um tour pelas principais telas — cobrança PIX, régua no WhatsApp, consulta de CPF e portal do cliente
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
                <button key={t.id} onClick={() => { setActive(i); }}
                  data-testid={`demo-tab-${t.id}`}
                  onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}
                  className={`w-full text-left flex items-center gap-3 px-4 py-3 rounded-xl border transition-all ${active === i
                    ? 'border-primary/50 bg-primary/10'
                    : `${isDark ? 'border-slate-800 hover:border-slate-700' : 'border-slate-200 hover:border-slate-300'}`}`}>
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${active === i ? 'bg-primary text-white' : (isDark ? 'bg-slate-800 text-slate-400' : 'bg-slate-100 text-slate-500')}`}>
                    <t.icon className="w-4 h-4" />
                  </div>
                  <span className={`text-sm font-medium flex-1 ${active === i ? 'text-primary' : ''}`}>{t.label}</span>
                  {active === i && (
                    <motion.div layoutId="demo-progress" className="w-1.5 h-1.5 rounded-full bg-primary"
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
                  app.gestorcred.cloud
                </div>
              </div>
              {/* Body */}
              <div className={`p-4 md:p-6 ${isDark ? 'bg-slate-950' : 'bg-slate-50'}`} style={{ minHeight: 320 }}>
                {mode === 'tour' ? (
                  <AnimatePresence mode="wait">
                    <motion.div key={currentId} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -12 }} transition={{ duration: 0.35 }} className="h-full">
                      <div className="flex items-center gap-2 mb-4">
                        {React.createElement(TABS[active].icon, { className: 'w-4 h-4 text-primary' })}
                        <span className="text-sm font-semibold">{TABS[active].label}</span>
                      </div>
                      <div style={{ minHeight: 250 }}>{screens[currentId]}</div>
                    </motion.div>
                  </AnimatePresence>
                ) : embed ? (
                  <div className="relative w-full" style={{ paddingTop: '56.25%' }}>
                    <iframe title="Demonstração GestorCred" src={embed}
                      className="absolute inset-0 w-full h-full rounded-lg"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                      allowFullScreen data-testid="demo-video-iframe" />
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center text-center h-full py-12" data-testid="demo-video-placeholder">
                    <motion.div className="w-16 h-16 rounded-full bg-primary/15 flex items-center justify-center mb-4"
                      animate={{ scale: [1, 1.08, 1] }} transition={{ duration: 1.8, repeat: Infinity }}>
                      <Play className="w-7 h-7 text-primary ml-1" />
                    </motion.div>
                    <p className="font-semibold mb-1">Vídeo em breve</p>
                    <p className={`text-sm max-w-sm ${softText}`}>
                      Grave um vídeo do sistema e cole o link do YouTube/Vimeo em
                      <code className="mx-1 px-1.5 py-0.5 rounded bg-primary/10 text-primary">VIDEO_DEMO_URL</code>
                      para exibi-lo aqui. Enquanto isso, confira o tour interativo.
                    </p>
                    <button onClick={() => setMode('tour')}
                      className="mt-4 text-sm font-medium text-primary hover:underline">
                      Ver tour interativo →
                    </button>
                  </div>
                )}
              </div>
            </div>

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
