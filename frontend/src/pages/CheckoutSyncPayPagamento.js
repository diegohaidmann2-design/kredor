import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { ArrowLeft, CheckCircle, Clock, Copy, ShieldCheck, QrCode } from 'lucide-react';
import { assinaturasAPI } from '../api/api';
import { QRCodeSVG } from 'qrcode.react';
import Loading from '../components/Loading';

const CheckoutSyncPayPagamento = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const transacaoId = searchParams.get('transacao');
  const transactionId = searchParams.get('transaction_id');

  const [status, setStatus] = useState('pending');
  const [pixCode, setPixCode] = useState('');
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState('');
  const [copiado, setCopiado] = useState(false);

  useEffect(() => {
    const storedPixCode = sessionStorage.getItem('syncpay_pix_code');
    if (storedPixCode) {
      setPixCode(storedPixCode);
      sessionStorage.removeItem('syncpay_pix_code');
    }

    const fetchTransacao = async () => {
      if (!transactionId) { setErro('Transacao nao encontrada'); setLoading(false); return; }
      try {
        const res = await assinaturasAPI.verificarStatusSyncPay(transactionId);
        if (res.data.data?.pix_code && !storedPixCode) setPixCode(res.data.data.pix_code);
        if (res.data.approved) setStatus('approved');
      } catch { /* silent */ }
      finally { setLoading(false); }
    };
    fetchTransacao();
  }, [transactionId]);

  const checkStatus = useCallback(async () => {
    if (!transactionId || status === 'approved') return;
    try {
      const res = await assinaturasAPI.verificarStatusSyncPay(transactionId);
      if (res.data.approved) setStatus('approved');
    } catch { /* silent */ }
  }, [transactionId, status]);

  useEffect(() => {
    if (status === 'approved') return;
    const interval = setInterval(checkStatus, 5000);
    return () => clearInterval(interval);
  }, [checkStatus, status]);

  useEffect(() => {
    if (status !== 'approved') return;
    const token = localStorage.getItem('checkout_token');
    if (token) { localStorage.setItem('token', token); localStorage.removeItem('checkout_token'); }
    const timer = setTimeout(() => navigate('/dashboard'), 3000);
    return () => clearTimeout(timer);
  }, [status, navigate]);

  const handleCopiar = () => {
    if (!pixCode) return;
    navigator.clipboard.writeText(pixCode).catch(() => {});
    setCopiado(true);
    setTimeout(() => setCopiado(false), 2500);
  };

  if (loading) return <Loading message="Carregando pagamento..." />;

  // Approved state
  if (status === 'approved') {
    return (
      <div className="min-h-screen flex items-center justify-center px-4" style={{ background: 'hsl(240,10%,4%)' }}>
        <div className="max-w-sm w-full text-center space-y-6" data-testid="syncpay-approved">
          <div className="w-20 h-20 mx-auto bg-emerald-500/20 rounded-full flex items-center justify-center">
            <CheckCircle className="w-10 h-10 text-emerald-400" />
          </div>
          <h2 className="text-2xl font-bold text-white">Pagamento Confirmado!</h2>
          <p className="text-zinc-400">Seu plano foi ativado. Redirecionando...</p>
          <div className="w-8 h-8 mx-auto border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: 'hsl(240,10%,4%)' }}>
      {/* Top bar */}
      <div className="border-b border-white/5">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-500 flex items-center justify-center">
              <span className="text-sm font-black text-white">K</span>
            </div>
            <span className="text-lg font-bold text-white">
              <span className="text-emerald-400">Kredor</span>
            </span>
          </div>
          <div className="flex items-center gap-2 text-zinc-500 text-xs">
            <ShieldCheck className="w-4 h-4" />
            <span className="hidden sm:inline">Pagamento Seguro</span>
          </div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        <Link to="/" className="inline-flex items-center gap-2 text-zinc-500 hover:text-zinc-300 text-sm mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Voltar
        </Link>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
          {/* Left - QR Code */}
          <div className="bg-zinc-950/50 backdrop-blur-2xl border border-white/10 rounded-2xl p-6 sm:p-8 text-center" data-testid="syncpay-pagamento-card">
            <div className="w-10 h-10 mx-auto bg-emerald-500/10 rounded-full flex items-center justify-center mb-4">
              <QrCode className="w-5 h-5 text-emerald-400" />
            </div>
            <h1 className="text-xl sm:text-2xl font-bold text-white mb-1">Pagamento PIX</h1>
            <p className="text-zinc-500 text-sm mb-6">Escaneie o QR Code com o app do seu banco</p>

            {pixCode ? (
              <div className="space-y-6">
                {/* QR Code gerado a partir do pix_code */}
                <div className="bg-white rounded-2xl p-4 sm:p-6 inline-block mx-auto" data-testid="syncpay-qr-image">
                  <QRCodeSVG
                    value={pixCode}
                    size={220}
                    level="M"
                    includeMargin={false}
                    bgColor="#ffffff"
                    fgColor="#000000"
                  />
                </div>

                {/* Status pulse */}
                <div className="flex items-center justify-center gap-2">
                  <div className="w-2 h-2 bg-amber-500 rounded-full animate-pulse" />
                  <p className="text-amber-400 text-sm font-medium">Aguardando pagamento...</p>
                </div>
              </div>
            ) : (
              <div className="py-12">
                <div className="w-10 h-10 mx-auto border-2 border-zinc-700 border-t-emerald-500 rounded-full animate-spin mb-4" />
                <p className="text-zinc-500 text-sm">Gerando QR Code...</p>
              </div>
            )}
          </div>

          {/* Right - PIX copia e cola + info */}
          <div className="space-y-6">
            {/* Timer / info */}
            <div className="bg-zinc-950/50 backdrop-blur-2xl border border-white/10 rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-9 h-9 rounded-full bg-amber-500/10 flex items-center justify-center flex-shrink-0">
                  <Clock className="w-4 h-4 text-amber-400" />
                </div>
                <div>
                  <p className="text-white text-sm font-semibold">Aguardando confirmacao</p>
                  <p className="text-zinc-500 text-xs">A pagina atualiza automaticamente</p>
                </div>
              </div>

              <div className="space-y-3 text-sm">
                <div className="flex items-start gap-2 text-zinc-400">
                  <span className="text-emerald-400 mt-0.5">1.</span>
                  <span>Abra o app do seu banco</span>
                </div>
                <div className="flex items-start gap-2 text-zinc-400">
                  <span className="text-emerald-400 mt-0.5">2.</span>
                  <span>Escaneie o QR Code ou copie o codigo PIX abaixo</span>
                </div>
                <div className="flex items-start gap-2 text-zinc-400">
                  <span className="text-emerald-400 mt-0.5">3.</span>
                  <span>Confirme o pagamento no app</span>
                </div>
              </div>
            </div>

            {/* PIX copia e cola */}
            {pixCode && (
              <div className="bg-zinc-950/50 backdrop-blur-2xl border border-white/10 rounded-2xl p-6">
                <p className="text-xs uppercase tracking-[0.2em] text-zinc-500 font-medium mb-3">PIX Copia e Cola</p>
                <div className="bg-zinc-900 border border-white/5 rounded-xl p-3 mb-4">
                  <p className="text-[11px] break-all font-mono text-zinc-400 leading-relaxed line-clamp-3" data-testid="syncpay-pix-code">
                    {pixCode}
                  </p>
                </div>
                <button onClick={handleCopiar} data-testid="syncpay-copy-btn"
                  className="w-full h-12 rounded-xl flex items-center justify-center gap-2 font-semibold text-sm transition-all duration-200"
                  style={{
                    background: copiado ? 'hsl(160,84%,39%)' : 'transparent',
                    color: copiado ? 'white' : 'hsl(160,84%,55%)',
                    border: copiado ? 'none' : '1.5px solid hsl(160,84%,39%)',
                  }}>
                  {copiado ? (
                    <><CheckCircle className="w-4 h-4" /> Codigo copiado!</>
                  ) : (
                    <><Copy className="w-4 h-4" /> Copiar codigo PIX</>
                  )}
                </button>
              </div>
            )}

            {/* Trust */}
            <div className="flex items-center gap-2 text-zinc-600 text-xs justify-center">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Pagamento seguro via SyncPay</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CheckoutSyncPayPagamento;
