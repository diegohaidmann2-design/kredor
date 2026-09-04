import React, { useState, useEffect, useCallback, useMemo } from 'react';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import ErrorMessage from '../components/ErrorMessage';
import { useModal } from '../components/Modal';
import { parcelasAPI, whatsappAPI } from '../api/api';
import { formatarMoeda, formatarData } from '../utils/formatters';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  CalendarDays, ChevronLeft, ChevronRight, MessageCircle, AlertTriangle,
  CalendarClock, CalendarCheck, List, Grid3x3, ExternalLink, Send, Phone
} from 'lucide-react';

const MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
const DIAS_SEMANA = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

// Retorna chave YYYY-MM-DD (local) de uma data ISO
const dateKey = (iso) => {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};
const todayKey = () => dateKey(new Date().toISOString());

const valorDevido = (p) => (p.valor_total - p.valor_pago + (p.valor_multa || 0) + (p.valor_juros_mora || 0));

const Agenda = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isMember = !!user?.owner_id;
  const modal = useModal();

  const [parcelas, setParcelas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [view, setView] = useState('calendario'); // calendario | lista
  const [refDate, setRefDate] = useState(() => { const d = new Date(); d.setDate(1); return d; });
  const [diaSelecionado, setDiaSelecionado] = useState(todayKey());

  useEffect(() => { if (isMember) navigate('/dashboard'); }, [isMember, navigate]);

  const carregar = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const { data } = await parcelasAPI.listarPendentes();
      setParcelas(data || []);
    } catch (err) {
      console.error('Erro ao carregar agenda:', err);
      setError('Erro ao carregar agenda de cobrança');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  // Agrupar parcelas por dia (chave YYYY-MM-DD)
  const parcelasPorDia = useMemo(() => {
    const mapa = {};
    for (const p of parcelas) {
      if (!p.data_vencimento) continue;
      const k = dateKey(p.data_vencimento);
      (mapa[k] = mapa[k] || []).push(p);
    }
    return mapa;
  }, [parcelas]);

  const hoje = todayKey();

  // Buckets de resumo
  const resumo = useMemo(() => {
    const atrasadas = parcelas.filter(p => p.status === 'atrasado');
    const venceHoje = parcelas.filter(p => dateKey(p.data_vencimento) === hoje && p.status !== 'atrasado');
    const em7dias = parcelas.filter(p => {
      const k = dateKey(p.data_vencimento);
      if (p.status === 'atrasado' || k === hoje) return false;
      const diff = Math.round((new Date(k) - new Date(hoje)) / 86400000);
      return diff > 0 && diff <= 7;
    });
    const soma = (arr) => arr.reduce((s, p) => s + valorDevido(p), 0);
    return {
      atrasadas, venceHoje, em7dias,
      totalAtrasado: soma(atrasadas), totalHoje: soma(venceHoje), total7: soma(em7dias),
    };
  }, [parcelas, hoje]);

  // Dias do calendário (com preenchimento das semanas)
  const diasCalendario = useMemo(() => {
    const ano = refDate.getFullYear();
    const mes = refDate.getMonth();
    const primeiroDia = new Date(ano, mes, 1);
    const inicioGrade = new Date(primeiroDia);
    inicioGrade.setDate(inicioGrade.getDate() - primeiroDia.getDay()); // volta pro domingo
    const dias = [];
    for (let i = 0; i < 42; i++) {
      const d = new Date(inicioGrade);
      d.setDate(inicioGrade.getDate() + i);
      dias.push(d);
    }
    return dias;
  }, [refDate]);

  const mudarMes = (delta) => {
    setRefDate(prev => { const d = new Date(prev); d.setMonth(d.getMonth() + delta); return d; });
  };

  const irParaHoje = () => {
    const d = new Date(); d.setDate(1); setRefDate(d); setDiaSelecionado(hoje);
  };

  // Cobrar 1 parcela via WhatsApp
  const cobrarParcela = async (p) => {
    setEnviando(true);
    try {
      const resp = await whatsappAPI.enviarCobrancaParcela(p.id);
      const modo = resp.data?.modo;
      modal.success(modo === 'fila' ? '✅ Mensagem na fila!' : '✅ Mensagem enviada!',
        `Cobrança de ${p.cliente_nome} ${modo === 'fila' ? 'será enviada em instantes.' : 'enviada com sucesso.'}`);
      carregar();
    } catch (err) {
      const status = err.response?.status;
      const msg = err.response?.data?.detail || 'Erro ao enviar mensagem';
      if (status === 503) modal.error('❌ WhatsApp não conectado', 'Conecte seu WhatsApp em WhatsApp > Conexões e tente novamente.');
      else modal.error('❌ Erro ao enviar', msg);
    } finally {
      setEnviando(false);
    }
  };

  // Cobrar todas as parcelas de um conjunto (dia / bucket)
  const cobrarLote = async (lista, titulo) => {
    const ids = lista.map(p => p.id);
    if (ids.length === 0) return;
    const ok = await modal.confirm(
      `Cobrar ${titulo}`,
      `Enviar cobrança via WhatsApp para ${ids.length} parcela(s)?`,
      'As mensagens serão enviadas em fila respeitando o anti-spam.'
    );
    if (!ok) return;
    setEnviando(true);
    try {
      const { data } = await parcelasAPI.cobrarEmMassa(ids);
      modal.success('✅ Cobranças disparadas',
        `${data.enviadas} enviada(s)${data.falhas > 0 ? ` • ${data.falhas} falha(s)` : ''}.`);
      carregar();
    } catch (err) {
      modal.error('Erro na cobrança em massa', err.response?.data?.detail || 'Falha ao processar lote.');
    } finally {
      setEnviando(false);
    }
  };

  // Link direto wa.me (fallback manual)
  const abrirWhatsAppDireto = (p) => {
    const tel = (p.cliente_telefone || '').replace(/\D/g, '');
    if (!tel) { modal.error('Sem telefone', 'Este cliente não possui telefone cadastrado.'); return; }
    const numero = tel.startsWith('55') ? tel : `55${tel}`;
    const texto = encodeURIComponent(
      `Olá ${p.cliente_nome}, tudo bem? Passando para lembrar da parcela ${p.numero_parcela}/${p.total_parcelas || '∞'} ` +
      `no valor de ${formatarMoeda(valorDevido(p))} com vencimento em ${formatarData(p.data_vencimento)}.`
    );
    window.open(`https://wa.me/${numero}?text=${texto}`, '_blank');
  };

  const parcelasDoDia = parcelasPorDia[diaSelecionado] || [];

  if (loading) return <Loading message="Carregando agenda..." />;

  const mesLabel = `${MESES[refDate.getMonth()]} ${refDate.getFullYear()}`;

  return (
    <Layout>
      {enviando && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-card rounded-lg p-8 shadow-2xl border border-border max-w-sm mx-4">
            <div className="flex flex-col items-center gap-4">
              <div className="w-14 h-14 border-4 border-primary/30 border-t-primary rounded-full animate-spin"></div>
              <p className="text-sm text-muted-foreground">Enviando cobrança via WhatsApp...</p>
            </div>
          </div>
        </div>
      )}

      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground flex items-center gap-2" data-testid="agenda-title">
              <CalendarDays className="w-7 h-7 text-primary" /> Agenda de Cobrança
            </h1>
            <p className="text-muted-foreground mt-1">Veja quem vence hoje, quem está atrasado e cobre com 1 clique</p>
          </div>
          <div className="flex items-center gap-1 bg-muted/40 rounded-lg p-1 self-start">
            <button
              onClick={() => setView('calendario')}
              className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-colors ${view === 'calendario' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
              data-testid="view-calendario"
            >
              <Grid3x3 className="w-4 h-4" /> Calendário
            </button>
            <button
              onClick={() => setView('lista')}
              className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-colors ${view === 'lista' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'}`}
              data-testid="view-lista"
            >
              <List className="w-4 h-4" /> Lista
            </button>
          </div>
        </div>

        {error && <ErrorMessage message={error} onRetry={carregar} />}

        {/* Cards de resumo (buckets) */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <button
            onClick={() => resumo.atrasadas.length && cobrarLote(resumo.atrasadas, 'Atrasadas')}
            className="text-left bg-card rounded-xl border border-red-500/30 p-4 hover:border-red-500/60 transition-colors group"
            data-testid="bucket-atrasadas"
          >
            <div className="flex items-center justify-between mb-1">
              <p className="text-sm text-muted-foreground flex items-center gap-1.5"><AlertTriangle className="w-4 h-4 text-red-500" /> Atrasadas</p>
              <span className="text-2xl font-bold text-red-500">{resumo.atrasadas.length}</span>
            </div>
            <p className="text-lg font-bold text-foreground">{formatarMoeda(resumo.totalAtrasado)}</p>
            {resumo.atrasadas.length > 0 && (
              <span className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-red-500 opacity-70 group-hover:opacity-100">
                <MessageCircle className="w-3 h-3" /> Cobrar todas
              </span>
            )}
          </button>

          <button
            onClick={() => resumo.venceHoje.length && cobrarLote(resumo.venceHoje, 'Vencem hoje')}
            className="text-left bg-card rounded-xl border border-amber-500/30 p-4 hover:border-amber-500/60 transition-colors group"
            data-testid="bucket-hoje"
          >
            <div className="flex items-center justify-between mb-1">
              <p className="text-sm text-muted-foreground flex items-center gap-1.5"><CalendarClock className="w-4 h-4 text-amber-500" /> Vencem hoje</p>
              <span className="text-2xl font-bold text-amber-500">{resumo.venceHoje.length}</span>
            </div>
            <p className="text-lg font-bold text-foreground">{formatarMoeda(resumo.totalHoje)}</p>
            {resumo.venceHoje.length > 0 && (
              <span className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-amber-500 opacity-70 group-hover:opacity-100">
                <MessageCircle className="w-3 h-3" /> Cobrar todas
              </span>
            )}
          </button>

          <button
            onClick={() => resumo.em7dias.length && cobrarLote(resumo.em7dias, 'Próximos 7 dias')}
            className="text-left bg-card rounded-xl border border-blue-500/30 p-4 hover:border-blue-500/60 transition-colors group"
            data-testid="bucket-7dias"
          >
            <div className="flex items-center justify-between mb-1">
              <p className="text-sm text-muted-foreground flex items-center gap-1.5"><CalendarCheck className="w-4 h-4 text-blue-500" /> Próximos 7 dias</p>
              <span className="text-2xl font-bold text-blue-500">{resumo.em7dias.length}</span>
            </div>
            <p className="text-lg font-bold text-foreground">{formatarMoeda(resumo.total7)}</p>
            {resumo.em7dias.length > 0 && (
              <span className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-blue-500 opacity-70 group-hover:opacity-100">
                <MessageCircle className="w-3 h-3" /> Cobrar todas
              </span>
            )}
          </button>
        </div>

        {view === 'calendario' ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Calendário */}
            <div className="lg:col-span-2 bg-card rounded-xl border border-border p-4" data-testid="calendario">
              <div className="flex items-center justify-between mb-4">
                <button onClick={() => mudarMes(-1)} className="p-2 rounded-lg hover:bg-muted transition-colors" data-testid="mes-anterior">
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <div className="flex items-center gap-3">
                  <h2 className="text-lg font-semibold text-foreground capitalize" data-testid="mes-label">{mesLabel}</h2>
                  <button onClick={irParaHoje} className="text-xs px-2 py-1 rounded-md bg-primary/10 text-primary font-medium hover:bg-primary/20 transition-colors" data-testid="btn-hoje">Hoje</button>
                </div>
                <button onClick={() => mudarMes(1)} className="p-2 rounded-lg hover:bg-muted transition-colors" data-testid="mes-proximo">
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>

              <div className="grid grid-cols-7 gap-1 mb-1">
                {DIAS_SEMANA.map(d => (
                  <div key={d} className="text-center text-xs font-medium text-muted-foreground py-1">{d}</div>
                ))}
              </div>

              <div className="grid grid-cols-7 gap-1">
                {diasCalendario.map((d, i) => {
                  const k = dateKey(d);
                  const doMes = d.getMonth() === refDate.getMonth();
                  const lista = parcelasPorDia[k] || [];
                  const temAtraso = lista.some(p => p.status === 'atrasado');
                  const isHoje = k === hoje;
                  const isSel = k === diaSelecionado;
                  const total = lista.reduce((s, p) => s + valorDevido(p), 0);
                  return (
                    <button
                      key={i}
                      onClick={() => setDiaSelecionado(k)}
                      className={`relative min-h-[64px] p-1.5 rounded-lg border text-left transition-colors flex flex-col
                        ${isSel ? 'border-primary bg-primary/10' : 'border-transparent hover:bg-muted/50'}
                        ${!doMes ? 'opacity-40' : ''}`}
                      data-testid={`dia-${k}`}
                    >
                      <span className={`text-xs font-medium ${isHoje ? 'w-5 h-5 flex items-center justify-center rounded-full bg-primary text-primary-foreground' : 'text-foreground'}`}>
                        {d.getDate()}
                      </span>
                      {lista.length > 0 && (
                        <div className="mt-auto space-y-0.5">
                          <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold ${temAtraso ? 'bg-red-500/15 text-red-500' : 'bg-blue-500/15 text-blue-500'}`}>
                            {lista.length} {lista.length === 1 ? 'parc.' : 'parc.'}
                          </span>
                          <p className="text-[9px] text-muted-foreground truncate leading-tight">{formatarMoeda(total)}</p>
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Painel do dia selecionado */}
            <div className="bg-card rounded-xl border border-border p-4" data-testid="painel-dia">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-xs text-muted-foreground">Dia selecionado</p>
                  <h3 className="text-lg font-semibold text-foreground">{formatarData(diaSelecionado)}</h3>
                </div>
                {parcelasDoDia.length > 0 && (
                  <button
                    onClick={() => cobrarLote(parcelasDoDia, `dia ${formatarData(diaSelecionado)}`)}
                    className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20 transition-colors"
                    data-testid="btn-cobrar-dia"
                  >
                    <Send className="w-3.5 h-3.5" /> Cobrar dia
                  </button>
                )}
              </div>
              {parcelasDoDia.length === 0 ? (
                <div className="py-12 text-center text-sm text-muted-foreground" data-testid="dia-vazio">
                  Nenhuma cobrança neste dia.
                </div>
              ) : (
                <div className="space-y-2 max-h-[520px] overflow-y-auto scrollbar-thin pr-1">
                  {parcelasDoDia.map(p => <ParcelaCard key={p.id} p={p} onCobrar={cobrarParcela} onWaDireto={abrirWhatsAppDireto} navigate={navigate} />)}
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Visão em lista por período */
          <div className="space-y-6">
            <BucketLista titulo="⚠️ Atrasadas" cor="red" lista={resumo.atrasadas} onCobrarLote={() => cobrarLote(resumo.atrasadas, 'Atrasadas')} onCobrar={cobrarParcela} onWaDireto={abrirWhatsAppDireto} navigate={navigate} testId="lista-atrasadas" />
            <BucketLista titulo="🔥 Vencem hoje" cor="amber" lista={resumo.venceHoje} onCobrarLote={() => cobrarLote(resumo.venceHoje, 'Vencem hoje')} onCobrar={cobrarParcela} onWaDireto={abrirWhatsAppDireto} navigate={navigate} testId="lista-hoje" />
            <BucketLista titulo="📅 Próximos 7 dias" cor="blue" lista={resumo.em7dias} onCobrarLote={() => cobrarLote(resumo.em7dias, 'Próximos 7 dias')} onCobrar={cobrarParcela} onWaDireto={abrirWhatsAppDireto} navigate={navigate} testId="lista-7dias" />
          </div>
        )}
      </div>
    </Layout>
  );
};

// Card de parcela individual
const ParcelaCard = ({ p, onCobrar, onWaDireto, navigate }) => {
  const atrasado = p.status === 'atrasado';
  return (
    <div className="rounded-lg border border-border/60 bg-muted/20 p-3" data-testid={`parcela-card-${p.id}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-foreground truncate">{p.cliente_nome || 'Cliente'}</p>
          <p className="text-xs text-muted-foreground flex items-center gap-1"><Phone className="w-3 h-3" /> {p.cliente_telefone || 'sem telefone'}</p>
          <div className="mt-1 flex items-center gap-2 flex-wrap">
            <span className="text-sm font-bold text-foreground">{formatarMoeda(valorDevido(p))}</span>
            <span className="text-[11px] text-muted-foreground">parc. {p.numero_parcela}/{p.total_parcelas || '∞'}</span>
            {atrasado && <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-red-500/10 text-red-500">{p.dias_atraso}d atraso</span>}
          </div>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-1.5">
        <button
          onClick={() => onCobrar(p)}
          className="flex-1 inline-flex items-center justify-center gap-1 px-2 py-1.5 rounded-md text-xs font-medium bg-green-500/10 text-green-600 dark:text-green-400 hover:bg-green-500/20 transition-colors"
          data-testid={`btn-cobrar-${p.id}`}
          title="Enviar cobrança pelo WhatsApp conectado"
        >
          <MessageCircle className="w-3.5 h-3.5" /> Cobrar
        </button>
        <button
          onClick={() => onWaDireto(p)}
          className="inline-flex items-center justify-center px-2 py-1.5 rounded-md text-xs font-medium bg-muted hover:bg-muted/70 text-muted-foreground transition-colors"
          data-testid={`btn-wa-direto-${p.id}`}
          title="Abrir conversa no WhatsApp"
        >
          <ExternalLink className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => navigate(`/emprestimos/${p.emprestimo_id}`)}
          className="inline-flex items-center justify-center px-2 py-1.5 rounded-md text-xs font-medium bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
          data-testid={`btn-ver-emprestimo-${p.id}`}
          title="Ver empréstimo"
        >
          Ver
        </button>
      </div>
    </div>
  );
};

// Bloco de lista por bucket
const BucketLista = ({ titulo, cor, lista, onCobrarLote, onCobrar, onWaDireto, navigate, testId }) => {
  const total = lista.reduce((s, p) => s + valorDevido(p), 0);
  const borda = { red: 'border-red-500/30', amber: 'border-amber-500/30', blue: 'border-blue-500/30' }[cor];
  return (
    <div className={`bg-card rounded-xl border ${borda}`} data-testid={testId}>
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div>
          <h2 className="text-base font-semibold text-foreground">{titulo}</h2>
          <p className="text-xs text-muted-foreground">{lista.length} parcela(s) • {formatarMoeda(total)}</p>
        </div>
        {lista.length > 0 && (
          <button
            onClick={onCobrarLote}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20 transition-colors"
            data-testid={`${testId}-cobrar-todas`}
          >
            <Send className="w-3.5 h-3.5" /> Cobrar todas
          </button>
        )}
      </div>
      {lista.length === 0 ? (
        <div className="p-6 text-center text-sm text-muted-foreground">Nada aqui 🎉</div>
      ) : (
        <div className="p-3 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2">
          {lista.map(p => <ParcelaCard key={p.id} p={p} onCobrar={onCobrar} onWaDireto={onWaDireto} navigate={navigate} />)}
        </div>
      )}
    </div>
  );
};

export default Agenda;
