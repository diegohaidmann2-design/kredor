import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { CheckCircle, Copy, Download, ArrowLeft, Loader, Check } from 'lucide-react';
import Loading from '../components/Loading';
import { assinaturasAPI } from '../api/api';

const CheckoutAsaasPagamento = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const transacaoId = searchParams.get('transacao');

  const [loading, setLoading] = useState(true);
  const [transacao, setTransacao] = useState(null);
  const [pixData, setPixData] = useState(null);
  const [boletoUrl, setBoletoUrl] = useState(null);
  const [copied, setCopied] = useState(false);
  const [erro, setErro] = useState('');

  useEffect(() => {
    if (!transacaoId) {
      navigate('/');
      return;
    }
    carregarTransacao();
  }, [transacaoId]);

  const carregarTransacao = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('checkout_token');

      const response = await assinaturasAPI.obterTransacao(transacaoId, {
        headers: { Authorization: `Bearer ${token}` }
      });

      setTransacao(response.data);
      
      // Se tem dados PIX
      if (response.data.pix) {
        setPixData(response.data.pix);
      }
      
      // Se tem boleto
      if (response.data.boleto) {
        setBoletoUrl(response.data.boleto.url);
      }

    } catch (err) {
      console.error('Erro ao carregar transação:', err);
      setErro('Não foi possível carregar as informações do pagamento.');
    } finally {
      setLoading(false);
    }
  };

  const copiarCodigoPix = () => {
    if (pixData?.payload) {
      navigator.clipboard.writeText(pixData.payload);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) {
    return <Loading message="Carregando informações do pagamento..." />;
  }

  if (erro) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-xl shadow-lg p-8 text-center">
          <div className="text-red-500 mb-4">❌</div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Erro</h2>
          <p className="text-gray-600 mb-6">{erro}</p>
          <button
            onClick={() => navigate('/')}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Voltar ao Início
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <button
          onClick={() => navigate('/')}
          className="mb-6 flex items-center gap-2 text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="w-4 h-4" />
          Voltar
        </button>

        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          {/* Status Header */}
          <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-8 text-center">
            <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <Loader className="w-8 h-8 animate-spin" />
            </div>
            <h1 className="text-2xl font-bold mb-2">Assinatura Criada!</h1>
            <p className="text-blue-100">Aguardando confirmação do pagamento</p>
          </div>

          <div className="p-8 space-y-6">
            {/* Informações da Assinatura */}
            <div className="bg-gray-50 rounded-xl p-6 space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-600">Plano:</span>
                <span className="font-semibold text-gray-900">{transacao?.plano_nome || 'Plano Selecionado'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Valor:</span>
                <span className="font-semibold text-gray-900">
                  R$ {transacao?.valor?.toFixed(2) || '0,00'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Status:</span>
                <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-medium">
                  Aguardando Pagamento
                </span>
              </div>
            </div>

            {/* QR Code PIX */}
            {pixData && (
              <div className="border-t border-gray-200 pt-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  🔷 Pagar com PIX
                </h3>
                
                <div className="bg-white border-2 border-gray-200 rounded-xl p-6">
                  {pixData.qrcode && (
                    <div className="flex justify-center mb-4">
                      <img 
                        src={`data:image/png;base64,${pixData.qrcode}`} 
                        alt="QR Code PIX"
                        className="w-64 h-64 border-4 border-gray-200 rounded-lg"
                      />
                    </div>
                  )}
                  
                  <p className="text-center text-sm text-gray-600 mb-4">
                    Escaneie o QR Code com o app do seu banco ou copie o código abaixo:
                  </p>
                  
                  <div className="bg-gray-50 rounded-lg p-4 break-all font-mono text-xs text-gray-700 mb-4">
                    {pixData.payload}
                  </div>
                  
                  <button
                    onClick={copiarCodigoPix}
                    className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium flex items-center justify-center gap-2 transition-colors"
                  >
                    {copied ? (
                      <>
                        <Check className="w-5 h-5" />
                        Código Copiado!
                      </>
                    ) : (
                      <>
                        <Copy className="w-5 h-5" />
                        Copiar Código PIX
                      </>
                    )}
                  </button>
                  
                  {pixData.expirationDate && (
                    <p className="text-center text-sm text-gray-500 mt-3">
                      ⏰ Expira em: {new Date(pixData.expirationDate).toLocaleString('pt-BR')}
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Link Boleto */}
            {boletoUrl && (
              <div className="border-t border-gray-200 pt-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  📄 Boleto Bancário
                </h3>
                
                <div className="bg-white border-2 border-gray-200 rounded-xl p-6 text-center">
                  <p className="text-gray-600 mb-4">
                    Seu boleto foi gerado com sucesso!
                  </p>
                  
                  <a
                    href={boletoUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                  >
                    <Download className="w-5 h-5" />
                    Baixar Boleto
                  </a>
                  
                  <p className="text-sm text-gray-500 mt-4">
                    O boleto pode levar alguns dias úteis para ser compensado
                  </p>
                </div>
              </div>
            )}

            {/* Informações Importantes */}
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-6">
              <h4 className="font-semibold text-blue-900 mb-3">ℹ️ Informações Importantes</h4>
              <ul className="space-y-2 text-sm text-blue-800">
                <li>• Após o pagamento ser confirmado, seu plano será ativado automaticamente</li>
                <li>• Você receberá um email de confirmação</li>
                <li>• Já pode fazer login no sistema com suas credenciais</li>
                <li>• O pagamento pode levar alguns minutos para ser processado</li>
              </ul>
            </div>

            {/* Botão Acessar Sistema */}
            <button
              onClick={() => {
                const token = localStorage.getItem('checkout_token');
                if (token) {
                  localStorage.setItem('token', token);
                  localStorage.removeItem('checkout_token');
                }
                navigate('/dashboard');
              }}
              className="w-full py-4 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white rounded-xl font-semibold text-lg flex items-center justify-center gap-2 transition-all shadow-lg hover:shadow-xl"
            >
              <CheckCircle className="w-6 h-6" />
              Acessar o Sistema
            </button>

            <p className="text-center text-sm text-gray-500">
              Seu acesso estará liberado assim que o pagamento for confirmado
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CheckoutAsaasPagamento;
