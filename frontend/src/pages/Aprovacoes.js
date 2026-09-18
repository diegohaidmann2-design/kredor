import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import ErrorMessage from '../components/ErrorMessage';
import { useModal } from '../components/Modal';
import { cadastroPublicoAPI } from '../api/api';
import { formatarCpfCnpj, formatarTelefone, formatarData } from '../utils/formatters';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  UserPlus, Link2, Copy, RefreshCw, Check, X, Trash2, Clock, CheckCircle2,
  XCircle, Phone, Mail, MapPin, ExternalLink, Eye, FileImage, PenTool, ZoomIn, ZoomOut, ChevronLeft, ChevronRight,
  FileDown, Loader2
} from 'lucide-react';

const TIPOS_ANEXO = [
  { key: 'selfie', label: 'Selfie', icon: Eye },
  { key: 'doc_frente', label: 'Doc. frente', icon: FileImage },
  { key: 'doc_verso', label: 'Doc. verso', icon: FileImage },
  { key: 'assinatura', label: 'Assinatura', icon: PenTool },
];

const LABEL_TIPO = { selfie: 'Selfie', doc_frente: 'Doc. frente', doc_verso: 'Doc. verso', assinatura: 'Assinatura' };

function useAnexoUrls(solicitacao) {
  const [urls, setUrls] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const anexos = solicitacao?.anexos || {};
    const tipos = TIPOS_ANEXO.map(t => t.key).filter(k => anexos[k]?.path);
    if (tipos.length === 0) { setUrls({}); return; }
    setLoading(true);
    const created = [];
    let cancelled = false;
    Promise.allSettled(tipos.map(async (tipo) => {
      try {
        const res = await cadastroPublicoAPI.obterAnexo(solicitacao.id, tipo);
        if (cancelled) return;
        const blobUrl = URL.createObjectURL(res.data);
        created.push(blobUrl);
        setUrls(prev => ({ ...prev, [tipo]: blobUrl }));
      } catch {
        // sem anexo ou erro — ignora
      }
    })).finally(() => { if (!cancelled) setLoading(false); });
    return () => {
      cancelled = true;
      created.forEach(u => URL.revokeObjectURL(u));
    };
  }, [solicitacao?.id, JSON.stringify(solicitacao?.anexos || {})]);

  // cleanup ao desmontar urls restantes
  useEffect(() => {
    return () => {
      Object.values(urls).forEach(u => { try { URL.revokeObjectURL(u); } catch {} });
    };
  }, []);

  return { urls, loading };
}

function Lightbox({ solicitacao, initialTipo, urls, onClose, onBaixarPdf, baixandoPdf }) {
  const tiposDisponiveis = TIPOS_ANEXO.map(t => t.key).filter(k => solicitacao?.anexos?.[k]?.path);
  const initialIdx = Math.max(0, tiposDisponiveis.indexOf(initialTipo));
  const [idx, setIdx] = useState(initialIdx);
  const [zoom, setZoom] = useState(1);
  const tipoAtual = tiposDisponiveis[idx];
  const urlAtual = urls[tipoAtual];

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowLeft') setIdx(i => Math.max(0, i - 1));
      if (e.key === 'ArrowRight') setIdx(i => Math.min(tiposDisponiveis.length - 1, i + 1));
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose, tiposDisponiveis.length]);

  if (!tipoAtual) return null;

  const hasPrev = idx > 0;
  const hasNext = idx < tiposDisponiveis.length - 1;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex flex-col" data-testid="anexo-lightbox">
      <div className="flex items-center justify-between p-3 text-white">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{solicitacao.nome} — {LABEL_TIPO[tipoAtual]}</span>
          <span className="text-xs opacity-60">({idx + 1}/{tiposDisponiveis.length})</span>
        </div>
        <div className="flex items-center gap-1">
          {onBaixarPdf && (
            <button
              onClick={onBaixarPdf}
              disabled={baixandoPdf}
              className="p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white flex items-center gap-1.5 text-xs mr-2 disabled:opacity-50"
              data-testid="lightbox-pdf"
              title="Baixar Ficha Cadastral em PDF"
            >
              {baixandoPdf ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileDown className="w-4 h-4 text-emerald-400" />}
              <span className="hidden sm:inline">Baixar Ficha PDF</span>
            </button>
          )}
          <button onClick={() => setZoom(z => Math.max(0.5, z - 0.25))} className="p-2 rounded-lg bg-white/10 hover:bg-white/20" data-testid="lightbox-zoom-out"><ZoomOut className="w-4 h-4" /></button>
          <span className="text-xs w-10 text-center">{Math.round(zoom * 100)}%</span>
          <button onClick={() => setZoom(z => Math.min(3, z + 0.25))} className="p-2 rounded-lg bg-white/10 hover:bg-white/20" data-testid="lightbox-zoom-in"><ZoomIn className="w-4 h-4" /></button>
          <button onClick={onClose} className="ml-2 p-2 rounded-lg bg-white/10 hover:bg-white/20" data-testid="lightbox-fechar"><X className="w-4 h-4" /></button>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center p-4 gap-2 min-h-0">
        {hasPrev && (
          <button onClick={() => { setIdx(i => i - 1); setZoom(1); }} className="p-2 rounded-full bg-white/10 text-white hover:bg-white/20 flex-shrink-0" data-testid="lightbox-prev"><ChevronLeft className="w-5 h-5" /></button>
        )}
        <div className="flex-1 flex items-center justify-center min-h-0 overflow-auto">
          {urlAtual ? (
            <img
              src={urlAtual}
              alt={LABEL_TIPO[tipoAtual]}
              className="max-w-full max-h-[70vh] object-contain bg-white rounded-lg transition-transform"
              style={{ transform: `scale(${zoom})`, transformOrigin: 'center' }}
              data-testid="lightbox-imagem"
            />
          ) : (
            <div className="text-white/60 text-sm">Carregando…</div>
          )}
        </div>
        {hasNext && (
          <button onClick={() => { setIdx(i => i + 1); setZoom(1); }} className="p-2 rounded-full bg-white/10 text-white hover:bg-white/20 flex-shrink-0" data-testid="lightbox-next"><ChevronRight className="w-5 h-5" /></button>
        )}
      </div>

      <div className="p-3 flex items-center justify-center gap-2 flex-wrap">
        {tiposDisponiveis.map((t, i) => (
          <button
            key={t}
            onClick={() => { setIdx(i); setZoom(1); }}
            className={`px-3 py-1.5 rounded-full text-xs font-medium border ${i === idx ? 'bg-white text-black border-white' : 'bg-white/10 text-white border-white/20'}`}
            data-testid={`lightbox-tab-${t}`}
          >
            {LABEL_TIPO[t]}
          </button>
        ))}
      </div>

      {/* Comparação selfie vs doc frente quando ambos existem */}
      {tiposDisponiveis.includes('selfie') && tiposDisponiveis.includes('doc_frente') && (
        <div className="px-4 pb-4">
          <div className="max-w-3xl mx-auto grid grid-cols-2 gap-3">
            <div className="rounded-lg overflow-hidden bg-white p-1">
              <p className="text-[11px] font-medium text-center text-muted-foreground mb-1">Selfie</p>
              {urls.selfie ? <img src={urls.selfie} alt="Selfie" className="w-full h-28 object-cover rounded" /> : <div className="h-28 bg-muted" />}
            </div>
            <div className="rounded-lg overflow-hidden bg-white p-1">
              <p className="text-[11px] font-medium text-center text-muted-foreground mb-1">Doc. frente</p>
              {urls.doc_frente ? <img src={urls.doc_frente} alt="Doc frente" className="w-full h-28 object-cover rounded" /> : <div className="h-28 bg-muted" />}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SolicitacaoCard({ s, onAprovar, onRejeitar, onExcluir, processando, navigate }) {
  const { urls, loading } = useAnexoUrls(s);
  const [lightboxTipo, setLightboxTipo] = useState(null);
  const [baixandoPdf, setBaixandoPdf] = useState(false);
  const anexosEntries = TIPOS_ANEXO.filter(t => s.anexos?.[t.key]?.path);
  const temAnexos = anexosEntries.length > 0;

  const handleBaixarPdf = async (e) => {
    e?.stopPropagation?.();
    setBaixandoPdf(true);
    try {
      const res = await cadastroPublicoAPI.baixarPdf(s.id);
      const blob = new Blob([res.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const safeNome = (s.nome || 'cliente').toLowerCase().replace(/[^a-z0-9]/g, '-');
      link.download = `ficha-cadastral-${safeNome}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Erro ao baixar ficha PDF:', err);
      alert('Não foi possível gerar a ficha em PDF.');
    } finally {
      setBaixandoPdf(false);
    }
  };

  return (
    <div className="bg-card border border-border rounded-xl p-4" data-testid={`solicitacao-${s.id}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold text-foreground truncate">{s.nome}</h3>
          <p className="text-xs text-muted-foreground">{formatarData(s.created_at)}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {s.cpf_cnpj && <span className="text-xs font-mono text-muted-foreground">{formatarCpfCnpj(s.cpf_cnpj)}</span>}
          <button
            onClick={handleBaixarPdf}
            disabled={baixandoPdf}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-muted text-foreground text-xs font-medium hover:bg-muted/70 transition-colors disabled:opacity-50"
            data-testid={`btn-pdf-${s.id}`}
            title="Baixar Ficha Cadastral em PDF"
          >
            {baixandoPdf ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileDown className="w-3.5 h-3.5 text-primary" />}
            <span className="hidden sm:inline">Ficha PDF</span>
          </button>
        </div>
      </div>

      <div className="mt-3 space-y-1.5 text-sm">
        <p className="flex items-center gap-2 text-muted-foreground"><Phone className="w-3.5 h-3.5" /> {formatarTelefone(s.telefone)}</p>
        {s.email && <p className="flex items-center gap-2 text-muted-foreground"><Mail className="w-3.5 h-3.5" /> {s.email}</p>}
        {s.endereco && (s.endereco.rua || s.endereco.cidade) && (
          <p className="flex items-center gap-2 text-muted-foreground">
            <MapPin className="w-3.5 h-3.5" />
            {[s.endereco.rua, s.endereco.numero, s.endereco.bairro, s.endereco.cidade, s.endereco.estado].filter(Boolean).join(', ')}
          </p>
        )}
        {s.observacoes && <p className="text-xs text-muted-foreground italic mt-1">"{s.observacoes}"</p>}
        {/* Dados financeiros */}
        {(s.tipo_emprego || s.renda_mensal || s.valor_emprestimo) && (
          <div className="mt-2 pt-2 border-t border-border/50 grid grid-cols-1 sm:grid-cols-3 gap-x-4 gap-y-1">
            {s.tipo_emprego && (
              <p className="text-xs text-muted-foreground"><span className="font-medium text-foreground/70">Emprego:</span> {s.tipo_emprego}</p>
            )}
            {s.renda_mensal && (
              <p className="text-xs text-muted-foreground"><span className="font-medium text-foreground/70">Renda:</span> R$ {s.renda_mensal}</p>
            )}
            {s.valor_emprestimo && (
              <p className="text-xs text-emerald-600 dark:text-emerald-400"><span className="font-medium">Empréstimo:</span> R$ {s.valor_emprestimo}</p>
            )}
          </div>
        )}
        {s.status === 'rejeitado' && s.motivo_rejeicao && (
          <p className="text-xs text-red-500 mt-1">Motivo: {s.motivo_rejeicao}</p>
        )}
      </div>

      {/* Anexos */}
      <div className="mt-3" data-testid={`anexos-${s.id}`}>
        {!temAnexos ? (
          <p className="text-xs text-muted-foreground border border-dashed border-border rounded-lg px-3 py-2 text-center">Sem anexos</p>
        ) : (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {TIPOS_ANEXO.map(t => {
                const meta = s.anexos?.[t.key];
                const has = !!meta?.path;
                const url = urls[t.key];
                const Icon = t.icon;
                return (
                  <button
                    key={t.key}
                    type="button"
                    disabled={!has}
                    onClick={() => has && setLightboxTipo(t.key)}
                    className={`relative rounded-lg border overflow-hidden text-left group ${has ? 'border-border hover:border-primary cursor-pointer' : 'border-dashed border-border bg-muted/20 cursor-default opacity-60'}`}
                    data-testid={`anexo-thumb-${s.id}-${t.key}`}
                    title={has ? `Ver ${t.label}` : `${t.label} não enviado`}
                  >
                    {has && url ? (
                      <img src={url} alt={t.label} className="w-full h-20 object-cover" />
                    ) : has ? (
                      <div className="w-full h-20 flex items-center justify-center bg-muted">
                        {loading ? <span className="text-xs text-muted-foreground">Carregando…</span> : <Icon className="w-5 h-5 text-muted-foreground" />}
                      </div>
                    ) : (
                      <div className="w-full h-20 flex flex-col items-center justify-center gap-1">
                        <Icon className="w-4 h-4 text-muted-foreground" />
                        <span className="text-[10px] text-muted-foreground">{t.label}</span>
                      </div>
                    )}
                    <span className={`absolute bottom-0 left-0 right-0 text-[10px] font-medium px-1.5 py-0.5 text-center ${has ? 'bg-black/60 text-white' : 'bg-transparent text-muted-foreground'}`}>{t.label}</span>
                    {has && <span className="absolute top-1 right-1 bg-black/60 text-white rounded p-1 opacity-0 group-hover:opacity-100 transition-opacity"><Eye className="w-3 h-3" /></span>}
                  </button>
                );
              })}
            </div>
            {s.consentimento?.aceito && (
              <p className="text-[11px] text-muted-foreground mt-1.5">✓ Consentimento {s.consentimento.versao_termo || 'v1'} em {formatarData(s.consentimento.aceito_em)}</p>
            )}
          </>
        )}
      </div>

      {lightboxTipo && (
        <Lightbox
          solicitacao={s}
          initialTipo={lightboxTipo}
          urls={urls}
          onClose={() => setLightboxTipo(null)}
          onBaixarPdf={handleBaixarPdf}
          baixandoPdf={baixandoPdf}
        />
      )}

      {s.status === 'pendente' && (
        <div className="mt-4 flex items-center gap-2">
          <button
            onClick={() => onAprovar(s)}
            disabled={processando === s.id}
            className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-sm font-medium hover:bg-emerald-500/20 transition-colors disabled:opacity-50"
            data-testid={`btn-aprovar-${s.id}`}
          >
            <Check className="w-4 h-4" /> Aprovar
          </button>
          <button
            onClick={() => onRejeitar(s)}
            disabled={processando === s.id}
            className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-red-500/10 text-red-500 text-sm font-medium hover:bg-red-500/20 transition-colors disabled:opacity-50"
            data-testid={`btn-rejeitar-${s.id}`}
          >
            <X className="w-4 h-4" /> Rejeitar
          </button>
        </div>
      )}

      {s.status === 'aprovado' && (
        <div className="mt-4 flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400"><CheckCircle2 className="w-4 h-4" /> Aprovado</span>
          {s.cliente_id && (
            <button onClick={() => navigate('/clientes')} className="text-xs text-primary hover:underline" data-testid={`btn-ver-cliente-${s.id}`}>Ver em Clientes</button>
          )}
        </div>
      )}

      {s.status === 'rejeitado' && (
        <div className="mt-4 flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-red-500"><XCircle className="w-4 h-4" /> Rejeitado</span>
          <button onClick={() => onExcluir(s)} className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-red-500 transition-colors" data-testid={`btn-excluir-${s.id}`}>
            <Trash2 className="w-3.5 h-3.5" /> Remover
          </button>
        </div>
      )}
    </div>
  );
}

const Aprovacoes = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const modal = useModal();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [link, setLink] = useState('');
  const [copiado, setCopiado] = useState(false);
  const [solicitacoes, setSolicitacoes] = useState([]);
  const [filtro, setFiltro] = useState('pendente');
  const [processando, setProcessando] = useState(null);

  const carregar = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const [linkRes, solRes] = await Promise.all([
        cadastroPublicoAPI.obterLink(),
        cadastroPublicoAPI.listarSolicitacoes(),
      ]);
      setLink(linkRes.data.url);
      setSolicitacoes(solRes.data || []);
    } catch (err) {
      console.error('Erro ao carregar aprovações:', err);
      setError('Não foi possível carregar as aprovações.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  const copiarLink = () => {
    navigator.clipboard.writeText(link);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 2000);
  };

  const regenerar = async () => {
    const ok = await modal.confirm('Gerar novo link?', 'O link atual deixará de funcionar.', 'Quem já tiver o link antigo não conseguirá mais enviar cadastro.');
    if (!ok) return;
    try {
      const { data } = await cadastroPublicoAPI.regenerarLink();
      setLink(data.url);
      modal.success('Novo link gerado', 'Compartilhe o novo link com seus clientes.');
    } catch {
      modal.error('Erro', 'Não foi possível gerar um novo link.');
    }
  };

  const aprovar = async (s) => {
    setProcessando(s.id);
    try {
      const { data } = await cadastroPublicoAPI.aprovar(s.id);
      const clienteId = data?.cliente_id;
      const criar = await modal.confirm(
        'Cliente aprovado!',
        `${s.nome} agora é seu cliente. Deseja criar um empréstimo para ${s.nome} agora?`,
        'Você pode fazer isso depois na tela de Empréstimos.'
      );
      if (criar && clienteId) {
        navigate(`/emprestimos?novoCliente=${clienteId}`);
        return;
      }
      carregar();
    } catch (err) {
      modal.error('Erro ao aprovar', err.response?.data?.detail || 'Falha ao aprovar cadastro.');
    } finally {
      setProcessando(null);
    }
  };

  const rejeitar = async (s) => {
    const ok = await modal.confirm('Rejeitar cadastro?', `Rejeitar o cadastro de ${s.nome}?`, 'A ficha ficará marcada como rejeitada.');
    if (!ok) return;
    setProcessando(s.id);
    try {
      await cadastroPublicoAPI.rejeitar(s.id, '');
      modal.success('Cadastro rejeitado', 'A ficha foi marcada como rejeitada.');
      carregar();
    } catch (err) {
      modal.error('Erro ao rejeitar', err.response?.data?.detail || 'Falha ao rejeitar.');
    } finally {
      setProcessando(null);
    }
  };

  const excluir = async (s) => {
    const ok = await modal.confirm('Remover solicitação?', `Remover a ficha de ${s.nome} da lista?`, 'Esta ação não pode ser desfeita.');
    if (!ok) return;
    try {
      await cadastroPublicoAPI.excluir(s.id);
      carregar();
    } catch {
      modal.error('Erro', 'Não foi possível remover.');
    }
  };

  const contagem = {
    pendente: solicitacoes.filter(s => s.status === 'pendente').length,
    aprovado: solicitacoes.filter(s => s.status === 'aprovado').length,
    rejeitado: solicitacoes.filter(s => s.status === 'rejeitado').length,
  };
  const filtradas = solicitacoes.filter(s => s.status === filtro);

  if (loading) return <Loading message="Carregando aprovações..." />;

  const tabs = [
    { id: 'pendente', label: 'Pendentes', icon: Clock, cor: 'amber', count: contagem.pendente },
    { id: 'aprovado', label: 'Aprovados', icon: CheckCircle2, cor: 'emerald', count: contagem.aprovado },
    { id: 'rejeitado', label: 'Rejeitados', icon: XCircle, cor: 'red', count: contagem.rejeitado },
  ];

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground flex items-center gap-2" data-testid="aprovacoes-title">
            <UserPlus className="w-7 h-7 text-primary" /> Cadastros & Aprovações
          </h1>
          <p className="text-muted-foreground mt-1">Compartilhe seu link, receba fichas e aprove novos clientes</p>
        </div>

        {error && <ErrorMessage message={error} onRetry={carregar} />}

        <div className="bg-card border border-border rounded-xl p-5 mb-6" data-testid="link-publico-card">
          <div className="flex items-center gap-2 mb-3">
            <Link2 className="w-5 h-5 text-primary" />
            <h2 className="font-semibold text-foreground">Seu link de cadastro público</h2>
          </div>
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              readOnly
              value={link}
              className="flex-1 px-3 py-2.5 bg-background border border-border rounded-lg text-foreground text-sm font-mono"
              data-testid="input-link-publico"
              onFocus={(e) => e.target.select()}
            />
            <div className="flex gap-2">
              <button onClick={copiarLink} className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity" data-testid="btn-copiar-link">
                {copiado ? <><Check className="w-4 h-4" /> Copiado</> : <><Copy className="w-4 h-4" /> Copiar</>}
              </button>
              <a href={link} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-muted text-foreground text-sm font-medium hover:bg-muted/70 transition-colors" data-testid="btn-abrir-link">
                <ExternalLink className="w-4 h-4" /> Abrir
              </a>
              <button onClick={regenerar} className="inline-flex items-center gap-1.5 px-3 py-2.5 rounded-lg bg-muted text-muted-foreground text-sm font-medium hover:bg-muted/70 transition-colors" data-testid="btn-regenerar-link" title="Gerar novo link">
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>
          <p className="text-xs text-muted-foreground mt-2">Envie este link pelo WhatsApp. O cliente preenche a ficha e ela aparece aqui como pendente.</p>
        </div>

        <div className="flex gap-2 mb-4 flex-wrap">
          {tabs.map(t => {
            const Icon = t.icon;
            const active = filtro === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setFiltro(t.id)}
                className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${active ? 'bg-primary text-primary-foreground' : 'bg-muted/40 text-muted-foreground hover:text-foreground'}`}
                data-testid={`tab-${t.id}`}
              >
                <Icon className="w-4 h-4" /> {t.label}
                <span className={`ml-1 px-1.5 py-0.5 rounded-full text-xs font-bold ${active ? 'bg-white/20' : 'bg-background'}`}>{t.count}</span>
              </button>
            );
          })}
        </div>

        {filtradas.length === 0 ? (
          <div className="bg-card border border-border rounded-xl p-10 text-center" data-testid="lista-vazia">
            <p className="text-muted-foreground">Nenhum cadastro {filtro === 'pendente' ? 'pendente' : filtro === 'aprovado' ? 'aprovado' : 'rejeitado'}.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="lista-solicitacoes">
            {filtradas.map(s => (
              <SolicitacaoCard key={s.id} s={s} onAprovar={aprovar} onRejeitar={rejeitar} onExcluir={excluir} processando={processando} navigate={navigate} />
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
};

export default Aprovacoes;
