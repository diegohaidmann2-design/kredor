import React, { useState, useEffect, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { consultasAPI, clientesAPI, emprestimosAPI, carteiraAPI } from '../api/api';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import {
  Search, ScanSearch, IdCard, Phone, Building2, Building, User, UserCheck, AlertCircle,
  ChevronDown, Clock, Trash2, ShieldCheck, Loader2, RefreshCw, MapPin, Mail, Globe,
  Briefcase, Users, CreditCard, Home, Car, Gavel, TrendingUp, PieChart, Coins,
  AlertTriangle, FileText, Vote, Heart, BadgeCheck, Shield, MessageSquare, Syringe,
  ShoppingBag, Wifi, Receipt, Fingerprint, Activity, Lock, ChevronsDownUp, ChevronsUpDown,
  FileDown, Link2, X, Check, ScanFace, Camera, Upload, Gauge, ShieldAlert, Wallet, Zap, Crown, Table as TableIcon
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
  // CNPJ
  dadosEmpresa: 'Dados da Empresa', simplesNacional: 'Simples Nacional', funcionarios: 'Funcionários',
  socios: 'Quadro Societário', estabelecimento: 'Estabelecimento', contato: 'Contato',
  atividadePrincipal: 'Atividade Principal', atividadesSecundarias: 'Atividades Secundárias',
  // Dívidas / Boa Vista
  registro_de_debitos: 'Registros de Débito', Protestos: 'Protestos', protestos: 'Protestos',
  score_de_credito: 'Score de Crédito', renda_presumida: 'Renda Presumida', localizacao: 'Localização',
  identificacao: 'Identificação', identificacao_empresa: 'Identificação da Empresa',
  pendenciasRestricoes: 'Pendências e Restrições', listaProtestos: 'Lista de Protestos',
  chequesSemFundo: 'Cheques sem Fundo', chequeSustado: 'Cheque Sustado', endereco: 'Endereço',
  listaDebitos: 'Lista de Débitos', listaPendenciasRestricoes: 'Lista de Pendências',
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
  // CNPJ
  cnpjBasico: 'CNPJ (Base)', naturezaJuridica: 'Natureza Jurídica', qualificacaoResponsavel: 'Qualificação do Responsável',
  capitalSocial: 'Capital Social', porteEmpresa: 'Porte', enteFederativoResponsavel: 'Ente Federativo',
  funcionariosTotal: 'Total de Funcionários', opcaoSimples: 'Opção Simples', dataOpcaoSimples: 'Data Opção Simples',
  dataExclusaoSimples: 'Data Exclusão Simples', opcaoMei: 'Opção MEI', dataOpcaoMei: 'Data Opção MEI',
  dataExclusaoMei: 'Data Exclusão MEI', tipoSocio: 'Tipo de Sócio', cpfCnpj: 'CPF / CNPJ',
  qualificacao: 'Qualificação', dataEntradaSociedade: 'Entrada na Sociedade', pais: 'País',
  representanteLegal: 'Representante Legal', nomeRepresentante: 'Nome do Representante',
  qualificacaoRepresentante: 'Qualificação do Representante', faixaEtaria: 'Faixa Etária', razaoSocialUltima: 'Razão Social',
  // Dívidas
  documento: 'Documento', nome_mae: 'Nome da Mãe', data_nascimento: 'Nascimento', regiao_cpf: 'Região do CPF',
  obito: 'Óbito', titulo_eleitor: 'Título de Eleitor', dependentes: 'Dependentes',
  situacao_receita_federal: 'Situação na Receita', total_dividas_devedor: 'Total de Dívidas',
  valor_total_dividas: 'Valor Total das Dívidas', data_primeira_divida: 'Primeira Dívida',
  valor_primeira_divida: 'Valor Primeira Dívida', data_maior_divida: 'Maior Dívida', valor_maior_divida: 'Valor Maior Dívida',
  valorRegistro: 'Valor', informante: 'Informante', dataVencimento: 'Vencimento', quantidade: 'Quantidade',
  valorTotal: 'Valor Total', faixa_renda_estimada: 'Renda Estimada', razao_social: 'Razão Social',
  situacaoCnpj: 'Situação do CNPJ', dataFundacao: 'Fundação', ufEmpresa: 'UF', nomeFantasia: 'Nome Fantasia',
  cartorio: 'Cartório', numeroCartorio: 'Cartório', municipio: 'Município', uf: 'UF', valor: 'Valor',
  ramoAtividadePrimario: 'Atividade Principal', cnae: 'CNAE', atividade: 'Atividade', quantidadePendencias: 'Qtd. Pendências',
  quantidadeCredores: 'Qtd. Credores', classificacaoAlfabetica: 'Classificação', probabilidade: 'Probabilidade', texto: 'Descrição',
};

const SECTION_ICONS = {
  dadosBasicos: UserCheck, rgHistorico: FileText, carteiraHabilitacao: Car, tituloHistorico: Vote,
  cnsHistorico: Heart, pisHistorico: BadgeCheck, codigoCtps: Briefcase, alistamentoMilitar: Shield,
  opiniaoPolitica: MessageSquare, poderAquisitivo: TrendingUp, serasaMosaic: PieChart,
  telefonesHistorico: Phone, emails: Mail, redesSociais: Globe, enderecos: MapPin, curriculos: FileText,
  empregos: Building2, empresas: Building, beneficios: Coins, dividas: AlertTriangle, vacinas: Syringe,
  parentesNovos: Users, compras: ShoppingBag, cartoesUsados: CreditCard, internet: Wifi, imoveis: Home,
  irpf: Receipt, veiculos: Car, processos: Gavel, interesses: Activity, consumos: Receipt,
  filiacao: Users, situacaoCadastral: ShieldCheck, biometria: Fingerprint,
  // CNPJ
  dadosEmpresa: Building, simplesNacional: Receipt, funcionarios: Users, socios: Users,
  estabelecimento: MapPin, contato: Phone, atividadePrincipal: Briefcase, atividadesSecundarias: Briefcase,
  // Dívidas
  registro_de_debitos: AlertTriangle, Protestos: Gavel, protestos: Gavel, score_de_credito: Activity,
  renda_presumida: TrendingUp, localizacao: MapPin, identificacao: UserCheck, identificacao_empresa: Building,
  pendenciasRestricoes: AlertTriangle, listaProtestos: Gavel, chequesSemFundo: CreditCard, endereco: MapPin,
};

const CATEGORIES = [
  { id: 'cadastral', label: 'Cadastral', icon: User, sections: ['rgHistorico', 'carteiraHabilitacao', 'tituloHistorico', 'cnsHistorico', 'pisHistorico', 'codigoCtps', 'alistamentoMilitar', 'situacaoCadastral', 'biometria'] },
  { id: 'contatos', label: 'Contatos & Endereços', icon: MapPin, sections: ['enderecos', 'telefonesHistorico', 'emails', 'redesSociais', 'internet'] },
  { id: 'financeiro', label: 'Financeiro & Profissional', icon: Briefcase, sections: ['poderAquisitivo', 'serasaMosaic', 'empregos', 'empresas', 'beneficios', 'dividas', 'irpf', 'compras', 'cartoesUsados', 'consumos'] },
  { id: 'patrimonio', label: 'Patrimônio & Legal', icon: Building, sections: ['imoveis', 'veiculos', 'processos', 'parentesNovos', 'interesses', 'curriculos', 'opiniaoPolitica', 'vacinas'] },
];

const EMPTY_VALUES = ['', 'não informado', 'nao informado', 'null', 'none', 'inexistente', 'n/a', 'na', 'não consta', 'nao consta', 'sem informação', 'sem informacao'];
const IGNORE_KEYS = new Set(['tipo']);

const prettify = (key) => {
  if (SECTION_LABELS[key]) return SECTION_LABELS[key];
  if (FIELD_LABELS[key]) return FIELD_LABELS[key];
  return String(key)
    .replace(/_/g, ' ')
    .replace(/([a-z\d])([A-Z])/g, '$1 $2')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/^./, (s) => s.toUpperCase());
};

const isEmptyVal = (v) => {
  if (v === null || v === undefined) return true;
  if (typeof v === 'string') return EMPTY_VALUES.includes(v.trim().toLowerCase());
  if (Array.isArray(v)) return v.every(isEmptyVal);
  if (typeof v === 'object') return Object.entries(v).every(([k, val]) => IGNORE_KEYS.has(k) || isEmptyVal(val));
  return false;
};

// Remove valores vazios/"INEXISTENTE" e itens de lista sem dados úteis (só 'tipo')
const limparValor = (v) => {
  if (Array.isArray(v)) return v.map(limparValor).filter((it) => !isEmptyVal(it));
  if (v && typeof v === 'object') {
    const out = {};
    Object.entries(v).forEach(([k, val]) => {
      const cv = val && typeof val === 'object' ? limparValor(val) : val;
      if (!isEmptyVal(cv)) out[k] = cv;
    });
    return out;
  }
  return v;
};

const formatCPF = (v) => {
  const d = (v || '').replace(/\D/g, '').slice(0, 11);
  return d.replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d)/, '$1.$2').replace(/(\d{3})(\d{1,2})$/, '$1-$2');
};

const formatCNPJ = (v) => {
  const d = (v || '').replace(/\D/g, '').slice(0, 14);
  return d
    .replace(/(\d{2})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d)/, '$1/$2')
    .replace(/(\d{4})(\d)/, '$1-$2');
};

const formatTelefone = (v) => {
  const d = (v || '').replace(/\D/g, '').slice(0, 11);
  if (d.length <= 10) {
    return d.replace(/(\d{2})(\d)/, '($1) $2').replace(/(\d{4})(\d)/, '$1-$2');
  }
  return d.replace(/(\d{2})(\d)/, '($1) $2').replace(/(\d{5})(\d)/, '$1-$2');
};

const formatDoc = (doc, tipo) => {
  if (tipo === 'cnpj' || tipo === 'cnpj-dividas') return formatCNPJ(doc);
  if (tipo === 'telefone') return formatTelefone(doc);
  if (tipo === 'nome') return doc || '';
  if (tipo === 'facial') return 'Reconhecimento facial';
  return formatCPF(doc); // cpf, cpf-dividas
};

const iconFor = (key) => SECTION_ICONS[key] || FileText;

// Conta campos preenchidos para decidir se o card é "grande" (ocupa 2 colunas)
const contarCampos = (v) => {
  if (Array.isArray(v)) return v.reduce((a, it) => a + (it && typeof it === 'object' ? Object.values(it).filter((x) => !isEmptyVal(x)).length : 1), 0);
  if (v && typeof v === 'object') return Object.values(v).filter((x) => !isEmptyVal(x)).length;
  return 1;
};

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
    <div className="grid gap-x-6 gap-y-3.5 grid-cols-[repeat(auto-fit,minmax(150px,1fr))]">
      {entries.map(([k, v]) => {
        const nested = typeof v === 'object' && v !== null;
        return (
          <div key={k} className={`min-w-0 ${nested ? 'col-span-full' : ''}`}>
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold break-words">{prettify(k)}</p>
            {nested ? (
              <div className="mt-1">{renderValue(v, depth)}</div>
            ) : (
              <p className="text-sm text-foreground font-medium break-words [overflow-wrap:anywhere] mt-0.5">
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
const InfoCard = ({ sectionKey, value, open, onToggle, wide }) => {
  const Icon = iconFor(sectionKey);
  const count = Array.isArray(value) ? value.length : null;
  return (
    <motion.div
      variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0, transition: { duration: 0.25 } } }}
      className={`rounded-2xl border border-border bg-card overflow-hidden transition-all hover:border-primary/30 shadow-sm ${wide ? 'lg:col-span-2' : ''}`}
      data-testid={`consulta-secao-${sectionKey}`}
    >
      <button
        onClick={onToggle}
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

const CompanyHero = ({ emp, cnpj, sociosCount }) => {
  if (!emp) return null;
  const stats = [
    ['Natureza Jurídica', emp.naturezaJuridica],
    ['Porte', emp.porteEmpresa],
    ['Capital Social', emp.capitalSocial],
    ['Responsável', emp.qualificacaoResponsavel],
    ['Total de Funcionários', emp.funcionariosTotal],
    ['Sócios', sociosCount != null ? String(sociosCount) : null],
  ].filter(([, v]) => !isEmptyVal(v));

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}
      className="rounded-3xl border border-primary/20 bg-gradient-to-br from-card via-card to-primary/5 p-6 sm:p-8 relative overflow-hidden shadow-xl"
      data-testid="consulta-empresa"
    >
      <div className="absolute -top-24 -right-24 w-72 h-72 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
      <div className="relative flex flex-col sm:flex-row sm:items-start gap-5">
        <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-primary/15 border border-primary/30 flex items-center justify-center text-primary shadow-inner flex-shrink-0">
          <Building className="w-8 h-8 sm:w-10 sm:h-10" />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight break-words" data-testid="consulta-razao-social">{emp.razaoSocial || '—'}</h2>
          <div className="flex flex-wrap items-center gap-2 mt-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-muted/80 font-mono text-xs font-semibold text-foreground border border-border/60">
              <Building2 className="w-3.5 h-3.5" /> {formatCNPJ(cnpj)}
            </span>
            {emp.porteEmpresa && (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-primary/10 text-primary border border-primary/20 text-xs font-semibold">
                {emp.porteEmpresa}
              </span>
            )}
          </div>
        </div>
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
    </motion.div>
  );
};

const BoaVistaBadge = ({ className = '' }) => (
  <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-xs font-semibold text-emerald-500 ${className}`} data-testid="boa-vista-badge">
    <span className="relative flex h-2 w-2">
      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
      <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
    </span>
    <ShieldCheck className="w-3.5 h-3.5" /> Boa Vista · Online
  </span>
);

const nivelRiscoStyle = (nivel) => {
  const n = (nivel || '').toLowerCase();
  if (n.includes('muito alto') || n.includes('alto')) return { badge: 'bg-red-500/15 text-red-400 border-red-500/30', bar: 'bg-red-500', text: 'text-red-400', ring: 'border-red-500/30' };
  if (n.includes('médio') || n.includes('medio')) return { badge: 'bg-amber-500/15 text-amber-400 border-amber-500/30', bar: 'bg-amber-500', text: 'text-amber-400', ring: 'border-amber-500/30' };
  if (n.includes('baixo')) return { badge: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30', bar: 'bg-emerald-500', text: 'text-emerald-400', ring: 'border-emerald-500/30' };
  return { badge: 'bg-muted text-muted-foreground border-border', bar: 'bg-primary', text: 'text-foreground', ring: 'border-border' };
};

const alertaLabels = {
  registro_debito: 'Registros de Débito', protestos: 'Protestos', cheques_sem_fundo: 'Cheques sem Fundo',
  participacao_em_empresas: 'Participação em Empresas', pendencias_restricoes: 'Pendências / Restrições',
  socios_relacionados: 'Sócios Relacionados',
};

const RiskHero = ({ aval, alertas, titulo, subtitulo }) => {
  if (!aval) return null;
  const st = nivelRiscoStyle(aval.nivel_risco);
  const score = Number(aval.score_risco) || 0;
  const bars = Math.max(1, Math.min(10, Math.round(score / 100)));
  const prob = aval.probabilidade_inadimplencia;
  const alertasArr = alertas ? Object.entries(alertas).filter(([, v]) => typeof v === 'number') : [];
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}
      className={`rounded-3xl border ${st.ring} bg-gradient-to-br from-card via-card to-primary/5 p-6 sm:p-8 relative overflow-hidden shadow-xl`}
      data-testid="consulta-risco"
    >
      <div className="absolute -top-24 -right-24 w-72 h-72 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
      <div className="relative flex flex-col lg:flex-row gap-6">
        <div className="flex items-start gap-4 flex-1 min-w-0">
          <div className={`w-16 h-16 rounded-2xl bg-primary/15 border ${st.ring} flex items-center justify-center ${st.text} flex-shrink-0`}>
            <Gauge className="w-8 h-8" />
          </div>
          <div className="min-w-0">
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">{subtitulo}</p>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl sm:text-2xl font-bold text-foreground tracking-tight break-words" data-testid="consulta-risco-nome">{titulo || '—'}</h2>
              <BoaVistaBadge />
            </div>
            <div className="flex flex-wrap items-center gap-2 mt-2">
              <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-md border text-xs font-semibold ${st.badge}`} data-testid="consulta-risco-nivel">
                <ShieldAlert className="w-3.5 h-3.5" /> Risco {aval.nivel_risco || '—'}
              </span>
              {aval.sugestao_negocio && (
                <span className="inline-flex items-center px-3 py-1 rounded-md bg-muted/80 border border-border/60 text-xs font-semibold text-foreground">
                  {aval.sugestao_negocio}
                </span>
              )}
            </div>
            {aval.resumo_analise && <p className="text-sm text-muted-foreground mt-3 max-w-xl">{aval.resumo_analise}</p>}
          </div>
        </div>

        <div className="w-full lg:w-72 flex-shrink-0 rounded-2xl bg-background/60 border border-border/60 p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">Score de Risco</span>
            {aval.classificacao_score && <span className={`text-xs font-semibold ${st.text}`}>{aval.classificacao_score}</span>}
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-3xl font-bold font-mono ${st.text}`} data-testid="consulta-risco-score">{score}</span>
            <div className="flex items-center gap-1 flex-1">
              {Array.from({ length: 10 }).map((_, i) => (
                <div key={i} className={`h-3 flex-1 rounded-sm ${i < bars ? st.bar : 'bg-muted'}`} />
              ))}
            </div>
          </div>
          {prob !== undefined && prob !== null && (
            <p className="text-xs text-muted-foreground mt-2">Prob. de inadimplência: <span className={`font-semibold ${st.text}`}>{prob}%</span></p>
          )}
        </div>
      </div>

      {alertasArr.length > 0 && (
        <div className="relative grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-6 border-t border-border/60" data-testid="consulta-risco-alertas">
          {alertasArr.map(([k, v]) => {
            const critico = Number(v) > 0;
            return (
              <div key={k} className={`rounded-xl border p-3.5 ${critico ? 'bg-red-500/5 border-red-500/20' : 'bg-background/60 border-border/60'}`}>
                <p className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold break-words">{alertaLabels[k] || prettify(k)}</p>
                <p className={`text-2xl font-bold font-mono mt-0.5 ${critico ? 'text-red-400' : 'text-foreground'}`}>{v}</p>
              </div>
            );
          })}
        </div>
      )}
    </motion.div>
  );
};


const VincularModal = ({ onClose, onConfirm }) => {
  const [busca, setBusca] = useState('');
  const [clientes, setClientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sel, setSel] = useState(null);
  const [emprestimos, setEmprestimos] = useState([]);
  const [empId, setEmpId] = useState('');
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    (async () => {
      try { const { data } = await clientesAPI.listar({ limit: 100 }); setClientes(data.items || data || []); }
      catch (e) { /* ignore */ } finally { setLoading(false); }
    })();
  }, []);

  const escolher = async (c) => {
    setSel(c); setEmpId(''); setEmprestimos([]);
    try {
      const { data } = await emprestimosAPI.listar({ cliente_id: c.id, limit: 100 });
      setEmprestimos(data.items || data || []);
    } catch (e) { setEmprestimos([]); }
  };

  const filtrados = clientes.filter((c) => {
    const q = busca.toLowerCase();
    return (c.nome || '').toLowerCase().includes(q) ||
      (c.cpf_cnpj || '').replace(/\D/g, '').includes(busca.replace(/\D/g, ''));
  });

  const confirmar = async () => {
    if (!sel) return;
    setSalvando(true);
    try { await onConfirm(sel, empId || null); } finally { setSalvando(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" data-testid="vincular-modal" onClick={onClose}>
      <div className="w-full max-w-lg rounded-2xl border border-border bg-card shadow-2xl max-h-[85vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h3 className="flex items-center gap-2 font-semibold text-foreground"><Link2 className="w-4 h-4 text-primary" /> Vincular a um cliente</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground" data-testid="vincular-fechar"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-5 space-y-4 overflow-y-auto">
          <div className="relative">
            <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
            <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar por nome ou CPF/CNPJ" data-testid="vincular-busca"
              className="w-full pl-10 pr-3 py-2.5 rounded-lg bg-background border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40" />
          </div>
          {loading ? <p className="text-sm text-muted-foreground">Carregando clientes...</p>
            : filtrados.length === 0 ? <p className="text-sm text-muted-foreground text-center py-4">Nenhum cliente encontrado.</p>
            : (
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1" data-testid="vincular-lista">
                {filtrados.map((c) => (
                  <button key={c.id} onClick={() => escolher(c)} data-testid={`vincular-cliente-${c.id}`}
                    className={`w-full text-left rounded-xl border p-3 transition-all flex items-center gap-3 ${sel?.id === c.id ? 'border-primary bg-primary/5' : 'border-border bg-background/50 hover:bg-sidebar-accent'}`}>
                    <span className="w-9 h-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center flex-shrink-0"><User className="w-4 h-4" /></span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium text-foreground truncate">{c.nome}</span>
                      <span className="block text-xs text-muted-foreground font-mono">{c.cpf_cnpj || '—'}</span>
                    </span>
                    {sel?.id === c.id && <Check className="w-4 h-4 text-primary" />}
                  </button>
                ))}
              </div>
            )}
          {sel && emprestimos.length > 0 && (
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-2">Empréstimo (opcional)</p>
              <select value={empId} onChange={(e) => setEmpId(e.target.value)} data-testid="vincular-emprestimo"
                className="w-full px-3 py-2.5 rounded-lg bg-background border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40">
                <option value="">Nenhum (só ao cliente)</option>
                {emprestimos.map((e) => (
                  <option key={e.id} value={e.id}>{`R$ ${e.valor_principal ?? e.valor ?? ''} · ${e.status || ''}`}</option>
                ))}
              </select>
            </div>
          )}
        </div>
        <div className="flex justify-end gap-2 px-5 py-4 border-t border-border">
          <button onClick={onClose} className="px-4 py-2 rounded-lg border border-border text-foreground hover:bg-sidebar-accent text-sm font-medium">Cancelar</button>
          <button onClick={confirmar} disabled={!sel || salvando} data-testid="vincular-confirmar"
            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90 disabled:opacity-50 flex items-center gap-2">
            {salvando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />} Vincular
          </button>
        </div>
      </div>
    </div>
  );
};

// ---------- CPF Premium: blocos (campos / tabela) ----------
const PremiumBloco = ({ bloco }) => {
  if (!bloco || typeof bloco !== 'object') return null;
  if (bloco.tipo === 'tabela') {
    const linhas = Array.isArray(bloco.linhas) ? bloco.linhas : [];
    if (linhas.length === 0) return null;
    const colunas = (Array.isArray(bloco.colunas) && bloco.colunas.length)
      ? bloco.colunas
      : Object.keys(linhas[0] || {});
    if (colunas.length === 0) return null;
    return (
      <div className="overflow-x-auto rounded-xl border border-border/60">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="bg-sidebar-accent/60">
              {colunas.map((c) => (
                <th key={c} className="px-2.5 py-2 font-semibold text-muted-foreground uppercase tracking-wider whitespace-nowrap text-left">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {linhas.map((r, i) => (
              <tr key={i} className="border-t border-border/40">
                {colunas.map((c) => (
                  <td key={c} className="px-2.5 py-2 text-foreground align-top break-words max-w-[220px]">
                    {isEmptyVal(r?.[c]) ? '—' : String(r[c])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  const dados = bloco.dados || {};
  const entries = Object.entries(dados).filter(([, v]) => !isEmptyVal(v));
  if (entries.length === 0) return null;
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3">
      {entries.map(([k, v]) => (
        <div key={k} className="min-w-0 flex flex-col">
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">{k}</span>
          <span className="text-sm text-foreground font-medium break-words">
            {typeof v === 'object' ? JSON.stringify(v) : String(v)}
          </span>
        </div>
      ))}
    </div>
  );
};

const PremiumSecao = ({ secao, index, open, onToggle }) => {
  const blocos = Array.isArray(secao?.blocos) ? secao.blocos : [];
  const temDados = blocos.some((b) => b && (
    b.tipo === 'tabela'
      ? (Array.isArray(b.linhas) && b.linhas.length > 0)
      : (b.dados && Object.values(b.dados).some((v) => !isEmptyVal(v)))
  ));
  if (!temDados) return null;
  return (
    <motion.div variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0 } }}
      className="rounded-2xl border border-border bg-card overflow-hidden" data-testid={`premium-secao-${index}`}>
      <button onClick={onToggle} data-testid={`premium-secao-toggle-${index}`}
        className="w-full flex items-center justify-between gap-3 px-4 py-3.5 hover:bg-sidebar-accent/50 transition-colors">
        <span className="flex items-center gap-2.5 text-sm font-semibold text-foreground text-left min-w-0">
          <span className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-500 flex items-center justify-center flex-shrink-0">
            <TableIcon className="w-4 h-4" />
          </span>
          <span className="truncate">{secao?.titulo || 'Seção'}</span>
        </span>
        <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform flex-shrink-0 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="px-4 pb-4 pt-1 space-y-4 border-t border-border/60">
          {blocos.map((b, i) => <PremiumBloco key={i} bloco={b} />)}
        </div>
      )}
    </motion.div>
  );
};

const PremiumProfile = ({ dados }) => {
  const chips = [
    ['Nascimento', dados.nascimento],
    ['Sexo', dados.sexo],
    ['Situação', dados.situacao_cadastral],
    ['Renda', dados.renda],
    ['Profissão', dados.profissao],
    ['Nome da Mãe', dados.nome_mae],
  ].filter(([, v]) => !isEmptyVal(v));
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}
      className="rounded-3xl border border-amber-500/30 bg-gradient-to-br from-card via-card to-amber-500/5 p-6 sm:p-8 relative overflow-hidden shadow-xl"
      data-testid="premium-profile">
      <div className="absolute -top-24 -right-24 w-72 h-72 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="relative flex flex-col sm:flex-row gap-5">
        <div className="w-28 h-28 rounded-2xl bg-muted/40 border border-border overflow-hidden flex items-center justify-center flex-shrink-0">
          {dados.foto
            ? <img src={dados.foto} alt={dados.nome || 'Foto'} className="w-full h-full object-cover" data-testid="premium-foto" onError={(e) => { e.target.style.display = 'none'; }} />
            : <User className="w-12 h-12 text-muted-foreground" />}
        </div>
        <div className="min-w-0 flex-1">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-amber-500/15 text-amber-500 border border-amber-500/30 text-[11px] font-bold uppercase tracking-wider mb-2">
            <Crown className="w-3.5 h-3.5" /> CPF Premium
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight break-words" data-testid="premium-nome">{dados.nome || '—'}</h2>
          <p className="text-sm text-muted-foreground font-mono mt-1 flex items-center gap-1.5">
            <IdCard className="w-3.5 h-3.5" /> {formatCPF(dados.documento)}
          </p>
          {chips.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t border-border/40">
              {chips.map(([label, v]) => (
                <span key={label} className="inline-flex flex-col px-3 py-1.5 rounded-lg bg-background/60 border border-border/60">
                  <span className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">{label}</span>
                  <span className="text-xs text-foreground font-medium break-words max-w-[200px]">{v}</span>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};

const MODULOS = [
  { id: 'cpf', label: 'CPF', icon: IdCard, ativo: true },
  { id: 'cpf-premium', label: 'CPF Premium', icon: Crown, ativo: true },
  { id: 'cnpj', label: 'CNPJ', icon: Building, ativo: true },
  { id: 'telefone', label: 'Telefone', icon: Phone, ativo: true },
  { id: 'nome', label: 'Nome Exato', icon: User, ativo: true },
  { id: 'cpf-dividas', label: 'Dívidas CPF', icon: ShieldAlert, ativo: true },
  { id: 'cnpj-dividas', label: 'Dívidas CNPJ', icon: ShieldAlert, ativo: true },
  { id: 'facial', label: 'Facial', icon: ScanFace, ativo: true },
];

const MODULO_INFO = {
  cpf: { label: 'CPF do consultado', placeholder: '000.000.000-00', icon: IdCard, digits: [11] },
  'cpf-premium': { label: 'CPF do consultado (dossiê Premium)', placeholder: '000.000.000-00', icon: Crown, digits: [11] },
  cnpj: { label: 'CNPJ da empresa', placeholder: '00.000.000/0000-00', icon: Building2, digits: [14] },
  telefone: { label: 'Telefone (com DDD)', placeholder: '(00) 00000-0000', icon: Phone, digits: [10, 11] },
  nome: { label: 'Nome exato (busca sem filtros)', placeholder: 'Ex.: João da Silva', icon: User, text: true },
  'cpf-dividas': { label: 'CPF para consulta de dívidas', placeholder: '000.000.000-00', icon: IdCard, digits: [11] },
  'cnpj-dividas': { label: 'CNPJ para consulta de dívidas', placeholder: '00.000.000/0000-00', icon: Building2, digits: [14] },
  facial: { label: 'Reconhecimento facial', icon: ScanFace, foto: true },
};

const Consultas = () => {
  const [modulo, setModulo] = useState('cpf');
  const [valor, setValor] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [resultado, setResultado] = useState(null);
  const [resultadoTipo, setResultadoTipo] = useState('cpf');
  const [historico, setHistorico] = useState([]);
  const [loadingHist, setLoadingHist] = useState(true);
  const [catAtiva, setCatAtiva] = useState(null);
  const [openSecoes, setOpenSecoes] = useState({});
  const [consultaId, setConsultaId] = useState(null);
  const [clienteVinc, setClienteVinc] = useState(null);
  const [showVincular, setShowVincular] = useState(false);
  const [baixandoPdf, setBaixandoPdf] = useState(false);
  const [fotoData, setFotoData] = useState('');
  const [fotoPreview, setFotoPreview] = useState('');
  const [carteiraInfo, setCarteiraInfo] = useState(null); // { saldo, precos: {tipo: valor} }
  const [saldoInsuficiente, setSaldoInsuficiente] = useState(null); // { preco, saldo, msg }
  const navigate = useNavigate();

  const carregarCarteira = useCallback(async () => {
    try {
      const { data } = await carteiraAPI.resumo();
      const precos = {};
      (data?.precos || []).forEach((p) => { precos[p.tipo] = p.valor; });
      setCarteiraInfo({ saldo: data?.carteira?.saldo || 0, precos });
    } catch { /* silencioso */ }
  }, []);
  useEffect(() => { carregarCarteira(); }, [carregarCarteira]);

  const carregarHistorico = useCallback(async () => {
    try {
      setLoadingHist(true);
      const { data } = await consultasAPI.historico({ tipo: modulo });
      setHistorico(data.itens || []);
    } catch (e) { /* silencioso */ } finally { setLoadingHist(false); }
  }, [modulo]);

  useEffect(() => { carregarHistorico(); }, [carregarHistorico]);

  const location = useLocation();
  useEffect(() => {
    const cid = new URLSearchParams(location.search).get('consulta');
    if (cid) abrirConsulta(cid);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search]);

  const formatEntrada = (raw, mod) => {
    if (mod === 'cnpj' || mod === 'cnpj-dividas') return formatCNPJ(raw);
    if (mod === 'telefone') return formatTelefone(raw);
    if (mod === 'nome') return raw;
    return formatCPF(raw); // cpf, cpf-dividas
  };

  const trocarModulo = (novo) => {
    if (novo === modulo) return;
    setModulo(novo);
    setValor('');
    setError('');
    setResultado(null);
    setFotoData('');
    setFotoPreview('');
  };

  const aplicarResultado = (data, id = null, cliente = null, tipo = 'cpf') => {
    const limpo = limparValor(data || {});
    setResultadoTipo(tipo);
    setResultado(limpo);
    setConsultaId(id);
    setClienteVinc(cliente);
    let openInit = {};
    if (tipo === 'cpf') {
      const primeira = CATEGORIES.find((c) => c.sections.some((s) => !isEmptyVal(limpo?.[s])));
      setCatAtiva(primeira ? primeira.id : 'outros');
    } else if (tipo === 'cpf-premium') {
      setCatAtiva(null);
      const secoes = Array.isArray(limpo?.dados?.secoes) ? limpo.dados.secoes : [];
      secoes.forEach((_, i) => { openInit[`premium-${i}`] = true; });
    } else {
      setCatAtiva(null);
    }
    setOpenSecoes(openInit);
  };

  const runConsulta = async (tipo, digits) => {
    setError(''); setSaldoInsuficiente(null); setResultado(null);
    try {
      setLoading(true);
      let resp;
      if (tipo === 'cpf') resp = await consultasAPI.cpf(digits);
      else if (tipo === 'cpf-premium') resp = await consultasAPI.cpfPremium(digits);
      else if (tipo === 'cnpj') resp = await consultasAPI.cnpj(digits);
      else if (tipo === 'telefone') resp = await consultasAPI.telefone(digits);
      else if (tipo === 'nome') resp = await consultasAPI.nome(digits);
      else if (tipo === 'cpf-dividas') resp = await consultasAPI.cpfDividas(digits);
      else if (tipo === 'cnpj-dividas') resp = await consultasAPI.cnpjDividas(digits);
      else if (tipo === 'facial') resp = await consultasAPI.facial(digits);
      else resp = await consultasAPI.cpf(digits);
      const { data } = resp;
      aplicarResultado(data.data, data.id, null, tipo);
      // Atualizar saldo local se veio na resposta
      if (data.carteira && typeof data.carteira.saldo_atual === 'number') {
        setCarteiraInfo((prev) => ({ ...(prev || {}), saldo: data.carteira.saldo_atual }));
      } else { carregarCarteira(); }
      carregarHistorico();
    } catch (e) {
      if (e.response?.status === 402) {
        const det = e.response?.data?.detail || {};
        setSaldoInsuficiente({
          preco: det.preco, saldo: det.saldo,
          msg: det.message || 'Saldo insuficiente na carteira.',
        });
      } else {
        setError(e.response?.data?.detail || 'Erro ao realizar a consulta.');
      }
    } finally { setLoading(false); }
  };

  const buscar = () => {
    setError('');
    if (modulo === 'facial') {
      if (!fotoData) { setError('Selecione uma foto (JPEG ou PNG) para analisar.'); return; }
      runConsulta('facial', fotoData);
      return;
    }
    if (modulo === 'nome') {
      const termo = valor.trim().replace(/\s+/g, ' ');
      if (termo.length < 4) { setError('Informe um nome com pelo menos 4 caracteres.'); return; }
      runConsulta('nome', termo);
      return;
    }
    const digits = valor.replace(/\D/g, '');
    const info = MODULO_INFO[modulo];
    if (!info) return;
    if (!info.digits.includes(digits.length)) {
      const msg = (modulo === 'cpf' || modulo === 'cpf-premium' || modulo === 'cpf-dividas') ? 'Informe um CPF válido com 11 dígitos.'
        : (modulo === 'cnpj' || modulo === 'cnpj-dividas') ? 'Informe um CNPJ válido com 14 dígitos.'
        : 'Informe um telefone válido com DDD (10 ou 11 dígitos).';
      setError(msg);
      return;
    }
    runConsulta(modulo, digits);
  };

  const onFotoSelecionada = (file) => {
    setError('');
    if (!file) return;
    if (!/^image\/(jpeg|png)$/.test(file.type)) { setError('Formato inválido. Envie JPEG ou PNG.'); return; }
    if (file.size > 8 * 1024 * 1024) { setError('A foto excede o limite de 8 MB.'); return; }
    const reader = new FileReader();
    reader.onload = () => { setFotoData(reader.result); setFotoPreview(reader.result); setResultado(null); };
    reader.readAsDataURL(file);
  };

  const consultarCpfDireto = (cpfDigits) => {
    const d = String(cpfDigits || '').replace(/\D/g, '').padStart(11, '0');
    if (d.length !== 11) return;
    setModulo('cpf');
    setValor(formatCPF(d));
    runConsulta('cpf', d);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const abrirConsulta = async (id) => {
    setError('');
    try {
      setLoading(true);
      const { data } = await consultasAPI.obter(id);
      const tipo = data.tipo || 'cpf';
      setModulo(tipo);
      aplicarResultado(data.data, data.id, data.cliente_nome ? { id: data.cliente_id, nome: data.cliente_nome } : null, tipo);
      if (data.documento) setValor(formatDoc(data.documento, tipo));
      else if (tipo === 'cpf' && data.data?.dadosBasicos?.cpf) setValor(formatCPF(data.data.dadosBasicos.cpf));
    } catch (e) { setError('Não foi possível abrir a consulta.'); } finally { setLoading(false); }
  };

  const excluirConsulta = async (id, ev) => {
    ev.stopPropagation();
    try { await consultasAPI.excluir(id); setHistorico((h) => h.filter((x) => x.id !== id)); } catch (e) { /* ignore */ }
  };

  const exportarPdf = async () => {
    if (!consultaId) return;
    setBaixandoPdf(true);
    try {
      const res = await consultasAPI.pdf(consultaId);
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `dossie-${valor.replace(/\D/g, '') || resultadoTipo}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (e) { setError('Não foi possível gerar o PDF.'); } finally { setBaixandoPdf(false); }
  };

  const confirmarVinculo = async (cliente, emprestimoId) => {
    await consultasAPI.vincular(consultaId, { cliente_id: cliente.id, emprestimo_id: emprestimoId });
    setClienteVinc({ id: cliente.id, nome: cliente.nome });
    setShowVincular(false);
    carregarHistorico();
  };

  // ===== Derivados apenas para CPF =====
  const categoriasComDados = (() => {
    if (!resultado || resultadoTipo !== 'cpf') return [];
    const usadas = new Set();
    const base = CATEGORIES.map((c) => {
      const secoes = c.sections.filter((s) => !isEmptyVal(resultado[s]));
      secoes.forEach((s) => usadas.add(s));
      return { ...c, secoes };
    }).filter((c) => c.secoes.length > 0);
    const outros = Object.keys(resultado).filter((k) => k !== 'dadosBasicos' && !usadas.has(k) && !CATEGORIES.some((c) => c.sections.includes(k)) && !isEmptyVal(resultado[k]));
    if (outros.length > 0) base.push({ id: 'outros', label: 'Outros', icon: Activity, secoes: outros });
    return base;
  })();

  const catCorrente = categoriasComDados.find((c) => c.id === catAtiva) || categoriasComDados[0];

  const chips = (() => {
    if (!resultado || resultadoTipo !== 'cpf') return [];
    const out = [];
    categoriasComDados.forEach((c) => c.secoes.forEach((s) => {
      const v = resultado[s];
      out.push({ key: s, catId: c.id, count: Array.isArray(v) ? v.length : (typeof v === 'object' ? Object.keys(v).length : 1) });
    }));
    return out.sort((a, b) => b.count - a.count).slice(0, 8);
  })();

  // ===== Derivados para CNPJ =====
  const cnpjSecoes = (resultadoTipo === 'cnpj' && resultado)
    ? Object.keys(resultado).filter((k) => k !== 'dadosEmpresa' && !isEmptyVal(resultado[k]))
    : [];

  // ===== Derivados para Telefone =====
  const telLista = (resultadoTipo === 'telefone' && resultado && Array.isArray(resultado.data)) ? resultado.data : [];

  // ===== Derivados para Nome =====
  const nomeLista = (resultadoTipo === 'nome' && resultado && Array.isArray(resultado.data)) ? resultado.data : [];

  // ===== Derivados para Dívidas (CPF/CNPJ) =====
  const isDividas = resultadoTipo === 'cpf-dividas' || resultadoTipo === 'cnpj-dividas';
  const dividasDC = isDividas && resultado ? (resultado.dados_consulta || {}) : {};
  const dividasAval = dividasDC.avaliacao_preliminar_credito || null;
  const dividasAlertas = dividasDC.alertas_restricoes || null;
  const dividasInner = ((dividasDC.dados_consulta || {}).data) || {};
  const dividasBloco = resultadoTipo === 'cnpj-dividas' ? (dividasInner.blocos || {}) : (dividasInner.saida || {});
  const dividasSecoes = Object.keys(dividasBloco).filter((k) => !isEmptyVal(dividasBloco[k]));
  const dividasTitulo = resultadoTipo === 'cnpj-dividas'
    ? dividasBloco.identificacao_empresa?.razao_social
    : dividasBloco.identificacao?.nome;

  // ===== Derivados para Facial =====
  const facialSR = (resultadoTipo === 'facial' && resultado) ? (resultado.SERVICE_RESPONSE || {}) : {};
  const facialResults = Array.isArray(facialSR.results) ? facialSR.results : [];

  // ===== Derivados para CPF Premium =====
  const premiumDados = (resultadoTipo === 'cpf-premium' && resultado) ? (resultado.dados || {}) : {};
  const premiumSecoes = Array.isArray(premiumDados.secoes) ? premiumDados.secoes : [];
  const premiumTodasAbertas = premiumSecoes.length > 0 && premiumSecoes.every((_, i) => openSecoes[`premium-${i}`]);
  const togglePremiumTodas = () => setOpenSecoes((prev) => {
    const next = { ...prev };
    premiumSecoes.forEach((_, i) => {
      if (premiumTodasAbertas) delete next[`premium-${i}`];
      else next[`premium-${i}`] = true;
    });
    return next;
  });

  const secoesAtuais = resultadoTipo === 'cpf' ? (catCorrente?.secoes || []) : (resultadoTipo === 'cnpj' ? cnpjSecoes : (isDividas ? dividasSecoes : []));
  const todasAbertas = secoesAtuais.length > 0 && secoesAtuais.every((s) => openSecoes[s]);
  const toggleSecao = (s) => setOpenSecoes((p) => ({ ...p, [s]: !p[s] }));
  const toggleTodas = () => setOpenSecoes((prev) => {
    const next = { ...prev };
    if (todasAbertas) secoesAtuais.forEach((s) => { delete next[s]; });
    else secoesAtuais.forEach((s) => { next[s] = true; });
    return next;
  });

  const info = MODULO_INFO[modulo] || MODULO_INFO.cpf;
  const InputIcon = info.icon;

  const renderAcoes = () => (
    <div className="flex flex-wrap items-center gap-2" data-testid="consulta-acoes">
      <button onClick={exportarPdf} disabled={baixandoPdf} data-testid="consulta-exportar-pdf"
        className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium border border-border bg-card text-foreground hover:bg-sidebar-accent hover:border-primary/40 transition-all disabled:opacity-50">
        {baixandoPdf ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileDown className="w-4 h-4" />} Exportar PDF
      </button>
      <button onClick={() => setShowVincular(true)} data-testid="consulta-vincular"
        className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium border transition-all ${clienteVinc ? 'border-primary/40 bg-primary/10 text-primary' : 'border-border bg-card text-foreground hover:bg-sidebar-accent hover:border-primary/40'}`}>
        <Link2 className="w-4 h-4" /> {clienteVinc ? `Vinculado: ${clienteVinc.nome}` : 'Vincular a cliente'}
      </button>
    </div>
  );

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

      {/* Barra da Carteira */}
      {carteiraInfo && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-gradient-to-r from-primary/10 via-primary/5 to-transparent border border-primary/20" data-testid="consultas-carteira-bar">
          <div className="w-10 h-10 rounded-xl bg-primary/15 flex items-center justify-center">
            <Wallet className="w-5 h-5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Saldo da carteira</p>
            <p className="font-display font-bold text-xl text-foreground" data-testid="consultas-saldo">
              R$ {Number(carteiraInfo.saldo || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
            </p>
          </div>
          <div className="hidden sm:block text-right pr-2">
            <p className="text-xs text-muted-foreground">Esta consulta</p>
            <p className="text-sm font-semibold text-foreground" data-testid="consultas-preco-atual">
              R$ {Number(carteiraInfo.precos?.[modulo] || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
            </p>
          </div>
          <button onClick={() => navigate('/carteira')} data-testid="consultas-btn-recarregar"
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90">
            <Zap className="w-4 h-4" /> Recarregar
          </button>
        </div>
      )}

      {/* Banner Saldo Insuficiente */}
      {saldoInsuficiente && (
        <motion.div initial={{ y: -6, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
          className="flex items-center gap-3 p-4 rounded-xl bg-amber-500/10 border border-amber-500/40" data-testid="banner-saldo-insuficiente">
          <ShieldAlert className="w-6 h-6 text-amber-500 flex-shrink-0" />
          <div className="flex-1">
            <p className="font-semibold text-foreground">Saldo insuficiente</p>
            <p className="text-sm text-muted-foreground">{saldoInsuficiente.msg}</p>
          </div>
          <button onClick={() => navigate('/carteira')} data-testid="banner-recarregar"
            className="px-4 py-2 rounded-lg bg-amber-500 text-amber-950 text-sm font-bold hover:opacity-90">
            Recarregar carteira
          </button>
        </motion.div>
      )}

      {/* Módulos */}
      <div className="flex flex-wrap gap-2">
        {MODULOS.map((m) => {
          const Icon = m.icon; const active = modulo === m.id;
          return (
            <button key={m.id} disabled={!m.ativo} onClick={() => m.ativo && trocarModulo(m.id)} data-testid={`consulta-modulo-${m.id}`}
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
            <div className="flex flex-wrap items-center justify-between gap-2">
              <label className="text-sm font-semibold text-foreground block">{info.label}</label>
              {(modulo === 'cpf-dividas' || modulo === 'cnpj-dividas') && <BoaVistaBadge />}
            </div>
            {info.foto ? (
              <div className="flex flex-col sm:flex-row gap-4 items-start">
                <label htmlFor="facial-upload" data-testid="consulta-facial-dropzone"
                  className="flex-1 w-full cursor-pointer rounded-2xl border-2 border-dashed border-border hover:border-primary/50 bg-background/50 p-6 flex flex-col items-center justify-center gap-2 text-center transition-colors min-h-[160px]">
                  {fotoPreview ? (
                    <img src={fotoPreview} alt="Prévia" className="max-h-40 rounded-xl object-contain" data-testid="consulta-facial-preview" />
                  ) : (
                    <>
                      <span className="w-12 h-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center"><Camera className="w-6 h-6" /></span>
                      <span className="text-sm font-medium text-foreground">Clique para enviar uma foto</span>
                      <span className="text-xs text-muted-foreground">JPEG ou PNG · até 8 MB</span>
                    </>
                  )}
                  <input id="facial-upload" type="file" accept="image/jpeg,image/png" className="hidden"
                    data-testid="consulta-facial-input"
                    onChange={(e) => onFotoSelecionada(e.target.files?.[0])} />
                </label>
                <div className="flex sm:flex-col gap-2 w-full sm:w-auto">
                  <button onClick={buscar} disabled={loading || !fotoData} data-testid="consulta-facial-buscar"
                    className="flex-1 px-6 py-3 rounded-xl bg-primary text-primary-foreground font-semibold hover:opacity-90 active:scale-[0.99] transition-all flex items-center justify-center gap-2 shadow-lg shadow-primary/20 disabled:opacity-50 whitespace-nowrap">
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ScanFace className="w-4 h-4" />} Analisar
                  </button>
                  {fotoPreview && (
                    <button onClick={() => { setFotoData(''); setFotoPreview(''); setResultado(null); }} data-testid="consulta-facial-limpar"
                      className="px-6 py-3 rounded-xl border border-border bg-card text-foreground text-sm font-medium hover:bg-sidebar-accent transition-all flex items-center justify-center gap-2 whitespace-nowrap">
                      <X className="w-4 h-4" /> Trocar
                    </button>
                  )}
                </div>
              </div>
            ) : (
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <InputIcon className="w-5 h-5 text-muted-foreground absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input type="text" inputMode={info.text ? 'text' : 'numeric'} value={valor}
                  onChange={(e) => setValor(formatEntrada(e.target.value, modulo))}
                  onKeyDown={(e) => e.key === 'Enter' && !loading && buscar()}
                  placeholder={info.placeholder} data-testid={`consulta-${modulo}-input`}
                  className={`w-full pl-11 pr-4 py-3 rounded-xl bg-background border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all ${info.text ? '' : 'font-mono'}`} />
              </div>
              <button onClick={buscar} disabled={loading} data-testid={`consulta-${modulo}-buscar`}
                className="px-6 py-3 rounded-xl bg-primary text-primary-foreground font-semibold hover:opacity-90 active:scale-[0.99] transition-all flex items-center justify-center gap-2 shadow-lg shadow-primary/20 disabled:opacity-50">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />} Consultar
              </button>
            </div>
            )}
            <div className="flex items-center gap-2">
              <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <ShieldCheck className="w-3.5 h-3.5 text-primary" /> Consulta segura processada no servidor.
              </p>
            </div>
            {error && (
              <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2.5" data-testid="consulta-erro">
                <AlertCircle className="w-4 h-4 flex-shrink-0" /> {error}
              </div>
            )}
          </div>

          {loading && !resultado && <Loading message="Consultando dados..." />}

          {/* ===== Resultado CPF ===== */}
          {resultado && resultadoTipo === 'cpf' && (
            <div className="space-y-5" data-testid="consulta-resultado">
              <HeroProfile basicos={resultado.dadosBasicos} sectionCounts={chips} onChipClick={setCatAtiva} />
              {renderAcoes()}

              {categoriasComDados.length > 0 && (
                <>
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
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
                    <button onClick={toggleTodas} data-testid="consulta-toggle-todas"
                      className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-sm font-medium border border-border bg-card text-foreground hover:bg-sidebar-accent hover:border-primary/40 transition-all self-start whitespace-nowrap">
                      {todasAbertas ? <ChevronsDownUp className="w-4 h-4" /> : <ChevronsUpDown className="w-4 h-4" />}
                      {todasAbertas ? 'Recolher tudo' : 'Expandir tudo'}
                    </button>
                  </div>

                  <motion.div
                    key={catCorrente?.id}
                    variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.05 } } }}
                    initial="hidden" animate="visible"
                    className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start [grid-auto-flow:dense]"
                  >
                    {catCorrente?.secoes.map((s) => (
                      <InfoCard key={s} sectionKey={s} value={resultado[s]} open={!!openSecoes[s]} onToggle={() => toggleSecao(s)} wide={contarCampos(resultado[s]) >= 8} />
                    ))}
                  </motion.div>
                </>
              )}
            </div>
          )}

          {/* ===== Resultado CPF Premium ===== */}
          {resultado && resultadoTipo === 'cpf-premium' && (
            <div className="space-y-5" data-testid="consulta-resultado">
              <PremiumProfile dados={premiumDados} />
              {renderAcoes()}

              {premiumSecoes.length > 0 && (
                <>
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm text-muted-foreground">
                      <span className="text-foreground font-semibold">{premiumSecoes.length}</span> seção(ões) no dossiê
                    </p>
                    <button onClick={togglePremiumTodas} data-testid="premium-toggle-todas"
                      className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-sm font-medium border border-border bg-card text-foreground hover:bg-sidebar-accent hover:border-primary/40 transition-all whitespace-nowrap">
                      {premiumTodasAbertas ? <ChevronsDownUp className="w-4 h-4" /> : <ChevronsUpDown className="w-4 h-4" />}
                      {premiumTodasAbertas ? 'Recolher tudo' : 'Expandir tudo'}
                    </button>
                  </div>
                  <motion.div
                    variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.03 } } }}
                    initial="hidden" animate="visible"
                    className="grid grid-cols-1 gap-3"
                    data-testid="premium-secoes"
                  >
                    {premiumSecoes.map((s, i) => (
                      <PremiumSecao key={i} secao={s} index={i}
                        open={!!openSecoes[`premium-${i}`]}
                        onToggle={() => toggleSecao(`premium-${i}`)} />
                    ))}
                  </motion.div>
                </>
              )}
            </div>
          )}

          {/* ===== Resultado CNPJ ===== */}
          {resultado && resultadoTipo === 'cnpj' && (
            <div className="space-y-5" data-testid="consulta-resultado">
              <CompanyHero emp={resultado.dadosEmpresa} cnpj={valor} sociosCount={Array.isArray(resultado.socios) ? resultado.socios.length : null} />
              {renderAcoes()}

              {cnpjSecoes.length > 0 && (
                <>
                  <div className="flex justify-end">
                    <button onClick={toggleTodas} data-testid="consulta-toggle-todas"
                      className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-sm font-medium border border-border bg-card text-foreground hover:bg-sidebar-accent hover:border-primary/40 transition-all whitespace-nowrap">
                      {todasAbertas ? <ChevronsDownUp className="w-4 h-4" /> : <ChevronsUpDown className="w-4 h-4" />}
                      {todasAbertas ? 'Recolher tudo' : 'Expandir tudo'}
                    </button>
                  </div>
                  <motion.div
                    variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.05 } } }}
                    initial="hidden" animate="visible"
                    className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start [grid-auto-flow:dense]"
                  >
                    {cnpjSecoes.map((s) => (
                      <InfoCard key={s} sectionKey={s} value={resultado[s]} open={!!openSecoes[s]} onToggle={() => toggleSecao(s)} wide={contarCampos(resultado[s]) >= 8} />
                    ))}
                  </motion.div>
                </>
              )}
            </div>
          )}

          {/* ===== Resultado Telefone ===== */}
          {resultado && resultadoTipo === 'telefone' && (
            <div className="space-y-5" data-testid="consulta-resultado">
              <motion.div
                initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}
                className="rounded-3xl border border-primary/20 bg-gradient-to-br from-card via-card to-primary/5 p-6 sm:p-8 relative overflow-hidden shadow-xl"
                data-testid="consulta-identidade"
              >
                <div className="absolute -top-24 -right-24 w-72 h-72 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
                <div className="relative flex items-center gap-5">
                  <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-primary/15 border border-primary/30 flex items-center justify-center text-primary shadow-inner flex-shrink-0">
                    <Phone className="w-8 h-8 sm:w-10 sm:h-10" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h2 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight break-words font-mono">{formatTelefone(valor)}</h2>
                    <p className="text-sm text-muted-foreground mt-1">
                      <span className="text-foreground font-semibold">{telLista.length}</span> pessoa(s) associada(s) a este número
                    </p>
                  </div>
                </div>
              </motion.div>
              {renderAcoes()}

              {telLista.length > 0 ? (
                <motion.div
                  variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.04 } } }}
                  initial="hidden" animate="visible"
                  className="grid grid-cols-1 md:grid-cols-2 gap-4"
                  data-testid="telefone-lista"
                >
                  {telLista.map((p, i) => {
                    const cpfDigits = String(p.cpfCnpj || '').replace(/\D/g, '');
                    const podeCpf = cpfDigits.length > 0 && cpfDigits.length <= 11;
                    return (
                      <motion.div key={i}
                        variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0 } }}
                        className="rounded-2xl border border-border bg-card p-4 hover:border-primary/30 transition-all"
                        data-testid={`telefone-pessoa-${i}`}
                      >
                        <div className="flex items-start gap-3">
                          <span className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center flex-shrink-0"><User className="w-5 h-5" /></span>
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-semibold text-foreground break-words">{p.nome || '—'}</p>
                            {p.cpfCnpj && <p className="text-xs text-muted-foreground font-mono mt-0.5">{formatCPF(cpfDigits.padStart(11, '0'))}</p>}
                          </div>
                        </div>
                        {Array.isArray(p.endereco) && p.endereco.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-border/60">{renderValue(p.endereco)}</div>
                        )}
                        {podeCpf && (
                          <button onClick={() => consultarCpfDireto(cpfDigits)} data-testid={`telefone-consultar-cpf-${i}`}
                            className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border border-border bg-background/50 text-foreground hover:bg-sidebar-accent hover:border-primary/40 transition-all">
                            <IdCard className="w-4 h-4" /> Consultar CPF
                          </button>
                        )}
                      </motion.div>
                    );
                  })}
                </motion.div>
              ) : (
                <div className="rounded-2xl border border-dashed border-border bg-card/40 p-8 text-center">
                  <p className="text-sm text-muted-foreground">Nenhuma pessoa associada a este telefone.</p>
                </div>
              )}
            </div>
          )}

          {/* ===== Resultado Nome ===== */}
          {resultado && resultadoTipo === 'nome' && (
            <div className="space-y-5" data-testid="consulta-resultado">
              <motion.div
                initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}
                className="rounded-3xl border border-primary/20 bg-gradient-to-br from-card via-card to-primary/5 p-6 sm:p-8 relative overflow-hidden shadow-xl"
                data-testid="consulta-identidade"
              >
                <div className="absolute -top-24 -right-24 w-72 h-72 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
                <div className="relative flex items-center gap-5">
                  <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-primary/15 border border-primary/30 flex items-center justify-center text-primary shadow-inner flex-shrink-0">
                    <Users className="w-8 h-8 sm:w-10 sm:h-10" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h2 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight break-words uppercase">{valor}</h2>
                    <p className="text-sm text-muted-foreground mt-1">
                      <span className="text-foreground font-semibold">{nomeLista.length}</span> pessoa(s) encontrada(s) com este nome
                    </p>
                  </div>
                </div>
              </motion.div>
              {renderAcoes()}

              {nomeLista.length > 0 ? (
                <motion.div
                  variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.04 } } }}
                  initial="hidden" animate="visible"
                  className="grid grid-cols-1 md:grid-cols-2 gap-4"
                  data-testid="nome-lista"
                >
                  {nomeLista.map((p, i) => {
                    const cpfDigits = String(p.cpf || '').replace(/\D/g, '');
                    const podeCpf = cpfDigits.length > 0 && cpfDigits.length <= 11;
                    const situacao = p.situacaoCadastral?.situacao;
                    const local = [p.cidade, p.uf].filter((x) => !isEmptyVal(x)).join(' / ');
                    const detalhes = [
                      ['Nascimento', p.nasc],
                      ['Sexo', p.sexo === 'M' ? 'Masculino' : p.sexo === 'F' ? 'Feminino' : p.sexo],
                      ['Local', local],
                      ['Nome da Mãe', p.filiacao?.nomeMae],
                    ].filter(([, v]) => !isEmptyVal(v));
                    return (
                      <motion.div key={i}
                        variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0 } }}
                        className="rounded-2xl border border-border bg-card p-4 hover:border-primary/30 transition-all"
                        data-testid={`nome-pessoa-${i}`}
                      >
                        <div className="flex items-start gap-3">
                          <span className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center flex-shrink-0"><User className="w-5 h-5" /></span>
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-semibold text-foreground break-words">{p.nome || '—'}</p>
                            {p.cpf && <p className="text-xs text-muted-foreground font-mono mt-0.5">{formatCPF(cpfDigits.padStart(11, '0'))}</p>}
                          </div>
                          {situacao && (
                            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-md border flex-shrink-0 ${/regular/i.test(situacao) ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' : 'bg-amber-500/10 text-amber-500 border-amber-500/20'}`}>
                              {situacao}
                            </span>
                          )}
                        </div>
                        {detalhes.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-border/60 grid grid-cols-2 gap-x-4 gap-y-2">
                            {detalhes.map(([label, v]) => (
                              <div key={label} className="min-w-0">
                                <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">{label}</p>
                                <p className="text-xs text-foreground font-medium break-words mt-0.5">{v}</p>
                              </div>
                            ))}
                          </div>
                        )}
                        {podeCpf && (
                          <button onClick={() => consultarCpfDireto(cpfDigits)} data-testid={`nome-consultar-cpf-${i}`}
                            className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border border-border bg-background/50 text-foreground hover:bg-sidebar-accent hover:border-primary/40 transition-all">
                            <IdCard className="w-4 h-4" /> Consultar CPF completo
                          </button>
                        )}
                      </motion.div>
                    );
                  })}
                </motion.div>
              ) : (
                <div className="rounded-2xl border border-dashed border-border bg-card/40 p-8 text-center">
                  <p className="text-sm text-muted-foreground">Nenhuma pessoa encontrada com este nome.</p>
                </div>
              )}
            </div>
          )}

          {/* ===== Resultado Dívidas (CPF/CNPJ) ===== */}
          {resultado && isDividas && (
            <div className="space-y-5" data-testid="consulta-resultado">
              <RiskHero
                aval={dividasAval}
                alertas={dividasAlertas}
                titulo={dividasTitulo || formatDoc(valor.replace(/\D/g, ''), resultadoTipo)}
                subtitulo={resultadoTipo === 'cnpj-dividas' ? 'Dívidas & Restrições — CNPJ (Boa Vista)' : 'Dívidas & Restrições — CPF (Boa Vista)'}
              />
              {renderAcoes()}

              {dividasSecoes.length > 0 && (
                <>
                  <div className="flex justify-end">
                    <button onClick={toggleTodas} data-testid="consulta-toggle-todas"
                      className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-sm font-medium border border-border bg-card text-foreground hover:bg-sidebar-accent hover:border-primary/40 transition-all whitespace-nowrap">
                      {todasAbertas ? <ChevronsDownUp className="w-4 h-4" /> : <ChevronsUpDown className="w-4 h-4" />}
                      {todasAbertas ? 'Recolher tudo' : 'Expandir tudo'}
                    </button>
                  </div>
                  <motion.div
                    variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.05 } } }}
                    initial="hidden" animate="visible"
                    className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start [grid-auto-flow:dense]"
                  >
                    {dividasSecoes.map((s) => (
                      <InfoCard key={s} sectionKey={s} value={dividasBloco[s]} open={!!openSecoes[s]} onToggle={() => toggleSecao(s)} wide={contarCampos(dividasBloco[s]) >= 8} />
                    ))}
                  </motion.div>
                </>
              )}
            </div>
          )}

          {/* ===== Resultado Facial ===== */}
          {resultado && resultadoTipo === 'facial' && (
            <div className="space-y-5" data-testid="consulta-resultado">
              <motion.div
                initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}
                className="rounded-3xl border border-primary/20 bg-gradient-to-br from-card via-card to-primary/5 p-6 sm:p-8 relative overflow-hidden shadow-xl"
                data-testid="consulta-identidade"
              >
                <div className="absolute -top-24 -right-24 w-72 h-72 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
                <div className="relative flex flex-col sm:flex-row sm:items-center gap-5">
                  {fotoPreview && <img src={fotoPreview} alt="Foto analisada" className="w-24 h-24 rounded-2xl object-cover border border-border flex-shrink-0" />}
                  <div className="min-w-0 flex-1">
                    <p className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">Reconhecimento Facial</p>
                    <h2 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
                      {facialResults.length} correspondência(s)
                    </h2>
                    <div className="flex flex-wrap items-center gap-2 mt-2">
                      <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-md border text-xs font-semibold ${facialSR.match_found ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' : 'bg-amber-500/15 text-amber-400 border-amber-500/30'}`} data-testid="consulta-facial-match">
                        {facialSR.match_found ? <Check className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
                        {facialSR.match_found ? 'Correspondência confirmada' : 'Sem correspondência forte'}
                      </span>
                      {facialSR.best_score !== undefined && (
                        <span className="inline-flex items-center px-3 py-1 rounded-md bg-muted/80 border border-border/60 text-xs font-semibold text-foreground font-mono">
                          Melhor score: {Math.round(Number(facialSR.best_score) * 100)}%
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </motion.div>
              {renderAcoes()}

              {facialResults.length > 0 ? (
                <motion.div
                  variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.04 } } }}
                  initial="hidden" animate="visible"
                  className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4"
                  data-testid="facial-lista"
                >
                  {facialResults.map((p, i) => {
                    const cpfDigits = String(p.cpf || '').replace(/\D/g, '');
                    const podeCpf = cpfDigits.length > 0 && cpfDigits.length <= 11;
                    const pct = p.score !== undefined ? Math.round(Number(p.score) * 100) : null;
                    return (
                      <motion.div key={i}
                        variants={{ hidden: { opacity: 0, y: 10 }, visible: { opacity: 1, y: 0 } }}
                        className="rounded-2xl border border-border bg-card overflow-hidden hover:border-primary/30 transition-all"
                        data-testid={`facial-pessoa-${i}`}
                      >
                        <div className="aspect-[4/3] bg-muted/40 overflow-hidden flex items-center justify-center">
                          {p.reference_photo_url
                            ? <img src={p.reference_photo_url} alt={p.nome || 'Referência'} className="w-full h-full object-cover" loading="lazy" onError={(e) => { e.target.style.display = 'none'; }} />
                            : <User className="w-10 h-10 text-muted-foreground" />}
                        </div>
                        <div className="p-4 space-y-2">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-semibold text-foreground break-words min-w-0">{p.nome || '—'}</p>
                            {pct !== null && <span className="text-xs font-mono font-bold text-primary flex-shrink-0">{pct}%</span>}
                          </div>
                          {p.cpf && <p className="text-xs text-muted-foreground font-mono">{formatCPF(cpfDigits.padStart(11, '0'))}</p>}
                          {p.source_type && <p className="text-[11px] text-muted-foreground">{p.source_type}</p>}
                          {podeCpf && (
                            <button onClick={() => consultarCpfDireto(cpfDigits)} data-testid={`facial-consultar-cpf-${i}`}
                              className="mt-1 w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border border-border bg-background/50 text-foreground hover:bg-sidebar-accent hover:border-primary/40 transition-all">
                              <IdCard className="w-4 h-4" /> Consultar CPF completo
                            </button>
                          )}
                        </div>
                      </motion.div>
                    );
                  })}
                </motion.div>
              ) : (
                <div className="rounded-2xl border border-dashed border-border bg-card/40 p-8 text-center">
                  <p className="text-sm text-muted-foreground">Nenhuma correspondência encontrada para esta foto.</p>
                </div>
              )}
            </div>
          )}


          {!resultado && !loading && (
            <div className="rounded-2xl border border-dashed border-border bg-card/40 p-12 text-center" data-testid="consulta-vazio">
              <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
                <ScanSearch className="w-7 h-7 text-primary" />
              </div>
              <p className="text-sm font-medium text-foreground">Nenhuma consulta realizada</p>
              <p className="text-sm text-muted-foreground mt-1">
                {modulo === 'cnpj' ? 'Digite um CNPJ e clique em Consultar para ver o dossiê da empresa.'
                  : modulo === 'cpf-premium' ? 'Digite um CPF e clique em Consultar para ver o dossiê Premium completo.'
                  : modulo === 'telefone' ? 'Digite um telefone com DDD e clique em Consultar para ver as pessoas associadas.'
                  : modulo === 'nome' ? 'Digite um nome exato e clique em Consultar para localizar pessoas.'
                  : modulo === 'cpf-dividas' ? 'Digite um CPF e clique em Consultar para ver o painel de dívidas e restrições.'
                  : modulo === 'cnpj-dividas' ? 'Digite um CNPJ e clique em Consultar para ver o painel de dívidas e restrições.'
                  : modulo === 'facial' ? 'Envie uma foto (JPEG ou PNG) e clique em Analisar para buscar correspondências faciais.'
                  : 'Digite um CPF e clique em Consultar para ver o dossiê completo.'}
              </p>
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
          <p className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">{(MODULOS.find((m) => m.id === modulo)?.label) || 'CPF'}</p>
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
                      <p className="text-sm font-semibold text-foreground truncate">{h.resumo?.nome || `Consulta ${(h.tipo || '').toUpperCase()}`}</p>
                      <p className="text-xs text-muted-foreground font-mono mt-0.5">{formatDoc(h.documento, h.tipo)}</p>
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
      {showVincular && <VincularModal onClose={() => setShowVincular(false)} onConfirm={confirmarVinculo} />}
    </div>
    </Layout>
  );
};

export default Consultas;
