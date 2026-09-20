import React, { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, Sun, Moon, ChevronDown, ArrowRight } from 'lucide-react';
import { Button } from './ui/button';
import { useTheme } from '../context/ThemeContext';
import logomark from '../assets/logomark.png';

// Itens do menu "Soluções" (todas as rotas já existem em App.js).
const SOLUCOES = [
  { label: 'Gestão de empréstimos', to: '/sistema-gestao-emprestimos' },
  { label: 'Cobrança no WhatsApp', to: '/cobranca-whatsapp' },
  { label: 'Cobrança PIX', to: '/cobranca-pix' },
  { label: 'Parcelas e juros', to: '/controle-de-parcelas-e-juros' },
  { label: 'Gestão de clientes', to: '/gestao-de-clientes' },
  { label: 'Consulta de CPF', to: '/consulta-cpf-credito' },
  { label: 'Calculadora de juros', to: '/calculadora-de-juros' },
];

const NAV = [
  { label: 'Como funciona', to: '/como-funciona' },
  { label: 'Preços', to: '/precos' },
  { label: 'Blog', to: '/blog' },
  { label: 'FAQ', to: '/faq' },
];

/**
 * Cabeçalho público unificado (marketing/SEO/institucional).
 * NÃO é usado no painel logado — o dashboard tem sidebar própria.
 * Tema controlado pelo ThemeContext (funciona em toda a área pública).
 */
const SiteHeader = () => {
  const { isDark, toggleTheme } = useTheme();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [solOpen, setSolOpen] = useState(false);
  const solRef = useRef(null);

  const isActive = (to) =>
    location.pathname === to || (to !== '/' && location.pathname.startsWith(`${to}/`));
  const solActive = SOLUCOES.some((s) => isActive(s.to));

  // Fecha os menus ao trocar de rota.
  useEffect(() => {
    setMobileOpen(false);
    setSolOpen(false);
  }, [location.pathname]);

  // Esc fecha qualquer menu aberto.
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') {
        setMobileOpen(false);
        setSolOpen(false);
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  // Trava o scroll do body quando o menu mobile está aberto.
  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileOpen]);

  // Clique fora fecha o dropdown de Soluções (desktop).
  useEffect(() => {
    const onClick = (e) => {
      if (solRef.current && !solRef.current.contains(e.target)) setSolOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const pill = isDark ? 'bg-slate-900/80 border-slate-700/70' : 'bg-white/85 border-slate-200';
  const linkBase = 'text-sm font-medium transition-colors px-3 py-2 rounded-lg';
  const linkIdle = isDark
    ? 'text-slate-300 hover:text-white hover:bg-white/5'
    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100';
  const linkActive = isDark ? 'text-white bg-white/10' : 'text-slate-900 bg-slate-100';
  const panelBg = isDark ? 'bg-slate-900 border-slate-700' : 'bg-white border-slate-200';
  const divider = isDark ? 'bg-slate-800' : 'bg-slate-200';

  return (
    <div className="sticky top-0 z-50 px-3 sm:px-4 pt-3 sm:pt-4" data-testid="site-header-wrapper">
      <header
        className={`mx-auto max-w-6xl rounded-2xl border backdrop-blur-xl shadow-lg shadow-black/5 ${pill}`}
        data-testid="site-header"
      >
        <nav
          className="flex items-center justify-between gap-2 px-4 sm:px-5 py-2.5"
          aria-label="Navegação principal"
        >
          {/* Marca */}
          <Link
            to="/"
            className="flex items-center gap-2 shrink-0"
            data-testid="site-brand"
            aria-label="Kredor - página inicial"
          >
            <img src={logomark} alt="Kredor" className="w-8 h-8 object-contain" />
            <span className="text-lg font-display font-bold">
              <span className="text-primary">Kredor</span>
            </span>
          </Link>

          {/* Navegação desktop */}
          <div className="hidden lg:flex items-center gap-1">
            <div className="relative" ref={solRef}>
              <button
                type="button"
                onClick={() => setSolOpen((v) => !v)}
                className={`${linkBase} inline-flex items-center gap-1 ${solActive ? linkActive : linkIdle}`}
                aria-haspopup="true"
                aria-expanded={solOpen}
                data-testid="site-nav-solucoes"
              >
                Soluções
                <ChevronDown className={`w-4 h-4 transition-transform ${solOpen ? 'rotate-180' : ''}`} />
              </button>
              {solOpen && (
                <div
                  className={`absolute left-0 mt-2 w-64 rounded-xl border p-2 shadow-xl ${panelBg}`}
                  role="menu"
                  data-testid="site-solucoes-menu"
                >
                  {SOLUCOES.map((s) => (
                    <Link
                      key={s.to}
                      to={s.to}
                      role="menuitem"
                      className={`block px-3 py-2 rounded-lg text-sm ${isActive(s.to) ? linkActive : linkIdle}`}
                    >
                      {s.label}
                    </Link>
                  ))}
                </div>
              )}
            </div>
            {NAV.map((n) => (
              <Link
                key={n.to}
                to={n.to}
                className={`${linkBase} ${isActive(n.to) ? linkActive : linkIdle}`}
                aria-current={isActive(n.to) ? 'page' : undefined}
                data-testid={`site-nav-${n.to.replace('/', '')}`}
              >
                {n.label}
              </Link>
            ))}
          </div>

          {/* Ações */}
          <div className="flex items-center gap-1 sm:gap-2">
            <button
              type="button"
              onClick={toggleTheme}
              className={`p-2 rounded-lg transition ${isDark ? 'text-slate-300 hover:text-white hover:bg-white/5' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'}`}
              aria-label={isDark ? 'Ativar tema claro' : 'Ativar tema escuro'}
              data-testid="site-theme-toggle"
            >
              {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
            <Link
              to="/login"
              className={`hidden sm:inline-flex ${linkBase} ${linkIdle}`}
              data-testid="site-login"
            >
              Entrar
            </Link>
            <Link to="/login" className="hidden sm:block">
              <Button
                size="sm"
                className="bg-primary hover:bg-primary/90 text-white rounded-lg"
                data-testid="site-cta"
              >
                Começar Agora
              </Button>
            </Link>
            <button
              type="button"
              onClick={() => setMobileOpen((v) => !v)}
              className={`lg:hidden p-2 rounded-lg transition ${isDark ? 'text-slate-300 hover:bg-white/5' : 'text-slate-600 hover:bg-slate-100'}`}
              aria-label={mobileOpen ? 'Fechar menu' : 'Abrir menu'}
              aria-expanded={mobileOpen}
              aria-controls="site-mobile-menu"
              data-testid="site-mobile-toggle"
            >
              {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </nav>
      </header>

      {/* Menu mobile (drawer) */}
      {mobileOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/40 lg:hidden"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <div
            id="site-mobile-menu"
            className={`fixed z-50 top-20 left-3 right-3 max-h-[80vh] overflow-y-auto rounded-2xl border p-4 shadow-2xl lg:hidden ${panelBg}`}
            data-testid="site-mobile-menu"
            role="dialog"
            aria-modal="true"
            aria-label="Menu de navegação"
          >
            <p className={`px-3 pt-1 pb-1 text-xs font-semibold uppercase tracking-wide ${isDark ? 'text-slate-500' : 'text-slate-400'}`}>
              Soluções
            </p>
            {SOLUCOES.map((s) => (
              <Link
                key={s.to}
                to={s.to}
                className={`block px-3 py-2 rounded-lg text-sm ${isActive(s.to) ? linkActive : linkIdle}`}
              >
                {s.label}
              </Link>
            ))}
            <div className={`my-2 h-px ${divider}`} />
            {NAV.map((n) => (
              <Link
                key={n.to}
                to={n.to}
                className={`block px-3 py-2 rounded-lg text-sm ${isActive(n.to) ? linkActive : linkIdle}`}
                aria-current={isActive(n.to) ? 'page' : undefined}
              >
                {n.label}
              </Link>
            ))}
            <div className={`my-2 h-px ${divider}`} />
            <Link to="/login" className={`block px-3 py-2 rounded-lg text-sm ${linkIdle}`}>
              Entrar
            </Link>
            <Link to="/login" className="block pt-1">
              <Button className="w-full bg-primary hover:bg-primary/90 text-white">
                Começar Agora <ArrowRight className="ml-2 w-4 h-4" />
              </Button>
            </Link>
          </div>
        </>
      )}
    </div>
  );
};

export default SiteHeader;
