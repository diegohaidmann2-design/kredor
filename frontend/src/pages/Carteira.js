import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { QRCodeCanvas } from 'qrcode.react';
import { carteiraAPI } from '../api/api';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import {
  Wallet, Plus, Zap, ArrowUpRight, ArrowDownRight, Gift, RefreshCw,
  CircleDollarSign, ShieldAlert, Copy, Check, Loader2, X, ClipboardCopy,
  Sparkles, TrendingDown, Receipt, QrCode, IdCard, Building, Phone, User,
  ScanFace, ChevronsUpDown, Bell, BellOff, Save, Info
} from 'lucide-react';

const money = (v) => `R$ ${Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const dt = (iso) => {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }); }
  catch { return iso; }
};

const TIPO_META = {
  cpf: { label: 'CPF', icon: IdCard },
  cnpj: { label: 'CNPJ', icon: Building },
  telefone: { label: 'Telefone', icon: Phone },
  nome: { label: 'Nome', icon: User },
  'cpf-dividas': { label: 'Dívidas CPF', icon: ShieldAlert },
  'cnpj-dividas': { label: 'Dívidas CNPJ', icon: ShieldAlert },
  facial: { label: 'Facial', icon: ScanFace },
};

const MOV_META = {
  recarga: { label: 'Recarga', color: 'text-emerald-500', bg: 'bg-emerald-500/10', icon: ArrowUpRight },
  consumo: { label: 'Consulta', color: 'text-rose-500', bg: 'bg-rose-500/10', icon: TrendingDown },
  bonus: { label: 'Bônus', color: 'text-amber-500', bg: 'bg-amber-500/10', icon: Gift },
  ajuste: { label: 'Ajuste', color: 'text-blue-500', bg: 'bg-blue-500/10', icon: Zap },
  estorno: { label: 'Estorno', color: 'text-purple-500', bg: 'bg-purple-500/10', icon: RefreshCw },
};

const PACOTES = [
  { valor: 20, destaque: null },
  { valor: 50, destaque: 'Mais popular' },
  { valor: 100, destaque: 'Melhor custo' },
  { valor: 200, destaque: null },
];

// ---------- Modal de Recarga ----------
const ModalRecarga = ({ open, onClose, gateways, onSuccess }) => {
  const [valor, setValor] = useState(50);
  const [customValor, setCustomValor] = useState('');
  const [gateway, setGateway] = useState('asaas');
  const [loading, setLoading] = useState(false);
  const [pix, setPix] = useState(null);
  const [recargaId, setRecargaId] = useState(null);
  const [copiado, setCopiado] = useState(false);
  const [pooling, setPooling] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) { setPix(null); setRecargaId(null); setError(''); setCopiado(false); setPooling(false); return; }
    // Selecionar primeiro gateway disponível
    if (gateways?.asaas) setGateway('asaas');
    else if (gateways?.syncpay) setGateway('syncpay');
  }, [open, gateways]);

  // Polling do status
  useEffect(() => {
    if (!recargaId || !pix) return;
    setPooling(true);
    let ativo = true;
    const iv = setInterval(async () => {
      try {
        const { data } = await carteiraAPI.statusRecarga(recargaId);
        if (data.status === 'paid') {
          setPooling(false);
          clearInterval(iv);
          if (ativo) { onSuccess?.(); onClose(); }
        }
      } catch {}
    }, 4000);
    return () => { ativo = false; setPooling(false); clearInterval(iv); };
  }, [recargaId, pix, onSuccess, onClose]);

  const valorFinal = customValor ? Number(customValor) : valor;

  const gerarPix = async () => {
    setError('');
    if (!valorFinal || valorFinal < 5) return setError('Valor mínimo de recarga: R$ 5,00');
    if (valorFinal > 5000) return setError('Valor máximo de recarga: R$ 5.000,00');
    setLoading(true);
    try {
      const api = gateway === 'syncpay' ? carteiraAPI.recargaSyncpay : carteiraAPI.recargaAsaas;
      const { data } = await api(valorFinal);
      setPix(data.pix || {});
      setRecargaId(data.recarga_id);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Erro ao gerar cobrança PIX. Tente novamente.');
    } finally { setLoading(false); }
  };

  const copiar = async () => {
    const codigo = pix?.payload;
    if (!codigo) return;
    try { await navigator.clipboard.writeText(codigo); setCopiado(true); setTimeout(() => setCopiado(false), 2000); } catch {}
  };

  if (!open) return null;

  const gatewaysDisponiveis = [];
  if (gateways?.asaas) gatewaysDisponiveis.push({ id: 'asaas', label: 'Asaas PIX' });
  if (gateways?.syncpay) gatewaysDisponiveis.push({ id: 'syncpay', label: 'SyncPay PIX' });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" data-testid="modal-recarga">
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
        className="bg-card border border-border rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <Zap className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="font-display font-bold text-lg text-foreground">Recarregar Carteira</h3>
              <p className="text-xs text-muted-foreground">Adicione saldo para usar consultas</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-sidebar-accent" data-testid="modal-recarga-fechar">
            <X className="w-5 h-5 text-muted-foreground" />
          </button>
        </div>

        {!pix ? (
          <div className="p-6 space-y-5">
            {gatewaysDisponiveis.length === 0 && (
              <div className="flex items-start gap-3 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-600 text-sm">
                <ShieldAlert className="w-5 h-5 mt-0.5 flex-shrink-0" />
                <span>Nenhum gateway de pagamento habilitado. Contate o administrador do sistema.</span>
              </div>
            )}
            {gatewaysDisponiveis.length > 1 && (
              <div>
                <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-2">Gateway</p>
                <div className="grid grid-cols-2 gap-2">
                  {gatewaysDisponiveis.map((gw) => (
                    <button key={gw.id} onClick={() => setGateway(gw.id)} data-testid={`gateway-${gw.id}`}
                      className={`px-3 py-2.5 rounded-lg border text-sm font-medium transition-all ${
                        gateway === gw.id ? 'border-primary bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:border-primary/50'
                      }`}>{gw.label}</button>
                  ))}
                </div>
              </div>
            )}

            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-2">Escolha um pacote</p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 gap-y-4 mt-3">
                {PACOTES.map((p) => (
                  <button key={p.valor} onClick={() => { setValor(p.valor); setCustomValor(''); }}
                    data-testid={`pacote-${p.valor}`}
                    className={`relative px-3 py-3 rounded-xl border text-center transition-all ${
                      !customValor && valor === p.valor
                        ? 'border-primary bg-primary/10 shadow-lg shadow-primary/10'
                        : 'border-border hover:border-primary/50'
                    }`}>
                    {p.destaque && (
                      <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] leading-none px-2 py-1 rounded-full bg-amber-500 text-amber-950 font-bold shadow-md">
                        {p.destaque}
                      </span>
                    )}
                    <p className="font-display font-bold text-foreground">{money(p.valor)}</p>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-2">Ou valor personalizado</p>
              <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg bg-background border border-border focus-within:ring-2 focus-within:ring-primary/40">
                <span className="text-muted-foreground">R$</span>
                <input type="number" min="5" max="5000" step="0.01" inputMode="decimal"
                  value={customValor} onChange={(e) => setCustomValor(e.target.value)}
                  placeholder="Ex.: 30,00" data-testid="input-valor-custom"
                  className="flex-1 bg-transparent outline-none text-foreground"/>
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-500 text-sm" data-testid="recarga-erro">
                {error}
              </div>
            )}

            <div className="pt-2">
              <button onClick={gerarPix} disabled={loading || gatewaysDisponiveis.length === 0}
                data-testid="btn-gerar-pix"
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-primary text-primary-foreground font-semibold text-sm hover:opacity-90 disabled:opacity-50 shadow-lg shadow-primary/20">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <QrCode className="w-4 h-4" />}
                Gerar PIX de {money(valorFinal || 0)}
              </button>
            </div>
          </div>
        ) : (
          <div className="p-6 space-y-4">
            <div className="text-center">
              <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Aguardando pagamento</p>
              <p className="text-3xl font-display font-bold text-foreground mt-1">{money(valorFinal)}</p>
            </div>
            {pix.qrcode_image ? (
              <div className="flex justify-center">
                <img src={`data:image/png;base64,${pix.qrcode_image}`} alt="QR Code PIX" className="w-56 h-56 rounded-xl border-4 border-white bg-white" />
              </div>
            ) : pix.payload ? (
              <div className="flex justify-center" data-testid="pix-qrcode">
                <div className="p-3 rounded-xl bg-white">
                  <QRCodeCanvas value={pix.payload} size={200} level="M" includeMargin={false} />
                </div>
              </div>
            ) : null}
            <div>
              <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-2">Ou copie o código PIX</p>
              <div className="flex items-center gap-2">
                <textarea readOnly value={pix.payload || ''} rows={2}
                  className="flex-1 px-3 py-2 rounded-lg bg-background border border-border text-foreground text-xs font-mono resize-none"
                  data-testid="pix-payload"/>
                <button onClick={copiar} data-testid="btn-copiar-pix"
                  className="p-2.5 rounded-lg border border-border hover:bg-sidebar-accent">
                  {copiado ? <Check className="w-4 h-4 text-emerald-500" /> : <ClipboardCopy className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              {pooling && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
              <span>Assim que o PIX for confirmado, seu saldo será atualizado automaticamente.</span>
            </div>
            <button onClick={onClose} className="w-full px-4 py-2.5 rounded-lg border border-border text-foreground text-sm">
              Fechar
            </button>
          </div>
        )}
      </motion.div>
    </div>
  );
};

// ---------- Card de Alerta de Saldo ----------
const CardAlerta = ({ carteira, onSaved }) => {
  const [minimo, setMinimo] = useState(carteira?.alerta_saldo_minimo ?? 10);
  const [emailOn, setEmailOn] = useState(carteira?.alerta_email_habilitado ?? true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    setMinimo(carteira?.alerta_saldo_minimo ?? 10);
    setEmailOn(carteira?.alerta_email_habilitado ?? true);
  }, [carteira]);

  const salvar = async () => {
    setSaving(true); setMsg('');
    try {
      await carteiraAPI.configurarAlerta({ saldo_minimo: Number(minimo), email_habilitado: emailOn });
      setMsg('Configuração salva!');
      onSaved?.();
      setTimeout(() => setMsg(''), 2500);
    } catch (e) {
      setMsg(e?.response?.data?.detail || 'Erro ao salvar');
    } finally { setSaving(false); }
  };

  const desativar = async () => {
    setMinimo(0);
    setSaving(true); setMsg('');
    try {
      await carteiraAPI.configurarAlerta({ saldo_minimo: 0, email_habilitado: emailOn });
      setMsg('Alerta desativado');
      onSaved?.();
      setTimeout(() => setMsg(''), 2500);
    } catch (e) {
      setMsg(e?.response?.data?.detail || 'Erro');
    } finally { setSaving(false); }
  };

  const ativo = Number(minimo || 0) > 0;

  return (
    <div className="p-6 rounded-2xl bg-card border border-border" data-testid="card-alerta">
      <div className="flex items-start justify-between gap-3 mb-4 flex-wrap">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${ativo ? 'bg-amber-500/15' : 'bg-sidebar-accent'}`}>
            {ativo ? <Bell className="w-5 h-5 text-amber-500" /> : <BellOff className="w-5 h-5 text-muted-foreground" />}
          </div>
          <div>
            <h2 className="font-display font-bold text-lg text-foreground">Alerta de saldo baixo</h2>
            <p className="text-xs text-muted-foreground">Avisamos antes que suas consultas travem</p>
          </div>
        </div>
        <span className={`text-xs px-2 py-1 rounded-md font-semibold ${ativo ? 'bg-emerald-500/15 text-emerald-500' : 'bg-muted text-muted-foreground'}`}>
          {ativo ? 'ATIVO' : 'DESATIVADO'}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
        <div className="md:col-span-1">
          <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-2">Avisar quando saldo ficar abaixo de</p>
          <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg bg-background border border-border focus-within:ring-2 focus-within:ring-primary/40">
            <span className="text-muted-foreground text-sm">R$</span>
            <input type="number" min="0" max="10000" step="0.01" value={minimo}
              onChange={(e) => setMinimo(e.target.value)} data-testid="alerta-input-minimo"
              className="flex-1 bg-transparent outline-none text-foreground font-mono" />
          </div>
          <p className="text-[11px] text-muted-foreground mt-1">Zero desativa o alerta</p>
        </div>

        <label className="flex items-center gap-3 p-3 rounded-lg border border-border cursor-pointer hover:bg-sidebar-accent">
          <input type="checkbox" checked={emailOn} onChange={(e) => setEmailOn(e.target.checked)}
            data-testid="alerta-email-toggle" className="accent-primary w-4 h-4" />
          <div>
            <p className="text-sm font-medium text-foreground">Também enviar por e-mail</p>
            <p className="text-xs text-muted-foreground">Sino + e-mail (snooze de 24h)</p>
          </div>
        </label>

        <div className="flex gap-2">
          <button onClick={salvar} disabled={saving} data-testid="alerta-salvar"
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:opacity-90 disabled:opacity-50">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Salvar
          </button>
          {ativo && (
            <button onClick={desativar} disabled={saving} data-testid="alerta-desativar"
              className="px-3 py-2.5 rounded-lg border border-border text-sm text-muted-foreground hover:text-foreground">
              Desativar
            </button>
          )}
        </div>
      </div>

      {msg && (
        <div className="mt-4 flex items-center gap-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-500 text-sm" data-testid="alerta-msg">
          <Check className="w-4 h-4" /> {msg}
        </div>
      )}
    </div>
  );
};

// ---------- Página Carteira ----------
const Carteira = () => {
  const [loading, setLoading] = useState(true);
  const [resumo, setResumo] = useState(null);
  const [gateways, setGateways] = useState(null);
  const [showRecarga, setShowRecarga] = useState(false);
  const [tab, setTab] = useState('todos');
  const [movs, setMovs] = useState([]);
  const [loadingMovs, setLoadingMovs] = useState(false);

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const [{ data: r }, { data: gw }] = await Promise.all([
        carteiraAPI.resumo(),
        carteiraAPI.gateways(),
      ]);
      setResumo(r);
      setGateways(gw);
    } catch (e) { /* silencioso */ }
    finally { setLoading(false); }
  }, []);

  const carregarMovs = useCallback(async (tipo) => {
    setLoadingMovs(true);
    try {
      const params = tipo && tipo !== 'todos' ? { tipo, limit: 100 } : { limit: 100 };
      const { data } = await carteiraAPI.movimentos(params);
      setMovs(data.itens || []);
    } catch { setMovs([]); } finally { setLoadingMovs(false); }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);
  useEffect(() => { carregarMovs(tab); }, [tab, carregarMovs]);

  const saldo = resumo?.carteira?.saldo || 0;
  const totalRecargas = resumo?.carteira?.total_recargas || 0;
  const totalConsumo = resumo?.carteira?.total_consumo || 0;

  return (
    <Layout>
      <div className="p-4 sm:p-6 space-y-4 sm:space-y-6" data-testid="carteira-page">
        {/* Header */}
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs px-2 py-0.5 rounded-md bg-amber-500/20 text-amber-500 font-bold tracking-wider">PRO</span>
              <span className="text-xs text-muted-foreground uppercase tracking-wider">Consultas Premium</span>
            </div>
            <h1 className="font-display font-bold text-3xl text-foreground tracking-tight">Carteira</h1>
            <p className="text-sm text-muted-foreground mt-1">Recarregue e acompanhe cada consulta realizada</p>
          </div>
          <button onClick={() => setShowRecarga(true)} data-testid="btn-recarregar"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-semibold text-sm hover:opacity-90 shadow-lg shadow-primary/20">
            <Plus className="w-4 h-4" /> Recarregar
          </button>
        </div>

        {loading ? <Loading /> : (
          <>
            {/* Cards resumo */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <motion.div initial={{ y: 8, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
                className="relative overflow-hidden p-6 rounded-2xl bg-gradient-to-br from-primary/20 via-primary/10 to-transparent border border-primary/30">
                <div className="absolute -right-4 -top-4 opacity-10">
                  <Wallet className="w-32 h-32 text-primary" />
                </div>
                <div className="relative">
                  <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">Saldo disponível</p>
                  <p className="text-4xl font-display font-bold text-foreground mt-2" data-testid="carteira-saldo">{money(saldo)}</p>
                  <p className="text-xs text-muted-foreground mt-2">Atualizado {dt(resumo?.carteira?.updated_at)}</p>
                </div>
              </motion.div>

              <div className="p-6 rounded-2xl bg-card border border-border">
                <div className="flex items-center gap-2 text-emerald-500 mb-2">
                  <ArrowUpRight className="w-4 h-4" />
                  <p className="text-xs uppercase tracking-wider font-semibold">Total recarregado</p>
                </div>
                <p className="text-2xl font-display font-bold text-foreground">{money(totalRecargas)}</p>
                <p className="text-xs text-muted-foreground mt-1">Somando bônus e recargas</p>
              </div>

              <div className="p-6 rounded-2xl bg-card border border-border">
                <div className="flex items-center gap-2 text-rose-500 mb-2">
                  <ArrowDownRight className="w-4 h-4" />
                  <p className="text-xs uppercase tracking-wider font-semibold">Total em consultas</p>
                </div>
                <p className="text-2xl font-display font-bold text-foreground">{money(totalConsumo)}</p>
                <p className="text-xs text-muted-foreground mt-1">Consumo acumulado</p>
              </div>
            </div>

            {/* Card de Alerta de Saldo */}
            <CardAlerta carteira={resumo?.carteira} onSaved={carregar} />

            {/* Tabela de preços */}
            <div className="p-6 rounded-2xl bg-card border border-border">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="font-display font-bold text-lg text-foreground">Preços por consulta</h2>
                  <p className="text-xs text-muted-foreground">Valor descontado da carteira a cada consulta</p>
                </div>
                <Sparkles className="w-5 h-5 text-amber-500" />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
                {(resumo?.precos || []).map((p) => {
                  const meta = TIPO_META[p.tipo] || { label: p.tipo, icon: Receipt };
                  const Icon = meta.icon;
                  const suficiente = saldo >= p.valor;
                  return (
                    <div key={p.tipo} data-testid={`preco-${p.tipo}`}
                      className={`p-3 rounded-xl border ${suficiente ? 'border-border' : 'border-rose-500/30 bg-rose-500/5'}`}>
                      <div className="flex items-center gap-2 mb-2">
                        <Icon className="w-4 h-4 text-muted-foreground" />
                        <p className="text-xs font-medium text-foreground truncate">{p.label || meta.label}</p>
                      </div>
                      <p className="font-display font-bold text-lg text-foreground">{money(p.valor)}</p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Movimentos */}
            <div className="p-6 rounded-2xl bg-card border border-border">
              <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
                <div>
                  <h2 className="font-display font-bold text-lg text-foreground">Movimentações</h2>
                  <p className="text-xs text-muted-foreground">Histórico de recargas, consultas e ajustes</p>
                </div>
                <div className="flex flex-wrap gap-1 p-1 rounded-lg bg-background border border-border">
                  {['todos', 'consumo', 'recarga', 'bonus', 'ajuste', 'estorno'].map((t) => (
                    <button key={t} onClick={() => setTab(t)} data-testid={`tab-${t}`}
                      className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all capitalize ${
                        tab === t ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'
                      }`}>{t === 'todos' ? 'Todos' : (MOV_META[t]?.label || t)}</button>
                  ))}
                </div>
              </div>

              {loadingMovs ? (
                <div className="py-8 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>
              ) : movs.length === 0 ? (
                <div className="py-10 text-center">
                  <Receipt className="w-10 h-10 text-muted-foreground/50 mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">Nenhuma movimentação encontrada</p>
                </div>
              ) : (
                <div className="divide-y divide-border">
                  {movs.map((m) => {
                    const meta = MOV_META[m.tipo] || { label: m.tipo, color: 'text-foreground', bg: 'bg-sidebar-accent', icon: Receipt };
                    const Icon = meta.icon;
                    return (
                      <div key={m.id} className="flex items-center gap-3 py-3" data-testid={`mov-${m.id}`}>
                        <div className={`w-10 h-10 rounded-xl ${meta.bg} flex items-center justify-center flex-shrink-0`}>
                          <Icon className={`w-5 h-5 ${meta.color}`} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-foreground truncate">{m.descricao}</p>
                          <p className="text-xs text-muted-foreground">{dt(m.created_at)} · {meta.label}</p>
                        </div>
                        <div className="text-right">
                          <p className={`font-display font-bold text-sm ${m.valor > 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                            {m.valor > 0 ? '+' : ''}{money(m.valor)}
                          </p>
                          <p className="text-[11px] text-muted-foreground">Saldo: {money(m.saldo_depois)}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </>
        )}
      </div>

      <ModalRecarga open={showRecarga} onClose={() => setShowRecarga(false)}
        gateways={gateways} onSuccess={carregar} />
    </Layout>
  );
};

export default Carteira;
