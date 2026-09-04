import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { consultasAPI } from '../api/api';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import {
  Search, ScanSearch, IdCard, Phone, Building2, Building, User, UserCheck, AlertCircle,
  ChevronDown, Clock, Trash2, ShieldCheck, Loader2, RefreshCw, MapPin, Mail, Globe,
  Briefcase, Users, CreditCard, Home, Car, Gavel, TrendingUp, PieChart, Coins,
  AlertTriangle, FileText, Vote, Heart, BadgeCheck, Shield, MessageSquare, Syringe,
  ShoppingBag, Wifi, Receipt, Sparkles, Fingerprint, Activity, Lock
} from 'lucide-react';

// ---------- Mapas de rótulos / ícones ----------
const SECTION_LABELS = {
  dadosBasicos: 'Dados Básicos', rgHistorico: 'RG (Histórico)', carteiraHabilitacao: 'CNH / Habilitação',
  tituloHistorico: 'Título de Eleitor', cnsHistorico: 'CNS (Cartão SUS)', pisHistorico: 'PIS / NIS',
  codigoCtps: 'CTPS', alistamentoMilitar: 'Alistamento Militar', opiniaoPolitica: 'Opinião Política',
  poderAquisitivo: 'Poder Aquisitivo', serasaMosaic: 'Serasa Mosaic', telefonesHistorico: 'Telefones',
  emails: 'E-mails', redesSociais: 'Redes Sociais', enderecos: 'Endereços', curriculos: 'Currículo',
  empregos: 'Empregos / Vínculos', empresas: 'Empresas', beneficios: 'Benefícios', dividas: 'Dívidas',
  vacinas: 'Vacinas', parentesNovos: 'Parentes', compras: 'Compras', cartoesUsados: 'Cartões',
  internet: 'Presença na Internet', imoveis: 'Imóveis', irpf: 'IRPF', veiculos: 'Veículos',
  processos: 'Processos', interesses: 'Interesses', consumos: 'Consumos', filiacao: 'Filiação',
  situacaoCadastral: 'Situação Cadastral', biometria: 'Biometria', corretores: 'Corretores',
};

const FIELD_LABELS = {
  cpf: 'CPF', nome: 'Nome', dataNasc: 'Nascimento', sexo: 'Sexo', estCivil: 'Estado Civil',
  faixaScore: 'Faixa de Score', rendaAtual: 'Renda Atual', salarioUltimo: 'Último Salário',
  salarioAno: 'Ano', escolaridade: 'Escolaridade', naturalidade: 'Naturalidade',
  nacionalidade: 'Nacionalidade', nomeMae: 'Nome da Mãe', nomePai: 'Nome do Pai',
  descricaoSit: 'Situação', dataSit: 'Data Situação', dataEnt: 'Data Entrada',
  logradouro: 'Logradouro', numero: 'Número', complemento: 'Complemento', bairro: 'Bairro',
  cidade: 'Cidade', siglaUf: 'UF', cep: 'CEP', ddd: 'DDD', telefone: 'Telefone', tipo: 'Tipo',
  operadora: 'Operadora', email: 'E-mail', razaoSocial: 'Razão Social', dataAdmissao: 'Admissão',
  dataDesligamento: 'Desligamento', valorSalarial: 'Salário', descricaoCbo: 'Cargo (CBO)',
};

const SECTION_ICONS = {
  dadosBasicos: UserCheck, rgHistorico: FileText, carteiraHabilitacao: Car, tituloHistorico: Vote,
  cnsHistorico: Heart, pisHistorico: BadgeCheck, codigoCtps: Briefcase, alistamentoMilitar: Shield,
  opiniaoPolitica: MessageSquare, poderAquisitivo: TrendingUp, serasaMosaic: PieChart,
  telefonesHistorico: Phone, emails: Mail, redesSociais: Globe, enderecos: MapPin, curriculos: FileText,
  empregos: Building2, empresas: Building, beneficios: Coins, dividas: AlertTriangle, vacinas: Syringe,
  parentesNovos: Users, compras: ShoppingBag, cartoesUsados: CreditCard, internet: Wifi, imoveis: Home,
  irpf: Receipt, veiculos: Car, processos: Gavel, interesses: Sparkles, consumos: Receipt,
  filiacao: Users, situacaoCadastral: ShieldCheck, biometria: Fingerprint,
};

const CATEGORIES = [
  { id: 'cadastral', label: 'Cadastral', icon: User, sections: ['rgHistorico', 'carteiraHabilitacao', 'tituloHistorico', 'cnsHistorico', 'pisHistorico', 'codigoCtps', 'alistamentoMilitar', 'situacaoCadastral', 'biometria'] },
  { id: 'contatos', label: 'Contatos & Endereços', icon: MapPin, sections: ['enderecos', 'telefonesHistorico', 'emails', 'redesSociais', 'internet'] },
  { id: 'financeiro', label: 'Financeiro & Profissional', icon: Briefcase, sections: ['poderAquisitivo', 'serasaMosaic', 'empregos', 'empresas', 'beneficios', 'dividas', 'irpf', 'compras', 'cartoesUsados', 'consumos'] },
  { id: 'patrimonio', label: 'Patrimônio & Legal', icon: Building, sections: ['imoveis', 'veiculos', 'processos', 'parentesNovos', 'interesses', 'curriculos', 'opiniaoPolitica', 'vacinas'] },
];

const EMPTY_VALUES = ['', 'Não Informado', 'NÃO INFORMADO', 'nao informado', 'null', null, undefined];

const prettify = (key) =>
  SECTION_LABELS[key] || FIELD_LABELS[key] ||
  key.replace(/([A-Z])/g, ' $1').replace(/^./, (s) => s.toUpperCase()).trim();

const isEmptyVal = (v) => {
  if (v === null || v === undefined) return true;
  if (typeof v === 'string') return EMPTY_VALUES.includes(v.trim());
  if (Array.isArray(v)) return v.length === 0;
  if (typeof v === 'object') return Object.values(v).every(isEmptyVal);
  return false;
};

const formatCPF = (v) => {
  const d = (v || '').replace(/\D/g, '').slice(0, 11);
  return d.replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2');
};

const iconFor = (key) => SECTION_ICONS[key] || FileText;

// Deriva risco/score a partir da faixaScore textual ("ENTRE 501 E 750")
const getScoreInfo = (faixaScore) => {
  if (!faixaScore) return null;
  const nums = String(faixaScore).match(/\d+/g);
  if (!nums || nums.length === 0) return null;
  const vals = nums.map(Number);
  const mid = vals.length >= 2 ? (Math.min(...vals) + Math.max(...vals)) / 2 : vals[0];
  const bars = Math.max(1, Math.min(10, Math.round(mid / 100)));
  let level;
  if (mid >= 701) level = { key: 'alto', label: 'Risco Baixo', badge: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30', bar: 'bg-emerald-500', text: 'text-emerald-400' };
  else if (mid >= 301) level = { key: 'medio', label: 'Risco Médio', badge: 'bg-amber-500/15 text-amber-400 border-amber-500/30', bar: 'bg-amber-500', text: 'text-amber-400' };
  else level = { key: 'baixo', label: 'Risco Alto', badge: 'bg-red-500/15 text-red-400 border-red-500/30', bar: 'bg-red-500', text: 'text-red-400' };
  return { mid: Math.round(mid), bars, ...level };
};

// ---------- Renderizadores (funções, não componentes -> evita ciclo no plugin) ----------
const renderValue = (value, depth = 0) => {
  if (isEmptyVal(value)) return null;
  if (Array.isArray(value)) {
    return (
      <div className="space-y-2.5">
        {value.map((item, i) => (
          <div key={i} className="rounded-xl bg-background/60 border border-border/60 p-3.5">
            {typeof item === 'object' ? renderKeyValueGrid(item, depth + 1) : <span className="text-sm text-foreground">{String(item)}</span>}
          </div>
        ))}
      </div>
    );
  }
  if (typeof value === 'object') return renderKeyValueGrid(value, depth + 1);
  return <span className="text-sm text-foreground break-words">{typeof value === 'boolean' ? (value ? 'Sim' : 'Não') : String(value)}</span>;
};

const renderKeyValueGrid = (obj, depth = 0) => {
  const entries = Object.entries(obj).filter(([, v]) => !isEmptyVal(v));
  if (entries.length === 0) return <span className="text-sm text-muted-foreground">Sem dados.</span>;
  return (
    <div className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
      {entries.map(([k, v]) => {
        const nested = typeof v === 'object' && v !== null;
        return (
          <div key={k} className={nested ? 'sm:col-span-2' : ''}>
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">{prettify(k)}</p>
            {nested ? (
              <div className="mt-1">{renderValue(v, depth)}</div>
            ) : (
              <p className="text-sm text-foreground font-medium break-words mt-0.5">
                {typeof v === 'boolean' ? (v ? 'Sim' : 'Não') : String(v)}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
};

// ---------- Componentes de UI ----------
const InfoCard = ({ sectionKey, value, index }) => {
  const [open, setOpen] = useState(false);
  const Icon = iconFor(sectionKey);
  const count = Array.isArray(value) ? value.length : null;
  return (
    <motion.div
      variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0, transition: { duration: 0.25 } } }}
      className="rounded-2xl border border-border bg-card overflow-hidden transition-all hover:border-primary/30 shadow-sm break-inside-avoid mb-4"
      data-testid={`consulta-secao-${sectionKey}`}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-4 bg-muted/20 hover:bg-sidebar-accent transition-colors"
        data-testid={`consulta-secao-toggle-${sectionKey}`}
      >
        <span className="flex items-center gap-3 font-semibold text-sm text-foreground">
          <span className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center flex-shrink-0">
            <Icon className="w-4 h-4" />
          </span>
          {prettify(sectionKey)}
          {count !== null && <span className="text-xs px-2.5 py-0.5 rounded-full bg-primary/15 text-primary font-mono">{count}</span>}
        </span>
        <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && <div className="px-5 py-4 border-t border-border/60">{renderValue(value)}</div>}
    </motion.div>
  );
};

const ScoreGauge = ({ scoreInfo }) => {
  if (!scoreInfo) return null;
  return (
    <div className="rounded-2xl bg-background/60 border border-border/60 p-4" data-testid="consulta-score">
      <div className="flex items-center justify-between mb-2">
        <span className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">
          <Activity className="w-3.5 h-3.5" /> Score de Crédito
        </span>
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md border text-xs font-semibold ${scoreInfo.badge}`} data-testid="consulta-score-badge">
          {scoreInfo.label}
        </span>
      </div>
      <div className="flex items-center gap-3">
        <span className={`text-2xl font-bold font-mono ${scoreInfo.text}`}>{scoreInfo.mid}</span>
        <div className="flex items-center gap-1 flex-1">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className={`h-3 flex-1 rounded-sm transition-all ${i < scoreInfo.bars ? scoreInfo.bar : 'bg-muted'}`} />
          ))}
        </div>
      </div>
    </div>
  );
};

const HeroProfile = ({ basicos, sectionCounts, onChipClick }) => {
  if (!basicos) return null;
  const scoreInfo = getScoreInfo(basicos.faixaScore);
  const stats = [
    ['Nascimento', basicos.dataNasc],
    ['Sexo', basicos.sexo === 'M' ? 'Masculino' : basicos.sexo === 'F' ? 'Feminino' : basicos.sexo],
    ['Estado Civil', basicos.estCivil],
    ['Renda Atual', basicos.rendaAtual ? `R$ ${basicos.rendaAtual}` : null],
    ['Nome da Mãe', basicos.filiacao?.nomeMae || basicos.nomeMae],
    ['Situação', basicos.situacaoCadastral?.descricaoSit || basicos.descricaoSit],
  ].filter(([, v]) => !isEmptyVal(v));

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}
      className="rounded-3xl border border-primary/20 bg-gradient-to-br from-card via-card to-primary/5 p-6 sm:p-8 relative overflow-hidden shadow-xl"
      data-testid="consulta-identidade"
    >
      <div className="absolute -top-24 -right-24 w-72 h-72 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
      <div className="relative flex flex-col sm:flex-row sm:items-start gap-5">
        <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-primary/15 border border-primary/30 flex items-center justify-center text-primary shadow-inner flex-shrink-0">
          <User className="w-8 h-8 sm:w-10 sm:h-10" />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight break-words" data-testid="consulta-nome">{basicos.nome || '—'}</h2>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-muted/80 font-mono text-xs font-semibold text-foreground border border-border/60">
              <IdCard className="w-3.5 h-3.5" /> {formatCPF(basicos.cpf)}
            </span>
            {basicos.situacaoCadastral?.descricaoSit && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 text-xs font-semibold">
                <ShieldCheck className="w-3.5 h-3.5" /> {basicos.situacaoCadastral.descricaoSit}
              </span>
            )}
          </div>
        </div>
        <div className="w-full sm:w-72 flex-shrink-0"><ScoreGauge scoreInfo={scoreInfo} /></div>
      </div>

      {stats.length > 0 && (
        <div className="relative grid grid-cols-2 sm:grid-cols-3 gap-3 mt-6 pt-6 border-t border-border/60">
          {stats.map(([label, v]) => (
            <div key={label} className="rounded-xl bg-background/60 border border-border/60 p-3.5">
              <p className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">{label}</p>
              <p className="text-sm font-semibold text-foreground mt-0.5 break-words">{v}</p>
            </div>
          ))}
        </div>
      )}

      {sectionCounts.length > 0 && (
        <div className="relative flex flex-wrap gap-2 mt-4 pt-4 border-t border-border/40" data-testid="consulta-chips">
          {sectionCounts.map(({ key, count, catId }) => {
            const Icon = iconFor(key);
            return (
              <button key={key} onClick={() => onChipClick(catId)} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-card border border-border text-xs font-medium text-foreground hover:border-primary/40 hover:text-primary transition-colors">
                <Icon className="w-3.5 h-3.5" /> {prettify(key)}
                <span className="font-mono text-primary">{count}</span>
              </button>
            );
          })}
        </div>
      )}
    </motion.div>
  );
};

const MODULOS = [
  { id: 'cpf', label: 'CPF', icon: IdCard, ativo: true },
  { id: 'cnpj', label: 'CNPJ', icon: Building, ativo: false },
  { id: 'telefone', label: 'Telefone', icon: Phone, ativo: false },
  { id: 'nome', label: 'Nome', icon: User, ativo: false },
];

const Consultas = () => {
  const [modulo, setModulo] = useState('cpf');
  const [cpf, setCpf] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [resultado, setResultado] = useState(null);
  const [quota, setQuota] = useState(null);
  const [historico, setHistorico] = useState([]);
  const [loadingHist, setLoadingHist] = useState(true);
  const [catAtiva, setCatAtiva] = useState(null);

  const carregarHistorico = useCallback(async () => {
    try {
      setLoadingHist(true);
      const { data } = await consultasAPI.historico({ tipo: 'cpf' });
      setHistorico(data.itens || []);
    } catch (e) { /* silencioso */ } finally { setLoadingHist(false); }
  }, []);

  useEffect(() => { carregarHistorico(); }, [carregarHistorico]);

  const aplicarResultado = (data, q) => {
    setResultado(data);
    setQuota(q);
    const primeira = CATEGORIES.find((c) => c.sections.some((s) => !isEmptyVal(data?.[s])));
    setCatAtiva(primeira ? primeira.id : 'outros');
  };

  const buscar = async () => {
    setError(''); setResultado(null);
    const digits = cpf.replace(/\D/g, '');
    if (digits.length !== 11) { setError('Informe um CPF válido com 11 dígitos.'); return; }
    try {
      setLoading(true);
      const { data } = await consultasAPI.cpf(digits);
      aplicarResultado(data.data, data.quota);
      carregarHistorico();
    } catch (e) {
      setError(e.response?.data?.detail || 'Erro ao realizar a consulta.');
    } finally { setLoading(false); }
  };

  const abrirConsulta = async (id) => {
    setError('');
    try {
      setLoading(true);
      const { data } = await consultasAPI.obter(id);
      aplicarResultado(data.data, data.quota);
      if (data.data?.dadosBasicos?.cpf) setCpf(formatCPF(data.data.dadosBasicos.cpf));
    } catch (e) { setError('Não foi possível abrir a consulta.'); } finally { setLoading(false); }
  };

  const excluirConsulta = async (id, ev) => {
    ev.stopPropagation();
    try { await consultasAPI.excluir(id); setHistorico((h) => h.filter((x) => x.id !== id)); } catch (e) { /* ignore */ }
  };

  // Categorias com contagem de seções preenchidas + categoria "Outros"
  const categoriasComDados = (() => {
    if (!resultado) return [];
    const usadas = new Set();
    const base = CATEGORIES.map((c) => {
      const secoes = c.sections.filter((s) => !isEmptyVal(resultado[s]));
      secoes.forEach((s) => usadas.add(s));
      return { ...c, secoes };
    }).filter((c) => c.secoes.length > 0);
    const outros = Object.keys(resultado).filter((k) => k !== 'dadosBasicos' && !usadas.has(k) && !CATEGORIES.some((c) => c.sections.includes(k)) && !isEmptyVal(resultado[k]));
    if (outros.length > 0) base.push({ id: 'outros', label: 'Outros', icon: Sparkles, secoes: outros });
    return base;
  })();

  const catCorrente = categoriasComDados.find((c) => c.id === catAtiva) || categoriasComDados[0];

  // Chips: principais seções com contagem para visão rápida
  const chips = (() => {
    if (!resultado) return [];
    const out = [];
    categoriasComDados.forEach((c) => c.secoes.forEach((s) => {
      const v = resultado[s];
      out.push({ key: s, catId: c.id, count: Array.isArray(v) ? v.length : (typeof v === 'object' ? Object.keys(v).length : 1) });
    }));
    return out.sort((a, b) => b.count - a.count).slice(0, 8);
  })();

  const quotaPct = quota?.day ? Math.max(0, Math.min(100, (quota.day.remaining / quota.day.limit) * 100)) : null;

  return (
    <Layout>
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6" data-testid="consultas-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-primary/15 border border-primary/20 flex items-center justify-center">
            <ScanSearch className="w-6 h-6 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground tracking-tight">Consultas Cadastrais & Score</h1>
            <p className="text-sm text-muted-foreground">Dossiê completo para análise de risco e concessão de crédito</p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 text-xs font-semibold self-start">
          <Lock className="w-3.5 h-3.5" /> Ambiente Seguro
        </span>
      </div>

      {/* Módulos */}
      <div className="flex flex-wrap gap-2">
        {MODULOS.map((m) => {
          const Icon = m.icon; const active = modulo === m.id;
          return (
            <button key={m.id} disabled={!m.ativo} onClick={() => m.ativo && setModulo(m.id)} data-testid={`consulta-modulo-${m.id}`}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all border ${
                active ? 'bg-primary text-primary-foreground border-primary font-semibold shadow-sm shadow-primary/20'
                : m.ativo ? 'bg-card text-foreground border-border hover:bg-sidebar-accent'
                : 'bg-card/40 text-muted-foreground border-border/40 cursor-not-allowed opacity-60'}`}>
              <Icon className="w-4 h-4" /> {m.label}
              {!m.ativo && <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted text-muted-foreground">Em breve</span>}
            </button>
          );
        })}
      </div>

      <div className="flex flex-col lg:flex-row gap-6 items-start">
        {/* Coluna principal */}
        <div className="flex-1 min-w-0 w-full space-y-5">
          {/* Busca */}
          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm space-y-4">
            <label className="text-sm font-semibold text-foreground block">CPF do consultado</label>
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <IdCard className="w-5 h-5 text-muted-foreground absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input type="text" inputMode="numeric" value={cpf}
                  onChange={(e) => setCpf(formatCPF(e.target.value))}
                  onKeyDown={(e) => e.key === 'Enter' && !loading && buscar()}
                  placeholder="000.000.000-00" data-testid="consulta-cpf-input"
                  className="w-full pl-11 pr-4 py-3 rounded-xl bg-background border border-border text-foreground font-mono placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all" />
              </div>
              <button onClick={buscar} disabled={loading} data-testid="consulta-cpf-buscar"
                className="px-6 py-3 rounded-xl bg-primary text-primary-foreground font-semibold hover:opacity-90 active:scale-[0.99] transition-all flex items-center justify-center gap-2 shadow-lg shadow-primary/20 disabled:opacity-50">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />} Consultar
              </button>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <ShieldCheck className="w-3.5 h-3.5 text-primary" /> Consulta segura processada no servidor.
              </p>
              {quota?.day && (
                <p className="text-xs text-muted-foreground" data-testid="consulta-quota">
                  Restantes hoje: <span className="text-foreground font-semibold font-mono">{quota.day.remaining}</span>/{quota.day.limit}
                </p>
              )}
            </div>
            {quotaPct !== null && (
              <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                <div className="h-full bg-primary transition-all duration-500 rounded-full" style={{ width: `${quotaPct}%` }} />
              </div>
            )}
            {error && (
              <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2.5" data-testid="consulta-erro">
                <AlertCircle className="w-4 h-4 flex-shrink-0" /> {error}
              </div>
            )}
          </div>

          {loading && !resultado && <Loading message="Consultando dados..." />}

          {resultado && (
            <div className="space-y-5" data-testid="consulta-resultado">
              <HeroProfile basicos={resultado.dadosBasicos} sectionCounts={chips} onChipClick={setCatAtiva} />

              {/* Tabs de categorias */}
              {categoriasComDados.length > 0 && (
                <>
                  <div className="flex flex-wrap gap-2" data-testid="consulta-categorias">
                    {categoriasComDados.map((c) => {
                      const Icon = c.icon; const active = catCorrente?.id === c.id;
                      return (
                        <button key={c.id} onClick={() => setCatAtiva(c.id)} data-testid={`consulta-cat-${c.id}`}
                          className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-sm font-medium transition-all border ${
                            active ? 'bg-primary text-primary-foreground border-primary font-semibold' : 'bg-card text-foreground border-border hover:bg-sidebar-accent'}`}>
                          <Icon className="w-4 h-4" /> {c.label}
                          <span className={`text-xs font-mono px-1.5 py-0.5 rounded ${active ? 'bg-primary-foreground/20' : 'bg-muted text-muted-foreground'}`}>{c.secoes.length}</span>
                        </button>
                      );
                    })}
                  </div>

                  <motion.div
                    key={catCorrente?.id}
                    variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.05 } } }}
                    initial="hidden" animate="visible"
                    className="columns-1 md:columns-2 2xl:columns-3 gap-4 [column-fill:_balance]"
                  >
                    {catCorrente?.secoes.map((s, i) => (
                      <InfoCard key={s} sectionKey={s} value={resultado[s]} index={i} />
                    ))}
                  </motion.div>
                </>
              )}
            </div>
          )}

          {!resultado && !loading && (
            <div className="rounded-2xl border border-dashed border-border bg-card/40 p-12 text-center" data-testid="consulta-vazio">
              <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                <ScanSearch className="w-7 h-7 text-primary" />
              </div>
              <p className="text-sm font-medium text-foreground">Nenhuma consulta realizada</p>
              <p className="text-sm text-muted-foreground mt-1">Digite um CPF e clique em Consultar para ver o dossiê completo.</p>
            </div>
          )}
        </div>

        {/* Histórico */}
        <div className="w-full lg:w-80 flex-shrink-0 rounded-2xl border border-border bg-card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Clock className="w-4 h-4 text-primary" /> Consultas recentes
            </h3>
            <button onClick={carregarHistorico} className="text-muted-foreground hover:text-foreground transition-colors" data-testid="consulta-hist-refresh">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
          {loadingHist ? (
            <p className="text-sm text-muted-foreground">Carregando...</p>
          ) : historico.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">Nenhuma consulta ainda.</p>
          ) : (
            <div className="space-y-2" data-testid="consulta-historico">
              {historico.map((h) => (
                <button key={h.id} onClick={() => abrirConsulta(h.id)} data-testid={`consulta-hist-item-${h.id}`}
                  className="w-full text-left rounded-xl border border-border/80 bg-background/50 hover:bg-sidebar-accent p-3.5 transition-all group relative hover:border-primary/30">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 pr-6">
                      <p className="text-sm font-semibold text-foreground truncate">{h.resumo?.nome || 'Consulta CPF'}</p>
                      <p className="text-xs text-muted-foreground font-mono mt-0.5">{formatCPF(h.documento)}</p>
                      {h.created_at && <p className="text-[11px] text-muted-foreground mt-1">{new Date(h.created_at).toLocaleString('pt-BR')}</p>}
                    </div>
                    <span onClick={(e) => excluirConsulta(h.id, e)} className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition p-1" data-testid={`consulta-hist-excluir-${h.id}`}>
                      <Trash2 className="w-4 h-4" />
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
    </Layout>
  );
};

export default Consultas;
