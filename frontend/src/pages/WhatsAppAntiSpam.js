import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import Button from '../components/Button';
import { whatsappAPI } from '../api/api';
import { 
  Shield, 
  Clock, 
  TrendingUp, 
  Play, 
  Pause, 
  RefreshCw, 
  BarChart3,
  AlertCircle,
  CheckCircle,
  XCircle,
  Zap,
  Calendar,
  MessageSquare
} from 'lucide-react';
import { useToast } from '../hooks/use-toast';

const WhatsAppAntiSpam = () => {
  const [config, setConfig] = useState(null);
  const [status, setStatus] = useState(null);
  const [estatisticas, setEstatisticas] = useState(null);
  const [fila, setFila] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [processando, setProcessando] = useState(false);
  const { toast } = useToast();

  const carregarDados = useCallback(async () => {
    try {
      const [configRes, statusRes, statsRes, filaRes] = await Promise.all([
        whatsappAPI.obterConfigAntiSpam(),
        whatsappAPI.verificarStatusAntiSpam(),
        whatsappAPI.obterEstatisticasFila(),
        whatsappAPI.listarFila(null, 10)
      ]);

      setConfig(configRes.data);
      setStatus(statusRes.data);
      setEstatisticas(statsRes.data);
      setFila(filaRes.data.mensagens || []);
    } catch (error) {
      console.error('Erro ao carregar dados:', error);
      toast({
        title: "Erro ao carregar",
        description: "Não foi possível carregar as configurações",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    carregarDados();
    
    // Atualizar a cada 10 segundos
    const interval = setInterval(carregarDados, 10000);
    return () => clearInterval(interval);
  }, [carregarDados]);

  const handleSalvarConfig = async (updates) => {
    try {
      setSaving(true);
      await whatsappAPI.atualizarConfigAntiSpam(updates);
      
      toast({
        title: "✅ Configurações salvas!",
        description: "As configurações foram atualizadas com sucesso",
        variant: "default"
      });
      
      await carregarDados();
    } catch (error) {
      console.error('Erro ao salvar:', error);
      toast({
        title: "Erro ao salvar",
        description: error.response?.data?.detail || "Erro ao atualizar configurações",
        variant: "destructive"
      });
    } finally {
      setSaving(false);
    }
  };

  const handleProcessarFila = async () => {
    try {
      setProcessando(true);
      const response = await whatsappAPI.processarFila(100);
      
      toast({
        title: "✅ Fila processada!",
        description: `${response.data.enviadas} enviadas, ${response.data.aguardando} aguardando, ${response.data.erro} erros`,
        variant: "default"
      });
      
      await carregarDados();
    } catch (error) {
      console.error('Erro ao processar:', error);
      toast({
        title: "Erro ao processar",
        description: error.response?.data?.detail || "Erro ao processar fila",
        variant: "destructive"
      });
    } finally {
      setProcessando(false);
    }
  };

  const handleToggleWarmingUp = async () => {
    try {
      if (config.warming_up_ativo) {
        await whatsappAPI.desativarWarmingUp();
        toast({
          title: "Warming Up desativado",
          description: "Modo de aquecimento foi desativado",
          variant: "default"
        });
      } else {
        await whatsappAPI.ativarWarmingUp();
        toast({
          title: "✅ Warming Up ativado!",
          description: "O sistema vai aumentar gradualmente o limite de envios nos próximos 14 dias",
          variant: "default"
        });
      }
      
      await carregarDados();
    } catch (error) {
      console.error('Erro:', error);
      toast({
        title: "Erro",
        description: error.response?.data?.detail || "Erro ao alterar warming up",
        variant: "destructive"
      });
    }
  };

  const handleReprocessarFalhadas = async () => {
    try {
      const response = await whatsappAPI.reprocessarFalhadas();
      
      toast({
        title: "✅ Mensagens reprocessadas!",
        description: response.data.message,
        variant: "default"
      });
      
      await carregarDados();
    } catch (error) {
      toast({
        title: "Erro",
        description: "Erro ao reprocessar mensagens falhadas",
        variant: "destructive"
      });
    }
  };

  const getDiaNome = (dia) => {
    const nomes = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];
    return nomes[dia];
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-foreground flex items-center gap-3">
              <Shield className="w-8 h-8 text-blue-500" />
              Anti-Spam WhatsApp
            </h1>
            <p className="text-muted-foreground mt-2">
              Configure limites e proteções para evitar bloqueios do WhatsApp
            </p>
          </div>
          
          <Button
            onClick={carregarDados}
            variant="outline"
            className="flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Atualizar
          </Button>
        </div>

        {/* Status Atual */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-card border border-border rounded-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">Status</span>
              {status?.pode_enviar ? (
                <CheckCircle className="w-5 h-5 text-green-500" />
              ) : (
                <XCircle className="w-5 h-5 text-red-500" />
              )}
            </div>
            <p className="text-2xl font-bold text-foreground">
              {status?.pode_enviar ? 'Pronto' : 'Bloqueado'}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {status?.razao || 'Pode enviar mensagens'}
            </p>
          </div>

          <div className="bg-card border border-border rounded-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">Hoje</span>
              <MessageSquare className="w-5 h-5 text-blue-500" />
            </div>
            <p className="text-2xl font-bold text-foreground">
              {status?.contador_hoje || 0} / {status?.limite_diario || 0}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Mensagens enviadas
            </p>
          </div>

          <div className="bg-card border border-border rounded-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">Na Fila</span>
              <Clock className="w-5 h-5 text-yellow-500" />
            </div>
            <p className="text-2xl font-bold text-foreground">
              {estatisticas?.pendentes || 0}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Mensagens aguardando
            </p>
          </div>

          <div className="bg-card border border-border rounded-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">Qualidade</span>
              <BarChart3 className="w-5 h-5 text-green-500" />
            </div>
            <p className="text-2xl font-bold text-foreground">
              {status?.taxa_qualidade?.toFixed(1) || 100}%
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Taxa de sucesso
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Configurações Principais */}
          <div className="lg:col-span-2 space-y-6">
            {/* Horário e Dias */}
            <div className="bg-card border border-border rounded-lg p-6">
              <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <Calendar className="w-5 h-5 text-blue-500" />
                Horário Comercial
              </h3>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-muted/30 rounded-lg">
                  <div>
                    <p className="font-medium text-foreground">Enviar fora do horário comercial</p>
                    <p className="text-sm text-muted-foreground">
                      Permite envios 24/7 sem restrição de horário
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config?.enviar_fora_horario || false}
                      onChange={(e) => handleSalvarConfig({ enviar_fora_horario: e.target.checked })}
                      disabled={saving}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-500"></div>
                  </label>
                </div>

                {!config?.enviar_fora_horario && (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-foreground mb-2">
                        Horário Início
                      </label>
                      <input
                        type="time"
                        value={config?.horario_inicio || '08:00'}
                        onChange={(e) => handleSalvarConfig({ horario_inicio: e.target.value })}
                        disabled={saving}
                        className="w-full px-4 py-2 bg-background border border-border rounded-lg text-foreground"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-foreground mb-2">
                        Horário Fim
                      </label>
                      <input
                        type="time"
                        value={config?.horario_fim || '20:00'}
                        onChange={(e) => handleSalvarConfig({ horario_fim: e.target.value })}
                        disabled={saving}
                        className="w-full px-4 py-2 bg-background border border-border rounded-lg text-foreground"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Limites */}
            <div className="bg-card border border-border rounded-lg p-6">
              <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-blue-500" />
                Limites de Envio
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Limite Diário
                  </label>
                  <input
                    type="number"
                    value={config?.limite_diario || 1000}
                    onChange={(e) => handleSalvarConfig({ limite_diario: parseInt(e.target.value) })}
                    disabled={saving || config?.warming_up_ativo}
                    className="w-full px-4 py-2 bg-background border border-border rounded-lg text-foreground"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Máximo de mensagens por dia
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Delay entre Envios (seg)
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      type="number"
                      value={config?.delay_minimo || 30}
                      onChange={(e) => handleSalvarConfig({ delay_minimo: parseInt(e.target.value) })}
                      disabled={saving}
                      placeholder="Min"
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground text-sm"
                    />
                    <input
                      type="number"
                      value={config?.delay_maximo || 90}
                      onChange={(e) => handleSalvarConfig({ delay_maximo: parseInt(e.target.value) })}
                      disabled={saving}
                      placeholder="Max"
                      className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground text-sm"
                    />
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Intervalo aleatório entre mensagens
                  </p>
                </div>
              </div>
            </div>

            {/* Warming Up */}
            <div className="bg-card border border-border rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Zap className="w-5 h-5 text-yellow-500" />
                  <h3 className="text-lg font-semibold text-foreground">
                    Warming Up
                  </h3>
                </div>
                <Button
                  onClick={handleToggleWarmingUp}
                  variant={config?.warming_up_ativo ? "destructive" : "default"}
                  size="sm"
                >
                  {config?.warming_up_ativo ? 'Desativar' : 'Ativar'}
                </Button>
              </div>

              <p className="text-sm text-muted-foreground mb-4">
                {config?.warming_up_ativo ? (
                  <>
                    <span className="text-green-500 font-medium">✓ Ativo</span> - 
                    Dia {config?.warming_up_dia || 0} de 14. 
                    O sistema está aumentando gradualmente o limite de envios.
                  </>
                ) : (
                  <>
                    Recomendado para números novos. Aumenta gradualmente o limite de envios 
                    nos primeiros 14 dias para evitar bloqueios.
                  </>
                )}
              </p>

              {config?.warming_up_ativo && (
                <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
                  <p className="text-sm text-yellow-600 dark:text-yellow-400">
                    ⚠️ Enquanto o warming up estiver ativo, você não poderá alterar manualmente o limite diário.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Painel Lateral */}
          <div className="space-y-6">
            {/* Ações Rápidas */}
            <div className="bg-card border border-border rounded-lg p-6">
              <h3 className="text-lg font-semibold text-foreground mb-4">
                Ações Rápidas
              </h3>

              <div className="space-y-3">
                <Button
                  onClick={handleProcessarFila}
                  loading={processando}
                  className="w-full flex items-center justify-center gap-2"
                  data-testid="processar-fila-btn"
                >
                  <Play className="w-4 h-4" />
                  Processar Fila Agora
                </Button>

                {estatisticas?.falhadas > 0 && (
                  <Button
                    onClick={handleReprocessarFalhadas}
                    variant="outline"
                    className="w-full flex items-center justify-center gap-2"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Reprocessar Falhadas ({estatisticas.falhadas})
                  </Button>
                )}
              </div>
            </div>

            {/* Fila Recente */}
            <div className="bg-card border border-border rounded-lg p-6">
              <h3 className="text-lg font-semibold text-foreground mb-4">
                Fila Recente
              </h3>

              {fila.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  Nenhuma mensagem na fila
                </p>
              ) : (
                <div className="space-y-3">
                  {fila.slice(0, 5).map((msg) => (
                    <div
                      key={msg._id}
                      className="p-3 bg-muted/30 rounded-lg border border-border"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-foreground">
                          {msg.cliente_nome}
                        </span>
                        <span className={`text-xs px-2 py-1 rounded ${
                          msg.status === 'pendente' 
                            ? 'bg-yellow-500/10 text-yellow-600' 
                            : msg.status === 'enviada'
                            ? 'bg-green-500/10 text-green-600'
                            : 'bg-red-500/10 text-red-600'
                        }`}>
                          {msg.status}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {msg.numero}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Estatísticas */}
            <div className="bg-card border border-border rounded-lg p-6">
              <h3 className="text-lg font-semibold text-foreground mb-4">
                Estatísticas
              </h3>

              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Pendentes</span>
                  <span className="text-sm font-medium text-foreground">
                    {estatisticas?.pendentes || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Enviadas</span>
                  <span className="text-sm font-medium text-green-600">
                    {estatisticas?.enviadas || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-muted-foreground">Falhadas</span>
                  <span className="text-sm font-medium text-red-600">
                    {estatisticas?.falhadas || 0}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default WhatsAppAntiSpam;
