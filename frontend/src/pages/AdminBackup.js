import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  Database, Download, RotateCcw, Trash2, Plus,
  CheckCircle, AlertTriangle, Clock, HardDrive, RefreshCw,
  Shield, Archive, History
} from 'lucide-react';
import { useToast } from '../hooks/use-toast';

const API = process.env.REACT_APP_BACKEND_URL;

const formatBytes = (bytes) => {
  if (!bytes) return '0 B';
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
};

const formatDate = (iso) => {
  if (!iso) return 'N/A';
  try {
    return new Date(iso).toLocaleString('pt-BR');
  } catch {
    return iso;
  }
};

export default function AdminBackup() {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [backups, setBackups] = useState([]);
  const [logs, setLogs] = useState([]);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [criandoBackup, setCriandoBackup] = useState(false);
  const [restaurando, setRestaurando] = useState(null);
  const [deletando, setDeletando] = useState(null);
  const [confirmarRestore, setConfirmarRestore] = useState(null);
  const [activeTab, setActiveTab] = useState('backups');

  const headers = { Authorization: `Bearer ${token}` };

  const fetchDados = useCallback(async () => {
    try {
      const [resBackups, resStatus, resLogs] = await Promise.all([
        fetch(`${API}/api/backup/listar`, { headers }),
        fetch(`${API}/api/backup/status`, { headers }),
        fetch(`${API}/api/backup/logs?limit=20`, { headers }),
      ]);

      if (resBackups.ok) {
        const d = await resBackups.json();
        setBackups(d.backups || []);
      }
      if (resStatus.ok) {
        setStatus(await resStatus.json());
      }
      if (resLogs.ok) {
        const d = await resLogs.json();
        setLogs(d.logs || []);
      }
    } catch (e) {
      console.error('Erro ao carregar dados:', e);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (!user || user.perfil !== 'admin') {
      navigate('/dashboard');
      return;
    }
    fetchDados();
  }, [user, navigate, fetchDados]);

  const handleCriarBackup = async () => {
    setCriandoBackup(true);
    try {
      const res = await fetch(`${API}/api/backup/criar`, {
        method: 'POST',
        headers,
      });
      const data = await res.json();
      if (res.ok) {
        toast({ title: 'Backup criado!', description: data.mensagem });
        await fetchDados();
      } else {
        toast({ title: 'Erro', description: data.detail || 'Falha ao criar backup', variant: 'destructive' });
      }
    } catch (e) {
      toast({ title: 'Erro', description: 'Erro de conexão', variant: 'destructive' });
    } finally {
      setCriandoBackup(false);
    }
  };

  const handleRestaurar = async (nome) => {
    setRestaurando(nome);
    setConfirmarRestore(null);
    try {
      const res = await fetch(`${API}/api/backup/restaurar/${encodeURIComponent(nome)}`, {
        method: 'POST',
        headers,
      });
      const data = await res.json();
      if (res.ok) {
        toast({ title: 'Restore concluído!', description: data.mensagem });
        await fetchDados();
      } else {
        toast({ title: 'Erro no restore', description: data.detail, variant: 'destructive' });
      }
    } catch (e) {
      toast({ title: 'Erro', description: 'Erro de conexão', variant: 'destructive' });
    } finally {
      setRestaurando(null);
    }
  };

  const handleDeletar = async (nome) => {
    setDeletando(nome);
    try {
      const res = await fetch(`${API}/api/backup/deletar/${encodeURIComponent(nome)}`, {
        method: 'DELETE',
        headers,
      });
      const data = await res.json();
      if (res.ok) {
        toast({ title: 'Backup deletado', description: data.mensagem });
        setBackups(prev => prev.filter(b => b.nome !== nome));
      } else {
        toast({ title: 'Erro', description: data.detail, variant: 'destructive' });
      }
    } catch (e) {
      toast({ title: 'Erro', description: 'Erro de conexão', variant: 'destructive' });
    } finally {
      setDeletando(null);
    }
  };

  const handleDownload = (nome) => {
    window.open(`${API}/api/backup/download/${encodeURIComponent(nome)}?token=${token}`, '_blank');
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 animate-spin text-primary" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="p-6 max-w-6xl mx-auto space-y-6" data-testid="admin-backup-page">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-500/10 rounded-xl flex items-center justify-center">
              <Database className="w-5 h-5 text-amber-500" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">Backup & Restore</h1>
              <p className="text-sm text-muted-foreground">Proteja os dados do sistema com backups automáticos</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={fetchDados}
              className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              data-testid="btn-refresh"
            >
              <RefreshCw className="w-4 h-4" />
              Atualizar
            </button>
            <button
              onClick={handleCriarBackup}
              disabled={criandoBackup}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500 text-white text-sm font-medium hover:bg-amber-600 transition-colors disabled:opacity-60"
              data-testid="btn-criar-backup"
            >
              {criandoBackup ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Plus className="w-4 h-4" />
              )}
              {criandoBackup ? 'Criando...' : 'Fazer Backup Agora'}
            </button>
          </div>
        </div>

        {/* Cards de status */}
        {status && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-card border border-border rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Archive className="w-4 h-4 text-blue-400" />
                <span className="text-sm text-muted-foreground">Total de Backups</span>
              </div>
              <p className="text-2xl font-bold text-foreground" data-testid="total-backups">{status.total_backups}</p>
              <p className="text-xs text-muted-foreground mt-1">Máx. {status.max_backups} mantidos</p>
            </div>
            <div className="bg-card border border-border rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-4 h-4 text-green-400" />
                <span className="text-sm text-muted-foreground">Último Backup</span>
              </div>
              <p className="text-sm font-medium text-foreground">
                {status.ultimo_backup ? formatDate(status.ultimo_backup.criado_em) : 'Nenhum ainda'}
              </p>
              {status.ultimo_backup && (
                <p className="text-xs text-muted-foreground mt-1">{formatBytes(status.ultimo_backup.tamanho_bytes)}</p>
              )}
            </div>
            <div className="bg-card border border-border rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Shield className="w-4 h-4 text-amber-400" />
                <span className="text-sm text-muted-foreground">Próximo Auto Backup</span>
              </div>
              <p className="text-sm font-medium text-foreground">A cada 6 horas</p>
              <p className="text-xs text-green-400 mt-1 flex items-center gap-1">
                <CheckCircle className="w-3 h-3" /> Job ativo
              </p>
            </div>
          </div>
        )}

        {/* Alerta informativo */}
        <div className="flex items-start gap-3 p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl">
          <AlertTriangle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-blue-400">Informação importante</p>
            <p className="text-xs text-muted-foreground mt-1">
              O restore substitui <strong>todos os dados atuais</strong> pelos dados do backup selecionado.
              Esta operação é irreversível. Use com cuidado.
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-border">
          <div className="flex gap-1">
            {[
              { id: 'backups', label: 'Backups Disponíveis', icon: HardDrive },
              { id: 'logs', label: 'Histórico', icon: History },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-amber-500 text-amber-500'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
                data-testid={`tab-${tab.id}`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
                {tab.id === 'backups' && (
                  <span className="ml-1 px-1.5 py-0.5 text-xs bg-amber-500/10 text-amber-500 rounded-full">
                    {backups.length}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Tab: Backups */}
        {activeTab === 'backups' && (
          <div>
            {backups.length === 0 ? (
              <div className="text-center py-16 text-muted-foreground">
                <Database className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p className="text-sm">Nenhum backup disponível.</p>
                <p className="text-xs mt-1">Clique em "Fazer Backup Agora" para criar o primeiro.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {backups.map((backup, idx) => (
                  <div
                    key={backup.nome}
                    className="flex items-center justify-between p-4 bg-card border border-border rounded-xl hover:border-amber-500/30 transition-colors"
                    data-testid={`backup-item-${idx}`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
                        idx === 0 ? 'bg-green-500/10' : 'bg-muted'
                      }`}>
                        <Archive className={`w-4 h-4 ${idx === 0 ? 'text-green-400' : 'text-muted-foreground'}`} />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-foreground truncate">{backup.nome}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatDate(backup.criado_em)} · {formatBytes(backup.tamanho_bytes)}
                        </p>
                      </div>
                      {idx === 0 && (
                        <span className="ml-2 text-xs px-2 py-0.5 bg-green-500/10 text-green-400 rounded-full flex-shrink-0">
                          Mais recente
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0 ml-4">
                      {/* Download */}
                      <button
                        onClick={() => handleDownload(backup.nome)}
                        className="p-2 rounded-lg text-muted-foreground hover:text-blue-400 hover:bg-blue-400/10 transition-colors"
                        title="Download"
                        data-testid={`btn-download-${idx}`}
                      >
                        <Download className="w-4 h-4" />
                      </button>

                      {/* Restore */}
                      {confirmarRestore === backup.nome ? (
                        <div className="flex items-center gap-1">
                          <span className="text-xs text-amber-400">Confirmar?</span>
                          <button
                            onClick={() => handleRestaurar(backup.nome)}
                            disabled={restaurando === backup.nome}
                            className="px-2 py-1 text-xs bg-amber-500 text-white rounded-lg hover:bg-amber-600 disabled:opacity-60"
                            data-testid={`btn-confirmar-restore-${idx}`}
                          >
                            {restaurando === backup.nome ? '...' : 'Sim'}
                          </button>
                          <button
                            onClick={() => setConfirmarRestore(null)}
                            className="px-2 py-1 text-xs border border-border text-muted-foreground rounded-lg hover:text-foreground"
                          >
                            Não
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setConfirmarRestore(backup.nome)}
                          disabled={!!restaurando}
                          className="p-2 rounded-lg text-muted-foreground hover:text-amber-400 hover:bg-amber-400/10 transition-colors disabled:opacity-40"
                          title="Restaurar este backup"
                          data-testid={`btn-restaurar-${idx}`}
                        >
                          <RotateCcw className="w-4 h-4" />
                        </button>
                      )}

                      {/* Delete */}
                      <button
                        onClick={() => handleDeletar(backup.nome)}
                        disabled={deletando === backup.nome}
                        className="p-2 rounded-lg text-muted-foreground hover:text-red-400 hover:bg-red-400/10 transition-colors disabled:opacity-40"
                        title="Deletar backup"
                        data-testid={`btn-deletar-${idx}`}
                      >
                        {deletando === backup.nome ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                          <Trash2 className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab: Logs */}
        {activeTab === 'logs' && (
          <div>
            {logs.length === 0 ? (
              <div className="text-center py-16 text-muted-foreground">
                <History className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p className="text-sm">Nenhum log de backup ainda.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {logs.map((log, idx) => (
                  <div
                    key={log.id || idx}
                    className="flex items-center justify-between p-3 bg-card border border-border rounded-xl text-sm"
                    data-testid={`log-item-${idx}`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                        log.status === 'sucesso' ? 'bg-green-400' : 'bg-red-400'
                      }`} />
                      <div className="min-w-0">
                        <span className={`text-xs px-2 py-0.5 rounded-full mr-2 ${
                          log.tipo === 'automatico'
                            ? 'bg-blue-500/10 text-blue-400'
                            : log.tipo === 'manual'
                            ? 'bg-amber-500/10 text-amber-400'
                            : 'bg-purple-500/10 text-purple-400'
                        }`}>
                          {log.tipo === 'automatico' ? 'Auto' : log.tipo === 'manual' ? 'Manual' : 'Restore'}
                        </span>
                        <span className="text-muted-foreground truncate">
                          {log.arquivo || log.erro || '—'}
                        </span>
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground flex-shrink-0 ml-4">
                      {log.tamanho_mb && <span className="mr-2">{log.tamanho_mb} MB</span>}
                      {formatDate(log.created_at)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
}
