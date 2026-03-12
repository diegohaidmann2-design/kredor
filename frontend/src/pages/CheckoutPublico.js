import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import Loading from '../components/Loading';
import { ArrowLeft, Check, CreditCard, Lock, Wallet, Tag, CheckCircle, X, User } from 'lucide-react';
import { assinaturasAPI, configuracoesAPI } from '../api/api';
import { useAuth } from '../context/AuthContext';

const CheckoutPublico = () => {
  const { planoId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user, isAuthenticated } = useAuth();
  const isUpgrade = searchParams.get('upgrade') === 'true' && isAuthenticated;

  const [plano, setPlano] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processando, setProcessando] = useState(false);
  const [erro, setErro] = useState('');
  const [gateway, setGateway] = useState(null);
  const [estrategia, setEstrategia] = useState('');
  const [metodoPagamento, setMetodoPagamento] = useState('cartao');

  const [formData, setFormData] = useState({
    nome: user?.nome || '',
    email: user?.email || '',
    senha: '',
    confirmarSenha: '',
    cpf: '',
    telefone: ''
  });

  // Atualizar formData quando o usuário carregar (para casos de upgrade)
  useEffect(() => {
    if (user && isUpgrade) {
      setFormData(prev => ({
        ...prev,
        nome: user.nome || '',
        email: user.email || ''
      }));
    }
  }, [user, isUpgrade]);

  // 🆕 Estado para cupom
  const [codigoCupom, setCodigoCupom] = useState('');
  const [cupomAplicado, setCupomAplicado] = useState(null);
  const [validandoCupom, setValidandoCupom] = useState(false);
  const [erroCupom, setErroCupom] = useState('');
  const [valorComDesconto, setValorComDesconto] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Buscar planos usando o service centralizado
        const planosResponse = await assinaturasAPI.listarPlanos();
        const planos = Array.isArray(planosResponse.data) ? planosResponse.data : [];
        const planoEncontrado = planos.find(p => p.id === planoId);

        if (!planoEncontrado || planoEncontrado.preco === 0) {
          navigate('/');
          return;
        }

        setPlano(planoEncontrado);

        // Buscar gateway configurado
        const gatewayResponse = await assinaturasAPI.listarGatewaysDisponiveis();
        const gatewayData = gatewayResponse.data;

        if (!gatewayData.gateway) {
          setErro('Sistema de pagamento não configurado. Entre em contato com o suporte.');
          setLoading(false);
          return;
        }

        setGateway(gatewayData.gateway);
        setEstrategia(gatewayData.estrategia);

        // Definir método padrão baseado nos métodos disponíveis
        if (gatewayData.gateway.metodos?.includes('cartao')) {
          setMetodoPagamento('cartao');
        } else if (gatewayData.gateway.metodos?.includes('pix')) {
          setMetodoPagamento('pix');
        }

      } catch (err) {
        console.error('Erro ao carregar dados:', err);
        setErro('Erro ao carregar informações. Tente novamente.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [planoId, navigate]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setErro('');
  };

  // 🆕 Função para aplicar cupom
  const handleAplicarCupom = async () => {
    if (!codigoCupom.trim()) {
      setErroCupom('Digite um código de cupom');
      return;
    }

    setValidandoCupom(true);
    setErroCupom('');

    try {
      const response = await assinaturasAPI.validarCupom(codigoCupom, formData.email);
      const data = response.data;

      if (data.valido) {
        // Calcular valor com desconto
        const desconto = (plano.preco * data.desconto_percentual) / 100;
        const valorFinal = plano.preco - desconto;

        setCupomAplicado({
          codigo: data.codigo,
          desconto_percentual: data.desconto_percentual,
          desconto: desconto,
          valor_final: valorFinal
        });
        setValorComDesconto(valorFinal);
        setErroCupom('');
      } else {
        setErroCupom(data.erro || 'Cupom inválido');
        setCupomAplicado(null);
        setValorComDesconto(null);
      }
    } catch (error) {
      setErroCupom('Erro ao validar cupom. Tente novamente.');
      setCupomAplicado(null);
      setValorComDesconto(null);
    } finally {
      setValidandoCupom(false);
    }
  };

  // 🆕 Função para remover cupom
  const handleRemoverCupom = () => {
    setCodigoCupom('');
    setCupomAplicado(null);
    setValorComDesconto(null);
    setErroCupom('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErro('');

    // Validações apenas para novos usuários
    if (!isUpgrade) {
      if (formData.senha.length < 6) {
        setErro('A senha deve ter pelo menos 6 caracteres');
        return;
      }

      if (formData.senha !== formData.confirmarSenha) {
        setErro('As senhas não coincidem');
        return;
      }

      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(formData.email)) {
        setErro('Email inválido');
        return;
      }
    }

    setProcessando(true);

    try {
      let response;

      // Usar o gateway definido pelo ADMIN, não pelo cliente
      if (gateway.id === 'asaas') {
        // Checkout via Asaas
        response = await assinaturasAPI.checkoutAsaas({
          plano_id: planoId,
          nome: formData.nome,
          email: formData.email,
          cpf: formData.cpf || '',
          senha: formData.senha,
          metodo_pagamento: metodoPagamento.toUpperCase(), // PIX, BOLETO, CREDIT_CARD
          codigo_cupom: cupomAplicado ? cupomAplicado.codigo : null,
          telefone: formData.telefone || null
        });
      } else if (gateway.id === 'stripe') {
        // Checkout via Stripe
        response = await assinaturasAPI.checkoutPublico({
          plano_id: planoId,
          nome: formData.nome,
          email: formData.email,
          senha: formData.senha,
          origin_url: window.location.origin,
          codigo_cupom: cupomAplicado ? cupomAplicado.codigo : null
        });
      } else if (gateway.id === 'mercadopago') {
        // Checkout via Mercado Pago
        response = await assinaturasAPI.checkoutMercadoPago({
          plano_id: planoId,
          nome: formData.nome,
          email: formData.email,
          senha: formData.senha,
          origin_url: window.location.origin,
          metodo_pagamento: metodoPagamento
        });
      }

      const data = response.data;

      // Salvar token no localStorage para fazer login automático após pagamento
      localStorage.setItem('checkout_token', data.token);

      // Se for Asaas, redirecionar para página de pagamento interna
      if (gateway.id === 'asaas') {
        navigate(`/checkout-asaas-pagamento?transacao=${data.transacao_id}`);
      } else {
        // Stripe e MercadoPago redirecionam para página externa
        window.location.href = data.checkout_url;
      }

    } catch (err) {
      setErro(err.response?.data?.detail || err.message || 'Erro ao processar pagamento. Tente novamente.');
      setProcessando(false);
    }
  };

  if (loading) {
    return <Loading message="Carregando informações do plano..." />;
  }

  if (!plano) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900 py-12 px-4">
      <div className="container mx-auto max-w-6xl">
        {/* Header */}
        <div className="mb-8">
          <Link to="/" className="inline-flex items-center text-sm text-slate-600 dark:text-slate-400 hover:text-primary mb-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Voltar para o início
          </Link>

          <div className="flex items-center gap-3 mb-2">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-400 to-green-500 flex items-center justify-center shadow-glow">
              <span className="text-xl font-display font-bold text-white">GC</span>
            </div>
            <div>
              <h1 className="text-2xl font-display font-bold text-slate-900 dark:text-white">
                <span className="text-emerald-500">Gestor</span>Cred
              </h1>
              <p className="text-sm text-slate-600 dark:text-slate-400">Checkout Seguro</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Formulário */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <Card>
              <CardHeader>
                <CardTitle>{isUpgrade ? 'Confirmar alteração de plano' : 'Criar conta e assinar'}</CardTitle>
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  {isUpgrade 
                    ? 'Confirme seus dados para prosseguir com o pagamento' 
                    : 'Preencha seus dados para continuar'}
                </p>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                  {erro && (
                    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200 px-4 py-3 rounded-lg text-sm" data-testid="checkout-error">
                      {erro}
                    </div>
                  )}

                  {isUpgrade ? (
                    // Informações do Usuário Logado (Upgrade)
                    <div className="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-200 dark:border-slate-700 mb-6">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                          <User className="w-6 h-6" />
                        </div>
                        <div>
                          <p className="text-sm text-slate-500 dark:text-slate-400 font-medium text-xs uppercase tracking-wider">Assinando como</p>
                          <p className="font-bold text-slate-900 dark:text-white">{user?.nome}</p>
                          <p className="text-sm text-slate-600 dark:text-slate-400">{user?.email}</p>
                        </div>
                      </div>
                    </div>
                  ) : (
                    // Formulário de Criação de Conta (Novo Usuário)
                    <>
                      <div>
                        <label className="block text-sm font-medium mb-2">Nome completo</label>
                        <input
                          type="text"
                          name="nome"
                          value={formData.nome}
                          onChange={handleChange}
                          className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700"
                          placeholder="Seu nome"
                          required
                          autoComplete="name"
                          data-testid="input-nome"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium mb-2">Email</label>
                        <input
                          type="email"
                          name="email"
                          value={formData.email}
                          onChange={handleChange}
                          className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700"
                          placeholder="seu@email.com"
                          required
                          autoComplete="email"
                          data-testid="input-email"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium mb-2">Senha</label>
                        <input
                          type="password"
                          name="senha"
                          value={formData.senha}
                          onChange={handleChange}
                          className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700"
                          placeholder="Mínimo 6 caracteres"
                          required
                          minLength={6}
                          autoComplete="new-password"
                          data-testid="input-senha"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium mb-2">Confirmar senha</label>
                        <input
                          type="password"
                          name="confirmarSenha"
                          value={formData.confirmarSenha}
                          onChange={handleChange}
                          className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700"
                          placeholder="Digite a senha novamente"
                          required
                          autoComplete="new-password"
                          data-testid="input-confirmar-senha"
                        />
                      </div>
                    </>
                  )}

                  {/* Info sobre Gateway Configurado */}
                  {gateway && (
                    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-3 rounded-lg">
                      <div className="flex items-center gap-2 text-sm text-blue-800 dark:text-blue-200">
                        <Lock className="w-4 h-4" />
                        <span>
                          Pagamento processado via <strong>{gateway.nome}</strong> - Ambiente seguro
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Seleção de Método (para Mercado Pago) */}
                  {gateway?.id === 'mercadopago' && gateway?.metodos?.length > 1 && (
                    <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded-lg">
                      <label className="block text-sm font-medium mb-3">Método de Pagamento</label>
                      <div className="flex gap-3">
                        {gateway.metodos.includes('cartao') && (
                          <button
                            type="button"
                            onClick={() => setMetodoPagamento('cartao')}
                            className={`flex-1 p-3 border-2 rounded-lg flex items-center justify-center gap-2 transition ${metodoPagamento === 'cartao'
                              ? 'border-primary bg-primary/5'
                              : 'border-slate-200 dark:border-slate-600'
                              }`}
                            data-testid="metodo-cartao"
                          >
                            <CreditCard className="w-5 h-5" />
                            <span className="text-sm font-medium">Cartão</span>
                          </button>
                        )}
                        {gateway.metodos.includes('pix') && (
                          <button
                            type="button"
                            onClick={() => setMetodoPagamento('pix')}
                            className={`flex-1 p-3 border-2 rounded-lg flex items-center justify-center gap-2 transition ${metodoPagamento === 'pix'
                              ? 'border-primary bg-primary/5'
                              : 'border-slate-200 dark:border-slate-600'
                              }`}
                            data-testid="metodo-pix"
                          >
                            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                              <path d="M12.5 2L6 8.5l3.5 3.5L6 15.5 12.5 22l6.5-6.5-3.5-3.5 3.5-3.5L12.5 2zm0 3.41L15.09 8.5 12.5 11.09 9.91 8.5l2.59-2.59zm0 8.18l2.59 2.59-2.59 2.59-2.59-2.59 2.59-2.59z" />
                            </svg>
                            <span className="text-sm font-medium">PIX</span>
                          </button>
                        )}
                      </div>
                    </div>
                  )}

                  {/* 🆕 Campo de Cupom */}
                  <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded-lg border-2 border-dashed border-slate-200 dark:border-slate-700">
                    <label className="block text-sm font-medium mb-2 flex items-center gap-2">
                      <Tag className="w-4 h-4" />
                      Cupom de Desconto (Opcional)
                    </label>

                    {!cupomAplicado ? (
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={codigoCupom}
                          onChange={(e) => setCodigoCupom(e.target.value.toUpperCase())}
                          className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-600"
                          placeholder="Digite o código"
                          disabled={validandoCupom}
                        />
                        <Button
                          type="button"
                          onClick={handleAplicarCupom}
                          disabled={validandoCupom || !codigoCupom.trim()}
                          className="bg-emerald-600 hover:bg-emerald-700 text-white"
                        >
                          {validandoCupom ? 'Validando...' : 'Aplicar'}
                        </Button>
                      </div>
                    ) : (
                      <div className="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 p-3 rounded-lg">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <CheckCircle className="w-5 h-5 text-emerald-600" />
                            <div>
                              <p className="text-sm font-medium text-emerald-800 dark:text-emerald-200">
                                Cupom {cupomAplicado.codigo} aplicado!
                              </p>
                              <p className="text-xs text-emerald-600 dark:text-emerald-300">
                                {cupomAplicado.desconto_percentual}% de desconto
                              </p>
                            </div>
                          </div>
                          <button
                            type="button"
                            onClick={handleRemoverCupom}
                            className="text-emerald-600 hover:text-emerald-800 dark:text-emerald-400"
                          >
                            <X className="w-5 h-5" />
                          </button>
                        </div>
                      </div>
                    )}

                    {erroCupom && (
                      <p className="text-xs text-red-600 dark:text-red-400 mt-2">{erroCupom}</p>
                    )}
                  </div>

                  <Button
                    type="submit"
                    className="w-full bg-primary hover:bg-primary/90 text-white"
                    disabled={processando}
                    data-testid="checkout-submit"
                  >
                    {processando ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                        Processando...
                      </>
                    ) : (
                      <>
                        {gateway?.id === 'stripe' ? (
                          <CreditCard className="w-4 h-4 mr-2" />
                        ) : (
                          <Wallet className="w-4 h-4 mr-2" />
                        )}
                        Continuar para pagamento
                      </>
                    )}
                  </Button>

                  <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 pt-2">
                    <Lock className="w-3 h-3" />
                    {gateway?.id === 'stripe'
                      ? 'Pagamento seguro processado pelo Stripe'
                      : 'Pagamento seguro processado pelo Mercado Pago'
                    }
                  </div>
                </form>
              </CardContent>
            </Card>
          </motion.div>

          {/* Resumo do Plano */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <Card className="sticky top-8">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Resumo do pedido</CardTitle>
                  {plano.destaque && (
                    <Badge className="bg-primary/10 text-primary">Popular</Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <h3 className="text-2xl font-bold mb-1">{plano.nome}</h3>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-primary">
                      R$ {plano.preco.toFixed(2).replace('.', ',')}
                    </span>
                    <span className="text-slate-600 dark:text-slate-400">/{plano.intervalo}</span>
                  </div>
                </div>

                <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
                  <h4 className="font-semibold mb-3">Recursos inclusos:</h4>
                  <ul className="space-y-2">
                    {plano.recursos.map((recurso, index) => (
                      <li key={index} className="flex items-start gap-2 text-sm">
                        <Check className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                        <span>{recurso}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
                  <h4 className="font-semibold mb-2">Limites:</h4>
                  <div className="space-y-1 text-sm text-slate-600 dark:text-slate-400">
                    <p>
                      • {plano.clientes === -1 ? 'Clientes ilimitados' : `Até ${plano.clientes} clientes`}
                    </p>
                    <p>
                      • {plano.emprestimos === -1 ? 'Empréstimos ilimitados' : `Até ${plano.emprestimos} empréstimos`}
                    </p>
                  </div>
                </div>

                {/* 🆕 Mostrar Desconto do Cupom */}
                {cupomAplicado && (
                  <div className="border-t border-slate-200 dark:border-slate-700 pt-4 bg-emerald-50 dark:bg-emerald-900/10 -mx-6 px-6 py-4">
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-slate-600 dark:text-slate-400">Subtotal:</span>
                        <span className="line-through">R$ {plano.preco.toFixed(2).replace('.', ',')}</span>
                      </div>
                      <div className="flex justify-between text-sm text-emerald-600 dark:text-emerald-400 font-medium">
                        <span>Desconto ({cupomAplicado.codigo}):</span>
                        <span>-R$ {cupomAplicado.desconto.toFixed(2).replace('.', ',')}</span>
                      </div>
                      <div className="flex justify-between text-lg font-bold border-t border-emerald-200 dark:border-emerald-800 pt-2">
                        <span>Total:</span>
                        <span className="text-emerald-600 dark:text-emerald-400">
                          R$ {cupomAplicado.valor_final.toFixed(2).replace('.', ',')}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Gateway Info */}
                <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
                  <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                    {gateway?.id === 'stripe' ? (
                      <>
                        <CreditCard className="w-4 h-4" />
                        <span>Pagamento via Stripe</span>
                      </>
                    ) : (
                      <>
                        <Wallet className="w-4 h-4" />
                        <span>Pagamento via Mercado Pago ({metodoPagamento === 'pix' ? 'PIX' : 'Cartão'})</span>
                      </>
                    )}
                  </div>
                </div>

                <div className="bg-slate-50 dark:bg-slate-800 p-4 rounded-lg">
                  <p className="text-xs text-slate-600 dark:text-slate-400">
                    Ao continuar, você concorda com nossos{' '}
                    <Link to="/termos" className="text-primary hover:underline">
                      Termos de Uso
                    </Link>{' '}
                    e{' '}
                    <Link to="/privacidade" className="text-primary hover:underline">
                      Política de Privacidade
                    </Link>
                  </p>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default CheckoutPublico;
