import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { CreditCard, QrCode, Copy, Check, Loader2, ArrowLeft, Lock, Shield } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { assinaturasAPI } from '../api/api';

const CheckoutTransparente = () => {
  const { planoId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isMember = !!user?.owner_id;

  // Redirecionar membros para o dashboard
  useEffect(() => {
    if (isMember) {
      navigate('/dashboard');
    }
  }, [isMember, navigate]);

  const [plano, setPlano] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processando, setProcessando] = useState(false);
  const [erro, setErro] = useState('');
  const [metodoEscolhido, setMetodoEscolhido] = useState(''); // 'pix' ou 'card'

  // Estados do PIX
  const [pixData, setPixData] = useState(null);
  const [pixCopied, setPixCopied] = useState(false);
  const [checandoPagamento, setChecandoPagamento] = useState(false);

  // Estados do Cartão
  const [cardForm, setCardForm] = useState({
    cardNumber: '',
    cardholderName: '',
    expirationDate: '',
    securityCode: '',
    identificationType: 'CPF',
    identificationNumber: '',
    installments: '1'
  });

  // Estados do Formulário Geral
  const [formData, setFormData] = useState({
    nome: '',
    email: '',
    senha: '',
    confirmarSenha: ''
  });

  const [mpLoaded, setMpLoaded] = useState(false);
  const [paymentMethodId, setPaymentMethodId] = useState('');

  // Carregar plano
  useEffect(() => {
    const fetchData = async () => {
      try {
        const { data: planos } = await assinaturasAPI.listarPlanos();
        const planoEncontrado = planos.find(p => p.id === planoId);

        if (!planoEncontrado || planoEncontrado.preco === 0) {
          navigate('/');
          return;
        }

        setPlano(planoEncontrado);
      } catch (err) {
        console.error('Erro ao carregar plano:', err);
        setErro('Erro ao carregar informações do plano');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [planoId, navigate]);

  // Carregar SDK do Mercado Pago
  useEffect(() => {
    const script = document.createElement('script');
    script.src = 'https://sdk.mercadopago.com/js/v2';
    script.async = true;
    script.onload = () => {
      setMpLoaded(true);
    };
    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
    };
  }, []);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setErro('');
  };

  const handleCardChange = (e) => {
    let value = e.target.value;
    const name = e.target.name;

    // Formatação de campos
    if (name === 'cardNumber') {
      value = value.replace(/\s/g, '').replace(/(\d{4})/g, '$1 ').trim();
    } else if (name === 'expirationDate') {
      value = value.replace(/\D/g, '').replace(/(\d{2})(\d)/, '$1/$2').substr(0, 5);
    } else if (name === 'securityCode') {
      value = value.replace(/\D/g, '').substr(0, 4);
    } else if (name === 'identificationNumber') {
      value = value.replace(/\D/g, '');
    }

    setCardForm({ ...cardForm, [name]: value });
  };

  // PIX: Copiar código
  const copiarCodigoPix = () => {
    navigator.clipboard.writeText(pixData.qr_code);
    setPixCopied(true);
    setTimeout(() => setPixCopied(false), 2000);
  };

  // PIX: Polling para verificar pagamento
  useEffect(() => {
    if (!pixData || checandoPagamento) return;

    const interval = setInterval(async () => {
      try {
        const { data } = await assinaturasAPI.verificarPagamentoStatus(pixData.payment_id);

        if (data.approved) {
          setChecandoPagamento(true);
          clearInterval(interval);

          // Aguardar um pouco para garantir que o backend atualizou o usuário
          setTimeout(() => {
            navigate('/dashboard?pagamento=sucesso');
          }, 2000);
        }
      } catch (err) {
        console.error('Erro ao verificar pagamento:', err);
      }
    }, 3000); // Verificar a cada 3 segundos

    return () => clearInterval(interval);
  }, [pixData, checandoPagamento, navigate]);

  // Validar formulário
  const validarFormulario = () => {
    if (!formData.nome || !formData.email || !formData.senha) {
      setErro('Preencha todos os campos');
      return false;
    }

    if (formData.senha.length < 6) {
      setErro('A senha deve ter pelo menos 6 caracteres');
      return false;
    }

    if (formData.senha !== formData.confirmarSenha) {
      setErro('As senhas não coincidem');
      return false;
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

    if (!validarFormulario()) return;

    setProcessando(true);
    setErro('');

    try {
      let data;
      try {
        const resp = await assinaturasAPI.checkoutTransparentePix({
          plano_id: planoId,
          nome: formData.nome,
          email: formData.email,
          senha: formData.senha
        });
        data = resp.data;
      } catch (apiErr) {
        console.error('Erro ao criar pagamento PIX:', apiErr.response?.data);
        throw new Error(apiErr.response?.data?.detail || 'Erro ao criar pagamento PIX');
      }

      // Salvar token imediatamente para permitir login após pagamento
      if (data.token) {
        localStorage.setItem('token', data.token);
        window.dispatchEvent(new Event('storage'));
      }

      setPixData(data);
      setMetodoEscolhido('pix-gerado');

    } catch (err) {
      console.error('Erro no checkout PIX:', err);
      setErro(err.message || 'Erro ao processar pagamento');
    } finally {
      setProcessando(false);
    }
  };

  // Submit Cartão
  const handleSubmitCard = async (e) => {
    e.preventDefault();

    if (!validarFormulario()) return;

    if (!cardForm.cardNumber || !cardForm.cardholderName || !cardForm.expirationDate || !cardForm.securityCode) {
      setErro('Preencha todos os dados do cartão');
      return;
    }

    setProcessando(true);
    setErro('');

    try {
      // Obter public key da configuração
      let config;
      try {
        const resp = await assinaturasAPI.listarGatewaysDisponiveis();
        config = resp.data;
      } catch (apiErr) {
        throw new Error('Erro ao carregar configurações do gateway');
      }

      if (!config.gateway || config.gateway.id !== 'mercadopago') {
        throw new Error('Mercado Pago não está configurado. Configure em /configuracoes');
      }

      const publicKey = config.gateway.public_key;

      if (!publicKey) {
        throw new Error('Public Key do Mercado Pago não encontrada');
      }

      if (!window.MercadoPago) {
        throw new Error('SDK do Mercado Pago não carregado');
      }

      const mp = new window.MercadoPago(publicKey);

      // Criar token do cartão
      const cardData = {
        cardNumber: cardForm.cardNumber.replace(/\s/g, ''),
        cardholderName: cardForm.cardholderName,
        cardExpirationMonth: cardForm.expirationDate.split('/')[0],
        cardExpirationYear: '20' + cardForm.expirationDate.split('/')[1],
        securityCode: cardForm.securityCode,
        identificationType: cardForm.identificationType,
        identificationNumber: cardForm.identificationNumber
      };

      const cardToken = await mp.createCardToken(cardData);

      if (!cardToken || !cardToken.id) {
        throw new Error('Erro ao processar dados do cartão');
      }

      // Identificar bandeira do cartão
      const paymentMethodId = cardToken.payment_method_id || 'master';

      // Enviar para backend
      let data;
      try {
        const resp = await assinaturasAPI.checkoutTransparenteCard({
          plano_id: planoId,
          nome: formData.nome,
          email: formData.email,
          senha: formData.senha,
          card_token: cardToken.id,
          installments: parseInt(cardForm.installments),
          payment_method_id: paymentMethodId
        });
        data = resp.data;
      } catch (apiErr) {
        console.error('Erro ao processar pagamento com cartão:', apiErr.response?.data);
        throw new Error(apiErr.response?.data?.detail || 'Erro ao processar pagamento');
      }

      if (data.success) {
        localStorage.setItem('token', data.token);
        navigate('/dashboard?pagamento=sucesso');
      } else {
        setErro(data.message || 'Pagamento não aprovado');
      }

    } catch (err) {
      console.error('Erro no checkout com cartão:', err);
      setErro(err.message || 'Erro ao processar pagamento');
    } finally {
      setProcessando(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-white" />
      </div>
    );
  }

  if (!plano) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/landing')}
            className="flex items-center gap-2 text-white/80 hover:text-white transition mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar
          </button>
          <h1 className="text-3xl font-bold text-white">Checkout Seguro</h1>
          <p className="text-white/60 mt-1">Complete seu pagamento</p>
        </div>

        <div className="grid lg:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {/* Resumo do Plano */}
          <div className="lg:col-span-1">
            <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20 sticky top-8">
              <h2 className="text-xl font-bold text-white mb-4">Resumo do Pedido</h2>
              <div className="space-y-3">
                <div className="flex justify-between text-white/80">
                  <span>Plano</span>
                  <span className="font-semibold text-white">{plano.nome}</span>
                </div>
                <div className="flex justify-between text-white/80">
                  <span>Período</span>
                  <span>{plano.intervalo}</span>
                </div>
                <div className="border-t border-white/20 pt-3 flex justify-between">
                  <span className="text-lg font-bold text-white">Total</span>
                  <span className="text-2xl font-bold text-emerald-400">
                    R$ {plano.preco.toFixed(2)}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Formulário */}
          <div className="lg:col-span-2">
            <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20">

              {/* Erro */}
              {erro && (
                <div className="mb-6 bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg">
                  {erro}
                </div>
              )}

              {/* Exibição do PIX Gerado */}
              {pixData && metodoEscolhido === 'pix-gerado' ? (
                <div className="text-center space-y-6">
                  <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-4 py-3 rounded-lg">
                    ✅ Pagamento PIX criado com sucesso!
                  </div>

                  <div className="bg-white/5 p-6 rounded-lg">
                    <h3 className="text-xl font-bold text-white mb-4">Escaneie o QR Code</h3>
                    <img
                      src={`data:image/png;base64,${pixData.qr_code_base64}`}
                      alt="QR Code PIX"
                      className="mx-auto w-64 h-64"
                    />
                  </div>

                  <div className="bg-white/5 p-4 rounded-lg">
                    <p className="text-white/80 mb-2 text-sm">Ou copie o código PIX:</p>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={pixData.qr_code}
                        readOnly
                        className="flex-1 bg-white/10 text-white px-3 py-2 rounded text-sm"
                      />
                      <button
                        onClick={copiarCodigoPix}
                        className="bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2 rounded flex items-center gap-2"
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
                </div>
              ) : (
                <>
                  {/* Seleção de Método (se ainda não escolheu) */}
                  {!metodoEscolhido && (
                    <div className="space-y-6">
                      <div>
                        <h2 className="text-2xl font-bold text-white mb-2">Escolha a forma de pagamento</h2>
                        <p className="text-white/60">Você permanecerá em nosso site durante todo o processo</p>
                      </div>

                      <div className="grid sm:grid-cols-2 gap-4">
                        <button
                          onClick={() => setMetodoEscolhido('pix')}
                          className="p-6 bg-white/5 hover:bg-white/10 border-2 border-white/20 hover:border-emerald-500 rounded-xl transition"
                        >
                          <QrCode className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
                          <h3 className="text-xl font-bold text-white mb-1">PIX</h3>
                          <p className="text-white/60 text-sm">Pagamento instantâneo</p>
                        </button>

                        <button
                          onClick={() => setMetodoEscolhido('card')}
                          className="p-6 bg-white/5 hover:bg-white/10 border-2 border-white/20 hover:border-purple-500 rounded-xl transition"
                        >
                          <CreditCard className="w-12 h-12 text-purple-400 mx-auto mb-3" />
                          <h3 className="text-xl font-bold text-white mb-1">Cartão de Crédito</h3>
                          <p className="text-white/60 text-sm">Aprovação imediata</p>
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
                          className="text-white/60 hover:text-white"
                        >
                          <ArrowLeft className="w-5 h-5" />
                        </button>
                        <div>
                          <h2 className="text-2xl font-bold text-white">Pagamento via PIX</h2>
                          <p className="text-white/60 text-sm">Preencha seus dados</p>
                        </div>
                      </div>

                      <div className="space-y-4">
                        <div>
                          <label className="block text-white/80 text-sm mb-2">Nome Completo</label>
                          <input
                            type="text"
                            name="nome"
                            value={formData.nome}
                            onChange={handleChange}
                            className="w-full bg-white/10 text-white px-4 py-3 rounded-lg border border-white/20 focus:border-emerald-500 focus:outline-none"
                            required
                          />
                        </div>

                        <div>
                          <label className="block text-white/80 text-sm mb-2">Email</label>
                          <input
                            type="email"
                            name="email"
                            value={formData.email}
                            onChange={handleChange}
                            className="w-full bg-white/10 text-white px-4 py-3 rounded-lg border border-white/20 focus:border-emerald-500 focus:outline-none"
                            required
                          />
                        </div>

                        <div>
                          <label className="block text-white/80 text-sm mb-2">Senha</label>
                          <input
                            type="password"
                            name="senha"
                            value={formData.senha}
                            onChange={handleChange}
                            className="w-full bg-white/10 text-white px-4 py-3 rounded-lg border border-white/20 focus:border-emerald-500 focus:outline-none"
                            required
                          />
                        </div>

                        <div>
                          <label className="block text-white/80 text-sm mb-2">Confirmar Senha</label>
                          <input
                            type="password"
                            name="confirmarSenha"
                            value={formData.confirmarSenha}
                            onChange={handleChange}
                            className="w-full bg-white/10 text-white px-4 py-3 rounded-lg border border-white/20 focus:border-emerald-500 focus:outline-none"
                            required
                          />
                        </div>
                      </div>

                      <button
                        type="submit"
                        disabled={processando}
                        className="w-full bg-emerald-500 hover:bg-emerald-600 text-white py-4 rounded-lg font-semibold flex items-center justify-center gap-2 disabled:opacity-50"
                      >
                        {processando ? (
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

                  {/* Formulário Cartão */}
                  {metodoEscolhido === 'card' && (
                    <form onSubmit={handleSubmitCard} className="space-y-6">
                      <div className="flex items-center gap-3 mb-6">
                        <button
                          type="button"
                          onClick={() => setMetodoEscolhido('')}
                          className="text-white/60 hover:text-white"
                        >
                          <ArrowLeft className="w-5 h-5" />
                        </button>
                        <div>
                          <h2 className="text-2xl font-bold text-white">Pagamento com Cartão</h2>
                          <p className="text-white/60 text-sm">Preencha seus dados e do cartão</p>
                        </div>
                      </div>

                      {/* Dados Pessoais */}
                      <div className="space-y-4">
                        <h3 className="text-white font-semibold">Dados Pessoais</h3>

                        <div>
                          <label className="block text-white/80 text-sm mb-2">Nome Completo</label>
                          <input
                            type="text"
                            name="nome"
                            value={formData.nome}
                            onChange={handleChange}
                            className="w-full bg-white/10 text-white px-4 py-3 rounded-lg border border-white/20 focus:border-purple-500 focus:outline-none"
                            required
                          />
                        </div>

                        <div>
                          <label className="block text-white/80 text-sm mb-2">Email</label>
                          <input
                            type="email"
                            name="email"
                            value={formData.email}
                            onChange={handleChange}
                            className="w-full bg-white/10 text-white px-4 py-3 rounded-lg border border-white/20 focus:border-purple-500 focus:outline-none"
                            required
                          />
                        </div>

                        <div className="grid sm:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-white/80 text-sm mb-2">Senha</label>
                            <input
                              type="password"
                              name="senha"
                              value={formData.senha}
                              onChange={handleChange}
                              className="w-full bg-white/10 text-white px-4 py-3 rounded-lg border border-white/20 focus:border-purple-500 focus:outline-none"
                              required
                            />
                          </div>

                          <div>
                            <label className="block text-white/80 text-sm mb-2">Confirmar Senha</label>
                            <input
                              type="password"
                              name="confirmarSenha"
                              value={formData.confirmarSenha}
                              onChange={handleChange}
                              className="w-full bg-white/10 text-white px-4 py-3 rounded-lg border border-white/20 focus:border-purple-500 focus:outline-none"
                              required
                            />
                          </div>
                        </div>
                      </div>

                      {/* Dados do Cartão */}
                      <div className="space-y-4 border-t border-white/20 pt-6">
                        <h3 className="text-white font-semibold">Dados do Cartão</h3>

                        <div>
                          <label className="block text-white/80 text-sm mb-2">Número do Cartão</label>
                          <input
                            type="text"
                            name="cardNumber"
                            value={cardForm.cardNumber}
                            onChange={handleCardChange}
                            placeholder="1234 5678 9012 3456"
                            maxLength="19"
                            className="w-full bg-white/10 text-white px-4 py-3 rounded-lg border border-white/20 focus:border-purple-500 focus:outline-none"
                            required
                          />
                        </div>

                        <div>
                          <label className="block text-white/80 text-sm mb-2">Nome no Cartão</label>
                          <input
                            type="text"
                            name="cardholderName"
                            value={cardForm.cardholderName}
                            onChange={handleCardChange}
                            placeholder="NOME COMO NO CARTÃO"
                            className="w-full bg-white/10 text-white px-4 py-3 rounded-lg border border-white/20 focus:border-purple-500 focus:outline-none uppercase"
                            required
                          />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-white/80 text-sm mb-2">Validade</label>
                            <input
                              type="text"
                              name="expirationDate"
                              value={cardForm.expirationDate}
                              onChange={handleCardChange}
                              placeholder="MM/AA"
                              maxLength="5"
                              className="w-full bg-white/10 text-white px-4 py-3 rounded-lg border border-white/20 focus:border-purple-500 focus:outline-none"
                              required
                            />
                          </div>

                          <div>
                            <label className="block text-white/80 text-sm mb-2">CVV</label>
                            <input
                              type="text"
                              name="securityCode"
                              value={cardForm.securityCode}
                              onChange={handleCardChange}
                              placeholder="123"
                              maxLength="4"
                              className="w-full bg-white/10 text-white px-4 py-3 rounded-lg border border-white/20 focus:border-purple-500 focus:outline-none"
                              required
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-white/80 text-sm mb-2">Documento</label>
                            <select
                              name="identificationType"
                              value={cardForm.identificationType}
                              onChange={handleCardChange}
                              className="w-full bg-white/10 text-white px-4 py-3 rounded-lg border border-white/20 focus:border-purple-500 focus:outline-none"
                            >
                              <option value="CPF">CPF</option>
                              <option value="CNPJ">CNPJ</option>
                            </select>
                          </div>

                          <div>
                            <label className="block text-white/80 text-sm mb-2">Número do Documento</label>
                            <input
                              type="text"
                              name="identificationNumber"
                              value={cardForm.identificationNumber}
                              onChange={handleCardChange}
                              placeholder={cardForm.identificationType === 'CPF' ? '000.000.000-00' : '00.000.000/0000-00'}
                              className="w-full bg-white/10 text-white px-4 py-3 rounded-lg border border-white/20 focus:border-purple-500 focus:outline-none"
                              required
                            />
                          </div>
                        </div>

                        <div>
                          <label className="block text-white/80 text-sm mb-2">Parcelas</label>
                          <select
                            name="installments"
                            value={cardForm.installments}
                            onChange={handleCardChange}
                            className="w-full bg-white/10 text-white px-4 py-3 rounded-lg border border-white/20 focus:border-purple-500 focus:outline-none"
                          >
                            <option value="1">1x de R$ {plano.preco.toFixed(2)} sem juros</option>
                            <option value="2">2x de R$ {(plano.preco / 2).toFixed(2)} sem juros</option>
                            <option value="3">3x de R$ {(plano.preco / 3).toFixed(2)} sem juros</option>
                          </select>
                        </div>
                      </div>

                      <button
                        type="submit"
                        disabled={processando || !mpLoaded}
                        className="w-full bg-purple-500 hover:bg-purple-600 text-white py-4 rounded-lg font-semibold flex items-center justify-center gap-2 disabled:opacity-50"
                      >
                        {processando ? (
                          <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            Processando pagamento...
                          </>
                        ) : (
                          <>
                            <CreditCard className="w-5 h-5" />
                            Finalizar Pagamento
                          </>
                        )}
                      </button>
                    </form>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CheckoutTransparente;
