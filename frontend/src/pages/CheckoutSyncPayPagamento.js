import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { ArrowLeft, CheckCircle, Clock, Copy, AlertTriangle } from 'lucide-react';
import { assinaturasAPI } from '../api/api';
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
  const [tentativas, setTentativas] = useState(0);

  // Buscar dados iniciais da transação
  useEffect(() => {
    const fetchTransacao = async () => {
      if (!transactionId) {
        setErro('Transação não encontrada');
        setLoading(false);
        return;
      }

      try {
        const res = await assinaturasAPI.verificarStatusSyncPay(transactionId);
        const data = res.data;

        if (data.data?.pix_code) setPixCode(data.data.pix_code);
        setStatus(data.approved ? 'approved' : 'pending');
      } catch {
        // A transação pode ainda não estar disponível para consulta, apenas continuar polling
      } finally {
        setLoading(false);
      }
    };

    // Buscar pix_code passado via sessionStorage (do checkout)
    const storedPixCode = sessionStorage.getItem('syncpay_pix_code');
    if (storedPixCode) {
      setPixCode(storedPixCode);
      sessionStorage.removeItem('syncpay_pix_code');
    }

    fetchTransacao();
  }, [transactionId]);

  // Polling para verificar status
  const checkStatus = useCallback(async () => {
    if (!transactionId || status === 'approved') return;

    try {
      const res = await assinaturasAPI.verificarStatusSyncPay(transactionId);
      if (res.data.approved) {
        setStatus('approved');
      }
      setTentativas(prev => prev + 1);
    } catch {
      // Silencioso - continuar tentando
    }
  }, [transactionId, status]);

  useEffect(() => {
    if (status === 'approved') return;

    const interval = setInterval(checkStatus, 5000); // a cada 5s
    return () => clearInterval(interval);
  }, [checkStatus, status]);

  // Quando aprovado, redirecionar após 3s
  useEffect(() => {
    if (status !== 'approved') return;

    const token = localStorage.getItem('checkout_token');
    if (token) {
      localStorage.setItem('token', token);
      localStorage.removeItem('checkout_token');
    }

    const timer = setTimeout(() => {
      navigate('/dashboard');
    }, 3000);
    return () => clearTimeout(timer);
  }, [status, navigate]);

  const handleCopiar = () => {
    if (pixCode) {
      navigator.clipboard.writeText(pixCode);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    }
  };

  if (loading) return <Loading message="Carregando dados do pagamento..." />;

  if (status === 'approved') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900 flex items-center justify-center px-4">
        <Card className="max-w-md w-full text-center" data-testid="syncpay-approved">
          <CardContent className="py-12 space-y-4">
            <div className="w-20 h-20 mx-auto bg-emerald-100 dark:bg-emerald-900/30 rounded-full flex items-center justify-center">
              <CheckCircle className="w-10 h-10 text-emerald-600" />
            </div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Pagamento Confirmado!</h2>
            <p className="text-slate-600 dark:text-slate-400">
              Seu plano foi ativado com sucesso. Redirecionando para o painel...
            </p>
            <div className="w-8 h-8 mx-auto border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900 py-12 px-4">
      <div className="container mx-auto max-w-lg">
        <div className="mb-6">
          <Link to="/" className="inline-flex items-center text-sm text-slate-600 dark:text-slate-400 hover:text-primary">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Voltar
          </Link>
        </div>

        <Card data-testid="syncpay-pagamento-card">
          <CardHeader className="text-center">
            <div className="w-12 h-12 mx-auto bg-cyan-100 dark:bg-cyan-900/30 rounded-full flex items-center justify-center mb-2">
              <Clock className="w-6 h-6 text-cyan-600" />
            </div>
            <CardTitle>Pagamento PIX via SyncPay</CardTitle>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Escaneie o QR Code ou copie o codigo para pagar
            </p>
          </CardHeader>
          <CardContent className="space-y-6">
            {erro && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3 rounded-lg flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-600" />
                <p className="text-sm text-red-800 dark:text-red-200">{erro}</p>
              </div>
            )}

            {/* PIX Copia e Cola */}
            {pixCode && (
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  PIX Copia e Cola
                </label>
                <div className="bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-3">
                  <p className="text-xs break-all font-mono text-slate-700 dark:text-slate-300 mb-3" data-testid="syncpay-pix-code">
                    {pixCode}
                  </p>
                  <Button
                    className="w-full"
                    variant="outline"
                    onClick={handleCopiar}
                    data-testid="syncpay-copy-btn"
                  >
                    <Copy className="w-4 h-4 mr-2" />
                    {copiado ? 'Copiado!' : 'Copiar codigo PIX'}
                  </Button>
                </div>
              </div>
            )}

            {!pixCode && !erro && (
              <div className="text-center py-6">
                <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">
                  Aguardando dados do QR Code...
                </p>
                <p className="text-xs text-slate-500">
                  O pagamento PIX foi criado. Use o app do seu banco para verificar cobranças pendentes.
                </p>
              </div>
            )}

            {/* Status info */}
            <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 p-3 rounded-lg">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-amber-500 rounded-full animate-pulse" />
                <p className="text-sm text-amber-800 dark:text-amber-200">
                  Aguardando confirmacao do pagamento...
                </p>
              </div>
              <p className="text-xs text-amber-600 dark:text-amber-300 mt-1">
                A pagina sera atualizada automaticamente apos o pagamento.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default CheckoutSyncPayPagamento;
