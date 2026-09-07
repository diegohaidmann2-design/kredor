import React, { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  ShieldAlert, Lock, Globe, Webhook, RefreshCw, Unlock, Clock, AlertTriangle
} from 'lucide-react';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import { segurancaAPI } from '../api/api';
import { useModal } from '../components/Modal';

const fmt = (iso) => {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString('pt-BR'); } catch (e) { return iso; }
};

const StatCard = ({ icon: Icon, label, value, tone }) => (
  <div
    data-testid={`seg-card-${label}`}
    className="rounded-xl border border-border bg-card p-5 flex items-center gap-4"
  >
    <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${tone}`}>
      <Icon className="w-6 h-6" />
    </div>
    <div>
      <div className="text-2xl font-bold text-foreground leading-none">{value}</div>
      <div className="text-sm text-muted-foreground mt-1">{label}</div>
    </div>
  </div>
);

const AdminSeguranca = () => {
  const modal = useModal();
  const [resumo, setResumo] = useState(null);
  const [contas, setContas] = useState([]);
  const [ips, setIps] = useState([]);
  const [webhooks, setWebhooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [auto, setAuto] = useState(true);
  const [ultimaAtualizacao, setUltimaAtualizacao] = useState(null);

  const carregar = useCallback(async () => {
    try {
      const [r, b, w] = await Promise.all([
        segurancaAPI.resumo(),
        segurancaAPI.loginBloqueios(),
        segurancaAPI.webhooksSuspeitos(),
      ]);
      setResumo(r.data);
      setContas(b.data.contas || []);
      setIps(b.data.ips || []);
      setWebhooks(w.data.itens || []);
      setUltimaAtualizacao(new Date());
    } catch (e) {
      // silencioso no auto-refresh
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  useEffect(() => {
    if (!auto) return undefined;
    const id = setInterval(carregar, 10000);
    return () => clearInterval(id);
  }, [auto, carregar]);

  const desbloquearConta = async (email) => {
    try { await segurancaAPI.desbloquearConta(email); await carregar(); }
    catch (e) { modal.error('Erro', e.response?.data?.detail || 'Falha ao desbloquear'); }
  };
  const desbloquearIp = async (ip) => {
    try { await segurancaAPI.desbloquearIp(ip); await carregar(); }
    catch (e) { modal.error('Erro', e.response?.data?.detail || 'Falha ao desbloquear'); }
  };

  if (loading && !resumo) return <Loading message="Carregando painel de segurança..." />;

  return (
    <Layout>
      <div className="p-4 sm:p-6" data-testid="admin-seguranca-page">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-4 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">Painel de Segurança</h1>
              <p className="text-sm text-muted-foreground">
                Bloqueios de login por IP/conta e webhooks suspeitos — em tempo real
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" /> {ultimaAtualizacao ? fmt(ultimaAtualizacao.toISOString()) : '—'}
            </span>
            <button
              data-testid="toggle-auto-refresh"
              onClick={() => setAuto((v) => !v)}
              className={`px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${auto ? 'bg-primary/10 text-primary border-primary/30' : 'bg-muted text-muted-foreground border-border'}`}
            >
              Auto {auto ? 'ON' : 'OFF'}
            </button>
            <button
              data-testid="btn-refresh-seguranca"
              onClick={carregar}
              className="px-3 py-2 rounded-lg text-sm font-medium bg-card text-foreground border border-border hover:bg-muted transition-colors flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" /> Atualizar
            </button>
          </div>
        </div>

        {/* Cards de resumo */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard icon={Lock} label="Contas bloqueadas" value={resumo?.contas_bloqueadas ?? '—'} tone="bg-red-500/15 text-red-500" />
          <StatCard icon={Globe} label="IPs bloqueados" value={resumo?.ips_bloqueados ?? '—'} tone="bg-orange-500/15 text-orange-500" />
          <StatCard icon={AlertTriangle} label="Tentativas ativas" value={resumo?.tentativas_ativas ?? '—'} tone="bg-amber-500/15 text-amber-500" />
          <StatCard icon={Webhook} label="Webhooks suspeitos" value={resumo?.webhooks_suspeitos ?? '—'} tone="bg-purple-500/15 text-purple-500" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Contas */}
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-center gap-2">
              <Lock className="w-4 h-4 text-red-500" />
              <h2 className="font-semibold text-foreground">Tentativas por conta (e-mail)</h2>
            </div>
            <div className="max-h-[420px] overflow-auto">
              <table className="w-full text-sm" data-testid="table-contas">
                <thead className="text-muted-foreground text-xs uppercase sticky top-0 bg-muted/50 backdrop-blur">
                  <tr><th className="text-left px-5 py-3 font-medium">E-mail</th><th className="text-center py-3 font-medium">Tent.</th><th className="text-left py-3 font-medium">Última</th><th className="text-center py-3 font-medium">Estado</th><th className="py-3" /></tr>
                </thead>
                <tbody>
                  {contas.length === 0 && (
                    <tr><td colSpan={5} className="px-5 py-8 text-center text-muted-foreground">Nenhuma tentativa registrada</td></tr>
                  )}
                  {contas.map((c, i) => (
                    <tr key={i} className="border-t border-border">
                      <td className="px-5 py-2 text-foreground">{c.email}</td>
                      <td className="text-center text-muted-foreground">{c.tentativas}</td>
                      <td className="text-muted-foreground text-xs">{fmt(c.ultima_tentativa)}</td>
                      <td className="text-center">
                        {c.bloqueado
                          ? <span className="px-2 py-0.5 rounded-full text-xs bg-red-500/15 text-red-500">Bloqueada</span>
                          : <span className="px-2 py-0.5 rounded-full text-xs bg-muted text-muted-foreground">Ativa</span>}
                      </td>
                      <td className="pr-4 text-right">
                        <button onClick={() => desbloquearConta(c.email)} title="Desbloquear"
                          data-testid={`unblock-conta-${c.email}`}
                          className="p-1.5 rounded-lg hover:bg-muted text-primary transition-colors"><Unlock className="w-4 h-4" /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>

          {/* IPs */}
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="px-5 py-4 border-b border-border flex items-center gap-2">
              <Globe className="w-4 h-4 text-orange-500" />
              <h2 className="font-semibold text-foreground">Tentativas por IP</h2>
            </div>
            <div className="max-h-[420px] overflow-auto">
              <table className="w-full text-sm" data-testid="table-ips">
                <thead className="text-muted-foreground text-xs uppercase sticky top-0 bg-muted/50 backdrop-blur">
                  <tr><th className="text-left px-5 py-3 font-medium">IP</th><th className="text-center py-3 font-medium">Tent.</th><th className="text-left py-3 font-medium">Última</th><th className="text-center py-3 font-medium">Estado</th><th className="py-3" /></tr>
                </thead>
                <tbody>
                  {ips.length === 0 && (
                    <tr><td colSpan={5} className="px-5 py-8 text-center text-muted-foreground">Nenhum IP registrado</td></tr>
                  )}
                  {ips.map((c, i) => (
                    <tr key={i} className="border-t border-border">
                      <td className="px-5 py-2 text-foreground font-mono text-xs">{c.ip}</td>
                      <td className="text-center text-muted-foreground">{c.tentativas}</td>
                      <td className="text-muted-foreground text-xs">{fmt(c.ultima_tentativa)}</td>
                      <td className="text-center">
                        {c.bloqueado
                          ? <span className="px-2 py-0.5 rounded-full text-xs bg-orange-500/15 text-orange-500">Bloqueado</span>
                          : <span className="px-2 py-0.5 rounded-full text-xs bg-muted text-muted-foreground">Ativo</span>}
                      </td>
                      <td className="pr-4 text-right">
                        <button onClick={() => desbloquearIp(c.ip)} title="Desbloquear"
                          data-testid={`unblock-ip-${c.ip}`}
                          className="p-1.5 rounded-lg hover:bg-muted text-primary transition-colors"><Unlock className="w-4 h-4" /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        </div>

        {/* Webhooks suspeitos */}
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-border bg-card overflow-hidden mt-6">
          <div className="px-5 py-4 border-b border-border flex items-center gap-2">
            <Webhook className="w-4 h-4 text-purple-500" />
            <h2 className="font-semibold text-foreground">Webhooks suspeitos</h2>
          </div>
          <div className="max-h-[420px] overflow-auto divide-y divide-border" data-testid="list-webhooks">
            {webhooks.length === 0 && (
              <div className="px-5 py-8 text-center text-muted-foreground">Nenhum webhook suspeito registrado</div>
            )}
            {webhooks.map((w, i) => (
              <div key={i} className="px-5 py-3 flex items-start gap-3">
                <AlertTriangle className="w-4 h-4 text-purple-500 mt-0.5 shrink-0" />
                <div className="min-w-0">
                  <div className="text-foreground text-sm">{w.descricao}</div>
                  <div className="text-xs text-muted-foreground mt-0.5 flex flex-wrap gap-x-3">
                    <span>{fmt(w.created_at)}</span>
                    {w.ip && <span className="font-mono">IP {w.ip}</span>}
                    {w.detalhes?.gateway && <span>gateway: {w.detalhes.gateway}</span>}
                    {w.detalhes?.transaction_id && <span className="truncate">tx: {w.detalhes.transaction_id}</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </Layout>
  );
};

export default AdminSeguranca;
