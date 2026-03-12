import React, { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import Loading from '../components/Loading';
import Button from '../components/Button';
import { configuracoesAPI, assinaturasAPI, superadminAPI, whatsappAPI } from '../api/api';
import { BACKEND_URL } from '../config/env';
import { useToast } from '../hooks/use-toast';
import EmailTestDialog from '../components/EmailTestDialog'; // Novo componente

const Configuracoes = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('landing');
  const { toast } = useToast();

  // Dialog de teste de email
  const [showEmailDialog, setShowEmailDialog] = useState(false);
  const [emailDialogStatus, setEmailDialogStatus] = useState('idle'); // idle, loading, success, error
  const [emailDialogMessage, setEmailDialogMessage] = useState('');
  const [emailDialogLogs, setEmailDialogLogs] = useState([]); // Adicionar logs para "Saiba mais"

  // Configurações da Landing
  const [config, setConfig] = useState({
    whatsapp_numero: '',
    whatsapp_mensagem: 'Olá! Gostaria de saber mais sobre o Gestor Cred.',
    nome_empresa: 'Gestor Cred',
    slogan: 'Sistema de Gestão de Empréstimos a Juros',
    descricao: 'Gerencie seus empréstimos de forma simples e profissional',
    cor_primaria: '#1e40af',
    plano_trial_dias: 7,
    plano_basico_preco: 97.0,
    plano_basico_clientes: 50,
    plano_basico_emprestimos: 100,
    plano_profissional_preco: 197.0,
    plano_profissional_clientes: 200,
    plano_profissional_emprestimos: 500,
    plano_enterprise_preco: 497.0,
    plano_enterprise_clientes: -1,
    plano_enterprise_emprestimos: -1
  });

  // Configurações de Gateway para Assinaturas
  const [assinaturaGatewayConfig, setAssinaturaGatewayConfig] = useState({
    estrategia: 'stripe_only',
    // Stripe
    stripe_habilitado: true,
    stripe_api_key: '',
    stripe_publishable_key: '',
    stripe_modo_sandbox: true,
    stripe_webhook_secret: '',
    stripe_webhook_url: '',
    // Mercado Pago
    mercadopago_habilitado: false,
    mercadopago_access_token: '',
    mercadopago_public_key: '',
    mercadopago_modo_sandbox: true,
    mercadopago_webhook_secret: '',
    mercadopago_webhook_url: '',
    mp_cartao_habilitado: true,
    mp_pix_habilitado: true,
    rotacao_contador: 0,
    gateway_primario: 'stripe'
  });

  // Configurações de Email SMTP
  const [emailConfig, setEmailConfig] = useState({
    smtp_provider: 'gmail',
    smtp_host: '',
    smtp_port: 587,
    smtp_user: '',
    smtp_password: '',
    smtp_from_email: '',
    smtp_from_name: 'Gestor Cred',
    smtp_use_tls: true,
    smtp_password_set: false
  });
  const [testingEmail, setTestingEmail] = useState(false);
  const [emailTeste, setEmailTeste] = useState('');

  // Configurações de IA
  const [iaConfig, setIaConfig] = useState({
    habilitado: true,
    provider: 'gemini',
    api_key: '',
    modelo: 'gemini-1.5-flash',
    temperatura: 0.7
  });

  // Configurações Evolution API (WhatsApp)
  const [evolutionConfig, setEvolutionConfig] = useState({
    habilitado: false,
    api_url: '',
    api_key: '',
    global_webhook_url: '',
    timeout: 30,
    max_tentativas_envio: 3
  });
  const [testingEvolution, setTestingEvolution] = useState(false);
  const [evolutionTestResult, setEvolutionTestResult] = useState(null);

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


  const carregarConfig = useCallback(async () => {
    try {
      setLoading(true);
      const [landingRes, assinaturaGatewayRes, emailRes, iaRes, evolutionRes, notificacoesRes] = await Promise.all([
        configuracoesAPI.obterLanding(),
        assinaturasAPI.obterGatewayConfig().catch(() => ({ data: {} })),
        superadminAPI.obterConfigEmail().catch(() => ({ data: {} })),
        configuracoesAPI.obterIA().catch(() => ({ data: {} })),
        whatsappAPI.obterConfigEvolution().catch(() => ({ data: {} })),
        configuracoesAPI.obterNotificacoes().catch(() => ({ data: {} }))
      ]);
      setConfig(prev => ({ ...prev, ...landingRes.data }));
      if (assinaturaGatewayRes.data && Object.keys(assinaturaGatewayRes.data).length > 0) {
        setAssinaturaGatewayConfig(prev => ({ ...prev, ...assinaturaGatewayRes.data }));
      }
      if (emailRes.data && Object.keys(emailRes.data).length > 0) {
        setEmailConfig(prev => ({ ...prev, ...emailRes.data }));
      }
      if (iaRes.data) {
        setIaConfig(prev => ({ ...prev, ...iaRes.data }));
      }
      if (evolutionRes.data && Object.keys(evolutionRes.data).length > 0) {
        setEvolutionConfig(prev => ({ ...prev, ...evolutionRes.data }));
      }
      if (notificacoesRes.data && Object.keys(notificacoesRes.data).length > 0) {
        setNotificacoesConfig(prev => ({ ...prev, ...notificacoesRes.data }));
      }
    } catch (err) {
      console.error('Erro ao carregar configurações:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    carregarConfig();
  }, [carregarConfig]);

  const carregarNotificacoesConfig = useCallback(async () => {
    try {
      const response = await configuracoesAPI.obterNotificacoes();
      if (response.data) {
        setNotificacoesConfig(response.data);
      }
    } catch (error) {
      console.error('Erro ao carregar configurações de notificações:', error);
    }
  }, []);

  const handleChange = (e) => {
    const { name, value, type } = e.target;
    setConfig(prev => ({
      ...prev,
      [name]: type === 'number' ? parseFloat(value) || 0 : value
    }));
  };

  const handleAssinaturaGatewayChange = (e) => {
    const { name, value, type, checked } = e.target;
    setAssinaturaGatewayConfig(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSaveLanding = async () => {
    try {
      setSaving(true);
      await configuracoesAPI.atualizarLanding(config);
      toast({
        title: "✅ Sucesso!",
        description: "Configurações da Landing salvas com sucesso!",
        variant: "default",
      });
    } catch (err) {
      toast({
        title: "❌ Erro",
        description: err.response?.data?.detail || 'Erro ao salvar configurações',
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveAssinaturaGateway = async () => {
    try {
      setSaving(true);

      console.log('Salvando configurações de gateway...', assinaturaGatewayConfig);

      const response = await assinaturasAPI.atualizarGatewayConfig(assinaturaGatewayConfig);

      console.log('Resposta do servidor:', response);

      toast({
        title: "✅ Configurações Salvas!",
        description: "As configurações de Gateway de Pagamento foram atualizadas com sucesso.",
        variant: "default",
      });
    } catch (err) {
      console.error('Erro ao salvar:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Erro ao salvar configurações';
      toast({
        title: "❌ Erro ao Salvar",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  // Handlers de Email SMTP
  const handleEmailConfigChange = (e) => {
    const { name, value, type, checked } = e.target;
    setEmailConfig(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : (type === 'number' ? parseInt(value) || 0 : value)
    }));
  };

  const handleProviderChange = (provider) => {
    const presets = {
      gmail: { smtp_host: 'smtp.gmail.com', smtp_port: 587, smtp_use_tls: true },
      hostinger: { smtp_host: 'smtp.hostinger.com', smtp_port: 465, smtp_use_tls: false },
      outlook: { smtp_host: 'smtp-mail.outlook.com', smtp_port: 587, smtp_use_tls: true },
      custom: { smtp_host: '', smtp_port: 587, smtp_use_tls: true }
    };
    setEmailConfig(prev => ({
      ...prev,
      smtp_provider: provider,
      ...presets[provider]
    }));
  };

  const handleSaveEmailConfig = async () => {
    try {
      setSaving(true);
      await superadminAPI.atualizarConfigEmail(emailConfig);

      toast({
        title: "✅ Configurações de Email Salvas!",
        description: "As configurações SMTP foram atualizadas com sucesso.",
        variant: "default",
      });

      // Atualizar flag de senha
      if (emailConfig.smtp_password) {
        setEmailConfig(prev => ({ ...prev, smtp_password_set: true, smtp_password: '' }));
      }
    } catch (err) {
      toast({
        title: "❌ Erro ao Salvar",
        description: err.response?.data?.detail || err.message || 'Erro ao salvar',
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleTestarEmail = async () => {
    if (!emailTeste) {
      toast({
        title: "⚠️ Atenção",
        description: "Digite um email para enviar o teste.",
        variant: "destructive",
      });
      return;
    }

    // Iniciar Modal
    setShowEmailDialog(true);
    setEmailDialogStatus('loading');
    setEmailDialogMessage(`Enviando teste para ${emailTeste}...`);
    setEmailDialogLogs([]);

    try {
      setTestingEmail(true);
      const response = await superadminAPI.testarConfigEmail(emailTeste);

      const result = response.data;

      setEmailDialogStatus('success');
      setEmailDialogMessage(`Email enviado com sucesso para ${emailTeste}`);
      setEmailDialogLogs(result.logs || []); // Salvar logs para o modal se necessário

    } catch (err) {
      console.error("Erro no teste de email:", err);
      setEmailDialogStatus('error');
      setEmailDialogMessage(err.response?.data?.detail || err.message || 'Erro desconhecido ao enviar email');
      setEmailDialogLogs([]); // Limpar logs em caso de erro, ou poderíamos tentar extrair se o backend retornasse
    } finally {
      setTestingEmail(false);
    }
  };

  const handleIaChange = (e) => {
    const { name, value, type, checked } = e.target;
    setIaConfig(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : (type === 'number' ? parseFloat(value) : value)
    }));
  };

  const handleSaveIaConfig = async () => {
    try {
      setSaving(true);
      await configuracoesAPI.atualizarIA(iaConfig);
      toast({
        title: "✅ Configurações de IA Salvas!",
        description: "Chave de API e preferências do assistente atualizadas.",
        variant: "default",
      });
    } catch (err) {
      toast({
        title: "❌ Erro ao Salvar",
        description: err.response?.data?.detail || 'Erro ao salvar configurações de IA',
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  // Handlers Evolution API
  const handleEvolutionChange = (e) => {
    const { name, value, type, checked } = e.target;
    setEvolutionConfig(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : (type === 'number' ? parseInt(value) || 0 : value)
    }));
  };

  const handleSaveEvolutionConfig = async () => {
    try {
      setSaving(true);
      await whatsappAPI.atualizarConfigEvolution(evolutionConfig);
      toast({
        title: "✅ Configurações da Evolution API Salvas!",
        description: "Os usuários já podem conectar seus WhatsApp.",
        variant: "default",
      });
      await carregarConfig();
    } catch (err) {
      toast({
        title: "❌ Erro ao Salvar",
        description: err.response?.data?.detail || 'Erro ao salvar configurações',
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveNotificacoesConfig = async () => {
    try {
      setSaving(true);
      await configuracoesAPI.atualizarNotificacoes(notificacoesConfig);
      toast({
        title: "✅ Configurações de Notificações Salvas!",
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


  const handleTestarEvolution = async () => {
    if (!evolutionConfig.api_url || !evolutionConfig.api_key) {
      toast({
        title: "⚠️ Atenção",
        description: "Preencha a URL da API e a API Key antes de testar.",
        variant: "destructive",
      });
      return;
    }

    try {
      setTestingEvolution(true);
      setEvolutionTestResult(null);
      
      // Testar através do backend (resolve mixed content - funciona com HTTP ou HTTPS)
      const response = await whatsappAPI.testarConfigEvolution(evolutionConfig);
      
      if (response.data.success) {
        setEvolutionTestResult({ success: true, message: '✅ Conexão estabelecida com sucesso!' });
        toast({
          title: "✅ Teste bem-sucedido!",
          description: "A Evolution API está configurada corretamente.",
          variant: "default",
        });
      } else {
        setEvolutionTestResult({ success: false, message: `❌ ${response.data.message}` });
        toast({
          title: "❌ Falha no teste",
          description: response.data.message,
          variant: "destructive",
        });
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Erro ao conectar com a Evolution API';
      setEvolutionTestResult({ success: false, message: `❌ Erro: ${errorMsg}` });
      toast({
        title: "❌ Erro de Conexão",
        description: errorMsg,
        variant: "destructive",
      });
    } finally {
      setTestingEvolution(false);
    }
  };


  if (loading) return <Loading message="Carregando configurações..." />;

  return (
    <Layout>
      <EmailTestDialog
        isOpen={showEmailDialog}
        onClose={() => setShowEmailDialog(false)}
        status={emailDialogStatus}
        message={emailDialogMessage}
        logs={emailDialogLogs}
        email={emailTeste}
        onRetry={handleTestarEmail}
      />
      <div className="container mx-auto px-4 py-8 pb-20">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground" data-testid="configuracoes-title">
            Configurações
          </h1>
          <p className="text-muted-foreground mt-1">Gerencie as configurações do sistema, Landing Page e Gateways de Pagamento</p>
        </div>

        {/* Tabs */}
        <div className="bg-card rounded-lg shadow-md mb-6">
          <div className="flex border-b border-border overflow-x-auto">
            <button
              onClick={() => setActiveTab('landing')}
              className={`flex-1 min-w-max px-6 py-4 text-center font-medium transition ${activeTab === 'landing'
                ? 'bg-blue-500/10 text-blue-400 border-b-2 border-blue-500'
                : 'text-muted-foreground hover:bg-muted/50'
                }`}
              data-testid="tab-landing"
            >
              <span className="flex items-center justify-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                Landing Page
              </span>
            </button>
            <button
              onClick={() => setActiveTab('planos')}
              className={`flex-1 min-w-max px-6 py-4 text-center font-medium transition ${activeTab === 'planos'
                ? 'bg-emerald-500/10 text-emerald-400 border-b-2 border-emerald-500'
                : 'text-muted-foreground hover:bg-muted/50'
                }`}
              data-testid="tab-planos"
            >
              <span className="flex items-center justify-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Planos e Preços
              </span>
            </button>
            <button
              onClick={() => setActiveTab('whatsapp')}
              className={`flex-1 min-w-max px-6 py-4 text-center font-medium transition ${activeTab === 'whatsapp'
                ? 'bg-green-500/10 text-green-400 border-b-2 border-green-500'
                : 'text-muted-foreground hover:bg-muted/50'
                }`}
              data-testid="tab-whatsapp"
            >
              <span className="flex items-center justify-center gap-2">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                </svg>
                WhatsApp
              </span>
            </button>
            <button
              onClick={() => setActiveTab('assinatura_gateway')}
              className={`flex-1 min-w-max px-6 py-4 text-center font-medium transition ${activeTab === 'assinatura_gateway'
                ? 'bg-purple-500/10 text-purple-400 border-b-2 border-purple-500'
                : 'text-muted-foreground hover:bg-muted/50'
                }`}
              data-testid="tab-assinatura-gateway"
            >
              <span className="flex items-center justify-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                </svg>
                Gateways (Assinaturas)
              </span>
            </button>
            <button
              onClick={() => setActiveTab('email')}
              className={`flex-1 min-w-max px-6 py-4 text-center font-medium transition ${activeTab === 'email'
                ? 'bg-red-500/10 text-red-400 border-b-2 border-red-500'
                : 'text-muted-foreground hover:bg-muted/50'
                }`}
              data-testid="tab-email"
            >
              <span className="flex items-center justify-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                Email SMTP
              </span>
            </button>
            <button
              onClick={() => setActiveTab('notificacoes')}
              className={`flex-1 min-w-max px-6 py-4 text-center font-medium transition ${activeTab === 'notificacoes'
                ? 'bg-yellow-500/10 text-yellow-400 border-b-2 border-yellow-500'
                : 'text-muted-foreground hover:bg-muted/50'
                }`}
              data-testid="tab-notificacoes"
            >
              <span className="flex items-center justify-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                </svg>
                Notificações Assinantes
              </span>
            </button>

            <button
              onClick={() => setActiveTab('assistente')}
              className={`flex-1 min-w-max px-6 py-4 text-center font-medium transition ${activeTab === 'assistente'
                ? 'bg-indigo-500/10 text-indigo-400 border-b-2 border-indigo-500'
                : 'text-muted-foreground hover:bg-muted/50'
                }`}
              data-testid="tab-assistente"
            >
              <span className="flex items-center justify-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                Assistente IA
              </span>
            </button>
            <button
              onClick={() => setActiveTab('evolution')}
              className={`flex-1 min-w-max px-6 py-4 text-center font-medium transition ${activeTab === 'evolution'
                ? 'bg-teal-500/10 text-teal-400 border-b-2 border-teal-500'
                : 'text-muted-foreground hover:bg-muted/50'
                }`}
              data-testid="tab-evolution"
            >
              <span className="flex items-center justify-center gap-2">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                </svg>
                Evolution API
              </span>
            </button>

          </div>
        </div>

        {/* Tab: Landing Page */}
        {activeTab === 'landing' && (
          <div className="bg-card rounded-lg shadow-md p-6" data-testid="config-landing">
            <h2 className="text-xl font-bold text-foreground mb-6">Configurações da Landing Page</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Nome da Empresa
                </label>
                <input
                  type="text"
                  name="nome_empresa"
                  value={config.nome_empresa}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  data-testid="input-nome-empresa"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">
                  Cor Primária
                </label>
                <div className="flex items-center space-x-3">
                  <input
                    type="color"
                    name="cor_primaria"
                    value={config.cor_primaria}
                    onChange={handleChange}
                    className="w-12 h-10 rounded cursor-pointer"
                  />
                  <input
                    type="text"
                    name="cor_primaria"
                    value={config.cor_primaria}
                    onChange={handleChange}
                    className="flex-1 px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    data-testid="input-cor-primaria"
                  />
                </div>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-foreground mb-2">
                  Slogan / Título Principal
                </label>
                <input
                  type="text"
                  name="slogan"
                  value={config.slogan}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  data-testid="input-slogan"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-foreground mb-2">
                  Descrição
                </label>
                <textarea
                  name="descricao"
                  value={config.descricao}
                  onChange={handleChange}
                  rows="3"
                  className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  data-testid="input-descricao"
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <Button onClick={handleSaveLanding} variant="primary" disabled={saving} data-testid="save-landing-btn">
                {saving ? 'Salvando...' : 'Salvar Landing'}
              </Button>
            </div>
          </div>
        )}

        {/* Tab: WhatsApp */}
        {activeTab === 'whatsapp' && (
          <div className="bg-card rounded-lg shadow-md p-6" data-testid="config-whatsapp">
            <h2 className="text-xl font-bold text-foreground mb-6 flex items-center">
              <svg className="w-8 h-8 text-green-500 mr-3" fill="currentColor" viewBox="0 0 24 24">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
              </svg>
              Configurações do WhatsApp
            </h2>

            <div className="space-y-6">
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4">
                <p className="text-sm text-green-400">
                  <strong>Dica:</strong> O botão flutuante do WhatsApp aparecerá na Landing Page e permitirá que visitantes entrem em contato diretamente com você.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Número do WhatsApp (com DDD)</label>
                <div className="flex items-center">
                  <span className="bg-muted border border-r-0 border-border px-3 py-2 rounded-l-md text-muted-foreground">+55</span>
                  <input
                    type="text"
                    name="whatsapp_numero"
                    value={config.whatsapp_numero}
                    onChange={handleChange}
                    placeholder="11999999999"
                    className="flex-1 px-3 py-2 border border-border rounded-r-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    data-testid="input-whatsapp-numero"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-foreground mb-2">Mensagem Padrão</label>
                <textarea
                  name="whatsapp_mensagem"
                  value={config.whatsapp_mensagem}
                  onChange={handleChange}
                  rows="3"
                  className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  data-testid="input-whatsapp-mensagem"
                />
              </div>

              <div className="flex justify-end">
                <Button onClick={handleSaveLanding} variant="primary" disabled={saving} data-testid="save-whatsapp-btn">
                  {saving ? 'Salvando...' : 'Salvar WhatsApp'}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Gateway de Assinaturas (Asaas + Mercado Pago) */}
        {activeTab === 'assinatura_gateway' && (
          <div className="space-y-6" data-testid="config-assinatura-gateway">
            <div className="bg-card rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold text-foreground mb-2">Gateway de Assinaturas</h2>
              <p className="text-muted-foreground mb-6">
                Configure como os pagamentos de assinaturas recorrentes serão processados (Asaas e/ou Mercado Pago).
              </p>

              {/* Estratégia de Gateway */}
              <div className="mb-8">
                <label className="block text-sm font-medium text-foreground mb-3">Estratégia de Pagamento</label>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <label className={`relative flex flex-col p-4 border-2 rounded-lg cursor-pointer transition ${assinaturaGatewayConfig.estrategia === 'asaas_only' ? 'border-green-500 bg-green-500/20' : 'border-border hover:border-border'}`}>
                    <input
                      type="radio"
                      name="estrategia"
                      value="asaas_only"
                      checked={assinaturaGatewayConfig.estrategia === 'asaas_only'}
                      onChange={handleAssinaturaGatewayChange}
                      className="sr-only"
                    />
                    <div className="flex items-center mb-2">
                      <div className="w-10 h-10 bg-green-500/30 rounded-full flex items-center justify-center mr-3">
                        <span className="text-green-400 font-bold text-xs">A</span>
                      </div>
                      <p className="font-medium text-foreground">Somente Asaas</p>
                    </div>
                    <p className="text-xs text-muted-foreground">Usar apenas Asaas (PIX/Boleto/Cartão)</p>
                  </label>

                  <label className={`relative flex flex-col p-4 border-2 rounded-lg cursor-pointer transition ${assinaturaGatewayConfig.estrategia === 'mercadopago_only' ? 'border-blue-500 bg-blue-500/20' : 'border-border hover:border-border'}`}>
                    <input
                      type="radio"
                      name="estrategia"
                      value="mercadopago_only"
                      checked={assinaturaGatewayConfig.estrategia === 'mercadopago_only'}
                      onChange={handleAssinaturaGatewayChange}
                      className="sr-only"
                    />
                    <div className="flex items-center mb-2">
                      <div className="w-10 h-10 bg-blue-500/30 rounded-full flex items-center justify-center mr-3">
                        <span className="text-blue-400 font-bold text-xs">MP</span>
                      </div>
                      <p className="font-medium text-foreground">Somente Mercado Pago</p>
                    </div>
                    <p className="text-xs text-muted-foreground">Usar apenas Mercado Pago (PIX e Cartão)</p>
                  </label>

                  <label className={`relative flex flex-col p-4 border-2 rounded-lg cursor-pointer transition ${assinaturaGatewayConfig.estrategia === 'rotacao' ? 'border-purple-500 bg-purple-500/20' : 'border-border hover:border-border'}`}>
                    <input
                      type="radio"
                      name="estrategia"
                      value="rotacao"
                      checked={assinaturaGatewayConfig.estrategia === 'rotacao'}
                      onChange={handleAssinaturaGatewayChange}
                      className="sr-only"
                    />
                    <div className="flex items-center mb-2">
                      <div className="w-10 h-10 bg-purple-500/30 rounded-full flex items-center justify-center mr-3">
                        <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                      </div>
                      <p className="font-medium text-foreground">Rotação</p>
                    </div>
                    <p className="text-xs text-muted-foreground">Alterna entre Asaas e Mercado Pago</p>
                  </label>

                  <label className={`relative flex flex-col p-4 border-2 rounded-lg cursor-pointer transition ${assinaturaGatewayConfig.estrategia === 'fallback' ? 'border-orange-500 bg-orange-500/20' : 'border-border hover:border-border'}`}>
                    <input
                      type="radio"
                      name="estrategia"
                      value="fallback"
                      checked={assinaturaGatewayConfig.estrategia === 'fallback'}
                      onChange={handleAssinaturaGatewayChange}
                      className="sr-only"
                    />
                    <div className="flex items-center mb-2">
                      <div className="w-10 h-10 bg-orange-500/30 rounded-full flex items-center justify-center mr-3">
                        <svg className="w-5 h-5 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                      </div>
                      <p className="font-medium text-foreground">Fallback</p>
                    </div>
                    <p className="text-xs text-muted-foreground">Se um falhar, usa o outro</p>
                  </label>
                </div>
              </div>

              {/* Gateway Primário (para fallback) */}
              {assinaturaGatewayConfig.estrategia === 'fallback' && (
                <div className="mb-6 bg-orange-500/20 border border-orange-500/30 rounded-lg p-4">
                  <label className="block text-sm font-medium text-foreground mb-2">Gateway Primário (tentar primeiro)</label>
                  <select
                    name="gateway_primario"
                    value={assinaturaGatewayConfig.gateway_primario}
                    onChange={handleAssinaturaGatewayChange}
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500"
                  >
                    <option value="asaas">Asaas</option>
                    <option value="mercadopago">Mercado Pago</option>
                  </select>
                </div>
              )}
            </div>

            {/* Configuração Asaas */}
            <div className="bg-card rounded-lg shadow-md p-6 border-l-4 border-green-500">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-foreground flex items-center">
                  <div className="w-8 h-8 bg-green-500/30 rounded-full flex items-center justify-center mr-3">
                    <span className="text-green-400 font-bold text-xs">A</span>
                  </div>
                  Asaas - Gateway Brasileiro 🇧🇷
                </h3>
                <div className="flex items-center gap-4">
                  {/* Modo Sandbox Toggle */}
                  <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${assinaturaGatewayConfig.asaas_ambiente === 'sandbox' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'}`}>
                    <span className={`w-2 h-2 rounded-full ${assinaturaGatewayConfig.asaas_ambiente === 'sandbox' ? 'bg-amber-400' : 'bg-emerald-400'}`}></span>
                    {assinaturaGatewayConfig.asaas_ambiente === 'sandbox' ? 'SANDBOX' : 'PRODUÇÃO'}
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      name="asaas_habilitado"
                      checked={assinaturaGatewayConfig.asaas_habilitado}
                      onChange={handleAssinaturaGatewayChange}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-muted-foreground/30 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-green-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-500"></div>
                  </label>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Ambiente</label>
                  <select
                    name="asaas_ambiente"
                    value={assinaturaGatewayConfig.asaas_ambiente}
                    onChange={handleAssinaturaGatewayChange}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-green-500"
                  >
                    <option value="sandbox">🧪 Sandbox (Testes)</option>
                    <option value="producao">🚀 Produção</option>
                  </select>
                  <p className="text-xs text-muted-foreground mt-1">
                    {assinaturaGatewayConfig.asaas_ambiente === 'sandbox' 
                      ? '⚠️ Modo de teste - nenhum pagamento real será processado' 
                      : '✅ Modo de produção - processará pagamentos reais'}
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">API Key do Asaas</label>
                  <input
                    type="password"
                    name="asaas_api_key"
                    value={assinaturaGatewayConfig.asaas_api_key}
                    onChange={handleAssinaturaGatewayChange}
                    className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-green-500 font-mono text-sm"
                    placeholder="$aact_YzU5YTE0M2M2N2I4MTliNzk0YTI5N..."
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Obtida em: <a href="https://www.asaas.com" target="_blank" rel="noopener noreferrer" className="text-green-400 hover:underline">Asaas → Configurações → Integrações → API</a>
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Webhook URL</label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      name="asaas_webhook_url"
                      value={assinaturaGatewayConfig.asaas_webhook_url}
                      onChange={handleAssinaturaGatewayChange}
                      className="flex-1 px-3 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-green-500 font-mono text-xs"
                      placeholder="https://sua-app.com/api/assinaturas/webhook-asaas"
                    />
                  </div>
                  <p className="text-xs text-slate-400 mb-2">URL do Webhook (configure no painel Asaas)</p>
                  <div className="bg-slate-700 rounded p-3 text-xs space-y-1 font-mono">
                    <p className="text-slate-300">📍 Configure no Asaas:</p>
                    <p className="text-slate-400 ml-4">
                      Asaas Dashboard → Configurações → Webhooks → + Novo Webhook
                    </p>
                    <p className="text-slate-300 mt-2">✅ Eventos para marcar:</p>
                    <p className="text-green-400 ml-4">• PAYMENT_RECEIVED</p>
                    <p className="text-green-400 ml-4">• PAYMENT_CONFIRMED</p>
                    <p className="text-yellow-400 ml-4">• PAYMENT_OVERDUE</p>
                    <p className="text-red-400 ml-4">• PAYMENT_DELETED</p>
                  </div>
                </div>

                {/* Info Box Asaas */}
                <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
                  <p className="text-sm text-green-400 mb-2 font-medium">💡 Sobre o Asaas:</p>
                  <ul className="text-xs text-green-300 space-y-1 ml-4">
                    <li>✅ Gateway brasileiro líder no mercado</li>
                    <li>✅ Suporta PIX (instantâneo), Boleto (3 dias) e Cartão</li>
                    <li>✅ Taxas competitivas e menores que internacionais</li>
                    <li>✅ Documentação em português</li>
                    <li>✅ Suporte nacional</li>
                  </ul>
                  <a 
                    href="https://www.asaas.com" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-xs text-green-400 hover:text-green-300 underline mt-2 inline-block"
                  >
                    🔗 Criar conta no Asaas (gratuito)
                  </a>
                </div>
              </div>
            </div>
                      checked={assinaturaGatewayConfig.stripe_habilitado}
                      onChange={handleAssinaturaGatewayChange}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-muted peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-card after:border-border after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                    <span className="ml-2 text-sm font-medium text-foreground">
                      {assinaturaGatewayConfig.stripe_habilitado ? 'Habilitado' : 'Desabilitado'}
                    </span>
                  </label>
                </div>
              </div>

              {/* Modo Sandbox Toggle */}
              <div className="mb-6 p-4 bg-muted/30 rounded-lg border border-border">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-foreground">Modo de Operação</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      {assinaturaGatewayConfig.stripe_modo_sandbox
                        ? 'Usando chaves de TESTE - Nenhuma cobrança real será feita'
                        : 'Usando chaves de PRODUÇÃO - Cobranças reais ativas'}
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      name="stripe_modo_sandbox"
                      checked={assinaturaGatewayConfig.stripe_modo_sandbox}
                      onChange={handleAssinaturaGatewayChange}
                      className="sr-only peer"
                    />
                    <div className="w-14 h-7 bg-emerald-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-amber-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-card after:border-border after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-amber-500"></div>
                    <span className="ml-3 text-sm font-semibold text-foreground">
                      {assinaturaGatewayConfig.stripe_modo_sandbox ? 'Sandbox' : 'Produção'}
                    </span>
                  </label>
                </div>
              </div>

              <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-lg p-3 mb-4">
                <p className="text-sm text-indigo-400">
                  Obtenha suas chaves em{' '}
                  <a href="https://dashboard.stripe.com/apikeys" target="_blank" rel="noopener noreferrer" className="underline font-medium hover:text-indigo-300">
                    dashboard.stripe.com/apikeys
                  </a>
                  {assinaturaGatewayConfig.stripe_modo_sandbox && (
                    <span className="block mt-1 text-amber-400">
                      ⚠️ Para modo sandbox, use chaves que começam com <code className="bg-amber-500/20 px-1 rounded">sk_test_</code> e <code className="bg-amber-500/20 px-1 rounded">pk_test_</code>
                    </span>
                  )}
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Secret Key
                    <span className="text-muted-foreground font-normal ml-2">
                      ({assinaturaGatewayConfig.stripe_modo_sandbox ? 'sk_test_' : 'sk_live_'}...)
                    </span>
                  </label>
                  <input
                    type="password"
                    name="stripe_api_key"
                    value={assinaturaGatewayConfig.stripe_api_key}
                    onChange={handleAssinaturaGatewayChange}
                    placeholder={assinaturaGatewayConfig.stripe_modo_sandbox ? "sk_test_..." : "sk_live_..."}
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-sm bg-background"
                    data-testid="input-stripe-secret-key"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    🔒 Chave secreta para processar pagamentos
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Publishable Key
                    <span className="text-muted-foreground font-normal ml-2">
                      ({assinaturaGatewayConfig.stripe_modo_sandbox ? 'pk_test_' : 'pk_live_'}...)
                    </span>
                  </label>
                  <input
                    type="text"
                    name="stripe_publishable_key"
                    value={assinaturaGatewayConfig.stripe_publishable_key || ''}
                    onChange={handleAssinaturaGatewayChange}
                    placeholder={assinaturaGatewayConfig.stripe_modo_sandbox ? "pk_test_..." : "pk_live_..."}
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-sm bg-background"
                    data-testid="input-stripe-publishable-key"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    🌐 Chave pública para checkout
                  </p>
                </div>
              </div>

              {/* Webhook Configuration */}
              <div className="mt-6 pt-6 border-t border-border">
                <h4 className="text-md font-semibold text-foreground mb-4 flex items-center gap-2">
                  <svg className="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Configuração de Webhook
                </h4>

                <div className="bg-slate-900 rounded-lg p-4 mb-4">
                  <p className="text-xs text-slate-400 mb-2">URL do Webhook (configure no painel Stripe)</p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 bg-slate-800 text-emerald-400 px-3 py-2 rounded text-sm font-mono break-all">
                      {BACKEND_URL}/api/assinaturas/webhook
                    </code>
                    <button
                      type="button"
                      onClick={async () => {
                        try {
                          const webhookUrl = `${BACKEND_URL}/api/assinaturas/webhook`;

                          // Tentar usar a API moderna do Clipboard
                          if (navigator.clipboard && navigator.clipboard.writeText) {
                            await navigator.clipboard.writeText(webhookUrl);
                          } else {
                            // Fallback para método antigo
                            const textArea = document.createElement('textarea');
                            textArea.value = webhookUrl;
                            textArea.style.position = 'fixed';
                            textArea.style.left = '-999999px';
                            document.body.appendChild(textArea);
                            textArea.select();
                            document.execCommand('copy');
                            document.body.removeChild(textArea);
                          }

                          toast({
                            title: 'URL copiada!',
                            description: 'URL do webhook copiada para a área de transferência.',
                            variant: 'success'
                          });
                        } catch (error) {
                          console.error('Erro ao copiar:', error);
                          toast({
                            title: 'Erro ao copiar',
                            description: 'Não foi possível copiar a URL. Por favor, copie manualmente.',
                            variant: 'destructive'
                          });
                        }
                      }}
                      className="p-2 bg-slate-700 hover:bg-slate-600 rounded text-slate-300 transition"
                      title="Copiar URL"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Webhook Signing Secret
                    <span className="text-red-500 ml-1">*</span>
                    <span className="text-muted-foreground font-normal ml-2 text-xs">(obrigatório para segurança)</span>
                  </label>
                  <input
                    type="password"
                    name="stripe_webhook_secret"
                    value={assinaturaGatewayConfig.stripe_webhook_secret}
                    onChange={handleAssinaturaGatewayChange}
                    placeholder="whsec_..."
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-sm bg-background"
                    data-testid="input-stripe-webhook-secret"
                    required
                  />
                  <p className="text-xs text-muted-foreground mt-2">
                    🔒 <strong>Importante:</strong> Encontre o signing secret em{' '}
                    <a href="https://dashboard.stripe.com/webhooks" target="_blank" rel="noopener noreferrer" className="text-indigo-400 underline">
                      Stripe Dashboard → Developers → Webhooks
                    </a>
                    . Selecione os eventos: <code className="bg-muted px-1 rounded text-xs">checkout.session.completed</code>, <code className="bg-muted px-1 rounded text-xs">invoice.paid</code>, <code className="bg-muted px-1 rounded text-xs">customer.subscription.updated</code>
                  </p>
                </div>
              </div>
            </div>

            {/* Configuração Mercado Pago */}
            <div className="bg-card rounded-lg shadow-md p-6 border-l-4 border-blue-500">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-foreground flex items-center">
                  <div className="w-8 h-8 bg-blue-500/30 rounded-full flex items-center justify-center mr-3">
                    <span className="text-blue-400 font-bold text-xs">MP</span>
                  </div>
                  Mercado Pago
                </h3>
                <div className="flex items-center gap-4">
                  {/* Modo Sandbox Toggle */}
                  <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${assinaturaGatewayConfig.mercadopago_modo_sandbox ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'}`}>
                    <span className={`w-2 h-2 rounded-full ${assinaturaGatewayConfig.mercadopago_modo_sandbox ? 'bg-amber-400' : 'bg-emerald-400'}`}></span>
                    {assinaturaGatewayConfig.mercadopago_modo_sandbox ? 'SANDBOX' : 'PRODUÇÃO'}
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      name="mercadopago_habilitado"
                      checked={assinaturaGatewayConfig.mercadopago_habilitado}
                      onChange={handleAssinaturaGatewayChange}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-muted peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-card after:border-border after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    <span className="ml-2 text-sm font-medium text-foreground">
                      {assinaturaGatewayConfig.mercadopago_habilitado ? 'Habilitado' : 'Desabilitado'}
                    </span>
                  </label>
                </div>
              </div>

              {/* Modo Sandbox Toggle */}
              <div className="mb-6 p-4 bg-muted/30 rounded-lg border border-border">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-foreground">Modo de Operação</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      {assinaturaGatewayConfig.mercadopago_modo_sandbox
                        ? 'Usando credenciais de TESTE - Nenhuma cobrança real será feita'
                        : 'Usando credenciais de PRODUÇÃO - Cobranças reais ativas'}
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      name="mercadopago_modo_sandbox"
                      checked={assinaturaGatewayConfig.mercadopago_modo_sandbox}
                      onChange={handleAssinaturaGatewayChange}
                      className="sr-only peer"
                    />
                    <div className="w-14 h-7 bg-emerald-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-amber-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-card after:border-border after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-amber-500"></div>
                    <span className="ml-3 text-sm font-semibold text-foreground">
                      {assinaturaGatewayConfig.mercadopago_modo_sandbox ? 'Sandbox' : 'Produção'}
                    </span>
                  </label>
                </div>
              </div>

              <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 mb-4">
                <p className="text-sm text-blue-400">
                  Obtenha suas credenciais em{' '}
                  <a href="https://www.mercadopago.com.br/developers/panel/app" target="_blank" rel="noopener noreferrer" className="underline font-medium hover:text-blue-300">
                    mercadopago.com.br/developers
                  </a>
                  {assinaturaGatewayConfig.mercadopago_modo_sandbox && (
                    <span className="block mt-1 text-amber-400">
                      ⚠️ Para modo sandbox, use credenciais de teste que começam com <code className="bg-amber-500/20 px-1 rounded">TEST-</code>
                    </span>
                  )}
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Access Token
                    <span className="text-muted-foreground font-normal ml-2">
                      ({assinaturaGatewayConfig.mercadopago_modo_sandbox ? 'TEST-' : 'APP_USR-'}...)
                    </span>
                  </label>
                  <input
                    type="password"
                    name="mercadopago_access_token"
                    value={assinaturaGatewayConfig.mercadopago_access_token}
                    onChange={handleAssinaturaGatewayChange}
                    placeholder={assinaturaGatewayConfig.mercadopago_modo_sandbox ? "TEST-..." : "APP_USR-..."}
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm bg-background"
                    data-testid="input-ass-mp-access-token"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Public Key
                    <span className="text-muted-foreground font-normal ml-2">
                      ({assinaturaGatewayConfig.mercadopago_modo_sandbox ? 'TEST-' : 'APP_USR-'}...)
                    </span>
                  </label>
                  <input
                    type="text"
                    name="mercadopago_public_key"
                    value={assinaturaGatewayConfig.mercadopago_public_key}
                    onChange={handleAssinaturaGatewayChange}
                    placeholder={assinaturaGatewayConfig.mercadopago_modo_sandbox ? "TEST-..." : "APP_USR-..."}
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm bg-background"
                    data-testid="input-ass-mp-public-key"
                  />
                </div>
              </div>

              {/* Webhook Configuration */}
              <div className="mt-6 pt-6 border-t border-border">
                <h4 className="text-md font-semibold text-foreground mb-4 flex items-center gap-2">
                  <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Configuração de Webhook (IPN)
                </h4>

                <div className="bg-slate-900 rounded-lg p-4 mb-4">
                  <p className="text-xs text-slate-400 mb-2">URL do Webhook (configure no painel Mercado Pago)</p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 bg-slate-800 text-emerald-400 px-3 py-2 rounded text-sm font-mono break-all">
                      {BACKEND_URL}/api/assinaturas/webhook-mercadopago
                    </code>
                    <button
                      type="button"
                      onClick={async () => {
                        try {
                          const webhookUrl = `${BACKEND_URL}/api/assinaturas/webhook-mercadopago`;

                          // Tentar usar a API moderna do Clipboard
                          if (navigator.clipboard && navigator.clipboard.writeText) {
                            await navigator.clipboard.writeText(webhookUrl);
                          } else {
                            // Fallback para método antigo
                            const textArea = document.createElement('textarea');
                            textArea.value = webhookUrl;
                            textArea.style.position = 'fixed';
                            textArea.style.left = '-999999px';
                            document.body.appendChild(textArea);
                            textArea.select();
                            document.execCommand('copy');
                            document.body.removeChild(textArea);
                          }

                          toast({
                            title: 'URL copiada!',
                            description: 'URL do webhook do Mercado Pago copiada para a área de transferência.',
                            variant: 'success'
                          });
                        } catch (error) {
                          console.error('Erro ao copiar:', error);
                          toast({
                            title: 'Erro ao copiar',
                            description: 'Não foi possível copiar a URL. Por favor, copie manualmente.',
                            variant: 'destructive'
                          });
                        }
                      }}
                      className="p-2 bg-slate-700 hover:bg-slate-600 rounded text-slate-300 transition"
                      title="Copiar URL"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Webhook Secret Key
                    <span className="text-red-500 ml-1">*</span>
                    <span className="text-muted-foreground font-normal ml-2 text-xs">(obrigatório para segurança)</span>
                  </label>
                  <input
                    type="password"
                    name="mercadopago_webhook_secret"
                    value={assinaturaGatewayConfig.mercadopago_webhook_secret}
                    onChange={handleAssinaturaGatewayChange}
                    placeholder="Chave de assinatura do webhook..."
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm bg-background"
                    data-testid="input-mp-webhook-secret"
                    required
                  />
                  <p className="text-xs text-muted-foreground mt-2">
                    🔒 <strong>Importante:</strong> Configure o webhook em{' '}
                    <a href="https://www.mercadopago.com.br/developers/panel/app" target="_blank" rel="noopener noreferrer" className="text-blue-400 underline">
                      Mercado Pago Developers → Sua Aplicação → Webhooks
                    </a>
                    . Eventos recomendados: <code className="bg-muted px-1 rounded text-xs">payment</code>, <code className="bg-muted px-1 rounded text-xs">subscription_preapproval</code>
                  </p>
                </div>
              </div>

              {/* Métodos do Mercado Pago */}
              <div className="flex flex-wrap gap-6 mt-6 pt-6 border-t border-border">
                <p className="w-full text-sm font-medium text-foreground mb-2">Métodos de Pagamento Aceitos:</p>
                <label className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    name="mp_cartao_habilitado"
                    checked={assinaturaGatewayConfig.mp_cartao_habilitado}
                    onChange={handleAssinaturaGatewayChange}
                    className="w-5 h-5 text-blue-400 border-border rounded focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm font-medium text-foreground flex items-center gap-2">
                    <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                    </svg>
                    Cartão de Crédito
                  </span>
                </label>
                <label className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    name="mp_pix_habilitado"
                    checked={assinaturaGatewayConfig.mp_pix_habilitado}
                    onChange={handleAssinaturaGatewayChange}
                    className="w-5 h-5 text-green-400 border-border rounded focus:ring-green-500"
                  />
                  <span className="ml-2 text-sm font-medium text-foreground flex items-center gap-2">
                    <svg className="w-5 h-5 text-green-400" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M13.59 4.41l2.83-2.83a1 1 0 011.41 0l4.59 4.59a1 1 0 010 1.41l-2.83 2.83a1 1 0 01-1.41 0l-4.59-4.59a1 1 0 010-1.41zm-3.18 3.18l-2.83 2.83a1 1 0 000 1.41l4.59 4.59a1 1 0 001.41 0l2.83-2.83a1 1 0 000-1.41l-4.59-4.59a1 1 0 00-1.41 0zM4.41 13.59l-2.83 2.83a1 1 0 000 1.41l4.59 4.59a1 1 0 001.41 0l2.83-2.83a1 1 0 000-1.41l-4.59-4.59a1 1 0 00-1.41 0z" />
                    </svg>
                    PIX
                  </span>
                </label>
              </div>
            </div>

            {/* Botão Salvar - Destacado */}
            <div className="flex justify-end mt-8 pt-6 border-t border-border">
              <Button
                onClick={handleSaveAssinaturaGateway}
                variant="primary"
                disabled={saving}
                data-testid="save-assinatura-gateway-btn"
                className="px-8 py-3 text-base font-semibold shadow-lg hover:shadow-xl transition-all"
              >
                {saving ? 'Salvando...' : 'Salvar Configurações'}
              </Button>
            </div>
          </div>
        )}

        {/* Tab: Planos e Preços */}
        {activeTab === 'planos' && (
          <div className="bg-card rounded-lg shadow-md p-6" data-testid="config-planos">
            <h2 className="text-xl font-bold text-foreground mb-4">Configuração de Planos e Preços</h2>
            <p className="text-sm text-muted-foreground mb-6">
              Configure os valores e limites dos planos de assinatura. Essas informações serão exibidas na Landing Page.
            </p>

            {/* Plano Trial */}
            <div className="mb-6 p-4 bg-muted/30 rounded-lg border border-border">
              <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Plano Trial (Gratuito)
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Duração (dias)
                  </label>
                  <input
                    type="number"
                    name="plano_trial_dias"
                    value={config.plano_trial_dias}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-background"
                    min="1"
                    max="30"
                  />
                </div>
              </div>
            </div>

            {/* Plano Básico */}
            <div className="mb-6 p-4 bg-muted/30 rounded-lg border border-border">
              <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Plano Básico
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Preço Mensal (R$)
                  </label>
                  <input
                    type="number"
                    name="plano_basico_preco"
                    value={config.plano_basico_preco}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 bg-background"
                    min="0"
                    step="0.01"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Limite de Clientes
                  </label>
                  <input
                    type="number"
                    name="plano_basico_clientes"
                    value={config.plano_basico_clientes}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 bg-background"
                    min="1"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Limite de Empréstimos
                  </label>
                  <input
                    type="number"
                    name="plano_basico_emprestimos"
                    onChange={handleChange}
                    value={config.plano_basico_emprestimos}
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 bg-background"
                    min="1"
                  />
                </div>
              </div>
            </div>

            {/* Plano Profissional */}
            <div className="mb-6 p-4 bg-muted/30 rounded-lg border border-border border-l-4 border-l-purple-500">
              <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                </svg>
                Plano Profissional
                <span className="ml-2 px-2 py-0.5 bg-purple-500/20 text-purple-400 text-xs font-semibold rounded-full">POPULAR</span>
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Preço Mensal (R$)
                  </label>
                  <input
                    type="number"
                    name="plano_profissional_preco"
                    value={config.plano_profissional_preco}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 bg-background"
                    min="0"
                    step="0.01"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Limite de Clientes
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      name="plano_profissional_clientes"
                      value={config.plano_profissional_clientes}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 bg-background"
                    />
                    <span className="absolute right-3 top-2.5 text-xs text-muted-foreground">(-1 = ilimitado)</span>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Limite de Empréstimos
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      name="plano_profissional_emprestimos"
                      value={config.plano_profissional_emprestimos}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500 bg-background"
                    />
                    <span className="absolute right-3 top-2.5 text-xs text-muted-foreground">(-1 = ilimitado)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Plano Enterprise */}
            <div className="mb-6 p-4 bg-muted/30 rounded-lg border border-border">
              <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
                Plano Enterprise
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Preço Mensal (R$)
                  </label>
                  <input
                    type="number"
                    name="plano_enterprise_preco"
                    value={config.plano_enterprise_preco}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-amber-500 bg-background"
                    min="0"
                    step="0.01"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Limite de Clientes
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      name="plano_enterprise_clientes"
                      value={config.plano_enterprise_clientes}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-amber-500 bg-background"
                    />
                    <span className="absolute right-3 top-2.5 text-xs text-muted-foreground">(-1 = ilimitado)</span>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Limite de Empréstimos
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      name="plano_enterprise_emprestimos"
                      value={config.plano_enterprise_emprestimos}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-amber-500 bg-background"
                    />
                    <span className="absolute right-3 top-2.5 text-xs text-muted-foreground">(-1 = ilimitado)</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <Button onClick={handleSaveLanding} variant="primary" disabled={saving} data-testid="save-planos-btn">
                {saving ? 'Salvando...' : 'Salvar Planos'}
              </Button>
            </div>
          </div>
        )}

        {/* Tab: Email SMTP */}
        {activeTab === 'email' && (
          <div className="space-y-6" data-testid="config-email">
            <div className="bg-card rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold text-foreground mb-2">Configurações de Email SMTP</h2>
              <p className="text-muted-foreground mb-6">
                Configure o servidor SMTP para envio de emails do sistema (notificações, recuperação de senha, etc).
              </p>

              {/* Provedor SMTP */}
              <div className="mb-8">
                <label className="block text-sm font-medium text-foreground mb-3">Provedor de Email</label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <label className={`relative flex flex-col p-4 border-2 rounded-lg cursor-pointer transition ${emailConfig.smtp_provider === 'gmail' ? 'border-red-500 bg-red-500/10' : 'border-border hover:border-border'}`}>
                    <input
                      type="radio"
                      name="smtp_provider"
                      value="gmail"
                      checked={emailConfig.smtp_provider === 'gmail'}
                      onChange={() => handleProviderChange('gmail')}
                      className="sr-only"
                    />
                    <div className="flex items-center mb-2">
                      <div className="w-10 h-10 bg-red-500/30 rounded-full flex items-center justify-center mr-3">
                        <svg className="w-5 h-5 text-red-400" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.273H1.636A1.636 1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z" />
                        </svg>
                      </div>
                      <p className="font-medium text-foreground">Gmail</p>
                    </div>
                    <p className="text-xs text-muted-foreground">smtp.gmail.com:587</p>
                  </label>

                  <label className={`relative flex flex-col p-4 border-2 rounded-lg cursor-pointer transition ${emailConfig.smtp_provider === 'hostinger' ? 'border-purple-500 bg-purple-500/10' : 'border-border hover:border-border'}`}>
                    <input
                      type="radio"
                      name="smtp_provider"
                      value="hostinger"
                      checked={emailConfig.smtp_provider === 'hostinger'}
                      onChange={() => handleProviderChange('hostinger')}
                      className="sr-only"
                    />
                    <div className="flex items-center mb-2">
                      <div className="w-10 h-10 bg-purple-500/30 rounded-full flex items-center justify-center mr-3">
                        <span className="text-purple-400 font-bold text-sm">H</span>
                      </div>
                      <p className="font-medium text-foreground">Hostinger</p>
                    </div>
                    <p className="text-xs text-muted-foreground">smtp.hostinger.com:465</p>
                  </label>

                  <label className={`relative flex flex-col p-4 border-2 rounded-lg cursor-pointer transition ${emailConfig.smtp_provider === 'outlook' ? 'border-blue-500 bg-blue-500/10' : 'border-border hover:border-border'}`}>
                    <input
                      type="radio"
                      name="smtp_provider"
                      value="outlook"
                      checked={emailConfig.smtp_provider === 'outlook'}
                      onChange={() => handleProviderChange('outlook')}
                      className="sr-only"
                    />
                    <div className="flex items-center mb-2">
                      <div className="w-10 h-10 bg-blue-500/30 rounded-full flex items-center justify-center mr-3">
                        <svg className="w-5 h-5 text-blue-400" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M24 7.387v10.478c0 .23-.08.424-.238.576-.158.154-.352.231-.578.231h-8.957v-6.324l1.91 1.423c.079.058.17.086.273.086.111 0 .213-.038.287-.115l.715-.706c.078-.063.13-.16.13-.263 0-.09-.035-.18-.102-.246l-4.334-3.346v-.016l-.086-.058c-.073-.043-.152-.064-.236-.064-.073 0-.146.016-.215.054l-.078.054v.016L8.15 12.41c-.073.063-.108.146-.108.246 0 .103.043.2.131.263l.715.706c.074.077.176.115.287.115.103 0 .194-.028.273-.086l1.91-1.423v6.324H.816c-.226 0-.42-.077-.578-.231C.08 18.17 0 17.98 0 17.748V7.387c0-.181.048-.348.144-.499.096-.15.219-.261.373-.333l5.68-2.324L12 7.91l5.803-3.679 5.68 2.324c.154.072.277.183.373.333.096.15.144.318.144.499zM8.15 4.18L0 6.757v-.403c0-.167.046-.32.137-.46.091-.14.209-.242.352-.308L5.803.893 8.15 4.18zm7.7 0l2.347-3.287 5.314 2.693c.143.066.261.168.352.308.091.14.137.293.137.46v.403L16.85 4.18z" />
                        </svg>
                      </div>
                      <p className="font-medium text-foreground">Outlook</p>
                    </div>
                    <p className="text-xs text-muted-foreground">smtp-mail.outlook.com:587</p>
                  </label>

                  <label className={`relative flex flex-col p-4 border-2 rounded-lg cursor-pointer transition ${emailConfig.smtp_provider === 'custom' ? 'border-gray-500 bg-gray-500/10' : 'border-border hover:border-border'}`}>
                    <input
                      type="radio"
                      name="smtp_provider"
                      value="custom"
                      checked={emailConfig.smtp_provider === 'custom'}
                      onChange={() => handleProviderChange('custom')}
                      className="sr-only"
                    />
                    <div className="flex items-center mb-2">
                      <div className="w-10 h-10 bg-gray-500/30 rounded-full flex items-center justify-center mr-3">
                        <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                      </div>
                      <p className="font-medium text-foreground">Personalizado</p>
                    </div>
                    <p className="text-xs text-muted-foreground">Servidor customizado</p>
                  </label>
                </div>
              </div>

              {/* Configurações do Servidor */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Servidor SMTP</label>
                  <input
                    type="text"
                    name="smtp_host"
                    value={emailConfig.smtp_host}
                    onChange={handleEmailConfigChange}
                    placeholder="smtp.exemplo.com"
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 bg-background"
                    readOnly={emailConfig.smtp_provider !== 'custom'}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Porta</label>
                  <input
                    type="number"
                    name="smtp_port"
                    value={emailConfig.smtp_port}
                    onChange={handleEmailConfigChange}
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 bg-background"
                    readOnly={emailConfig.smtp_provider !== 'custom'}
                  />
                </div>
              </div>

              {/* Credenciais */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Email/Usuário SMTP</label>
                  <input
                    type="email"
                    name="smtp_user"
                    value={emailConfig.smtp_user}
                    onChange={handleEmailConfigChange}
                    placeholder="seu@email.com"
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Senha {emailConfig.smtp_password_set && <span className="text-green-400 text-xs">(configurada)</span>}
                  </label>
                  <input
                    type="password"
                    name="smtp_password"
                    value={emailConfig.smtp_password}
                    onChange={handleEmailConfigChange}
                    placeholder={emailConfig.smtp_password_set ? '••••••••' : 'Senha ou App Password'}
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 bg-background"
                  />
                  {emailConfig.smtp_provider === 'gmail' && (
                    <p className="text-xs text-amber-400 mt-1">
                      ⚠️ Para Gmail, use uma <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" className="underline">Senha de App</a>
                    </p>
                  )}
                </div>
              </div>

              {/* Remetente */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Email Remetente</label>
                  <input
                    type="email"
                    name="smtp_from_email"
                    value={emailConfig.smtp_from_email}
                    onChange={handleEmailConfigChange}
                    placeholder="noreply@suaempresa.com"
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Nome do Remetente</label>
                  <input
                    type="text"
                    name="smtp_from_name"
                    value={emailConfig.smtp_from_name}
                    onChange={handleEmailConfigChange}
                    placeholder="Gestor Cred"
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-red-500 bg-background"
                  />
                </div>
              </div>

              {/* TLS */}
              <div className="mb-6">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    name="smtp_use_tls"
                    checked={emailConfig.smtp_use_tls}
                    onChange={handleEmailConfigChange}
                    className="w-5 h-5 rounded border-border text-red-500 focus:ring-red-500"
                  />
                  <span className="text-foreground">Usar TLS/STARTTLS</span>
                  <span className="text-xs text-muted-foreground">(porta 587 geralmente usa TLS, porta 465 usa SSL direto)</span>
                </label>
                <p className="text-xs text-amber-400 mt-2">
                  ⚠️ Para Hostinger porta 465: deixe desmarcado (usa SSL). Para Gmail porta 587: deixe marcado (usa TLS).
                </p>
              </div>

              {/* Botão Salvar */}
              <div className="flex justify-end">
                <Button onClick={handleSaveEmailConfig} variant="primary" disabled={saving}>
                  {saving ? 'Salvando...' : 'Salvar Configurações'}
                </Button>
              </div>
            </div>

            {/* Teste de Email */}
            <div className="bg-card rounded-lg shadow-md p-6 border-l-4 border-green-500">
              <h3 className="text-lg font-bold text-foreground mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Testar Configurações
              </h3>
              <p className="text-muted-foreground mb-4 text-sm">
                Salve as configurações acima e depois envie um email de teste para verificar se está funcionando.
              </p>
              <div className="flex gap-3">
                <input
                  type="email"
                  value={emailTeste}
                  onChange={(e) => setEmailTeste(e.target.value)}
                  placeholder="email@teste.com"
                  className="flex-1 px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 bg-background"
                />
                <Button
                  onClick={handleTestarEmail}
                  variant="secondary"
                  disabled={testingEmail}
                  className="bg-green-500/20 hover:bg-green-500/30 text-green-400 border-green-500/30"
                >
                  {testingEmail ? 'Enviando...' : 'Enviar Teste'}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Assistente IA */}

        {/* Tab Notificações */}
        {activeTab === 'notificacoes' && (
          <div className="bg-card rounded-lg shadow-md p-8">
            <h2 className="text-2xl font-bold text-foreground mb-6 flex items-center gap-2">
              <svg className="w-6 h-6 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              Configurações de Notificações para Assinantes
            </h2>

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
                  Quando Enviar Notificações?
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
                      <p className="text-sm text-muted-foreground">Notificações que aparecem no painel do gestor</p>
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
                        <p className="text-xs text-yellow-500 mt-1">⚠️ Certifique-se de ter conectado seu WhatsApp na aba "WhatsApp"</p>
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
        )}


        {activeTab === 'assistente' && (
          <div className="space-y-6" data-testid="config-assistente">
            <div className="bg-card rounded-lg shadow-md p-6">
              <h2 className="text-xl font-bold text-foreground mb-4">Configuração do Assistente IA</h2>
              <p className="text-muted-foreground mb-6">
                Configure a chave de API para o assistente virtual do sistema.
              </p>

              <div className="mb-6">
                <label className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    name="habilitado"
                    checked={iaConfig.habilitado}
                    onChange={handleIaChange}
                    className="w-5 h-5 rounded border-border text-indigo-500 focus:ring-indigo-500"
                  />
                  <span className="ml-2 text-foreground font-medium">Habilitar Assistente IA</span>
                </label>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Provedor</label>
                  <select
                    name="provider"
                    value={iaConfig.provider}
                    onChange={handleIaChange}
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-background"
                  >
                    <option value="gemini">Google Gemini</option>
                    <option value="openai">OpenAI (GPT)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">Modelo</label>
                  <input
                    type="text"
                    name="modelo"
                    value={iaConfig.modelo}
                    onChange={handleIaChange}
                    placeholder="ex: gemini-1.5-flash"
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-background"
                  />
                </div>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-foreground mb-2">
                  Chave da API (API Key)
                </label>
                <input
                  type="password"
                  name="api_key"
                  value={iaConfig.api_key}
                  onChange={handleIaChange}
                  placeholder="Cole sua chave de API aqui"
                  className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-sm bg-background"
                />
                <p className="text-xs text-muted-foreground mt-2">
                  {iaConfig.provider === 'gemini'
                    ? <span>Obtenha sua chave no <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" className="text-indigo-400 underline">Google AI Studio</a></span>
                    : <span>Obtenha sua chave no <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-indigo-400 underline">OpenAI Platform</a></span>
                  }
                </p>
              </div>

              <div className="flex justify-end">
                <Button onClick={handleSaveIaConfig} variant="primary" disabled={saving}>
                  {saving ? 'Salvando...' : 'Salvar Configuração IA'}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Evolution API (WhatsApp) */}
        {activeTab === 'evolution' && (
          <div className="space-y-6" data-testid="config-evolution">
            <div className="bg-card rounded-lg shadow-md p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-xl font-bold text-foreground flex items-center gap-3">
                    <svg className="w-7 h-7 text-teal-500" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                    </svg>
                    Evolution API - Configuração WhatsApp
                  </h2>
                  <p className="text-muted-foreground mt-2">
                    Configure a Evolution API para permitir que os usuários conectem seus WhatsApp
                  </p>
                </div>
              </div>

              <div className="bg-teal-500/10 border border-teal-500/30 rounded-lg p-4 mb-6">
                <div className="flex items-start gap-3">
                  <svg className="w-5 h-5 text-teal-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div className="text-sm text-teal-400">
                    <p className="font-semibold mb-1">ℹ️ O que é Evolution API?</p>
                    <p>A Evolution API é uma API open-source para integração com WhatsApp Multi-device. Com ela, os usuários podem conectar seus WhatsApp e enviar mensagens automáticas.</p>
                    <p className="mt-2">
                      <strong>Documentação:</strong>{' '}
                      <a href="https://doc.evolution-api.com" target="_blank" rel="noopener noreferrer" className="underline">
                        doc.evolution-api.com
                      </a>
                    </p>
                  </div>
                </div>
              </div>

              {/* Habilitar/Desabilitar */}
              <div className="mb-6">
                <label className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    name="habilitado"
                    checked={evolutionConfig.habilitado}
                    onChange={handleEvolutionChange}
                    className="w-5 h-5 rounded border-border text-teal-500 focus:ring-teal-500"
                    data-testid="evolution-habilitado"
                  />
                  <span className="ml-3 text-foreground font-medium">
                    Habilitar Evolution API (permitir conexões WhatsApp)
                  </span>
                </label>
              </div>

              {/* Campos de Configuração */}
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    URL da Evolution API <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="url"
                    name="api_url"
                    value={evolutionConfig.api_url}
                    onChange={handleEvolutionChange}
                    placeholder="http://192.168.1.100:8080 ou https://api.example.com"
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500 bg-background"
                    disabled={!evolutionConfig.habilitado}
                    data-testid="evolution-api-url"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    URL completa da sua Evolution API (aceita HTTP ou HTTPS, sem barra no final)
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    API Key <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="password"
                    name="api_key"
                    value={evolutionConfig.api_key}
                    onChange={handleEvolutionChange}
                    placeholder="Cole sua API Key aqui"
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500 font-mono text-sm bg-background"
                    disabled={!evolutionConfig.habilitado}
                    data-testid="evolution-api-key"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Chave de autenticação da Evolution API
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Webhook URL Global (opcional)
                  </label>
                  <input
                    type="url"
                    name="global_webhook_url"
                    value={evolutionConfig.global_webhook_url}
                    onChange={handleEvolutionChange}
                    placeholder="https://seu-webhook.com/evolution"
                    className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500 bg-background"
                    disabled={!evolutionConfig.habilitado}
                    data-testid="evolution-webhook"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    URL para receber eventos de todas as instâncias (opcional)
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Timeout (segundos)
                    </label>
                    <input
                      type="number"
                      name="timeout"
                      value={evolutionConfig.timeout}
                      onChange={handleEvolutionChange}
                      min="10"
                      max="120"
                      className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500 bg-background"
                      disabled={!evolutionConfig.habilitado}
                      data-testid="evolution-timeout"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Máximo de Tentativas de Envio
                    </label>
                    <input
                      type="number"
                      name="max_tentativas_envio"
                      value={evolutionConfig.max_tentativas_envio}
                      onChange={handleEvolutionChange}
                      min="1"
                      max="10"
                      className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-teal-500 bg-background"
                      disabled={!evolutionConfig.habilitado}
                      data-testid="evolution-max-tentativas"
                    />
                  </div>
                </div>
              </div>

              {/* Resultado do Teste */}
              {evolutionTestResult && (
                <div className={`mt-6 p-4 rounded-lg ${
                  evolutionTestResult.success 
                    ? 'bg-emerald-500/10 border border-emerald-500/30' 
                    : 'bg-red-500/10 border border-red-500/30'
                }`}>
                  <p className={evolutionTestResult.success ? 'text-emerald-400' : 'text-red-400'}>
                    {evolutionTestResult.message}
                  </p>
                </div>
              )}

              {/* Botões */}
              <div className="flex gap-3 justify-end mt-6">
                <Button
                  onClick={handleTestarEvolution}
                  variant="outline"
                  disabled={testingEvolution || !evolutionConfig.habilitado || !evolutionConfig.api_url || !evolutionConfig.api_key}
                  data-testid="test-evolution-btn"
                >
                  {testingEvolution ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Testando...
                    </>
                  ) : (
                    <>
                      🔍 Testar Conexão
                    </>
                  )}
                </Button>
                <Button
                  onClick={handleSaveEvolutionConfig}
                  variant="primary"
                  disabled={saving || !evolutionConfig.habilitado}
                  data-testid="save-evolution-btn"
                >
                  {saving ? 'Salvando...' : '💾 Salvar Configurações'}
                </Button>
              </div>
            </div>

            {/* Informações Adicionais */}
            <div className="bg-card rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold text-foreground mb-4">📚 Próximos Passos</h3>
              <div className="space-y-3 text-sm text-muted-foreground">
                <div className="flex items-start gap-3">
                  <span className="text-teal-500 font-bold">1.</span>
                  <p>Configure a Evolution API acima e clique em <strong>Testar Conexão</strong></p>
                </div>
                <div className="flex items-start gap-3">
                  <span className="text-teal-500 font-bold">2.</span>
                  <p>Após salvar, os usuários poderão acessar <strong>/whatsapp</strong> para conectar seus WhatsApp</p>
                </div>
                <div className="flex items-start gap-3">
                  <span className="text-teal-500 font-bold">3.</span>
                  <p>Cada usuário terá sua própria instância e poderá enviar mensagens via WhatsApp</p>
                </div>
              </div>
            </div>
          </div>
        )}


        {/* Preview Link */}
        {(activeTab === 'landing' || activeTab === 'planos' || activeTab === 'whatsapp') && (
          <div className="mt-6 bg-blue-50 border border-blue-500/30 rounded-lg p-4">
            <p className="text-sm text-blue-400">
              <strong>Preview:</strong> Após salvar, você pode visualizar a Landing Page em{' '}
              <a href="/landing" target="_blank" rel="noopener noreferrer" className="font-semibold underline">/landing</a>
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default Configuracoes;
