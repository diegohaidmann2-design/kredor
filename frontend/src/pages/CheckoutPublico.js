import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '../components/ui/button';
import Loading from '../components/Loading';
import { ArrowLeft, Check, Lock, Tag, CheckCircle, X, User, ShieldCheck, QrCode, CreditCard, Receipt, Loader2, Star, Users, TrendingUp, Zap } from 'lucide-react';
import { assinaturasAPI } from '../api/api';
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
  const [metodoPagamento, setMetodoPagamento] = useState('pix');

  const [formData, setFormData] = useState({
    nome: user?.nome || '',
    email: user?.email || '',
    senha: '',
    confirmarSenha: '',
    cpf: '',
    telefone: ''
  });

  useEffect(() => {
    if (user && isUpgrade) {
      setFormData(prev => ({ ...prev, nome: user.nome || '', email: user.email || '' }));
    }
  }, [user, isUpgrade]);

  const [codigoCupom, setCodigoCupom] = useState('');
  const [cupomAplicado, setCupomAplicado] = useState(null);
  const [validandoCupom, setValidandoCupom] = useState(false);
  const [erroCupom, setErroCupom] = useState('');
  const [socialProof, setSocialProof] = useState(null);
  const [atividadeIndex, setAtividadeIndex] = useState(0);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const planosResponse = await assinaturasAPI.listarPlanos();
        const planos = Array.isArray(planosResponse.data) ? planosResponse.data : [];
        const planoEncontrado = planos.find(p => p.id === planoId);
        if (!planoEncontrado || planoEncontrado.preco === 0) { navigate('/'); return; }
        setPlano(planoEncontrado);

        const gatewayResponse = await assinaturasAPI.listarGatewaysDisponiveis();
        const gatewayData = gatewayResponse.data;
        if (!gatewayData.gateway) { setErro('Sistema de pagamento indisponivel.'); setLoading(false); return; }
        setGateway(gatewayData.gateway);

        if (gatewayData.gateway.id === 'syncpay') setMetodoPagamento('pix');
        else if (gatewayData.gateway.id === 'asaas') setMetodoPagamento('pix');
        else if (gatewayData.gateway.metodos?.includes('pix')) setMetodoPagamento('pix');
        else if (gatewayData.gateway.metodos?.includes('cartao')) setMetodoPagamento('cartao');

        // Social proof
        try {
          const spRes = await assinaturasAPI.obterSocialProof();
          setSocialProof(spRes.data);
        } catch { /* silent */ }
      } catch { setErro('Erro ao carregar. Tente novamente.'); }
      finally { setLoading(false); }
    };
    fetchData();
  }, [planoId, navigate]);

  const handleChange = (e) => { setFormData({ ...formData, [e.target.name]: e.target.value }); setErro(''); };

  const handleAplicarCupom = async () => {
    if (!codigoCupom.trim()) { setErroCupom('Digite um codigo'); return; }
    setValidandoCupom(true); setErroCupom('');
    try {
      const response = await assinaturasAPI.validarCupom(codigoCupom, formData.email);
      const data = response.data;
      if (data.valido) {
        const desconto = (plano.preco * data.desconto_percentual) / 100;
        setCupomAplicado({ codigo: data.codigo, desconto_percentual: data.desconto_percentual, desconto, valor_final: plano.preco - desconto });
        setErroCupom('');
      } else { setErroCupom(data.erro || 'Cupom invalido'); setCupomAplicado(null); }
    } catch { setErroCupom('Erro ao validar cupom.'); setCupomAplicado(null); }
    finally { setValidandoCupom(false); }
  };

  const handleRemoverCupom = () => { setCodigoCupom(''); setCupomAplicado(null); setErroCupom(''); };

  const valorFinal = cupomAplicado ? cupomAplicado.valor_final : plano?.preco || 0;

  // Rotacionar atividade recente
  useEffect(() => {
    if (!socialProof?.atividade_recente?.length) return;
    const timer = setInterval(() => {
      setAtividadeIndex(prev => (prev + 1) % socialProof.atividade_recente.length);
    }, 8000);
    return () => clearInterval(timer);
  }, [socialProof]);

  const handleSubmit = async (e) => {
    e.preventDefault(); setErro('');
    if (!isUpgrade) {
      if (formData.senha.length < 6) { setErro('A senha deve ter pelo menos 6 caracteres'); return; }
      if (formData.senha !== formData.confirmarSenha) { setErro('As senhas nao coincidem'); return; }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) { setErro('Email invalido'); return; }
    }
    setProcessando(true);
    try {
      let response;
      if (gateway.id === 'asaas') {
        response = await assinaturasAPI.checkoutAsaas({ plano_id: planoId, nome: formData.nome, email: formData.email, cpf: formData.cpf || '', senha: formData.senha, metodo_pagamento: metodoPagamento.toUpperCase(), codigo_cupom: cupomAplicado?.codigo || null, telefone: formData.telefone || null });
      } else if (gateway.id === 'syncpay') {
        response = await assinaturasAPI.checkoutSyncPay({ plano_id: planoId, nome: formData.nome, email: formData.email, senha: formData.senha, cpf: formData.cpf || null, telefone: formData.telefone || null, codigo_cupom: cupomAplicado?.codigo || null });
      } else if (gateway.id === 'mercadopago') {
        response = await assinaturasAPI.checkoutMercadoPago({ plano_id: planoId, nome: formData.nome, email: formData.email, senha: formData.senha, origin_url: window.location.origin, metodo_pagamento: metodoPagamento });
      } else {
        // Sem ramo para o gateway: antes caía em `response.data` de undefined e o visitante
        // via "Erro ao processar" sem pista. (O ramo do Stripe saiu: a tarefa 3.1 aposentou
        // esse gateway e /assinaturas/checkout-publico não existe mais no backend.)
        setErro('Forma de pagamento indisponível no momento. Tente novamente em alguns minutos.');
        setProcessando(false);
        return;
      }
      const data = response.data;
      localStorage.setItem('checkout_token', data.token);
      if (gateway.id === 'asaas') navigate(`/checkout-asaas-pagamento?transacao=${data.transacao_id}`);
      else if (gateway.id === 'syncpay') { if (data.pix_code) sessionStorage.setItem('syncpay_pix_code', data.pix_code); navigate(`/checkout-syncpay-pagamento?transacao=${data.transacao_id}&transaction_id=${data.transaction_id}`); }
      else window.location.href = data.checkout_url;
    } catch (err) { setErro(err.response?.data?.detail || 'Erro ao processar. Tente novamente.'); setProcessando(false); }
  };

  if (loading) return <Loading message="Preparando checkout..." />;
  if (!plano) return null;

  const inputClass = "w-full bg-zinc-900 border border-white/10 rounded-xl px-4 py-3.5 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all text-sm";
  const labelClass = "block text-sm font-medium text-zinc-300 mb-2";

  return (
    <div className="min-h-screen" style={{ background: 'hsl(240,10%,4%)' }}>
      {/* Top bar */}
      <div className="border-b border-white/5">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 group" data-testid="checkout-logo">
            <div className="w-9 h-9 rounded-lg bg-emerald-500 flex items-center justify-center">
              <span className="text-sm font-black text-white">K</span>
            </div>
            <span className="text-lg font-bold text-white">
              <span className="text-emerald-400">Kredor</span>
            </span>
          </Link>
          <div className="flex items-center gap-2 text-zinc-500 text-xs">
            <ShieldCheck className="w-4 h-4" />
            <span>Checkout Seguro</span>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-16">
        {/* Back link */}
        <Link to="/" className="inline-flex items-center gap-2 text-zinc-500 hover:text-zinc-300 text-sm mb-6 sm:mb-8 transition-colors" data-testid="checkout-back">
          <ArrowLeft className="w-4 h-4" />
          Voltar
        </Link>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-16 items-start">
          {/* LEFT COLUMN - Form */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="col-span-1 lg:col-span-7 space-y-8">

            {/* Social Proof Stats Bar */}
            {socialProof && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
                className="grid grid-cols-3 gap-3 sm:flex sm:flex-wrap sm:gap-6 py-3 border-b border-white/5 pb-6">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
                    <Users className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-emerald-400" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-white text-xs sm:text-sm font-bold">{socialProof.gestores_ativos}+</p>
                    <p className="text-zinc-500 text-[10px] sm:text-xs leading-tight">gestores ativos</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
                    <TrendingUp className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-emerald-400" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-white text-xs sm:text-sm font-bold">{socialProof.emprestimos_gerenciados}+</p>
                    <p className="text-zinc-500 text-[10px] sm:text-xs leading-tight">emprestimos</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
                    <Zap className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-emerald-400" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-white text-xs sm:text-sm font-bold">{socialProof.transacoes_processadas}+</p>
                    <p className="text-zinc-500 text-[10px] sm:text-xs leading-tight">pagamentos</p>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Step indicator */}
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-zinc-500 mb-2">
                {isUpgrade ? 'Upgrade de Plano' : 'Passo unico'}
              </p>
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold tracking-tight text-white">
                {isUpgrade ? 'Confirmar upgrade' : 'Finalize sua assinatura'}
              </h1>
            </div>

            {erro && (
              <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
                className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-xl text-sm flex items-center gap-2" data-testid="checkout-error">
                <X className="w-4 h-4 flex-shrink-0" />
                {erro}
              </motion.div>
            )}

            <form onSubmit={handleSubmit} id="checkout-form" className="space-y-6" data-testid="checkout-form">
              {isUpgrade ? (
                /* Logged-in user card */
                <div className="flex items-center gap-4 p-5 border border-white/10 rounded-xl bg-zinc-900/50" data-testid="upgrade-user-card">
                  <div className="w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                    <User className="w-6 h-6 text-emerald-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-semibold truncate">{user?.nome}</p>
                    <p className="text-zinc-400 text-sm truncate">{user?.email}</p>
                  </div>
                  <span className="flex items-center gap-1 text-emerald-400 text-xs font-medium bg-emerald-500/10 px-3 py-1 rounded-full flex-shrink-0">
                    <CheckCircle className="w-3 h-3" />
                    Verificado
                  </span>
                </div>
              ) : (
                /* Registration fields */
                <div className="space-y-5">
                  <p className="text-xs uppercase tracking-[0.2em] text-zinc-500 font-medium">Dados pessoais</p>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className={labelClass}>Nome completo</label>
                      <input type="text" name="nome" value={formData.nome} onChange={handleChange}
                        className={inputClass} placeholder="Seu nome completo" required autoComplete="name" data-testid="input-nome" />
                    </div>
                    <div>
                      <label className={labelClass}>Email</label>
                      <input type="email" name="email" value={formData.email} onChange={handleChange}
                        className={inputClass} placeholder="voce@email.com" required autoComplete="email" data-testid="input-email" />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className={labelClass}>Senha</label>
                      <input type="password" name="senha" value={formData.senha} onChange={handleChange}
                        className={inputClass} placeholder="Min. 6 caracteres" required minLength={6} autoComplete="new-password" data-testid="input-senha" />
                    </div>
                    <div>
                      <label className={labelClass}>Confirmar senha</label>
                      <input type="password" name="confirmarSenha" value={formData.confirmarSenha} onChange={handleChange}
                        className={inputClass} placeholder="Repita a senha" required autoComplete="new-password" data-testid="input-confirmar-senha" />
                    </div>
                  </div>

                  {(gateway?.id === 'asaas' || gateway?.id === 'syncpay') && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className={labelClass}>CPF/CNPJ</label>
                        <input type="text" name="cpf" value={formData.cpf} onChange={handleChange}
                          className={inputClass} placeholder="000.000.000-00" required data-testid="input-cpf" />
                      </div>
                      <div>
                        <label className={labelClass}>Telefone <span className="text-zinc-600">(opcional)</span></label>
                        <input type="text" name="telefone" value={formData.telefone} onChange={handleChange}
                          className={inputClass} placeholder="(00) 00000-0000" data-testid="input-telefone" />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Payment method */}
              {gateway?.metodos?.length > 0 && (
                <div className="space-y-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-zinc-500 font-medium">Metodo de pagamento</p>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {gateway.metodos.includes('pix') && (
                      <button type="button" onClick={() => setMetodoPagamento('pix')} data-testid="payment-method-pix"
                        className={`${metodoPagamento === 'pix'
                          ? 'border-2 border-emerald-500 bg-emerald-500/5 shadow-[0_0_15px_rgba(16,185,129,0.15)]'
                          : 'border border-white/10 bg-zinc-900/30 hover:bg-zinc-900/80'
                        } relative flex flex-col items-center p-5 rounded-xl cursor-pointer transition-all duration-200`}>
                        <QrCode className={`w-6 h-6 mb-2 ${metodoPagamento === 'pix' ? 'text-emerald-400' : 'text-zinc-400'}`} />
                        <span className="text-sm font-semibold text-white">PIX</span>
                        <span className="text-xs text-zinc-500 mt-0.5">Aprovacao instantanea</span>
                        {metodoPagamento === 'pix' && (
                          <div className="absolute top-2 right-2 w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                            <Check className="w-3 h-3 text-white" />
                          </div>
                        )}
                      </button>
                    )}
                    {gateway.metodos.includes('boleto') && (
                      <button type="button" onClick={() => setMetodoPagamento('boleto')} data-testid="payment-method-boleto"
                        className={`${metodoPagamento === 'boleto'
                          ? 'border-2 border-emerald-500 bg-emerald-500/5 shadow-[0_0_15px_rgba(16,185,129,0.15)]'
                          : 'border border-white/10 bg-zinc-900/30 hover:bg-zinc-900/80'
                        } relative flex flex-col items-center p-5 rounded-xl cursor-pointer transition-all duration-200`}>
                        <Receipt className={`w-6 h-6 mb-2 ${metodoPagamento === 'boleto' ? 'text-emerald-400' : 'text-zinc-400'}`} />
                        <span className="text-sm font-semibold text-white">Boleto</span>
                        <span className="text-xs text-zinc-500 mt-0.5">Alguns dias uteis</span>
                        {metodoPagamento === 'boleto' && (
                          <div className="absolute top-2 right-2 w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                            <Check className="w-3 h-3 text-white" />
                          </div>
                        )}
                      </button>
                    )}
                    {gateway.metodos.includes('cartao') && (
                      <button type="button" onClick={() => setMetodoPagamento('cartao')} data-testid="payment-method-card"
                        className={`${metodoPagamento === 'cartao'
                          ? 'border-2 border-emerald-500 bg-emerald-500/5 shadow-[0_0_15px_rgba(16,185,129,0.15)]'
                          : 'border border-white/10 bg-zinc-900/30 hover:bg-zinc-900/80'
                        } relative flex flex-col items-center p-5 rounded-xl cursor-pointer transition-all duration-200`}>
                        <CreditCard className={`w-6 h-6 mb-2 ${metodoPagamento === 'cartao' ? 'text-emerald-400' : 'text-zinc-400'}`} />
                        <span className="text-sm font-semibold text-white">Cartao</span>
                        <span className="text-xs text-zinc-500 mt-0.5">Credito/Debito</span>
                        {metodoPagamento === 'cartao' && (
                          <div className="absolute top-2 right-2 w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                            <Check className="w-3 h-3 text-white" />
                          </div>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* CTA - visible on mobile only (desktop has it in the sidebar) */}
              <div className="lg:hidden pb-20">
                <button type="submit" disabled={processando} data-testid="checkout-submit-button-mobile"
                  className="w-full h-14 rounded-xl flex items-center justify-between px-6 text-white font-bold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed bg-emerald-600 hover:bg-emerald-500"
                  style={{ boxShadow: '0 4px 14px 0 rgba(10,168,118,0.39)' }}>
                  <span className="flex items-center gap-2 text-base">
                    {processando ? (<><Loader2 className="w-5 h-5 animate-spin" /> Processando...</>) : (<><Lock className="w-4 h-4" /> Confirmar Pagamento</>)}
                  </span>
                  {!processando && plano && <span className="text-base font-black">R$ {valorFinal.toFixed(2).replace('.', ',')}</span>}
                </button>
              </div>
            </form>
          </motion.div>

          {/* RIGHT COLUMN - Order Summary */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.1 }}
            className="col-span-1 lg:col-span-5 lg:sticky lg:top-8">
            <div className="bg-zinc-950/50 backdrop-blur-2xl border border-white/10 rounded-2xl p-6 lg:p-8 shadow-[0_8px_32px_rgba(0,0,0,0.4)]">

              {/* Plan badge */}
              {plano.destaque && (
                <div className="flex items-center gap-1.5 text-emerald-400 text-xs font-semibold bg-emerald-500/10 px-3 py-1.5 rounded-full w-fit mb-4">
                  <Star className="w-3 h-3" />
                  Mais Popular
                </div>
              )}

              <h3 className="text-xl sm:text-2xl font-bold text-white mb-1">Plano {plano.nome}</h3>
              <div className="flex items-baseline gap-1.5 mb-6">
                <span className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tighter text-white">
                  R$ {valorFinal.toFixed(2).replace('.', ',')}
                </span>
                <span className="text-zinc-500 text-sm">/{plano.intervalo}</span>
              </div>

              {/* Features */}
              <div className="space-y-3 mb-6">
                {plano.recursos.map((recurso, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                      <Check className="w-3 h-3 text-emerald-400" />
                    </div>
                    <span className="text-sm text-zinc-300">{recurso}</span>
                  </div>
                ))}
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                    <Check className="w-3 h-3 text-emerald-400" />
                  </div>
                  <span className="text-sm text-zinc-300">
                    {plano.clientes === -1 ? 'Clientes ilimitados' : `Ate ${plano.clientes} clientes`}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                    <Check className="w-3 h-3 text-emerald-400" />
                  </div>
                  <span className="text-sm text-zinc-300">
                    {plano.emprestimos === -1 ? 'Emprestimos ilimitados' : `Ate ${plano.emprestimos} emprestimos`}
                  </span>
                </div>
              </div>

              <div className="border-t border-white/10 my-6" />

              {/* Coupon */}
              <div className="mb-6">
                <p className="text-xs uppercase tracking-[0.2em] text-zinc-500 font-medium mb-3 flex items-center gap-1.5">
                  <Tag className="w-3 h-3" />
                  Cupom de desconto
                </p>
                {!cupomAplicado ? (
                  <div className="flex gap-2">
                    <input type="text" value={codigoCupom} onChange={(e) => setCodigoCupom(e.target.value.toUpperCase())}
                      className="flex-1 bg-zinc-900 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all"
                      placeholder="CODIGO" disabled={validandoCupom} data-testid="coupon-input" />
                    <Button type="button" onClick={handleAplicarCupom} disabled={validandoCupom || !codigoCupom.trim()}
                      className="bg-zinc-800 hover:bg-zinc-700 text-white border border-white/10 text-sm px-4" data-testid="apply-coupon-button">
                      {validandoCupom ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Aplicar'}
                    </Button>
                  </div>
                ) : (
                  <div className="flex items-center justify-between bg-emerald-500/10 border border-emerald-500/20 px-4 py-3 rounded-lg">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-emerald-400" />
                      <span className="text-sm text-emerald-400 font-medium">{cupomAplicado.codigo}</span>
                      <span className="text-xs text-emerald-400/70">-{cupomAplicado.desconto_percentual}%</span>
                    </div>
                    <button type="button" onClick={handleRemoverCupom} className="text-zinc-500 hover:text-zinc-300 transition-colors">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                )}
                {erroCupom && <p className="text-xs text-red-400 mt-2">{erroCupom}</p>}
              </div>

              {/* Price breakdown */}
              {cupomAplicado && (
                <div className="space-y-2 mb-4">
                  <div className="flex justify-between text-sm">
                    <span className="text-zinc-500">Subtotal</span>
                    <span className="text-zinc-400 line-through">R$ {plano.preco.toFixed(2).replace('.', ',')}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-emerald-400">Desconto ({cupomAplicado.codigo})</span>
                    <span className="text-emerald-400">-R$ {cupomAplicado.desconto.toFixed(2).replace('.', ',')}</span>
                  </div>
                  <div className="border-t border-white/10 pt-2 flex justify-between">
                    <span className="text-white font-semibold">Total</span>
                    <span className="text-white font-bold text-lg">R$ {cupomAplicado.valor_final.toFixed(2).replace('.', ',')}</span>
                  </div>
                </div>
              )}

              {/* CTA Button - desktop */}
              <div className="hidden lg:block">
                <button type="submit" form="checkout-form" disabled={processando} data-testid="checkout-submit-button"
                  className="w-full h-16 rounded-xl flex items-center justify-between px-6 text-white font-bold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ background: processando ? 'hsl(160,84%,30%)' : 'hsl(160,84%,39%)', boxShadow: '0 4px 14px 0 rgba(10,168,118,0.39)' }}
                  onMouseEnter={(e) => { if (!processando) e.currentTarget.style.background = 'hsl(160,84%,45%)'; }}
                  onMouseLeave={(e) => { if (!processando) e.currentTarget.style.background = 'hsl(160,84%,39%)'; }}>
                  <span className="flex items-center gap-2 text-lg">
                    {processando ? (<><Loader2 className="w-5 h-5 animate-spin" /> Processando...</>) : (<><Lock className="w-4 h-4" /> Confirmar Pagamento</>)}
                  </span>
                  {!processando && plano && <span className="text-lg font-black">R$ {valorFinal.toFixed(2).replace('.', ',')}</span>}
                </button>
              </div>

              {/* Trust signals */}
              <div className="mt-6 space-y-3">
                <div className="flex items-center gap-2 text-zinc-600 text-xs">
                  <Lock className="w-3.5 h-3.5" />
                  <span>Criptografia de ponta a ponta</span>
                </div>
                <div className="flex items-center gap-2 text-zinc-600 text-xs">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Pagamento 100% seguro via {gateway?.nome || 'Gateway'}</span>
                </div>
              </div>

              {/* Terms */}
              <p className="text-xs text-zinc-600 mt-4">
                Ao continuar, voce concorda com nossos{' '}
                <Link to="/termos" className="text-zinc-400 hover:text-emerald-400 underline underline-offset-2 transition-colors">Termos</Link>{' '}e{' '}
                <Link to="/privacidade" className="text-zinc-400 hover:text-emerald-400 underline underline-offset-2 transition-colors">Privacidade</Link>
              </p>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Floating activity toast */}
      <AnimatePresence mode="wait">
        {socialProof?.atividade_recente?.length > 0 && (
          <motion.div
            key={atividadeIndex}
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -15 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="fixed bottom-4 left-4 right-4 sm:right-auto sm:left-6 sm:bottom-6 z-50 flex items-center gap-3 bg-zinc-900/95 backdrop-blur-xl border border-white/10 rounded-xl px-4 py-3 shadow-2xl sm:max-w-xs"
            data-testid="social-proof-toast"
          >
            <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
              <User className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white text-sm font-medium truncate">
                {socialProof.atividade_recente[atividadeIndex]?.nome}
              </p>
              <p className="text-zinc-500 text-xs truncate">
                Assinou o plano {socialProof.atividade_recente[atividadeIndex]?.plano}
              </p>
            </div>
            <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse flex-shrink-0" />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default CheckoutPublico;
