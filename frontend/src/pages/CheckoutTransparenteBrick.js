import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { QrCode, ArrowLeft, Loader2, Check, Copy, Lock, Shield, Info, AlertCircle, CheckCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { assinaturasAPI } from '../api/api';

const CheckoutTransparenteBrick = () => {
  const { planoId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const isUpgrade = searchParams.get('upgrade') === 'true';
  const isMember = !!user?.owner_id;

  // Redirecionar membros para o dashboard
  useEffect(() => {
    if (isMember) {
      navigate('/dashboard');
    }
  }, [isMember, navigate]);

  const [plano, setPlano] = useState(null);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState('');
  const [metodoEscolhido, setMetodoEscolhido] = useState(''); // 'pix' ou 'card'

  // Estados do PIX
  const [pixData, setPixData] = useState(null);
  const [pixCopied, setPixCopied] = useState(false);
  const [checandoPagamento, setChecandoPagamento] = useState(false);
  const [processandoPix, setProcessandoPix] = useState(false);
  const [pagamentoAprovado, setPagamentoAprovado] = useState(false);
  const [showCpfTooltip, setShowCpfTooltip] = useState(false);

  // Estados gerais
  const [formData, setFormData] = useState({
    nome: '',
    email: '',
    senha: '',
    confirmarSenha: '',
    cpf: '',
    telefone: ''
  });

  const [mpInstance, setMpInstance] = useState(null);
  const [brickController, setBrickController] = useState(null);
  const [publicKey, setPublicKey] = useState('');
  const [gatewayConfig, setGatewayConfig] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Buscar plano usando service centralizado
        const planosResponse = await assinaturasAPI.listarPlanos();
        const listaPlanos = Array.isArray(planosResponse.data) ? planosResponse.data : [];
        const planoEncontrado = listaPlanos.find(p => p.id === planoId);

        if (!planoEncontrado) {
          setErro('Plano não encontrado.');
          setLoading(false);
          return;
        }

        if (planoEncontrado.preco === 0) {
          navigate('/');
          return;
        }

        setPlano(planoEncontrado);

        // Buscar configuração do gateway
        const configResponse = await assinaturasAPI.listarGatewaysDisponiveis();
        const gatewayData = configResponse.data;

        // Verificar se o gateway é Mercado Pago
        if (!gatewayData.gateway || gatewayData.gateway.id !== 'mercadopago') {
          // Se não for Mercado Pago, redirecionar para checkout público (Stripe)
          navigate(`/checkout/${planoId}${isUpgrade ? '?upgrade=true' : ''}`);
          return;
        }

        setGatewayConfig(gatewayData.gateway);

        if (gatewayData.gateway && gatewayData.gateway.public_key) {
          setPublicKey(gatewayData.gateway.public_key);
        }

      } catch (err) {
        setErro(err.response?.data?.detail || 'Erro ao carregar informações do plano');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [planoId, navigate, isUpgrade]);

  // Preencher dados do usuário se estiver logado (upgrade de plano)
  useEffect(() => {
    if (user && isUpgrade) {
      setFormData(prev => ({
        ...prev,
        nome: user.nome || '',
        email: user.email || ''
        // senha e confirmarSenha não são preenchidos por segurança
        // cpf e telefone virão do backend se necessário
      }));
    }
  }, [user, isUpgrade]);

  // Carregar SDK do Mercado Pago APENAS se gateway for MP
  useEffect(() => {
    if (!gatewayConfig || gatewayConfig.id !== 'mercadopago') {
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://sdk.mercadopago.com/js/v2';
    script.async = true;
    document.body.appendChild(script);

    return () => {
      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
    };
  }, [gatewayConfig]);

  // Inicializar Card Payment Brick
  useEffect(() => {
    if (!publicKey || !window.MercadoPago || !plano || metodoEscolhido !== 'card') {
      return;
    }

    const initBrick = async () => {
      try {
        // Destruir brick anterior se existir
        if (brickController) {
          await brickController.unmount();
        }

        const mp = new window.MercadoPago(publicKey);
        setMpInstance(mp);

        const bricksBuilder = mp.bricks();

        const settings = {
          initialization: {
            amount: plano.preco,
          },
          customization: {
            visual: {
              style: {
                theme: 'dark',
                customVariables: {
                  baseColor: '#a855f7',
                  textPrimaryColor: '#ffffff',
                  textSecondaryColor: '#cbd5e1',
                  inputBackgroundColor: '#1e293b',
                  formBackgroundColor: 'transparent',
                }
              }
            },
            paymentMethods: {
              maxInstallments: 3,
            }
          },
          callbacks: {
            onReady: () => {},
            onSubmit: async (formData) => {
              return handleCardPayment(formData);
            },
            onError: (error) => {
              setErro('Erro ao processar pagamento. Tente novamente.');
            },
          },
        };

        const controller = await bricksBuilder.create(
          'cardPayment',
          'cardPaymentBrick_container',
          settings
        );

        setBrickController(controller);

      } catch (error) {
        setErro('Erro ao carregar formulário de pagamento');
      }
    };

    initBrick();

    return () => {
      if (brickController) {
        brickController.unmount();
      }
    };
  }, [publicKey, plano, metodoEscolhido]);

  // Handler para pagamento com cartão via Brick
  const handleCardPayment = async (cardFormData) => {
    try {
      // Mostrar loading
      setProcessandoPix(true); // Reusar o estado para loading geral
      setErro('');

      // Validar dados gerais
      if (!formData.nome || !formData.email || !formData.cpf) {
        setErro('Preencha todos os campos obrigatórios');
        setProcessandoPix(false);
        throw new Error('Preencha todos os campos obrigatórios');
      }

      // Validar CPF
      if (!validarCPF(formData.cpf)) {
        setErro('CPF inválido');
        setProcessandoPix(false);
        throw new Error('CPF inválido');
      }

      // Validar telefone se preenchido
      if (formData.telefone) {
        const telefoneLimpo = formData.telefone.replace(/\D/g, '');
        if (telefoneLimpo.length < 10 || telefoneLimpo.length > 11) {
          setErro('Telefone inválido');
          setProcessandoPix(false);
          throw new Error('Telefone inválido');
        }
      }

      // Se não é upgrade (novo usuário), validar senha
      if (!isUpgrade) {
        if (!formData.senha || formData.senha.length < 8) {
          setErro('A senha deve ter pelo menos 8 caracteres, com letras e números');
          setProcessandoPix(false);
          throw new Error('A senha deve ter pelo menos 8 caracteres, com letras e números');
        }

        if (formData.senha !== formData.confirmarSenha) {
          setErro('As senhas não coincidem');
          setProcessandoPix(false);
          throw new Error('As senhas não coincidem');
        }
      }

      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(formData.email)) {
        setErro('Email inválido');
        setProcessandoPix(false);
        throw new Error('Email inválido');
      }

      // Enviar para backend
      const response = await assinaturasAPI.checkoutTransparenteCard({
        plano_id: planoId,
        nome: formData.nome,
        email: formData.email,
        senha: formData.senha,
        cpf: formData.cpf,
        telefone: formData.telefone,
        card_token: cardFormData.token,
        installments: cardFormData.installments,
        payment_method_id: cardFormData.payment_method_id
      });

      const data = response.data;

      if (data.success) {
        localStorage.setItem('token', data.token);
        navigate('/dashboard?pagamento=sucesso');
      } else {
        throw new Error(data.message || 'Pagamento não aprovado');
      }

    } catch (error) {
      setErro(error.response?.data?.detail || error.message || 'Erro ao processar pagamento');
      setProcessandoPix(false);
      throw error; // Propagar erro para o Brick
    } finally {
      setProcessandoPix(false);
    }
  };

  // Máscaras e validações
  const aplicarMascaraCPF = (valor) => {
    return valor
      .replace(/\D/g, '')
      .replace(/(\d{3})(\d)/, '$1.$2')
      .replace(/(\d{3})(\d)/, '$1.$2')
      .replace(/(\d{3})(\d{1,2})/, '$1-$2')
      .replace(/(-\d{2})\d+?$/, '$1');
  };

  const aplicarMascaraTelefone = (valor) => {
    return valor
      .replace(/\D/g, '')
      .replace(/(\d{2})(\d)/, '($1) $2')
      .replace(/(\d{5})(\d)/, '$1-$2')
      .replace(/(-\d{4})\d+?$/, '$1');
  };

  const validarCPF = (cpf) => {
    cpf = cpf.replace(/\D/g, '');
    if (cpf.length !== 11) return false;
    if (/^(\d)\1{10}$/.test(cpf)) return false;

    let soma = 0;
    let resto;

    for (let i = 1; i <= 9; i++) {
      soma += parseInt(cpf.substring(i - 1, i)) * (11 - i);
    }
    resto = (soma * 10) % 11;
    if (resto === 10 || resto === 11) resto = 0;
    if (resto !== parseInt(cpf.substring(9, 10))) return false;

    soma = 0;
    for (let i = 1; i <= 10; i++) {
      soma += parseInt(cpf.substring(i - 1, i)) * (12 - i);
    }
    resto = (soma * 10) % 11;
    if (resto === 10 || resto === 11) resto = 0;
    if (resto !== parseInt(cpf.substring(10, 11))) return false;

    return true;
  };

  const handleChange = (e) => {
    let { name, value } = e.target;

    // Aplicar máscaras
    if (name === 'cpf') {
      value = aplicarMascaraCPF(value);
    } else if (name === 'telefone') {
      value = aplicarMascaraTelefone(value);
    }

    setFormData({ ...formData, [name]: value });
    setErro('');
  };

  // Validar formulário PIX
  const validarFormulario = () => {
    if (!formData.nome || !formData.email) {
      setErro('Por favor, preencha todos os campos obrigatórios');
      return false;
    }

    if (!formData.cpf || !validarCPF(formData.cpf)) {
      setErro('CPF inválido');
      return false;
    }

    // Validar telefone se preenchido
    if (formData.telefone) {
      const telefoneLimpo = formData.telefone.replace(/\D/g, '');
      if (telefoneLimpo.length < 10 || telefoneLimpo.length > 11) {
        setErro('Telefone inválido');
        return false;
      }
    }

    // Se não é upgrade (novo usuário), validar senha
    if (!isUpgrade) {
      if (!formData.senha || formData.senha.length < 8) {
        setErro('A senha deve ter pelo menos 8 caracteres, com letras e números');
        return false;
      }

      if (formData.senha !== formData.confirmarSenha) {
        setErro('As senhas não coincidem');
        return false;
      }
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      setErro('Email inválido');
      return false;
    }

    return true;
  };

  // Submit PIX
  const handleSubmitPix = async (e) => {
    e.preventDefault();

    // Se não é upgrade, validar formulário completo
    if (!isUpgrade && !validarFormulario()) return;

    setProcessandoPix(true);
    setErro('');

    try {
      // Determinar qual endpoint usar
      const isUserUpgrade = isUpgrade && user;

      let response;

      if (isUserUpgrade) {
        // Upgrade - usar endpoint com autenticação
        response = await assinaturasAPI.upgradePix({
          plano_id: planoId,
          cpf: formData.cpf.replace(/\D/g, ''),
          telefone: formData.telefone.replace(/\D/g, '')
        });
      } else {
        // Novo usuário - criar conta e pagamento
        response = await assinaturasAPI.checkoutTransparentePix({
          plano_id: planoId,
          nome: formData.nome,
          email: formData.email,
          senha: formData.senha,
          cpf: formData.cpf.replace(/\D/g, ''),
          telefone: formData.telefone ? formData.telefone.replace(/\D/g, '') : ''
        });
      }

      setPixData(response.data);
      setMetodoEscolhido('pix-gerado');
      setProcessandoPix(false);

    } catch (err) {
      // Axios coloca a resposta de erro em err.response
      let errorMessage = 'Erro ao processar pagamento. Por favor, tente novamente.';

      if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.message) {
        errorMessage = err.message;
      }

      setErro(errorMessage);
      setProcessandoPix(false);
    }
  };

  // PIX: Copiar código
  const copiarCodigoPix = () => {
    navigator.clipboard.writeText(pixData.qr_code);
    setPixCopied(true);
    setTimeout(() => setPixCopied(false), 2000);
  };

  // PIX: Polling para verificar pagamento
  useEffect(() => {
    if (!pixData || checandoPagamento || pagamentoAprovado) return;

    const interval = setInterval(async () => {
      try {
        const response = await assinaturasAPI.verificarPagamentoStatus(pixData.payment_id);

        if (response.data.approved) {
          setChecandoPagamento(true);
          setPagamentoAprovado(true);
          clearInterval(interval);

          // Salvar token para login automático
          if (pixData.token) {
            localStorage.setItem('token', pixData.token);
          }

          // Redirecionar após 3 segundos mostrando mensagem de sucesso
          setTimeout(() => {
            // Recarregar página para atualizar contexto de auth
            window.location.href = '/dashboard?pagamento=sucesso';
          }, 3000);
        }
      } catch (err) {
        // Silencioso no polling
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [pixData, checandoPagamento, pagamentoAprovado, navigate]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-white" />
      </div>
    );
  }

  if (!plano) {
    if (erro) {
      return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-6 rounded-xl max-w-md text-center">
            <h2 className="text-xl font-bold mb-2">Erro ao carregar</h2>
            <p>{erro}</p>
            <button
              onClick={() => navigate('/landing')}
              className="mt-4 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition"
            >
              Voltar para Início
            </button>
          </div>
        </div>
      );
    }
    return null;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="container mx-auto px-4 py-8">
        {/* Header com Logo */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center shadow-lg">
                <span className="text-lg font-bold text-white">K</span>
              </div>
              <span className="text-xl font-bold">
                <span className="text-emerald-500">Kredor</span>
              </span>
            </div>
            <button
              onClick={() => navigate('/landing')}
              className="flex items-center gap-2 text-slate-400 hover:text-white transition"
            >
              <ArrowLeft className="w-4 h-4" />
              Voltar
            </button>
          </div>
          <h1 className="text-3xl font-bold text-white">Checkout Seguro</h1>
          <p className="text-slate-400 mt-1">Complete seu pagamento</p>
        </div>

        <div className="grid lg:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {/* Resumo do Plano */}
          <div className="lg:col-span-1">
            <div className="bg-slate-900 backdrop-blur-xl rounded-2xl p-6 border border-slate-800 shadow-2xl sticky top-8">
              <h2 className="text-xl font-bold text-white mb-4">Resumo do Pedido</h2>
              <div className="space-y-3">
                <div className="flex justify-between text-slate-400">
                  <span>Plano</span>
                  <span className="font-semibold text-white">{plano.nome}</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Período</span>
                  <span>{plano.intervalo}</span>
                </div>
                <div className="border-t border-slate-800 pt-3 flex justify-between">
                  <span className="text-lg font-bold text-white">Total</span>
                  <span className="text-2xl font-bold text-emerald-500">
                    R$ {plano.preco.toFixed(2)}
                  </span>
                </div>
              </div>

              {/* Banners de Segurança */}
              <div className="mt-6 pt-6 border-t border-slate-800">
                <div className="flex items-center gap-2 text-sm text-slate-400 mb-4">
                  <Lock className="w-5 h-5 text-emerald-500" />
                  <span className="font-semibold text-white">Pagamento 100% seguro</span>
                </div>

                <div className="space-y-2">
                  {/* Mercado Pago */}
                  <div className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition">
                    <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
                      <span className="text-sm font-bold text-white">MP</span>
                    </div>
                    <div>
                      <span className="text-sm font-semibold text-white block">Mercado Pago</span>
                      <span className="text-xs text-slate-500">Gateway Oficial</span>
                    </div>
                  </div>

                  {/* SSL */}
                  <div className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition">
                    <Lock className="w-10 h-10 text-emerald-500 flex-shrink-0" />
                    <div>
                      <span className="text-sm font-semibold text-white block">SSL 256 bits</span>
                      <span className="text-xs text-slate-500">Criptografia de ponta</span>
                    </div>
                  </div>

                  {/* PCI DSS */}
                  <div className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition">
                    <Shield className="w-10 h-10 text-emerald-500 flex-shrink-0" />
                    <div>
                      <span className="text-sm font-semibold text-white block">Certificado PCI DSS</span>
                      <span className="text-xs text-slate-500">Padrão de segurança</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Formulário */}
          <div className="lg:col-span-2">
            <div className="bg-slate-900 backdrop-blur-xl rounded-2xl p-6 border border-slate-800 shadow-2xl relative">

              {/* Loading Overlay */}
              {processandoPix && (
                <div className="absolute inset-0 bg-slate-900/80 backdrop-blur-sm rounded-2xl z-50 flex items-center justify-center">
                  <div className="text-center">
                    <Loader2 className="w-12 h-12 text-emerald-500 animate-spin mx-auto mb-4" />
                    <p className="text-white font-semibold text-lg">Processando pagamento...</p>
                    <p className="text-slate-400 text-sm mt-2">Por favor, aguarde</p>
                  </div>
                </div>
              )}

              {/* Erro */}
              {erro && (
                <div className="mb-6 bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg">
                  {erro}
                </div>
              )}

              {/* Exibição do PIX Gerado */}
              {pixData && metodoEscolhido === 'pix-gerado' ? (
                pagamentoAprovado ? (
                  // TELA DE SUCESSO
                  <div className="text-center space-y-6 py-8">
                    <div className="w-24 h-24 mx-auto bg-emerald-500/20 rounded-full flex items-center justify-center">
                      <Check className="w-12 h-12 text-emerald-500" />
                    </div>
                    <div>
                      <h2 className="text-3xl font-bold text-emerald-400 mb-2">Pagamento Aprovado!</h2>
                      <p className="text-slate-400">Sua conta foi criada com sucesso.</p>
                    </div>
                    <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-6 py-4 rounded-xl">
                      <p className="text-lg font-semibold">🎉 Bem-vindo ao Kredor!</p>
                      <p className="text-sm mt-2 text-emerald-300">Redirecionando para o dashboard em instantes...</p>
                    </div>
                    <div className="flex items-center justify-center gap-2 text-slate-400">
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span>Preparando sua conta...</span>
                    </div>
                  </div>
                ) : (
                  // TELA DO QR CODE
                  <div className="text-center space-y-6">
                    <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-4 py-3 rounded-lg">
                      ✅ Pagamento PIX criado com sucesso!
                    </div>

                    <div className="bg-slate-800/50 p-6 rounded-xl border border-slate-700">
                      <h3 className="text-xl font-bold text-white mb-4">Escaneie o QR Code</h3>
                      <img
                        src={`data:image/png;base64,${pixData.qr_code_base64}`}
                        alt="QR Code PIX"
                        className="mx-auto w-64 h-64 bg-white p-4 rounded-xl"
                      />
                    </div>

                    <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700">
                      <p className="text-slate-400 mb-2 text-sm">Ou copie o código PIX:</p>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={pixData.qr_code}
                          readOnly
                          className="flex-1 bg-slate-800 text-white px-3 py-2 rounded-lg text-sm border border-slate-700"
                        />
                        <button
                          onClick={copiarCodigoPix}
                          className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition shadow-lg"
                        >
                          {pixCopied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                          {pixCopied ? 'Copiado!' : 'Copiar'}
                        </button>
                      </div>
                    </div>

                    <div className="bg-blue-500/10 border border-blue-500/30 text-blue-400 px-4 py-3 rounded-lg flex items-center justify-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Aguardando pagamento...
                    </div>

                    <div className="bg-amber-500/10 border border-amber-500/30 text-amber-400 px-4 py-3 rounded-lg text-sm">
                      ⏱️ <strong>Prazo de validade:</strong> Este QR Code expira em 24 horas
                    </div>

                    <p className="text-slate-500 text-sm">
                      ⚠️ Não feche esta página. Você será redirecionado automaticamente após o pagamento.
                    </p>
                  </div>
                )
              ) : (
                <>
                  {/* Seleção de Método */}
                  {!metodoEscolhido && (
                    <div className="space-y-6">
                      <div>
                        <h2 className="text-2xl font-bold text-white mb-2">Escolha a forma de pagamento</h2>
                        <p className="text-slate-400">Você permanecerá em nosso site durante todo o processo</p>
                      </div>

                      <div className="grid sm:grid-cols-2 gap-4">
                        <button
                          onClick={() => setMetodoEscolhido('pix')}
                          className="p-6 bg-slate-800/50 hover:bg-slate-800 border-2 border-slate-700 hover:border-emerald-500 rounded-xl transition-all duration-200 hover:scale-105 hover:shadow-xl"
                        >
                          <QrCode className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
                          <h3 className="text-xl font-bold text-white mb-1">PIX</h3>
                          <p className="text-slate-400 text-sm">Pagamento instantâneo</p>
                        </button>

                        <button
                          onClick={() => setMetodoEscolhido('card')}
                          className="p-6 bg-slate-800/50 hover:bg-slate-800 border-2 border-slate-700 hover:border-purple-500 rounded-xl transition-all duration-200 hover:scale-105 hover:shadow-xl"
                          disabled={!publicKey}
                        >
                          <svg className="w-12 h-12 text-purple-400 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                          </svg>
                          <h3 className="text-xl font-bold text-white mb-1">Cartão de Crédito</h3>
                          <p className="text-slate-400 text-sm">Aprovação imediata</p>
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Formulário PIX */}
                  {metodoEscolhido === 'pix' && (
                    <form onSubmit={handleSubmitPix} className="space-y-6">
                      <div className="flex items-center gap-3 mb-6">
                        <button
                          type="button"
                          onClick={() => setMetodoEscolhido('')}
                          className="text-slate-400 hover:text-white transition"
                        >
                          <ArrowLeft className="w-5 h-5" />
                        </button>
                        <div>
                          <h2 className="text-2xl font-bold text-white">Pagamento via PIX</h2>
                          <p className="text-slate-400 text-sm">Preencha seus dados</p>
                        </div>
                      </div>

                      <div className="space-y-4">
                        <div>
                          <label className="block text-slate-300 text-sm mb-2 font-medium">Nome Completo</label>
                          <input
                            type="text"
                            name="nome"
                            value={formData.nome}
                            onChange={handleChange}
                            className="w-full bg-slate-800 text-white px-4 py-3 rounded-lg border border-slate-700 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/30 focus:outline-none transition placeholder-slate-500"
                            placeholder="Seu nome completo"
                            required
                          />
                        </div>

                        <div>
                          <div className="flex items-center gap-2 mb-2">
                            <label className="block text-slate-300 text-sm font-medium">CPF *</label>
                            <div className="relative group">
                              <Info
                                className="w-4 h-4 text-slate-400 cursor-help"
                                onMouseEnter={() => setShowCpfTooltip(true)}
                                onMouseLeave={() => setShowCpfTooltip(false)}
                              />
                              {showCpfTooltip && (
                                <div className="absolute left-0 top-6 z-50 w-64 bg-slate-900 border border-slate-700 rounded-lg p-3 shadow-xl">
                                  <p className="text-xs text-slate-300 mb-2">
                                    <strong className="text-emerald-400">CPF Válido Necessário</strong>
                                  </p>
                                  <p className="text-xs text-slate-400 mb-2">
                                    O CPF deve ser válido e será verificado pelo Mercado Pago.
                                  </p>
                                  <p className="text-xs text-slate-500">
                                    💡 Para testes, use um gerador de CPF válido.
                                  </p>
                                </div>
                              )}
                            </div>
                          </div>
                          <div className="relative">
                            <input
                              type="text"
                              name="cpf"
                              value={formData.cpf}
                              onChange={handleChange}
                              className={`w-full bg-slate-800 text-white px-4 py-3 rounded-lg border transition placeholder-slate-500 ${formData.cpf && !validarCPF(formData.cpf)
                                ? 'border-red-500 focus:border-red-500 focus:ring-2 focus:ring-red-500/30'
                                : formData.cpf && validarCPF(formData.cpf)
                                  ? 'border-emerald-500 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/30'
                                  : 'border-slate-700 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/30'
                                } focus:outline-none`}
                              placeholder="000.000.000-00"
                              maxLength="14"
                              required
                            />
                            {formData.cpf && (
                              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                                {validarCPF(formData.cpf) ? (
                                  <CheckCircle className="w-5 h-5 text-emerald-500" />
                                ) : (
                                  <AlertCircle className="w-5 h-5 text-red-500" />
                                )}
                              </div>
                            )}
                          </div>
                          {formData.cpf && !validarCPF(formData.cpf) && (
                            <div className="flex items-center gap-1 mt-1">
                              <AlertCircle className="w-3 h-3 text-red-400" />
                              <p className="text-red-400 text-xs">CPF inválido - Verifique os dígitos</p>
                            </div>
                          )}
                          {formData.cpf && validarCPF(formData.cpf) && (
                            <div className="flex items-center gap-1 mt-1">
                              <CheckCircle className="w-3 h-3 text-emerald-400" />
                              <p className="text-emerald-400 text-xs">CPF válido</p>
                            </div>
                          )}
                        </div>

                        <div>
                          <label className="block text-slate-300 text-sm mb-2 font-medium">Email *</label>
                          <input
                            type="email"
                            name="email"
                            value={formData.email}
                            onChange={handleChange}
                            className="w-full bg-slate-800 text-white px-4 py-3 rounded-lg border border-slate-700 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/30 focus:outline-none transition placeholder-slate-500"
                            placeholder="seu@email.com"
                            required
                          />
                          {formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email) && (
                            <p className="text-red-400 text-xs mt-1">Email inválido</p>
                          )}
                        </div>

                        <div>
                          <label className="block text-slate-300 text-sm mb-2 font-medium">Telefone (Opcional)</label>
                          <input
                            type="text"
                            name="telefone"
                            value={formData.telefone}
                            onChange={handleChange}
                            className="w-full bg-slate-800 text-white px-4 py-3 rounded-lg border border-slate-700 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/30 focus:outline-none transition placeholder-slate-500"
                            placeholder="(11) 99999-9999"
                            maxLength="15"
                          />
                          {formData.telefone && formData.telefone.replace(/\D/g, '').length > 0 && formData.telefone.replace(/\D/g, '').length < 10 && (
                            <p className="text-red-400 text-xs mt-1">Telefone inválido</p>
                          )}
                        </div>

                        {/* Campos de senha apenas para novos usuários */}
                        {!isUpgrade && (
                          <>
                            <div>
                              <label className="block text-slate-300 text-sm mb-2 font-medium">Senha *</label>
                              <input
                                type="password"
                                name="senha"
                                value={formData.senha}
                                onChange={handleChange}
                                className="w-full bg-slate-800 text-white px-4 py-3 rounded-lg border border-slate-700 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/30 focus:outline-none transition placeholder-slate-500"
                                placeholder="Mínimo 8 caracteres"
                                required
                              />
                              {formData.senha && formData.senha.length < 8 && (
                                <p className="text-red-400 text-xs mt-1">Mínimo 8 caracteres</p>
                              )}
                            </div>

                            <div>
                              <label className="block text-slate-300 text-sm mb-2 font-medium">Confirmar Senha *</label>
                              <input
                                type="password"
                                name="confirmarSenha"
                                value={formData.confirmarSenha}
                                onChange={handleChange}
                                className="w-full bg-slate-800 text-white px-4 py-3 rounded-lg border border-slate-700 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/30 focus:outline-none transition placeholder-slate-500"
                                placeholder="Digite a senha novamente"
                                required
                              />
                              {formData.confirmarSenha && formData.senha !== formData.confirmarSenha && (
                                <p className="text-red-400 text-xs mt-1">As senhas não coincidem</p>
                              )}
                            </div>
                          </>
                        )}
                      </div>

                      <button
                        type="submit"
                        disabled={processandoPix}
                        className="w-full bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-700 hover:to-emerald-600 text-white py-4 rounded-lg font-semibold flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition shadow-lg hover:shadow-emerald-500/50 transform hover:-translate-y-0.5"
                      >
                        {processandoPix ? (
                          <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            Gerando PIX...
                          </>
                        ) : (
                          <>
                            <QrCode className="w-5 h-5" />
                            Gerar QR Code PIX
                          </>
                        )}
                      </button>
                    </form>
                  )}

                  {/* Card Payment Brick */}
                  {metodoEscolhido === 'card' && (
                    <div className="space-y-6">
                      <div className="flex items-center gap-3 mb-6">
                        <button
                          type="button"
                          onClick={() => {
                            setMetodoEscolhido('');
                            if (brickController) {
                              brickController.unmount();
                            }
                          }}
                          className="text-slate-400 hover:text-white transition"
                        >
                          <ArrowLeft className="w-5 h-5" />
                        </button>
                        <div>
                          <h2 className="text-2xl font-bold text-white">Pagamento com Cartão</h2>
                          <p className="text-slate-400 text-sm">Preencha seus dados e do cartão</p>
                        </div>
                      </div>

                      {/* Dados Pessoais */}
                      <div className="space-y-4 bg-slate-800/50 p-4 rounded-lg">
                        <h3 className="text-white font-semibold">
                          {isUpgrade ? 'Confirme seus dados' : 'Dados Pessoais'}
                        </h3>

                        {isUpgrade ? (
                          <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-700 mb-4">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-500">
                                <CheckCircle className="w-6 h-6" />
                              </div>
                              <div>
                                <p className="text-xs text-slate-500 uppercase tracking-wider">Assinando como</p>
                                <p className="font-bold text-white">{user?.nome}</p>
                                <p className="text-sm text-slate-400">{user?.email}</p>
                              </div>
                            </div>
                          </div>
                        ) : (
                          <>
                            <div>
                              <label className="block text-slate-300 text-sm mb-2 font-medium">Nome Completo *</label>
                              <input
                                type="text"
                                name="nome"
                                value={formData.nome}
                                onChange={handleChange}
                                className="w-full bg-slate-800 text-white px-4 py-3 rounded-lg border border-slate-700 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/30 focus:outline-none transition placeholder-slate-500"
                                placeholder="Seu nome completo"
                                required
                              />
                            </div>

                            <div>
                              <label className="block text-slate-300 text-sm mb-2 font-medium">Email *</label>
                              <input
                                type="email"
                                name="email"
                                value={formData.email}
                                onChange={handleChange}
                                className="w-full bg-slate-800 text-white px-4 py-3 rounded-lg border border-slate-700 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/30 focus:outline-none transition placeholder-slate-500"
                                placeholder="seu@email.com"
                                required
                              />
                              {formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email) && (
                                <p className="text-red-400 text-xs mt-1">Email inválido</p>
                              )}
                            </div>
                          </>
                        )}

                        <div>
                          <label className="block text-slate-300 text-sm mb-2 font-medium">CPF *</label>
                          <input
                            type="text"
                            name="cpf"
                            value={formData.cpf}
                            onChange={handleChange}
                            className="w-full bg-slate-800 text-white px-4 py-3 rounded-lg border border-slate-700 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/30 focus:outline-none transition placeholder-slate-500"
                            placeholder="000.000.000-00"
                            maxLength="14"
                            required
                          />
                          {formData.cpf && !validarCPF(formData.cpf) && (
                            <p className="text-red-400 text-xs mt-1">CPF inválido</p>
                          )}
                        </div>

                        <div>
                          <label className="block text-slate-300 text-sm mb-2 font-medium">Telefone (Opcional)</label>
                          <input
                            type="text"
                            name="telefone"
                            value={formData.telefone}
                            onChange={handleChange}
                            className="w-full bg-slate-800 text-white px-4 py-3 rounded-lg border border-slate-700 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/30 focus:outline-none transition placeholder-slate-500"
                            placeholder="(11) 99999-9999"
                            maxLength="15"
                          />
                          {formData.telefone && formData.telefone.replace(/\D/g, '').length > 0 && formData.telefone.replace(/\D/g, '').length < 10 && (
                            <p className="text-red-400 text-xs mt-1">Telefone inválido</p>
                          )}
                        </div>

                        {/* Campos de senha apenas para novos usuários */}
                        {!isUpgrade && (
                          <div className="grid sm:grid-cols-2 gap-4">
                            <div>
                              <label className="block text-slate-300 text-sm mb-2 font-medium">Senha *</label>
                              <input
                                type="password"
                                name="senha"
                                value={formData.senha}
                                onChange={handleChange}
                                className="w-full bg-slate-800 text-white px-4 py-3 rounded-lg border border-slate-700 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/30 focus:outline-none transition placeholder-slate-500"
                                placeholder="Mínimo 8 caracteres"
                                required
                              />
                              {formData.senha && formData.senha.length < 8 && (
                                <p className="text-red-400 text-xs mt-1">Mínimo 8 caracteres</p>
                              )}
                            </div>

                            <div>
                              <label className="block text-slate-300 text-sm mb-2 font-medium">Confirmar Senha *</label>
                              <input
                                type="password"
                                name="confirmarSenha"
                                value={formData.confirmarSenha}
                                onChange={handleChange}
                                className="w-full bg-slate-800 text-white px-4 py-3 rounded-lg border border-slate-700 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/30 focus:outline-none transition placeholder-slate-500"
                                placeholder="Digite novamente"
                                required
                              />
                              {formData.confirmarSenha && formData.senha !== formData.confirmarSenha && (
                                <p className="text-red-400 text-xs mt-1">As senhas não coincidem</p>
                              )}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Container do Card Payment Brick */}
                      <div id="cardPaymentBrick_container" className="min-h-[400px]"></div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>

        {/* Footer com Banners de Segurança */}
        <div className="mt-12 max-w-6xl mx-auto">
          <div className="bg-slate-900 backdrop-blur-xl rounded-2xl p-8 border border-slate-800">
            <div className="text-center mb-8">
              <div className="inline-flex items-center gap-2 bg-emerald-500/10 px-4 py-2 rounded-full mb-4">
                <Shield className="w-5 h-5 text-emerald-500" />
                <span className="text-emerald-400 font-semibold">Ambiente 100% Seguro</span>
              </div>
              <p className="text-sm text-slate-400">Seus dados estão protegidos com as melhores tecnologias de segurança</p>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {/* SSL Certificate */}
              <div className="flex flex-col items-center p-4 bg-slate-800/50 rounded-xl hover:bg-slate-800 transition">
                <Lock className="w-10 h-10 text-emerald-500 mb-3" />
                <span className="text-sm font-semibold text-white text-center">SSL 256-bit</span>
                <span className="text-xs text-slate-500 text-center mt-1">Criptografia</span>
              </div>

              {/* Mercado Pago */}
              <div className="flex flex-col items-center p-4 bg-slate-800/50 rounded-xl hover:bg-slate-800 transition">
                <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center mb-3">
                  <span className="text-lg font-bold text-white">MP</span>
                </div>
                <span className="text-sm font-semibold text-white text-center">Mercado Pago</span>
                <span className="text-xs text-slate-500 text-center mt-1">Gateway Oficial</span>
              </div>

              {/* PCI DSS */}
              <div className="flex flex-col items-center p-4 bg-slate-800/50 rounded-xl hover:bg-slate-800 transition">
                <Shield className="w-10 h-10 text-emerald-500 mb-3" />
                <span className="text-sm font-semibold text-white text-center">PCI DSS</span>
                <span className="text-xs text-slate-500 text-center mt-1">Certificado</span>
              </div>

              {/* Dados Protegidos */}
              <div className="flex flex-col items-center p-4 bg-slate-800/50 rounded-xl hover:bg-slate-800 transition">
                <svg className="w-10 h-10 text-emerald-500 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                <span className="text-sm font-semibold text-white text-center">Dados Protegidos</span>
                <span className="text-xs text-slate-500 text-center mt-1">LGPD</span>
              </div>
            </div>

            <div className="mt-8 pt-6 border-t border-slate-800 text-center">
              <p className="text-xs text-slate-500">
                Todos os pagamentos são processados de forma segura. Não armazenamos dados de cartão de crédito.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CheckoutTransparenteBrick;
