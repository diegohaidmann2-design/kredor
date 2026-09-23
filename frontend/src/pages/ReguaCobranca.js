import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import Button from '../components/Button';
import { whatsappAPI } from '../api/api';
import {
  CalendarClock, Bell, AlertTriangle, CheckCircle, Play, RefreshCw,
  Send, History, Zap
} from 'lucide-react';
import { useToast } from '../hooks/use-toast';

const OPCOES_LEMBRETE = [7, 5, 3, 2, 1];
const OPCOES_ATRASO = [1, 3, 5, 7, 15, 30];

const ReguaCobranca = () => {
  const [config, setConfig] = useState(null);
  const [historico, setHistorico] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [executando, setExecutando] = useState(false);
  const { toast } = useToast();

  const carregar = useCallback(async () => {
    try {
      const [cfgRes, histRes] = await Promise.all([
        whatsappAPI.obterConfigRegua(),
        whatsappAPI.historicoRegua(30),
      ]);
      setConfig(cfgRes.data);
      setHistorico(histRes.data.itens || []);
    } catch (e) {
      toast({ title: 'Erro ao carregar', description: 'Não foi possível carregar a régua', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => { carregar(); }, [carregar]);

  const salvar = async (patch) => {
    const novo = { ...config, ...patch };
    setConfig(novo);
    setSaving(true);
    try {
      const res = await whatsappAPI.atualizarConfigRegua(novo);
      setConfig(res.data);
    } catch (e) {
      toast({ title: 'Erro ao salvar', variant: 'destructive' });
      carregar();
    } finally {
      setSaving(false);
    }
  };

  const toggleDia = (campo, dia) => {
    const atual = config[campo] || [];
    const novo = atual.includes(dia) ? atual.filter((d) => d !== dia) : [...atual, dia].sort((a, b) => a - b);
    salvar({ [campo]: novo });
  };

  const executarAgora = async () => {
    setExecutando(true);
    try {
      const res = await whatsappAPI.executarRegua();
      const s = res.data.stats || {};
      toast({
        title: 'Régua executada',
        description: `Enfileiradas: ${s.enfileiradas || 0} (lembrete ${s.lembrete || 0}, cobrança ${s.cobranca || 0}, atraso ${s.atraso || 0}). Ignoradas (já enviadas): ${s.puladas_duplicadas || 0}. Sem telefone: ${s.sem_telefone || 0}.`,
      });
      carregar();
    } catch (e) {
      toast({ title: 'Erro ao executar', description: e?.response?.data?.detail || 'Falha', variant: 'destructive' });
    } finally {
      setExecutando(false);
    }
  };

  if (loading || !config) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-6 h-6 animate-spin text-emerald-500" />
        </div>
      </Layout>
    );
  }

  const Toggle = ({ checked, onChange, testId }) => (
    <label className="relative inline-flex items-center cursor-pointer">
      <input type="checkbox" className="sr-only peer" checked={!!checked} onChange={onChange} data-testid={testId} />
      <div className="w-11 h-6 bg-neutral-300 dark:bg-neutral-700 peer-checked:bg-emerald-500 rounded-full transition-colors after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-5"></div>
    </label>
  );

  const Chip = ({ ativo, onClick, children, testId }) => (
    <button
      type="button"
      onClick={onClick}
      data-testid={testId}
      className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
        ativo
          ? 'bg-emerald-500 border-emerald-500 text-white'
          : 'bg-transparent border-neutral-300 dark:border-neutral-700 text-neutral-600 dark:text-neutral-300 hover:border-emerald-400'
      }`}
    >
      {children}
    </button>
  );

  return (
    <Layout>
      <div className="max-w-4xl mx-auto space-y-6" data-testid="regua-page">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="font-cabinet font-black text-3xl sm:text-4xl tracking-tighter text-foreground flex items-center gap-3">
              <CalendarClock className="w-8 h-8 text-emerald-500" />
              Régua de Cobrança
            </h1>
            <p className="text-muted-foreground mt-1">Envie lembretes e cobranças automáticas por WhatsApp, respeitando o anti-spam.</p>
          </div>
          <Button onClick={executarAgora} disabled={executando} data-testid="regua-executar-btn">
            {executando ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Executar agora
          </Button>
        </div>

        {/* Ativar régua */}
        <div className="rounded-2xl border border-border bg-card p-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${config.ativo ? 'bg-emerald-500/15 text-emerald-500' : 'bg-neutral-200 dark:bg-neutral-800 text-neutral-500'}`}>
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <p className="font-semibold text-foreground">Régua automática {config.ativo ? 'ativada' : 'desativada'}</p>
              <p className="text-sm text-muted-foreground">Quando ativa, roda todo dia às 09:00 e enfileira os envios do dia.</p>
            </div>
          </div>
          <Toggle checked={config.ativo} onChange={(e) => salvar({ ativo: e.target.checked })} testId="regua-ativo-toggle" />
        </div>

        {/* Lembrete antes do vencimento */}
        <div className="rounded-2xl border border-border bg-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bell className="w-5 h-5 text-blue-500" />
              <h2 className="font-semibold text-foreground">Lembrete antes do vencimento</h2>
            </div>
            <Toggle checked={config.lembrete_ativo} onChange={(e) => salvar({ lembrete_ativo: e.target.checked })} testId="regua-lembrete-toggle" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-2">Enviar quantos dias antes:</p>
            <div className="flex flex-wrap gap-2">
              {OPCOES_LEMBRETE.map((d) => (
                <Chip key={d} ativo={(config.lembrete_dias_antes || []).includes(d)} onClick={() => toggleDia('lembrete_dias_antes', d)} testId={`regua-lembrete-dia-${d}`}>
                  {d} dia{d > 1 ? 's' : ''}
                </Chip>
              ))}
            </div>
          </div>
        </div>

        {/* Vencimento hoje */}
        <div className="rounded-2xl border border-border bg-card p-5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Send className="w-5 h-5 text-amber-500" />
            <div>
              <h2 className="font-semibold text-foreground">Cobrança no dia do vencimento</h2>
              <p className="text-sm text-muted-foreground">Envia uma mensagem no dia em que a parcela vence.</p>
            </div>
          </div>
          <Toggle checked={config.vencimento_ativo} onChange={(e) => salvar({ vencimento_ativo: e.target.checked })} testId="regua-vencimento-toggle" />
        </div>

        {/* Atraso */}
        <div className="rounded-2xl border border-border bg-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-500" />
              <h2 className="font-semibold text-foreground">Cobrança de parcela em atraso</h2>
            </div>
            <Toggle checked={config.atraso_ativo} onChange={(e) => salvar({ atraso_ativo: e.target.checked })} testId="regua-atraso-toggle" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-2">Enviar quantos dias após o vencimento:</p>
            <div className="flex flex-wrap gap-2">
              {OPCOES_ATRASO.map((d) => (
                <Chip key={d} ativo={(config.atraso_dias || []).includes(d)} onClick={() => toggleDia('atraso_dias', d)} testId={`regua-atraso-dia-${d}`}>
                  {d} dia{d > 1 ? 's' : ''}
                </Chip>
              ))}
            </div>
          </div>
        </div>

        {/* Valor mínimo */}
        <div className="rounded-2xl border border-border bg-card p-5">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            <h2 className="font-semibold text-foreground">Valor mínimo para cobrar</h2>
          </div>
          <p className="text-sm text-muted-foreground mb-3">
            Não cobrar sobras menores que este valor. Evita mandar mensagem por centavos para quem
            já pagou a parcela. Parcela que nunca foi paga é cobrada sempre, mesmo abaixo disso.
          </p>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">R$</span>
            <input
              type="number"
              min="0"
              step="0.01"
              defaultValue={config.valor_minimo ?? 5}
              onBlur={(e) => salvar({ valor_minimo: parseFloat(e.target.value) || 0 })}
              className="w-32 px-3 py-2 bg-background border border-border rounded-md text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              data-testid="regua-valor-minimo"
            />
          </div>
        </div>

        {/* Histórico */}
        <div className="rounded-2xl border border-border bg-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <History className="w-5 h-5 text-emerald-500" />
            <h2 className="font-semibold text-foreground">Últimos envios da régua</h2>
          </div>
          {historico.length === 0 ? (
            <p className="text-sm text-muted-foreground" data-testid="regua-historico-vazio">Nenhum envio ainda. Ative a régua ou clique em "Executar agora".</p>
          ) : (
            <div className="space-y-2" data-testid="regua-historico-lista">
              {historico.map((it) => (
                <div key={it._id} className="flex items-center justify-between text-sm border-b border-border/60 pb-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-emerald-500" />
                    <span className="capitalize font-medium text-foreground">{it.tipo}</span>
                    <span className="text-muted-foreground">→ {it.numero_destino}</span>
                  </div>
                  <span className="text-muted-foreground">{it.data_ref}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {saving && <p className="text-xs text-muted-foreground text-right">Salvando…</p>}
      </div>
    </Layout>
  );
};

export default ReguaCobranca;
