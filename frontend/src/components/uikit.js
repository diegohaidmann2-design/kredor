import React from 'react';
import { Search, X } from 'lucide-react';
import AnimatedNumber from './AnimatedNumber';

const ICON = 1.5;

// ---- Tokens de status (neo-brutalista) ----
const TONE = {
  success: { dot: 'bg-emerald-500', ring: 'bg-emerald-500/10 text-emerald-500 ring-emerald-500/20' },
  warning: { dot: 'bg-amber-500', ring: 'bg-amber-500/10 text-amber-500 ring-amber-500/20' },
  danger: { dot: 'bg-rose-500', ring: 'bg-rose-500/10 text-rose-500 ring-rose-500/20' },
  info: { dot: 'bg-blue-500', ring: 'bg-blue-500/10 text-blue-500 ring-blue-500/20' },
  neutral: { dot: 'bg-slate-400', ring: 'bg-slate-500/10 text-slate-400 ring-slate-500/20' },
};

// Badge de status neo-brutalista: canto reto suave, ring interno, ponto colorido.
export const StatusBadge = ({ tone = 'neutral', children, dot = true, testId, className = '' }) => {
  const t = TONE[tone] || TONE.neutral;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md ring-1 ring-inset px-2 py-0.5 text-xs font-medium uppercase tracking-wider ${t.ring} ${className}`}
      data-testid={testId}
    >
      {dot && <span className={`h-1.5 w-1.5 rounded-full ${t.dot}`} />}
      {children}
    </span>
  );
};

// Avatar circular esmeralda com inicial (fonte mono).
export const Avatar = ({ name = '', size = 'md', testId, className = '' }) => {
  const dim = { sm: 'h-8 w-8 text-xs', md: 'h-10 w-10 text-sm', lg: 'h-11 w-11 text-base' }[size] || 'h-10 w-10 text-sm';
  const initial = (name || '').trim().charAt(0).toUpperCase() || '?';
  return (
    <div
      className={`${dim} rounded-full bg-emerald-500/10 ring-1 ring-emerald-500/20 flex items-center justify-center shrink-0 ${className}`}
      data-testid={testId}
    >
      <span className="text-emerald-400 font-mono font-semibold">{initial}</span>
    </div>
  );
};

// Cartão de seção padrão (substitui cards com shadow genérica).
export const SectionCard = ({ children, className = '', testId }) => (
  <div className={`rounded-xl bg-card ring-1 ring-border p-6 ${className}`} data-testid={testId}>
    {children}
  </div>
);

// Campo de formulário minimalista (foco esmeralda), sem emojis.
export const FormField = ({ label, children, hint, htmlFor, className = '' }) => (
  <div className={className}>
    {label && (
      <label htmlFor={htmlFor} className="block text-[11px] uppercase tracking-wider text-muted-foreground mb-1">
        {label}
      </label>
    )}
    {children}
    {hint && <p className="text-xs text-muted-foreground mt-1">{hint}</p>}
  </div>
);

export const inputMinimal =
  'w-full bg-transparent border-0 border-b border-border px-1 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-emerald-500 transition-colors';

// Cabeçalho de página no padrão da tela de Pagamentos.
export const PageHeader = ({ title, subtitle, children, testId, adornment }) => (
  <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
    <div className="min-w-0">
      <h1
        className="font-cabinet font-black text-3xl sm:text-4xl tracking-tighter text-foreground flex items-center gap-3"
        data-testid={testId}
      >
        {title}
        {adornment}
      </h1>
      {subtitle && <p className="text-muted-foreground mt-1.5">{subtitle}</p>}
    </div>
    {children && <div className="flex items-center gap-2 shrink-0">{children}</div>}
  </header>
);

// Cartão de indicador (KPI) idêntico ao de Pagamentos.
export const KpiCard = ({ label, amount, format = (n) => n, hint, Icon, tone = 'default', highlight = false, testId, delay = 0, isText = false }) => {
  const toneText = { default: 'text-foreground', green: 'text-emerald-400', red: 'text-red-400', amber: 'text-amber-400' }[tone];
  return (
    <div
      className={`relative rounded-xl bg-card p-6 ring-1 transition-all duration-200 hover:-translate-y-px animate-slide-up ${
        highlight ? 'ring-emerald-500/30 bg-gradient-to-br from-emerald-500/[0.06] to-transparent' : 'ring-border hover:ring-foreground/20'
      }`}
      style={{ animationDelay: `${delay}ms` }}
      data-testid={testId}
    >
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">{label}</p>
        {Icon && <Icon className={`w-4 h-4 ${highlight ? 'text-emerald-400' : 'text-muted-foreground'}`} strokeWidth={ICON} />}
      </div>
      {isText ? (
        <p className={`font-mono text-2xl sm:text-[1.7rem] font-semibold tracking-tight ${toneText}`}>{format(amount)}</p>
      ) : (
        <AnimatedNumber value={amount} format={format} className={`font-mono text-2xl sm:text-[1.7rem] font-semibold tracking-tight ${toneText}`} />
      )}
      {hint && <p className="text-xs text-muted-foreground mt-1.5">{hint}</p>}
    </div>
  );
};

// Estado vazio no padrão de Pagamentos.
export const EmptyState = ({ icon: Icon, titulo, subtitulo, testId, children }) => (
  <div className="flex flex-col items-center justify-center py-16 text-center" data-testid={testId}>
    {Icon && <Icon className="w-12 h-12 text-muted-foreground/30 mb-4" strokeWidth={1.25} />}
    <p className="font-cabinet font-bold text-lg text-foreground">{titulo}</p>
    {subtitulo && <p className="text-sm text-muted-foreground mt-1">{subtitulo}</p>}
    {children && <div className="mt-4">{children}</div>}
  </div>
);

// Campo de busca minimalista (borda inferior, foco esmeralda).
export const SearchBar = ({ value, onChange, placeholder, testId, resultText }) => (
  <div className="mb-6">
    <div className="relative max-w-md">
      <Search className="absolute left-1 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" strokeWidth={ICON} />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-transparent border-0 border-b border-border pl-7 pr-8 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-emerald-500 transition-colors"
        data-testid={testId}
      />
      {value && (
        <button
          onClick={() => onChange('')}
          className="absolute right-0 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
          title="Limpar busca"
        >
          <X className="w-4 h-4" strokeWidth={ICON} />
        </button>
      )}
    </div>
    {value && resultText && <p className="text-xs text-muted-foreground mt-2">{resultText}</p>}
  </div>
);

// Abas com sublinhado animado esmeralda.
export const UnderlineTabs = ({ tabs, active, onChange }) => (
  <div className="flex items-center gap-6 border-b border-border mb-6 overflow-x-auto">
    {tabs.map((t) => (
      <button
        key={t.id}
        onClick={() => onChange(t.id)}
        className={`relative -mb-px pb-3 text-sm font-medium transition-colors whitespace-nowrap ${
          active === t.id ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
        }`}
        data-testid={`tab-${t.id}`}
      >
        {t.label}
        {t.count != null && <span className="ml-1.5 font-mono text-xs text-muted-foreground">({t.count})</span>}
        {active === t.id && <span className="absolute left-0 right-0 -bottom-px h-0.5 rounded-full bg-emerald-500" />}
      </button>
    ))}
  </div>
);

// Wrapper padrão de página.
export const PageShell = ({ children }) => (
  <div className="container mx-auto px-4 sm:px-6 py-8 font-satoshi">{children}</div>
);
