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
  XCircle, Phone, Mail, MapPin, ExternalLink
} from 'lucide-react';

const Aprovacoes = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isMember = !!user?.owner_id;
  const modal = useModal();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [link, setLink] = useState('');
  const [copiado, setCopiado] = useState(false);
  const [solicitacoes, setSolicitacoes] = useState([]);
  const [filtro, setFiltro] = useState('pendente');
  const [processando, setProcessando] = useState(null);

  useEffect(() => { if (isMember) navigate('/dashboard'); }, [isMember, navigate]);

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
      await cadastroPublicoAPI.aprovar(s.id);
      modal.success('Cadastro aprovado!', `${s.nome} agora é seu cliente.`);
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

        {/* Link público */}
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

        {/* Tabs */}
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

        {/* Lista */}
        {filtradas.length === 0 ? (
          <div className="bg-card border border-border rounded-xl p-10 text-center" data-testid="lista-vazia">
            <p className="text-muted-foreground">Nenhum cadastro {filtro === 'pendente' ? 'pendente' : filtro === 'aprovado' ? 'aprovado' : 'rejeitado'}.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="lista-solicitacoes">
            {filtradas.map(s => (
              <div key={s.id} className="bg-card border border-border rounded-xl p-4" data-testid={`solicitacao-${s.id}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="font-semibold text-foreground truncate">{s.nome}</h3>
                    <p className="text-xs text-muted-foreground">{formatarData(s.created_at)}</p>
                  </div>
                  {s.cpf_cnpj && <span className="text-xs font-mono text-muted-foreground">{formatarCpfCnpj(s.cpf_cnpj)}</span>}
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
                  {s.status === 'rejeitado' && s.motivo_rejeicao && (
                    <p className="text-xs text-red-500 mt-1">Motivo: {s.motivo_rejeicao}</p>
                  )}
                </div>

                {s.status === 'pendente' && (
                  <div className="mt-4 flex items-center gap-2">
                    <button
                      onClick={() => aprovar(s)}
                      disabled={processando === s.id}
                      className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-sm font-medium hover:bg-emerald-500/20 transition-colors disabled:opacity-50"
                      data-testid={`btn-aprovar-${s.id}`}
                    >
                      <Check className="w-4 h-4" /> Aprovar
                    </button>
                    <button
                      onClick={() => rejeitar(s)}
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
                    <button onClick={() => excluir(s)} className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-red-500 transition-colors" data-testid={`btn-excluir-${s.id}`}>
                      <Trash2 className="w-3.5 h-3.5" /> Remover
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
};

export default Aprovacoes;
