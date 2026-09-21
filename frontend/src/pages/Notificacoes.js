import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import { useModal } from '../components/Modal';
import { notificacoesAPI } from '../api/api';
import { formatarDataHora } from '../utils/formatters';
import { toast } from '../hooks/use-toast';
import {
  Bell, BellRing, MailOpen, CalendarClock, AlertTriangle, CheckCircle2,
  Settings2, CreditCard, LifeBuoy, Sparkle, Trash2, Check, RefreshCw,
  CheckCheck, Info, Inbox
} from 'lucide-react';

// Mapa único de tipo -> ícone + paleta. Cobre os tipos de negócio e os de sistema/assinatura.
const TIPO_CFG = {
  vencimento:          { Icon: CalendarClock, label: 'Vencimento',  accent: 'amber',   chip: 'bg-amber-500/12 text-amber-500',     bar: 'bg-amber-500',   soft: 'bg-amber-500/[0.05]',   badge: 'bg-amber-500/15 text-amber-600 dark:text-amber-400' },
  atraso:              { Icon: AlertTriangle, label: 'Atraso',      accent: 'red',     chip: 'bg-red-500/12 text-red-500',         bar: 'bg-red-500',     soft: 'bg-red-500/[0.05]',     badge: 'bg-red-500/15 text-red-600 dark:text-red-400' },
  pagamento:           { Icon: CheckCircle2,  label: 'Pagamento',   accent: 'emerald', chip: 'bg-emerald-500/12 text-emerald-500', bar: 'bg-emerald-500', soft: 'bg-emerald-500/[0.05]', badge: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400' },
  sistema:             { Icon: Settings2,     label: 'Sistema',     accent: 'sky',     chip: 'bg-sky-500/12 text-sky-500',         bar: 'bg-sky-500',     soft: 'bg-sky-500/[0.05]',     badge: 'bg-sky-500/15 text-sky-600 dark:text-sky-400' },
  boas_vindas:         { Icon: Sparkle,       label: 'Boas-vindas', accent: 'violet',  chip: 'bg-violet-500/12 text-violet-500',   bar: 'bg-violet-500',  soft: 'bg-violet-500/[0.05]',  badge: 'bg-violet-500/15 text-violet-600 dark:text-violet-400' },
  assinatura_expirando:{ Icon: CreditCard,    label: 'Assinatura',  accent: 'amber',   chip: 'bg-amber-500/12 text-amber-500',     bar: 'bg-amber-500',   soft: 'bg-amber-500/[0.05]',   badge: 'bg-amber-500/15 text-amber-600 dark:text-amber-400' },
  assinatura_expirada: { Icon: CreditCard,    label: 'Assinatura',  accent: 'red',     chip: 'bg-red-500/12 text-red-500',         bar: 'bg-red-500',     soft: 'bg-red-500/[0.05]',     badge: 'bg-red-500/15 text-red-600 dark:text-red-400' },
  trial_expirando:     { Icon: CreditCard,    label: 'Trial',       accent: 'amber',   chip: 'bg-amber-500/12 text-amber-500',     bar: 'bg-amber-500',   soft: 'bg-amber-500/[0.05]',   badge: 'bg-amber-500/15 text-amber-600 dark:text-amber-400' },
  trial_expirado:      { Icon: CreditCard,    label: 'Trial',       accent: 'red',     chip: 'bg-red-500/12 text-red-500',         bar: 'bg-red-500',     soft: 'bg-red-500/[0.05]',     badge: 'bg-red-500/15 text-red-600 dark:text-red-400' },
  plano_atualizado:    { Icon: CreditCard,    label: 'Plano',       accent: 'emerald', chip: 'bg-emerald-500/12 text-emerald-500', bar: 'bg-emerald-500', soft: 'bg-emerald-500/[0.05]', badge: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400' },
  suporte_novo:        { Icon: LifeBuoy,      label: 'Suporte',     accent: 'sky',     chip: 'bg-sky-500/12 text-sky-500',         bar: 'bg-sky-500',     soft: 'bg-sky-500/[0.05]',     badge: 'bg-sky-500/15 text-sky-600 dark:text-sky-400' },
  suporte_resposta:    { Icon: LifeBuoy,      label: 'Suporte',     accent: 'sky',     chip: 'bg-sky-500/12 text-sky-500',         bar: 'bg-sky-500',     soft: 'bg-sky-500/[0.05]',     badge: 'bg-sky-500/15 text-sky-600 dark:text-sky-400' },
  suporte_mensagem:    { Icon: LifeBuoy,      label: 'Suporte',     accent: 'sky',     chip: 'bg-sky-500/12 text-sky-500',         bar: 'bg-sky-500',     soft: 'bg-sky-500/[0.05]',     badge: 'bg-sky-500/15 text-sky-600 dark:text-sky-400' },
  suporte_resolvido:   { Icon: LifeBuoy,      label: 'Suporte',     accent: 'emerald', chip: 'bg-emerald-500/12 text-emerald-500', bar: 'bg-emerald-500', soft: 'bg-emerald-500/[0.05]', badge: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400' },
};
const CFG_PADRAO = { Icon: Bell, label: 'Aviso', accent: 'slate', chip: 'bg-muted text-muted-foreground', bar: 'bg-muted-foreground', soft: 'bg-muted/40', badge: 'bg-muted text-muted-foreground' };
const cfgDe = (tipo) => TIPO_CFG[tipo] || CFG_PADRAO;

const Notificacoes = () => {
  const [notificacoes, setNotificacoes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [verificando, setVerificando] = useState(false);
  const [filtro, setFiltro] = useState('todas');
  const [error, setError] = useState('');
  const modal = useModal();

  const carregarNotificacoes = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const response = await notificacoesAPI.listar({
        apenas_nao_lidas: filtro === 'nao_lidas'
      });
      setNotificacoes(response.data);
    } catch (err) {
      console.error('Erro ao carregar notificações:', err);
      setError('Não foi possível carregar as notificações.');
    } finally {
      setLoading(false);
    }
  }, [filtro]);

  useEffect(() => {
    carregarNotificacoes();
  }, [carregarNotificacoes]);

  const marcarComoLida = async (id) => {
    try {
      await notificacoesAPI.marcarLida(id);
      setNotificacoes(prev => prev.map(n => (n.id === id ? { ...n, lida: true } : n)));
    } catch (err) {
      toast({ title: 'Erro', description: 'Não foi possível marcar como lida.', variant: 'destructive' });
      console.error('Erro ao marcar como lida:', err);
    }
  };

  const marcarTodasComoLidas = async () => {
    try {
      await notificacoesAPI.marcarTodasLidas();
      setNotificacoes(prev => prev.map(n => ({ ...n, lida: true })));
    } catch (err) {
      toast({ title: 'Erro', description: 'Não foi possível marcar todas como lidas.', variant: 'destructive' });
      console.error('Erro ao marcar todas como lidas:', err);
    }
  };

  const limparTodasNotificacoes = () => {
    modal.confirm(
      'Limpar Todas as Notificações',
      'Tem certeza que deseja apagar TODAS as notificações? Esta ação não pode ser desfeita.',
      async () => {
        try {
          await notificacoesAPI.limparTodas();
          setNotificacoes([]);
          modal.success('Sucesso', 'Todas as notificações foram removidas.');
        } catch (err) {
          console.error('Erro ao limpar notificações:', err);
          modal.error('Erro', 'Não foi possível limpar as notificações.');
        }
      }
    );
  };

  const excluirNotificacao = async (id) => {
    try {
      await notificacoesAPI.excluir(id);
      setNotificacoes(prev => prev.filter(n => n.id !== id));
    } catch (err) {
      toast({ title: 'Erro', description: 'Não foi possível excluir notificação.', variant: 'destructive' });
      console.error('Erro ao excluir notificação:', err);
    }
  };

  const verificarVencimentos = async () => {
    try {
      setVerificando(true);
      const response = await notificacoesAPI.verificarVencimentos();
      modal.success('Verificação Concluída', response.data.message || 'Vencimentos verificados com sucesso.');
      carregarNotificacoes();
    } catch (err) {
      console.error('Erro ao verificar vencimentos:', err);
      modal.error('Erro na Verificação', 'Não foi possível verificar os vencimentos. Tente novamente.');
    } finally {
      setVerificando(false);
    }
  };

  const naoLidas = notificacoes.filter(n => !n.lida).length;
  const totalVencimentos = notificacoes.filter(n => n.tipo === 'vencimento').length;
  const totalAtrasos = notificacoes.filter(n => n.tipo === 'atraso').length;

  const resumo = [
    { key: 'total',  label: 'Total',       valor: notificacoes.length, Icon: Bell,          chip: 'bg-primary/12 text-primary',     valorCls: 'text-foreground' },
    { key: 'lidas',  label: 'Não lidas',   valor: naoLidas,             Icon: MailOpen,      chip: 'bg-sky-500/12 text-sky-500',     valorCls: 'text-sky-500' },
    { key: 'venc',   label: 'Vencimentos', valor: totalVencimentos,     Icon: CalendarClock, chip: 'bg-amber-500/12 text-amber-500', valorCls: 'text-amber-500' },
    { key: 'atraso', label: 'Atrasos',     valor: totalAtrasos,         Icon: AlertTriangle, chip: 'bg-red-500/12 text-red-500',     valorCls: 'text-red-500' },
  ];

  const infoItens = [
    { Icon: CalendarClock, cls: 'bg-amber-500/12 text-amber-500',   titulo: 'Vencimentos', texto: 'Alertas de parcelas que vencem nos próximos 7 dias.' },
    { Icon: AlertTriangle, cls: 'bg-red-500/12 text-red-500',       titulo: 'Atrasos',     texto: 'Parcelas já vencidas e ainda não pagas.' },
    { Icon: CheckCircle2,  cls: 'bg-emerald-500/12 text-emerald-500', titulo: 'Pagamentos', texto: 'Confirmações de pagamentos recebidos.' },
  ];

  if (loading) return <Loading message="Carregando notificações..." />;

  return (
    <Layout>
      <div className="container mx-auto max-w-5xl px-4 py-8 md:py-10">
        {/* Cabeçalho */}
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div className="flex items-start gap-3">
            <div className="relative mt-0.5 flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/12 text-primary">
              <BellRing className="h-5 w-5" />
              {naoLidas > 0 && (
                <span className="absolute -right-1 -top-1 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-primary px-1 text-[11px] font-bold text-primary-foreground">
                  {naoLidas > 9 ? '9+' : naoLidas}
                </span>
              )}
            </div>
            <div>
              <h1 className="font-display text-2xl md:text-3xl font-bold text-foreground" data-testid="notificacoes-title">
                Notificações
              </h1>
              <p className="mt-0.5 text-sm text-muted-foreground">
                {naoLidas > 0 ? `Você tem ${naoLidas} não lida${naoLidas > 1 ? 's' : ''}` : 'Tudo em dia — nenhuma pendência por aqui'}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {naoLidas > 0 && (
              <button
                onClick={marcarTodasComoLidas}
                data-testid="marcar-todas-lidas"
                className="inline-flex items-center gap-2 rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-muted"
              >
                <CheckCheck className="h-4 w-4" /> Marcar todas
              </button>
            )}
            {notificacoes.length > 0 && (
              <button
                onClick={limparTodasNotificacoes}
                data-testid="limpar-todas"
                className="inline-flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/[0.06] px-3.5 py-2.5 text-sm font-medium text-red-500 transition-colors hover:bg-red-500/15"
              >
                <Trash2 className="h-4 w-4" /> Limpar
              </button>
            )}
            <button
              onClick={verificarVencimentos}
              disabled={verificando}
              data-testid="verificar-vencimentos"
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/20 transition-all hover:brightness-110 disabled:opacity-60"
            >
              <RefreshCw className={`h-4 w-4 ${verificando ? 'animate-spin' : ''}`} />
              {verificando ? 'Verificando…' : 'Verificar vencimentos'}
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-500">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" /> {error}
          </div>
        )}

        {/* Cards de resumo */}
        <div className="mb-8 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {resumo.map((c, i) => (
            <motion.div
              key={c.key}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.35 }}
              className="group rounded-2xl border border-border bg-card p-4 transition-colors hover:border-primary/30"
            >
              <div className="flex items-center justify-between">
                <span className={`flex h-10 w-10 items-center justify-center rounded-xl ${c.chip} transition-transform group-hover:scale-105`}>
                  <c.Icon className="h-5 w-5" />
                </span>
                <span className={`font-display text-3xl font-bold tabular-nums ${c.valorCls}`}>{c.valor}</span>
              </div>
              <p className="mt-3 text-sm font-medium text-muted-foreground">{c.label}</p>
            </motion.div>
          ))}
        </div>

        {/* Filtros segmentados */}
        <div className="mb-5 inline-flex rounded-xl border border-border bg-muted/40 p-1">
          <button
            onClick={() => setFiltro('todas')}
            data-testid="filtro-todas"
            className={`rounded-lg px-4 py-1.5 text-sm font-medium transition-all ${filtro === 'todas' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
          >
            Todas
          </button>
          <button
            onClick={() => setFiltro('nao_lidas')}
            data-testid="filtro-nao-lidas"
            className={`rounded-lg px-4 py-1.5 text-sm font-medium transition-all ${filtro === 'nao_lidas' ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
          >
            Não lidas {naoLidas > 0 && <span className="ml-1 rounded-full bg-primary/15 px-1.5 text-xs font-bold text-primary">{naoLidas}</span>}
          </button>
        </div>

        {/* Lista */}
        {notificacoes.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border bg-card/50 p-10 text-center" data-testid="sem-notificacoes">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <Inbox className="h-7 w-7" />
            </div>
            <h3 className="font-display text-lg font-semibold text-foreground">Nenhuma notificação</h3>
            <p className="mx-auto mt-1.5 max-w-md text-sm text-muted-foreground">
              Rode uma verificação para gerar alertas de parcelas próximas do vencimento ou já atrasadas.
            </p>
            <button
              onClick={verificarVencimentos}
              disabled={verificando}
              className="mt-5 inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/20 transition-all hover:brightness-110 disabled:opacity-60"
            >
              <RefreshCw className={`h-4 w-4 ${verificando ? 'animate-spin' : ''}`} /> Verificar agora
            </button>
          </div>
        ) : (
          <div className="space-y-2.5">
            <AnimatePresence initial={false}>
              {notificacoes.map((notif, i) => {
                const cfg = cfgDe(notif.tipo);
                const { Icon } = cfg;
                return (
                  <motion.div
                    key={notif.id}
                    layout
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, x: -12, height: 0, marginBottom: 0 }}
                    transition={{ delay: Math.min(i * 0.03, 0.25), duration: 0.3 }}
                    className={`group relative flex gap-3 overflow-hidden rounded-2xl border border-border p-4 transition-colors hover:border-primary/30 sm:gap-4 sm:p-5 ${!notif.lida ? cfg.soft : 'bg-card'}`}
                    data-testid={`notificacao-${notif.id}`}
                  >
                    {/* Barra de acento (não lida) */}
                    {!notif.lida && <span className={`absolute inset-y-0 left-0 w-1 ${cfg.bar}`} />}

                    {/* Ícone */}
                    <span className={`flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl ${cfg.chip}`}>
                      <Icon className="h-5 w-5" />
                    </span>

                    {/* Conteúdo */}
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                        <h3 className={`text-sm font-semibold text-foreground ${!notif.lida ? '' : 'text-foreground/90'}`}>
                          {notif.titulo}
                        </h3>
                        {!notif.lida && <span className="h-2 w-2 flex-shrink-0 rounded-full bg-primary" title="Não lida" />}
                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${cfg.badge}`}>
                          {cfg.label}
                        </span>
                      </div>
                      <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{notif.mensagem}</p>
                      <div className="mt-2.5 flex items-center gap-3">
                        <span className="text-xs text-muted-foreground/80">{formatarDataHora(notif.created_at)}</span>
                        {!notif.lida && (
                          <button
                            onClick={() => marcarComoLida(notif.id)}
                            data-testid={`marcar-lida-${notif.id}`}
                            className="inline-flex items-center gap-1 text-xs font-medium text-primary transition-colors hover:text-primary/80"
                          >
                            <Check className="h-3.5 w-3.5" /> Marcar como lida
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Excluir */}
                    <button
                      onClick={() => excluirNotificacao(notif.id)}
                      title="Excluir notificação"
                      data-testid={`excluir-${notif.id}`}
                      className="flex-shrink-0 self-start rounded-lg p-2 text-muted-foreground/60 opacity-0 transition-all hover:bg-red-500/10 hover:text-red-500 focus:opacity-100 group-hover:opacity-100"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}

        {/* Como funcionam */}
        <div className="mt-8 rounded-2xl border border-border bg-card/60 p-5">
          <div className="mb-4 flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/12 text-primary">
              <Info className="h-4 w-4" />
            </span>
            <h3 className="font-display text-sm font-semibold text-foreground">Como funcionam as notificações</h3>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            {infoItens.map((it, idx) => (
              <div key={idx} className="flex items-start gap-2.5 rounded-xl border border-border/60 bg-background/50 p-3">
                <span className={`mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg ${it.cls}`}>
                  <it.Icon className="h-4 w-4" />
                </span>
                <div>
                  <p className="text-sm font-semibold text-foreground">{it.titulo}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{it.texto}</p>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            Use <span className="font-medium text-foreground">Verificar vencimentos</span> para atualizar os alertas manualmente a qualquer momento.
          </p>
        </div>
      </div>
    </Layout>
  );
};

export default Notificacoes;
