import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import Button from '../components/Button';
import { whatsappAPI } from '../api/api';
import { MessageSquareText, Eye, Save, Copy, RefreshCw, Lock, Variable } from 'lucide-react';
import { useToast } from '../hooks/use-toast';

const TIPO_LABEL = {
  lembrete: 'Lembrete',
  cobranca: 'Cobrança',
  atraso: 'Atraso',
  confirmacao: 'Confirmação',
  boas_vindas: 'Boas-vindas',
};

const VARIAVEIS = ['{cliente_nome}', '{numero_parcela}', '{total_parcelas}', '{valor}', '{data_vencimento}', '{dias}'];

const WhatsAppTemplates = () => {
  const [templates, setTemplates] = useState([]);
  const [rascunhos, setRascunhos] = useState({}); // id -> mensagem editada
  const [loading, setLoading] = useState(true);
  const [salvandoId, setSalvandoId] = useState(null);
  const [preview, setPreview] = useState({ id: null, texto: '' });
  const { toast } = useToast();

  const carregar = useCallback(async () => {
    try {
      const res = await whatsappAPI.listarTemplates();
      const lista = res.data.templates || [];
      setTemplates(lista);
      const draft = {};
      lista.forEach((t) => { draft[t.id] = t.mensagem; });
      setRascunhos(draft);
    } catch (e) {
      toast({ title: 'Erro ao carregar templates', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => { carregar(); }, [carregar]);

  const salvar = async (t) => {
    setSalvandoId(t.id);
    try {
      const novaMsg = rascunhos[t.id];
      if (t.padrao) {
        // Templates padrão não podem ser editados: cria uma cópia editável
        const dup = await whatsappAPI.duplicarTemplate(t.id, `${t.nome} (Personalizado)`);
        const novoId = dup.data.template.id;
        await whatsappAPI.atualizarTemplate(novoId, { mensagem: novaMsg });
        toast({ title: 'Cópia personalizada criada', description: 'O template padrão foi copiado e sua versão editada foi salva.' });
      } else {
        await whatsappAPI.atualizarTemplate(t.id, { mensagem: novaMsg });
        toast({ title: 'Template salvo' });
      }
      carregar();
    } catch (e) {
      toast({ title: 'Erro ao salvar', description: e?.response?.data?.detail || 'Falha', variant: 'destructive' });
    } finally {
      setSalvandoId(null);
    }
  };

  const toggleAtivo = async (t) => {
    try {
      await whatsappAPI.atualizarTemplate(t.id, { ativo: !t.ativo });
      setTemplates((prev) => prev.map((x) => (x.id === t.id ? { ...x, ativo: !x.ativo } : x)));
    } catch (e) {
      toast({ title: 'Erro ao alterar status', variant: 'destructive' });
    }
  };

  const previewTemplate = async (t) => {
    try {
      const res = await whatsappAPI.previewTemplate(rascunhos[t.id]);
      setPreview({ id: t.id, texto: res.data.preview });
    } catch (e) {
      toast({ title: 'Erro no preview', variant: 'destructive' });
    }
  };

  const inserirVariavel = (id, v) => {
    setRascunhos((prev) => ({ ...prev, [id]: (prev[id] || '') + ' ' + v }));
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-6 h-6 animate-spin text-emerald-500" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto space-y-6" data-testid="templates-page">
        <div>
          <h1 className="text-3xl font-bold text-foreground flex items-center gap-3">
            <MessageSquareText className="w-8 h-8 text-emerald-500" />
            Templates de Mensagem
          </h1>
          <p className="text-muted-foreground mt-1">Edite os textos das mensagens de cobrança, lembrete e confirmação.</p>
        </div>

        <div className="rounded-xl border border-border bg-card/60 p-4 flex items-start gap-2 text-sm text-muted-foreground">
          <Variable className="w-4 h-4 mt-0.5 text-emerald-500 shrink-0" />
          <span>Variáveis disponíveis: {VARIAVEIS.map((v) => <code key={v} className="mx-1 px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">{v}</code>)}</span>
        </div>

        <div className="space-y-4">
          {templates.map((t) => (
            <div key={t.id} className="rounded-2xl border border-border bg-card p-5 space-y-3" data-testid={`template-card-${t.tipo}`}>
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-foreground">{t.nome}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">{TIPO_LABEL[t.tipo] || t.tipo}</span>
                  {t.padrao && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-neutral-200 dark:bg-neutral-800 text-neutral-500 flex items-center gap-1"><Lock className="w-3 h-3" /> Padrão</span>
                  )}
                </div>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <span className="text-muted-foreground">{t.ativo ? 'Ativo' : 'Inativo'}</span>
                  <input type="checkbox" className="sr-only peer" checked={!!t.ativo} onChange={() => toggleAtivo(t)} data-testid={`template-ativo-${t.tipo}`} />
                  <div className="w-10 h-5 bg-neutral-300 dark:bg-neutral-700 peer-checked:bg-emerald-500 rounded-full relative transition-colors after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:after:translate-x-5"></div>
                </label>
              </div>

              <textarea
                value={rascunhos[t.id] || ''}
                onChange={(e) => setRascunhos((prev) => ({ ...prev, [t.id]: e.target.value }))}
                rows={6}
                data-testid={`template-textarea-${t.tipo}`}
                className="w-full rounded-xl border border-border bg-background p-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono"
              />

              <div className="flex flex-wrap gap-1.5">
                {VARIAVEIS.map((v) => (
                  <button key={v} type="button" onClick={() => inserirVariavel(t.id, v)} className="text-xs px-2 py-1 rounded-md border border-border text-muted-foreground hover:border-emerald-400 hover:text-emerald-500 transition-colors">
                    {v}
                  </button>
                ))}
              </div>

              {preview.id === t.id && (
                <div className="rounded-xl bg-[#075E54]/5 border border-emerald-500/20 p-3" data-testid={`template-preview-${t.tipo}`}>
                  <p className="text-xs text-muted-foreground mb-1">Pré-visualização:</p>
                  <pre className="whitespace-pre-wrap text-sm text-foreground font-sans">{preview.texto}</pre>
                </div>
              )}

              <div className="flex items-center gap-2">
                <Button variant="outline" onClick={() => previewTemplate(t)} data-testid={`template-preview-btn-${t.tipo}`}>
                  <Eye className="w-4 h-4" /> Pré-visualizar
                </Button>
                <Button onClick={() => salvar(t)} disabled={salvandoId === t.id} data-testid={`template-salvar-btn-${t.tipo}`}>
                  {salvandoId === t.id ? <RefreshCw className="w-4 h-4 animate-spin" /> : (t.padrao ? <Copy className="w-4 h-4" /> : <Save className="w-4 h-4" />)}
                  {t.padrao ? 'Salvar cópia' : 'Salvar'}
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </Layout>
  );
};

export default WhatsAppTemplates;
