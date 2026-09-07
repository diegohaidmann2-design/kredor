import React, { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  ShieldAlert, Lock, Globe, Webhook, RefreshCw, Unlock, Clock, AlertTriangle
} from 'lucide-react';
import { segurancaAPI } from '../api/api';
import { useModal } from '../components/Modal';

const fmt = (iso) => {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleString('pt-BR'); } catch (e) { return iso; }
};

const StatCard = ({ icon: Icon, label, value, tone }) => (
  <div
    data-testid={`seg-card-${label}`}
    className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 flex items-center gap-4"
  >
    <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${tone}`}>
      <Icon className="w-6 h-6" />
    </div>
    <div>
      <div className="text-2xl font-bold text-white leading-none">{value}</div>
      <div className="text-sm text-slate-400 mt-1">{label}</div>
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

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="admin-seguranca-page">
      <div className="flex items-center justify-between flex-wrap gap-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-emerald-500/15 text-emerald-400 flex items-center justify-center">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Painel de Segurança</h1>
            <p className="text-sm text-slate-400">
              Bloqueios de login por IP/conta e webhooks suspeitos — em tempo real
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500 flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" /> {ultimaAtualizacao ? fmt(ultimaAtualizacao.toISOString()) : '—'}
          </span>
          <button
            data-testid="toggle-auto-refresh"
            onClick={() => setAuto((v) => !v)}
            className={`px-3 py-2 rounded-lg text-sm font-medium border ${auto ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' : 'bg-white/5 text-slate-400 border-white/10'}`}
          >
            Auto {auto ? 'ON' : 'OFF'}
          </button>
          <button
            data-testid="btn-refresh-seguranca"
            onClick={carregar}
            className="px-3 py-2 rounded-lg text-sm font-medium bg-white/5 text-white border border-white/10 hover:bg-white/10 flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" /> Atualizar
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard icon={Lock} label="Contas bloqueadas" value={resumo?.contas_bloqueadas ?? '—'} tone="bg-red-500/15 text-red-400" />
        <StatCard icon={Globe} label="IPs bloqueados" value={resumo?.ips_bloqueados ?? '—'} tone="bg-orange-500/15 text-orange-400" />
        <StatCard icon={AlertTriangle} label="Tentativas ativas" value={resumo?.tentativas_ativas ?? '—'} tone="bg-amber-500/15 text-amber-400" />
        <StatCard icon={Webhook} label="Webhooks suspeitos" value={resumo?.webhooks_suspeitos ?? '—'} tone="bg-purple-500/15 text-purple-400" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Contas */}
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden">
          <div className="px-5 py-4 border-b border-white/10 flex items-center gap-2">
            <Lock className="w-4 h-4 text-red-400" />
            <h2 className="font-semibold text-white">Tentativas por conta (e-mail)</h2>
          </div>
          <div className="max-h-[420px] overflow-auto">
            <table className="w-full text-sm" data-testid="table-contas">
              <thead className="text-slate-400 text-xs sticky top-0 bg-[#0d1117]">
                <tr><th className="text-left px-5 py-2">E-mail</th><th className="text-center py-2">Tent.</th><th className="text-left py-2">Última</th><th className="text-center py-2">Estado</th><th className="py-2" /></tr>
              </thead>
              <tbody>
                {contas.length === 0 && (
                  <tr><td colSpan={5} className="px-5 py-8 text-center text-slate-500">Nenhuma tentativa registrada</td></tr>
                )}
                {contas.map((c, i) => (
                  <tr key={i} className="border-t border-white/5">
                    <td className="px-5 py-2 text-slate-200">{c.email}</td>
                    <td className="text-center text-slate-300">{c.tentativas}</td>
                    <td className="text-slate-400 text-xs">{fmt(c.ultima_tentativa)}</td>
                    <td className="text-center">
                      {c.bloqueado
                        ? <span className="px-2 py-0.5 rounded-full text-xs bg-red-500/15 text-red-400">Bloqueada</span>
                        : <span className="px-2 py-0.5 rounded-full text-xs bg-slate-500/15 text-slate-400">Ativa</span>}
                    </td>
                    <td className="pr-4 text-right">
                      <button onClick={() => desbloquearConta(c.email)} title="Desbloquear"
                        data-testid={`unblock-conta-${c.email}`}
                        className="p-1.5 rounded-lg hover:bg-white/10 text-emerald-400"><Unlock className="w-4 h-4" /></button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* IPs */}
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden">
          <div className="px-5 py-4 border-b border-white/10 flex items-center gap-2">
            <Globe className="w-4 h-4 text-orange-400" />
            <h2 className="font-semibold text-white">Tentativas por IP</h2>
          </div>
          <div className="max-h-[420px] overflow-auto">
            <table className="w-full text-sm" data-testid="table-ips">
              <thead className="text-slate-400 text-xs sticky top-0 bg-[#0d1117]">
                <tr><th className="text-left px-5 py-2">IP</th><th className="text-center py-2">Tent.</th><th className="text-left py-2">Última</th><th className="text-center py-2">Estado</th><th className="py-2" /></tr>
              </thead>
              <tbody>
                {ips.length === 0 && (
                  <tr><td colSpan={5} className="px-5 py-8 text-center text-slate-500">Nenhum IP registrado</td></tr>
                )}
                {ips.map((c, i) => (
                  <tr key={i} className="border-t border-white/5">
                    <td className="px-5 py-2 text-slate-200 font-mono text-xs">{c.ip}</td>
                    <td className="text-center text-slate-300">{c.tentativas}</td>
                    <td className="text-slate-400 text-xs">{fmt(c.ultima_tentativa)}</td>
                    <td className="text-center">
                      {c.bloqueado
                        ? <span className="px-2 py-0.5 rounded-full text-xs bg-orange-500/15 text-orange-400">Bloqueado</span>
                        : <span className="px-2 py-0.5 rounded-full text-xs bg-slate-500/15 text-slate-400">Ativo</span>}
                    </td>
                    <td className="pr-4 text-right">
                      <button onClick={() => desbloquearIp(c.ip)} title="Desbloquear"
                        data-testid={`unblock-ip-${c.ip}`}
                        className="p-1.5 rounded-lg hover:bg-white/10 text-emerald-400"><Unlock className="w-4 h-4" /></button>
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
        className="rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden mt-6">
        <div className="px-5 py-4 border-b border-white/10 flex items-center gap-2">
          <Webhook className="w-4 h-4 text-purple-400" />
          <h2 className="font-semibold text-white">Webhooks suspeitos</h2>
        </div>
        <div className="max-h-[420px] overflow-auto divide-y divide-white/5" data-testid="list-webhooks">
          {webhooks.length === 0 && (
            <div className="px-5 py-8 text-center text-slate-500">Nenhum webhook suspeito registrado</div>
          )}
          {webhooks.map((w, i) => (
            <div key={i} className="px-5 py-3 flex items-start gap-3">
              <AlertTriangle className="w-4 h-4 text-purple-400 mt-0.5 shrink-0" />
              <div className="min-w-0">
                <div className="text-slate-200 text-sm">{w.descricao}</div>
                <div className="text-xs text-slate-500 mt-0.5 flex flex-wrap gap-x-3">
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

      {loading && <p className="text-center text-slate-500 mt-6">Carregando…</p>}
    </div>
  );
};

export default AdminSeguranca;
