import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import Button from '../components/Button';
import { useToast } from '../hooks/use-toast';
import { configuracoesAPI, whatsappAPI } from '../api/api';
import { Copy, Trash2, Edit, Eye, Plus, Save, X } from 'lucide-react';

const ConfigNotificacoes = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('notificacoes'); // 'notificacoes' ou 'templates'

  // Estados para Templates
  const [templates, setTemplates] = useState([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [previewTemplate, setPreviewTemplate] = useState('');
  const [filtroTipo, setFiltroTipo] = useState('');
  
  // Formulário de template
  const [templateForm, setTemplateForm] = useState({
    nome: '',
    tipo: 'cobranca',
    mensagem: '',
    descricao: '',
    ativo: true
  });

  // Configurações de Notificações
  const [notificacoesConfig, setNotificacoesConfig] = useState({
    periodos: [
      { dias: 3, momento: 'antes', ativo: true, hora_envio: '09:00' },
      { dias: 0, momento: 'no_dia', ativo: true, hora_envio: '09:00' },
      { dias: 3, momento: 'depois', ativo: true, hora_envio: '10:00' }
    ],
    canais: {
      sistema: true,
      whatsapp: false,
      email: false
    },
    template_whatsapp: "Olá {cliente_nome}! 👋\n\nParcela #{numero} de R$ {valor} vence em {dias} dias.\n\nData de vencimento: {data_vencimento}",
    template_whatsapp_atraso: "Olá {cliente_nome}! ⚠️\n\nA parcela #{numero} de R$ {valor} está em atraso há {dias} dias.\n\nData de vencimento: {data_vencimento}\n\nPor favor, regularize sua situação.",
    enviar_para_cliente: true,
    ativo: true
  });

  const carregarNotificacoesConfig = useCallback(async () => {
    try {
      const response = await configuracoesAPI.obterNotificacoes();
      if (response.data) {
        setNotificacoesConfig(response.data);
      }
    } catch (error) {
      console.error('Erro ao carregar configurações de notificações:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    carregarNotificacoesConfig();
  }, [carregarNotificacoesConfig]);

  const handleSaveNotificacoesConfig = async () => {
    try {
      setSaving(true);
      await configuracoesAPI.atualizarNotificacoes(notificacoesConfig);
      toast({
        title: "✅ Configurações Salvas!",
        description: "As notificações automáticas foram configuradas com sucesso.",
        variant: "default",
      });
      await carregarNotificacoesConfig();
    } catch (err) {
      toast({
        title: "❌ Erro ao Salvar",
        description: err.response?.data?.detail || 'Erro ao salvar configurações de notificações',
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleRestaurarNotificacoesPadrao = async () => {
    try {
      setSaving(true);
      const response = await configuracoesAPI.restaurarNotificacoesPadrao();
      setNotificacoesConfig(response.data.dados);
      toast({
        title: "✅ Configurações Restauradas!",
        description: "As configurações padrão foram restauradas.",
        variant: "default",
      });
    } catch (err) {
      toast({
        title: "❌ Erro",
        description: err.response?.data?.detail || 'Erro ao restaurar configurações',
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const adicionarPeriodo = () => {
    setNotificacoesConfig(prev => ({
      ...prev,
      periodos: [
        ...prev.periodos,
        { dias: 1, momento: 'antes', ativo: true, hora_envio: '09:00' }
      ]
    }));
  };

  const removerPeriodo = (index) => {
    setNotificacoesConfig(prev => ({
      ...prev,
      periodos: prev.periodos.filter((_, i) => i !== index)
    }));
  };

  const atualizarPeriodo = (index, campo, valor) => {
    setNotificacoesConfig(prev => ({
      ...prev,
      periodos: prev.periodos.map((p, i) => 
        i === index ? { ...p, [campo]: valor } : p
      )
    }));
  };

  // ===== FUNÇÕES DE TEMPLATES =====
  
  const carregarTemplates = async () => {
    try {
      setLoadingTemplates(true);
      const response = await whatsappAPI.listarTemplates(filtroTipo || null);
      setTemplates(response.data.templates || []);
    } catch (error) {
      console.error('Erro ao carregar templates:', error);
      toast({
        title: "❌ Erro",
        description: "Não foi possível carregar os templates",
        variant: "destructive",
      });
    } finally {
      setLoadingTemplates(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'templates') {
      carregarTemplates();
    }
  }, [activeTab, filtroTipo]);

  const abrirModalNovoTemplate = () => {
    setEditingTemplate(null);
    setTemplateForm({
      nome: '',
      tipo: 'cobranca',
      mensagem: '',
      descricao: '',
      ativo: true
    });
    setPreviewTemplate('');
    setShowTemplateModal(true);
  };

  const abrirModalEditarTemplate = (template) => {
    setEditingTemplate(template);
    setTemplateForm({
      nome: template.nome,
      tipo: template.tipo,
      mensagem: template.mensagem,
      descricao: template.descricao || '',
      ativo: template.ativo
    });
    gerarPreview(template.mensagem);
    setShowTemplateModal(true);
  };

  const gerarPreview = async (mensagem) => {
    if (!mensagem) {
      setPreviewTemplate('');
      return;
    }
    
    try {
      const response = await whatsappAPI.previewTemplate(mensagem);
      setPreviewTemplate(response.data.preview);
    } catch (error) {
      console.error('Erro ao gerar preview:', error);
    }
  };

  const handleSalvarTemplate = async () => {
    try {
      setSaving(true);
      
      if (editingTemplate) {
        // Editar
        await whatsappAPI.atualizarTemplate(editingTemplate.id, templateForm);
        toast({
          title: "✅ Template Atualizado!",
          description: "O template foi atualizado com sucesso.",
        });
      } else {
        // Criar novo
        await whatsappAPI.criarTemplate(templateForm);
        toast({
          title: "✅ Template Criado!",
          description: "O template foi criado com sucesso.",
        });
      }
      
      setShowTemplateModal(false);
      await carregarTemplates();
    } catch (err) {
      toast({
        title: "❌ Erro",
        description: err.response?.data?.detail || 'Erro ao salvar template',
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDuplicarTemplate = async (template) => {
    try {
      const novoNome = `${template.nome} (Cópia)`;
      await whatsappAPI.duplicarTemplate(template.id, novoNome);
      toast({
        title: "✅ Template Duplicado!",
        description: "Você pode editar a cópia agora.",
      });
      await carregarTemplates();
    } catch (err) {
      toast({
        title: "❌ Erro",
        description: err.response?.data?.detail || 'Erro ao duplicar template',
        variant: "destructive",
      });
    }
  };

  const handleExcluirTemplate = async (template) => {
    if (!window.confirm(`Deseja realmente excluir o template "${template.nome}"?`)) {
      return;
    }
    
    try {
      await whatsappAPI.excluirTemplate(template.id);
      toast({
        title: "✅ Template Excluído!",
        description: "O template foi excluído com sucesso.",
      });
      await carregarTemplates();
    } catch (err) {
      toast({
        title: "❌ Erro",
        description: err.response?.data?.detail || 'Erro ao excluir template',
        variant: "destructive",
      });
    }
  };

  const handleRestaurarPadrao = async () => {
    if (!window.confirm('Deseja restaurar os templates padrão? Isso não afetará seus templates personalizados.')) {
      return;
    }
    
    try {
      setSaving(true);
      await whatsappAPI.restaurarTemplatesPadrao();
      toast({
        title: "✅ Templates Restaurados!",
        description: "Os templates padrão foram restaurados com sucesso.",
      });
      await carregarTemplates();
    } catch (err) {
      toast({
        title: "❌ Erro",
        description: err.response?.data?.detail || 'Erro ao restaurar templates',
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const inserirVariavel = (variavel) => {
    const textarea = document.querySelector('textarea[name="mensagem"]');
    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const text = templateForm.mensagem;
      const newText = text.substring(0, start) + variavel + text.substring(end);
      
      setTemplateForm(prev => ({ ...prev, mensagem: newText }));
      gerarPreview(newText);
      
      // Restaurar cursor
      setTimeout(() => {
        textarea.focus();
        textarea.setSelectionRange(start + variavel.length, start + variavel.length);
      }, 0);
    }
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
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <div className="bg-card rounded-lg shadow-md p-8">
          <h1 className="text-3xl font-bold text-foreground mb-2 flex items-center gap-3">
            <svg className="w-8 h-8 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
            Configurações de Notificações
          </h1>
          <p className="text-muted-foreground mb-6">
            Configure quando e como seus clientes receberão notificações sobre parcelas e vencimentos
          </p>

          {/* Tabs */}
          <div className="flex gap-2 mb-6 border-b border-border">
            <button
              onClick={() => setActiveTab('notificacoes')}
              className={`px-4 py-2 font-medium transition-colors ${
                activeTab === 'notificacoes'
                  ? 'text-primary border-b-2 border-primary'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              📧 Períodos e Canais
            </button>
            <button
              onClick={() => setActiveTab('templates')}
              className={`px-4 py-2 font-medium transition-colors ${
                activeTab === 'templates'
                  ? 'text-primary border-b-2 border-primary'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              📝 Templates WhatsApp
            </button>
          </div>

          {/* Conteúdo da aba Notificações */}
          {activeTab === 'notificacoes' && (
          <div className="space-y-8">
            {/* Status Geral */}
            <div className="bg-muted/30 rounded-lg p-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={notificacoesConfig.ativo}
                  onChange={(e) => setNotificacoesConfig(prev => ({ ...prev, ativo: e.target.checked }))}
                  className="w-5 h-5 rounded border-border text-blue-500 focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-foreground font-medium">
                  Ativar Sistema de Notificações Automáticas
                </span>
              </label>
              <p className="text-sm text-muted-foreground mt-2 ml-8">
                Quando ativo, o sistema verificará automaticamente vencimentos e enviará notificações conforme configurado.
              </p>
            </div>

            {/* Períodos de Notificação */}
            <div>
              <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Quando Enviar Notificações para Clientes?
              </h3>
              
              <div className="space-y-3">
                {notificacoesConfig.periodos.map((periodo, index) => (
                  <div key={index} className="bg-muted/20 rounded-lg p-4 flex items-center gap-4">
                    <input
                      type="checkbox"
                      checked={periodo.ativo}
                      onChange={(e) => atualizarPeriodo(index, 'ativo', e.target.checked)}
                      className="w-5 h-5 rounded border-border text-blue-500"
                    />
                    
                    <input
                      type="number"
                      min="0"
                      max="30"
                      value={periodo.dias}
                      onChange={(e) => atualizarPeriodo(index, 'dias', parseInt(e.target.value) || 0)}
                      className="w-20 px-3 py-2 bg-background border border-border rounded-lg text-foreground"
                    />
                    
                    <span className="text-foreground">dias</span>
                    
                    <select
                      value={periodo.momento}
                      onChange={(e) => atualizarPeriodo(index, 'momento', e.target.value)}
                      className="px-4 py-2 bg-background border border-border rounded-lg text-foreground"
                    >
                      <option value="antes">antes do vencimento</option>
                      <option value="no_dia">no dia do vencimento</option>
                      <option value="depois">após o vencimento (atraso)</option>
                    </select>
                    
                    <button
                      onClick={() => removerPeriodo(index)}
                      className="ml-auto p-2 text-red-500 hover:bg-red-500/10 rounded-lg transition"
                      title="Remover período"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
              
              <button
                onClick={adicionarPeriodo}
                className="mt-3 px-4 py-2 bg-blue-500/10 text-blue-400 border border-blue-500/30 rounded-lg hover:bg-blue-500/20 transition flex items-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Adicionar Período Personalizado
              </button>
            </div>

            {/* Canais de Envio */}
            <div>
              <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                Canais de Envio
              </h3>
              
              <div className="space-y-3">
                <label className="flex items-center gap-3 p-4 bg-muted/20 rounded-lg cursor-pointer hover:bg-muted/30 transition">
                  <input
                    type="checkbox"
                    checked={notificacoesConfig.canais.sistema}
                    onChange={(e) => setNotificacoesConfig(prev => ({
                      ...prev,
                      canais: { ...prev.canais, sistema: e.target.checked }
                    }))}
                    className="w-5 h-5 rounded border-border text-blue-500"
                  />
                  <div>
                    <span className="text-foreground font-medium">Sistema (Notificações Internas)</span>
                    <p className="text-sm text-muted-foreground">Notificações que aparecem no seu painel</p>
                  </div>
                </label>
                
                <label className="flex items-center gap-3 p-4 bg-muted/20 rounded-lg cursor-pointer hover:bg-muted/30 transition">
                  <input
                    type="checkbox"
                    checked={notificacoesConfig.canais.whatsapp}
                    onChange={(e) => setNotificacoesConfig(prev => ({
                      ...prev,
                      canais: { ...prev.canais, whatsapp: e.target.checked }
                    }))}
                    className="w-5 h-5 rounded border-border text-green-500"
                  />
                  <div className="flex-1">
                    <span className="text-foreground font-medium flex items-center gap-2">
                      <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                      </svg>
                      WhatsApp (Enviar para Cliente)
                    </span>
                    <p className="text-sm text-muted-foreground">Mensagens enviadas diretamente para o WhatsApp do cliente</p>
                    {!notificacoesConfig.canais.whatsapp && (
                      <p className="text-xs text-yellow-500 mt-1">⚠️ Certifique-se de conectar seu WhatsApp em: Menu → WhatsApp</p>
                    )}
                  </div>
                </label>
                
                <label className="flex items-center gap-3 p-4 bg-muted/20 rounded-lg cursor-not-allowed opacity-50">
                  <input
                    type="checkbox"
                    checked={notificacoesConfig.canais.email}
                    disabled
                    className="w-5 h-5 rounded border-border"
                  />
                  <div>
                    <span className="text-foreground font-medium">Email (Em breve)</span>
                    <p className="text-sm text-muted-foreground">Notificações por email</p>
                  </div>
                </label>
              </div>
            </div>

            {/* Templates de Mensagem WhatsApp */}
            {notificacoesConfig.canais.whatsapp && (
              <div>
                <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                  <svg className="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                  </svg>
                  Templates de Mensagem WhatsApp
                </h3>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Mensagem de Vencimento:
                    </label>
                    <textarea
                      value={notificacoesConfig.template_whatsapp}
                      onChange={(e) => setNotificacoesConfig(prev => ({ ...prev, template_whatsapp: e.target.value }))}
                      rows={5}
                      className="w-full px-4 py-3 bg-background border border-border rounded-lg text-foreground font-mono text-sm"
                      placeholder="Olá {cliente_nome}!..."
                    />
                    <p className="text-xs text-muted-foreground mt-2">
                      Variáveis disponíveis: <code className="bg-muted px-2 py-1 rounded">{'{cliente_nome}'}</code>, <code className="bg-muted px-2 py-1 rounded">{'{numero}'}</code>, <code className="bg-muted px-2 py-1 rounded">{'{valor}'}</code>, <code className="bg-muted px-2 py-1 rounded">{'{dias}'}</code>, <code className="bg-muted px-2 py-1 rounded">{'{data_vencimento}'}</code>
                    </p>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Mensagem de Atraso:
                    </label>
                    <textarea
                      value={notificacoesConfig.template_whatsapp_atraso}
                      onChange={(e) => setNotificacoesConfig(prev => ({ ...prev, template_whatsapp_atraso: e.target.value }))}
                      rows={5}
                      className="w-full px-4 py-3 bg-background border border-border rounded-lg text-foreground font-mono text-sm"
                      placeholder="Olá {cliente_nome}!..."
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Opções Adicionais */}
            <div>
              <h3 className="text-lg font-semibold text-foreground mb-4">Opções Adicionais</h3>
              <div className="space-y-3">
                <label className="flex items-center gap-3 p-4 bg-muted/20 rounded-lg cursor-pointer">
                  <input
                    type="checkbox"
                    checked={notificacoesConfig.enviar_para_cliente}
                    onChange={(e) => setNotificacoesConfig(prev => ({ ...prev, enviar_para_cliente: e.target.checked }))}
                    className="w-5 h-5 rounded border-border text-blue-500"
                  />
                  <div>
                    <span className="text-foreground font-medium">Enviar para Cliente</span>
                    <p className="text-sm text-muted-foreground">Quando ativo, notificações são enviadas para o cliente (via WhatsApp)</p>
                  </div>
                </label>
              </div>
            </div>

            {/* Botões de Ação */}
            <div className="flex gap-4 pt-6 border-t border-border">
              <Button
                onClick={handleSaveNotificacoesConfig}
                loading={saving}
                className="flex-1"
              >
                💾 Salvar Configurações
              </Button>
              
              <button
                onClick={handleRestaurarNotificacoesPadrao}
                disabled={saving}
                className="px-6 py-3 bg-muted text-foreground rounded-lg hover:bg-muted/80 transition disabled:opacity-50"
              >
                🔄 Restaurar Padrão
              </button>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default ConfigNotificacoes;
