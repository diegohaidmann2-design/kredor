import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { adminCarteirasAPI } from '../api/api';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import {
  Wallet, DollarSign, Users, TrendingUp, TrendingDown, Search, Save,
  Zap, Edit, X, Check, Loader2, RefreshCw, ArrowUpRight, ArrowDownRight,
  Filter, Eye, AlertCircle
} from 'lucide-react';
import { toast } from '../hooks/use-toast';

const money = (v) => `R$ ${Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const dt = (iso) => { if (!iso) return '—'; try { return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }); } catch { return iso; } };

// ---------- Modal Ajuste ----------
const ModalAjuste = ({ open, onClose, carteira, onSaved }) => {
  const [tipo, setTipo] = useState('credito');
  const [valor, setValor] = useState('');
  const [motivo, setMotivo] = useState('');
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => { if (open) { setTipo('credito'); setValor(''); setMotivo(''); setErr(''); } }, [open]);

  if (!open) return null;
  const submit = async () => {
    setErr('');
    const v = Number(valor);
    if (!v || v <= 0) return setErr('Informe um valor maior que zero.');
    if (motivo.trim().length < 3) return setErr('Descreva o motivo (mínimo 3 caracteres).');
    setLoading(true);
    try {
      await adminCarteirasAPI.ajuste(carteira.owner_id, {
        valor: tipo === 'credito' ? v : -v,
        motivo: motivo.trim(),
      });
      onSaved?.();
      onClose();
    } catch (e) {
      setErr(e?.response?.data?.detail || 'Erro ao aplicar ajuste');
    } finally { setLoading(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" data-testid="modal-ajuste">
      <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
        className="bg-card border border-border rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <h3 className="font-display font-bold text-lg text-foreground">Ajustar saldo</h3>
            <p className="text-xs text-muted-foreground truncate max-w-[280px]">{carteira?.dono?.email}</p>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-sidebar-accent"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-6 space-y-4">
          <div className="p-3 rounded-lg bg-sidebar-accent">
            <p className="text-xs text-muted-foreground">Saldo atual</p>
            <p className="font-display font-bold text-xl text-foreground">{money(carteira?.saldo || 0)}</p>
          </div>

          <div>
            <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-2">Tipo</p>
            <div className="grid grid-cols-2 gap-2">
              <button onClick={() => setTipo('credito')} data-testid="ajuste-tipo-credito"
                className={`px-3 py-2 rounded-lg border font-medium text-sm ${tipo === 'credito' ? 'border-emerald-500 bg-emerald-500/10 text-emerald-500' : 'border-border text-muted-foreground'}`}>
                + Crédito
              </button>
              <button onClick={() => setTipo('debito')} data-testid="ajuste-tipo-debito"
                className={`px-3 py-2 rounded-lg border font-medium text-sm ${tipo === 'debito' ? 'border-rose-500 bg-rose-500/10 text-rose-500' : 'border-border text-muted-foreground'}`}>
                – Débito
              </button>
            </div>
          </div>

          <div>
            <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-2">Valor</p>
            <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg bg-background border border-border">
              <span className="text-muted-foreground">R$</span>
              <input type="number" step="0.01" min="0.01" value={valor} onChange={(e) => setValor(e.target.value)}
                placeholder="0,00" data-testid="ajuste-valor" className="flex-1 bg-transparent outline-none" />
            </div>
          </div>

          <div>
            <p className="text-xs uppercase tracking-wider text-muted-foreground font-semibold mb-2">Motivo</p>
            <textarea rows={2} value={motivo} onChange={(e) => setMotivo(e.target.value)} data-testid="ajuste-motivo"
              placeholder="Ex.: Estorno de recarga em duplicidade" className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm resize-none" />
          </div>

          {err && <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-500 text-sm">{err}</div>}

          <button onClick={submit} disabled={loading} data-testid="ajuste-salvar"
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:opacity-90 disabled:opacity-50">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Aplicar ajuste
          </button>
        </div>
      </motion.div>
    </div>
  );
};

// ---------- Modal Detalhes ----------
const ModalDetalhes = ({ open, ownerId, onClose }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!open || !ownerId) return;
    (async () => {
      setLoading(true);
      try {
        const { data: d } = await adminCarteirasAPI.detalhes(ownerId);
        setData(d);
      } finally { setLoading(false); }
    })();
  }, [open, ownerId]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" data-testid="modal-detalhes">
      <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
        className="bg-card border border-border rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h3 className="font-display font-bold text-lg text-foreground">Detalhes da Carteira</h3>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-sidebar-accent"><X className="w-4 h-4" /></button>
        </div>
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {loading ? <Loading /> : data && (
            <>
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 rounded-lg bg-sidebar-accent">
                  <p className="text-xs text-muted-foreground">Saldo</p>
                  <p className="font-display font-bold text-lg text-foreground">{money(data.carteira?.saldo)}</p>
                </div>
                <div className="p-3 rounded-lg bg-emerald-500/10">
                  <p className="text-xs text-emerald-500">Recargas</p>
                  <p className="font-display font-bold text-lg text-foreground">{money(data.carteira?.total_recargas)}</p>
                </div>
                <div className="p-3 rounded-lg bg-rose-500/10">
                  <p className="text-xs text-rose-500">Consumo</p>
                  <p className="font-display font-bold text-lg text-foreground">{money(data.carteira?.total_consumo)}</p>
                </div>
              </div>

              <div>
                <p className="text-sm font-medium text-foreground mb-2">Últimas movimentações</p>
                <div className="divide-y divide-border">
                  {(data.movimentos?.itens || []).map((m) => (
                    <div key={m.id} className="flex items-center gap-3 py-2 text-sm">
                      <div className="flex-1 min-w-0">
                        <p className="text-foreground truncate">{m.descricao}</p>
                        <p className="text-xs text-muted-foreground">{dt(m.created_at)}</p>
                      </div>
                      <p className={`font-semibold ${m.valor > 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                        {m.valor > 0 ? '+' : ''}{money(m.valor)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </motion.div>
    </div>
  );
};

// ---------- Página Principal ----------
const AdminCarteiras = () => {
  const [tab, setTab] = useState('carteiras');
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [carteiras, setCarteiras] = useState([]);
  const [totalCarteiras, setTotalCarteiras] = useState(0);
  const [precos, setPrecos] = useState([]);
  const [busca, setBusca] = useState('');
  const [modalAjuste, setModalAjuste] = useState(null);
  const [modalDetalhes, setModalDetalhes] = useState(null);
  const [precoEdit, setPrecoEdit] = useState({});

  const carregar = useCallback(async () => {
    setLoading(true);
    try {
      const [dash, list, pr] = await Promise.all([
        adminCarteirasAPI.dashboard(),
        adminCarteirasAPI.listar({ limit: 100, busca }),
        adminCarteirasAPI.precos(),
      ]);
      setDashboard(dash.data);
      setCarteiras(list.data.itens || []);
      setTotalCarteiras(list.data.total || 0);
      setPrecos(pr.data.itens || []);
    } catch (e) {
      toast({ title: 'Erro', description: "Não foi possível carregar as carteiras.", variant: 'destructive' });
      console.error(e);
    }
    finally { setLoading(false); }
  }, [busca]);

  useEffect(() => { carregar(); }, [carregar]);

  const salvarPreco = async (tipo, patch) => {
    try {
      const atual = precos.find((p) => p.tipo === tipo) || {};
      const body = { valor: Number(patch.valor ?? atual.valor), ativo: patch.ativo ?? atual.ativo };
      const { data } = await adminCarteirasAPI.atualizarPreco(tipo, body);
      setPrecos((prev) => prev.map((p) => (p.tipo === tipo ? { ...p, ...data } : p)));
      setPrecoEdit((prev) => ({ ...prev, [tipo]: undefined }));
    } catch (e) { alert(e?.response?.data?.detail || 'Erro ao salvar preço'); }
  };

  return (
    <Layout>
      <div className="p-4 sm:p-6 space-y-4 sm:space-y-6" data-testid="admin-carteiras-page">
        <div className="flex items-start justify-between flex-wrap gap-3">
          <div>
            <p className="text-xs text-amber-500 uppercase tracking-wider font-semibold">Super Admin</p>
            <h1 className="font-display font-bold text-3xl text-foreground tracking-tight">Carteiras & Preços</h1>
            <p className="text-sm text-muted-foreground mt-1">Gerencie saldos, movimentações e preços das consultas</p>
          </div>
          <button onClick={carregar} className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border text-sm hover:bg-sidebar-accent" data-testid="btn-atualizar">
            <RefreshCw className="w-4 h-4" /> Atualizar
          </button>
        </div>

        {/* Dashboard */}
        {dashboard && !loading && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-card border border-border">
              <div className="flex items-center gap-2 text-primary mb-2"><Wallet className="w-4 h-4" /><p className="text-xs uppercase tracking-wider font-semibold">Saldo Total</p></div>
              <p className="text-2xl font-display font-bold text-foreground" data-testid="stat-saldo-total">{money(dashboard.saldo_total)}</p>
              <p className="text-xs text-muted-foreground mt-1">{dashboard.total_carteiras} carteiras</p>
            </div>
            <div className="p-4 rounded-xl bg-card border border-border">
              <div className="flex items-center gap-2 text-emerald-500 mb-2"><TrendingUp className="w-4 h-4" /><p className="text-xs uppercase tracking-wider font-semibold">Receita 30d</p></div>
              <p className="text-2xl font-display font-bold text-foreground" data-testid="stat-receita">{money(dashboard.receita_30d?.total || 0)}</p>
              <p className="text-xs text-muted-foreground mt-1">{dashboard.receita_30d?.qtd || 0} recargas</p>
            </div>
            <div className="p-4 rounded-xl bg-card border border-border">
              <div className="flex items-center gap-2 text-rose-500 mb-2"><TrendingDown className="w-4 h-4" /><p className="text-xs uppercase tracking-wider font-semibold">Consumo Total</p></div>
              <p className="text-2xl font-display font-bold text-foreground">{money(dashboard.consumo_acumulado)}</p>
              <p className="text-xs text-muted-foreground mt-1">Acumulado</p>
            </div>
            <div className="p-4 rounded-xl bg-card border border-border">
              <div className="flex items-center gap-2 text-blue-500 mb-2"><Users className="w-4 h-4" /><p className="text-xs uppercase tracking-wider font-semibold">Recargas Total</p></div>
              <p className="text-2xl font-display font-bold text-foreground">{money(dashboard.recargas_acumuladas)}</p>
              <p className="text-xs text-muted-foreground mt-1">Somando bônus</p>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 p-1 rounded-xl bg-card border border-border w-fit">
          {[
            { id: 'carteiras', label: 'Carteiras', icon: Wallet },
            { id: 'precos', label: 'Preços', icon: DollarSign },
            { id: 'consumo', label: 'Consumo por tipo', icon: TrendingDown },
          ].map((t) => (
            <button key={t.id} onClick={() => setTab(t.id)} data-testid={`tab-${t.id}`}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                tab === t.id ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'
              }`}>
              <t.icon className="w-4 h-4" /> {t.label}
            </button>
          ))}
        </div>

        {loading ? <Loading /> : (
          <>
            {tab === 'carteiras' && (
              <div className="rounded-2xl bg-card border border-border overflow-hidden">
                <div className="p-4 border-b border-border flex items-center gap-2">
                  <div className="flex-1 flex items-center gap-2 px-3 py-2 rounded-lg bg-background border border-border">
                    <Search className="w-4 h-4 text-muted-foreground" />
                    <input value={busca} onChange={(e) => setBusca(e.target.value)}
                      placeholder="Buscar por nome ou e-mail…" data-testid="input-busca"
                      className="flex-1 bg-transparent outline-none text-sm" />
                  </div>
                  <p className="text-xs text-muted-foreground">{totalCarteiras} carteira(s)</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-sidebar-accent text-xs uppercase tracking-wider text-muted-foreground">
                      <tr>
                        <th className="text-left px-4 py-3">Cliente</th>
                        <th className="text-right px-4 py-3">Saldo</th>
                        <th className="text-right px-4 py-3 hidden md:table-cell">Recargas</th>
                        <th className="text-right px-4 py-3 hidden md:table-cell">Consumo</th>
                        <th className="text-left px-4 py-3 hidden lg:table-cell">Atualizada</th>
                        <th className="text-right px-4 py-3">Ações</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {carteiras.map((c) => (
                        <tr key={c.id} className="hover:bg-sidebar-accent/50" data-testid={`carteira-row-${c.owner_id}`}>
                          <td className="px-4 py-3">
                            <p className="font-medium text-foreground truncate max-w-[220px]">{c.dono?.nome}</p>
                            <p className="text-xs text-muted-foreground truncate max-w-[220px]">{c.dono?.email}</p>
                          </td>
                          <td className="px-4 py-3 text-right font-display font-bold text-foreground">{money(c.saldo)}</td>
                          <td className="px-4 py-3 text-right text-emerald-500 hidden md:table-cell">{money(c.total_recargas)}</td>
                          <td className="px-4 py-3 text-right text-rose-500 hidden md:table-cell">{money(c.total_consumo)}</td>
                          <td className="px-4 py-3 text-xs text-muted-foreground hidden lg:table-cell">{dt(c.updated_at)}</td>
                          <td className="px-4 py-3 text-right">
                            <div className="inline-flex gap-1">
                              <button onClick={() => setModalDetalhes(c.owner_id)} data-testid={`btn-detalhes-${c.owner_id}`}
                                className="p-2 rounded-lg hover:bg-sidebar-accent" title="Ver detalhes">
                                <Eye className="w-4 h-4 text-muted-foreground" />
                              </button>
                              <button onClick={() => setModalAjuste(c)} data-testid={`btn-ajuste-${c.owner_id}`}
                                className="p-2 rounded-lg hover:bg-sidebar-accent" title="Ajustar saldo">
                                <Zap className="w-4 h-4 text-amber-500" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                      {carteiras.length === 0 && (
                        <tr><td colSpan={6} className="px-4 py-10 text-center text-muted-foreground text-sm">Nenhuma carteira encontrada</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {tab === 'precos' && (
              <div className="rounded-2xl bg-card border border-border overflow-hidden">
                <div className="p-4 border-b border-border flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-amber-500" />
                  <p className="text-xs text-muted-foreground">Alterações refletem imediatamente para novas consultas</p>
                </div>
                <div className="divide-y divide-border">
                  {precos.map((p) => {
                    const editing = precoEdit[p.tipo] !== undefined;
                    const valorEd = precoEdit[p.tipo]?.valor ?? p.valor;
                    const ativoEd = precoEdit[p.tipo]?.ativo ?? p.ativo;
                    return (
                      <div key={p.tipo} className="flex items-center gap-3 px-4 py-3" data-testid={`preco-row-${p.tipo}`}>
                        <div className="flex-1">
                          <p className="font-medium text-foreground">{p.label || p.tipo}</p>
                          <p className="text-xs text-muted-foreground">{p.tipo}</p>
                        </div>

                        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-background border border-border">
                          <span className="text-xs text-muted-foreground">R$</span>
                          <input type="number" step="0.01" min="0" value={valorEd}
                            onChange={(e) => setPrecoEdit((prev) => ({ ...prev, [p.tipo]: { ...prev[p.tipo], valor: e.target.value, ativo: ativoEd } }))}
                            onFocus={() => setPrecoEdit((prev) => ({ ...prev, [p.tipo]: prev[p.tipo] || { valor: p.valor, ativo: p.ativo } }))}
                            data-testid={`preco-input-${p.tipo}`}
                            className="w-24 bg-transparent outline-none text-right font-mono text-sm" />
                        </div>

                        <label className="flex items-center gap-1.5 cursor-pointer">
                          <input type="checkbox" checked={ativoEd}
                            onChange={(e) => setPrecoEdit((prev) => ({ ...prev, [p.tipo]: { valor: valorEd, ativo: e.target.checked } }))}
                            data-testid={`preco-ativo-${p.tipo}`}
                            className="accent-primary" />
                          <span className="text-xs text-muted-foreground">Ativo</span>
                        </label>

                        {editing ? (
                          <div className="flex gap-1">
                            <button onClick={() => salvarPreco(p.tipo, { valor: valorEd, ativo: ativoEd })}
                              data-testid={`preco-salvar-${p.tipo}`}
                              className="p-2 rounded-lg bg-primary text-primary-foreground"><Check className="w-4 h-4" /></button>
                            <button onClick={() => setPrecoEdit((prev) => ({ ...prev, [p.tipo]: undefined }))}
                              className="p-2 rounded-lg border border-border"><X className="w-4 h-4" /></button>
                          </div>
                        ) : (
                          <button onClick={() => setPrecoEdit((prev) => ({ ...prev, [p.tipo]: { valor: p.valor, ativo: p.ativo } }))}
                            data-testid={`preco-editar-${p.tipo}`}
                            className="p-2 rounded-lg hover:bg-sidebar-accent"><Edit className="w-4 h-4 text-muted-foreground" /></button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {tab === 'consumo' && dashboard && (
              <div className="rounded-2xl bg-card border border-border overflow-hidden">
                <div className="p-4 border-b border-border">
                  <h3 className="font-medium text-foreground">Consumo dos últimos 30 dias</h3>
                  <p className="text-xs text-muted-foreground">Valor e quantidade de consultas por tipo</p>
                </div>
                <div className="divide-y divide-border">
                  {(dashboard.consumo_30d_por_tipo || []).map((c, idx) => (
                    <div key={idx} className="flex items-center px-4 py-3" data-testid={`consumo-row-${c.tipo}`}>
                      <p className="flex-1 font-medium text-foreground">{c.tipo}</p>
                      <p className="text-sm text-muted-foreground w-20 text-right">{c.qtd} consultas</p>
                      <p className="font-display font-bold text-foreground w-32 text-right">{money(c.valor_total)}</p>
                    </div>
                  ))}
                  {(dashboard.consumo_30d_por_tipo || []).length === 0 && (
                    <div className="px-4 py-10 text-center text-muted-foreground text-sm">Nenhum consumo nos últimos 30 dias</div>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <ModalAjuste open={!!modalAjuste} carteira={modalAjuste || {}} onClose={() => setModalAjuste(null)} onSaved={carregar} />
      <ModalDetalhes open={!!modalDetalhes} ownerId={modalDetalhes} onClose={() => setModalDetalhes(null)} />
    </Layout>
  );
};

export default AdminCarteiras;
