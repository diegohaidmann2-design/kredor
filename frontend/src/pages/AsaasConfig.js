import React, { useState, useEffect } from 'react';
import { Shield, CheckCircle, XCircle, AlertCircle, ExternalLink, Copy, Check } from 'lucide-react';
import Layout from '../components/Layout';
import Button from '../components/Button';
import Loading from '../components/Loading';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

const AsaasConfig = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [config, setConfig] = useState({
    habilitado: false,
    api_key: '',
    ambiente: 'sandbox',
    webhook_url: ''
  });
  const [testResult, setTestResult] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    carregarConfig();
  }, []);

  const carregarConfig = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.get(`${BACKEND_URL}/api/asaas/config`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setConfig(response.data);
      
      // Gerar webhook URL automática
      if (!response.data.webhook_url) {
        const webhookUrl = `${BACKEND_URL}/api/assinaturas/webhook-asaas`;
        setConfig(prev => ({ ...prev, webhook_url: webhookUrl }));
      }
    } catch (err) {
      console.error('Erro ao carregar config:', err);
      setError('Erro ao carregar configurações');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError('');
      setSuccess('');
      
      const token = localStorage.getItem('token');
      await axios.put(`${BACKEND_URL}/api/asaas/config`, config, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setSuccess('Configurações salvas com sucesso!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      console.error('Erro ao salvar:', err);
      setError(err.response?.data?.detail || 'Erro ao salvar configurações');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    try {
      setTesting(true);
      setTestResult(null);
      setError('');
      
      const token = localStorage.getItem('token');
      const response = await axios.post(`${BACKEND_URL}/api/asaas/config/testar`, config, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setTestResult(response.data);
    } catch (err) {
      console.error('Erro ao testar:', err);
      setTestResult({
        success: false,
        message: err.response?.data?.detail || 'Erro ao testar conexão'
      });
    } finally {
      setTesting(false);
    }
  };

  const copyWebhookUrl = () => {
    navigator.clipboard.writeText(config.webhook_url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <Layout>
        <Loading />
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-200">
          <div className="flex items-center gap-3 mb-2">
            <Shield className="w-8 h-8 text-blue-600" />
            <h1 className="text-2xl font-bold text-gray-900">Configurações Asaas</h1>
          </div>
          <p className="text-gray-600">
            Configure a integração com o Asaas para processar pagamentos e assinaturas do sistema
          </p>
        </div>

        {/* Alerts */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
            <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-red-900">Erro</p>
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          </div>
        )}

        {success && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-start gap-3">
            <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-green-900">Sucesso</p>
              <p className="text-green-700 text-sm">{success}</p>
            </div>
          </div>
        )}

        {/* Test Result */}
        {testResult && (
          <div className={`${testResult.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'} border rounded-lg p-4 flex items-start gap-3`}>
            {testResult.success ? (
              <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
            ) : (
              <XCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            )}
            <div className="flex-1">
              <p className={`font-medium ${testResult.success ? 'text-green-900' : 'text-red-900'}`}>
                {testResult.success ? 'Teste bem-sucedido!' : 'Teste falhou'}
              </p>
              <p className={`text-sm ${testResult.success ? 'text-green-700' : 'text-red-700'}`}>
                {testResult.message}
              </p>
              {testResult.success && testResult.conta && (
                <div className="mt-2 text-sm text-green-700">
                  <p><strong>Conta:</strong> {testResult.conta}</p>
                  {testResult.email && <p><strong>Email:</strong> {testResult.email}</p>}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Info Box */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-900 space-y-2">
              <p className="font-medium">ℹ️ Como configurar o Asaas:</p>
              <ol className="list-decimal list-inside space-y-1 ml-2">
                <li>Acesse <a href="https://www.asaas.com" target="_blank" rel="noopener noreferrer" className="underline font-medium">www.asaas.com</a> e faça login</li>
                <li>Vá em: <strong>Configurações → Integrações → Chave de API</strong></li>
                <li>Copie a chave (começa com <code className="bg-blue-100 px-1 rounded">$aact_...</code>)</li>
                <li>Cole abaixo e teste a conexão</li>
                <li>Configure o webhook no painel do Asaas (URL abaixo)</li>
              </ol>
            </div>
          </div>
        </div>

        {/* Configurações */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="p-6 space-y-6">
            <h2 className="text-lg font-semibold text-gray-900">Configuração da API</h2>

            {/* Toggle Habilitado */}
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div>
                <label className="font-medium text-gray-900">Habilitar Asaas</label>
                <p className="text-sm text-gray-600">Ative para processar pagamentos pelo Asaas</p>
              </div>
              <button
                onClick={() => setConfig(prev => ({ ...prev, habilitado: !prev.habilitado }))}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  config.habilitado ? 'bg-blue-600' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    config.habilitado ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* Ambiente */}
            <div>
              <label className="block font-medium text-gray-900 mb-2">
                Ambiente
              </label>
              <select
                value={config.ambiente}
                onChange={(e) => setConfig(prev => ({ ...prev, ambiente: e.target.value }))}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="sandbox">🧪 Sandbox (Testes)</option>
                <option value="producao">🚀 Produção</option>
              </select>
              <p className="text-sm text-gray-500 mt-1">
                {config.ambiente === 'sandbox' 
                  ? '⚠️ Modo de teste - use chave de sandbox' 
                  : '✅ Modo de produção - processará pagamentos reais'}
              </p>
            </div>

            {/* API Key */}
            <div>
              <label className="block font-medium text-gray-900 mb-2">
                API Key do Asaas *
              </label>
              <div className="relative">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={config.api_key}
                  onChange={(e) => setConfig(prev => ({ ...prev, api_key: e.target.value }))}
                  placeholder="$aact_YzU5YTE0M2M2N2I4MTliNzk0YTI5N2U5MzdjNWZmNDQ6OjAwMDAwMDAwMDAwMDAwNDcwNTk6OiRhYWNoXzk4ZmQzMDFmLTY4NjUtNDRjYy1hMGYxLWVmMzg1YmFlYWRiMA=="
                  className="w-full px-4 py-2 pr-20 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                />
                <button
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 text-xs font-medium px-2 py-1"
                >
                  {showKey ? '🙈 Ocultar' : '👁️ Mostrar'}
                </button>
              </div>
              <p className="text-sm text-gray-500 mt-1">
                Chave de API encontrada em: Asaas → Configurações → Integrações
              </p>
            </div>

            {/* Webhook URL */}
            <div>
              <label className="block font-medium text-gray-900 mb-2">
                Webhook URL
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={config.webhook_url}
                  readOnly
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 font-mono text-sm"
                />
                <button
                  onClick={copyWebhookUrl}
                  className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors flex items-center gap-2"
                >
                  {copied ? (
                    <>
                      <Check className="w-4 h-4 text-green-600" />
                      <span className="text-sm text-green-600">Copiado!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4" />
                      <span className="text-sm">Copiar</span>
                    </>
                  )}
                </button>
              </div>
              <p className="text-sm text-gray-500 mt-1">
                Configure esta URL no painel do Asaas: <strong>Configurações → Webhooks</strong>
              </p>
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-4 border-t">
              <Button
                onClick={handleTest}
                variant="outline"
                disabled={!config.api_key || testing}
                className="flex items-center gap-2"
              >
                {testing ? (
                  <>
                    <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                    Testando...
                  </>
                ) : (
                  <>
                    <Shield className="w-4 h-4" />
                    Testar Conexão
                  </>
                )}
              </Button>

              <Button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2"
              >
                {saving ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Salvando...
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4" />
                    Salvar Configurações
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>

        {/* Documentação */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="p-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">📚 Documentação</h2>
            
            <div className="space-y-3">
              <div>
                <h3 className="font-medium text-gray-900 mb-1">🔑 Obtendo sua API Key</h3>
                <ol className="text-sm text-gray-600 space-y-1 list-decimal list-inside ml-4">
                  <li>Acesse o painel do Asaas</li>
                  <li>Vá em <strong>Configurações → Integrações</strong></li>
                  <li>Clique em <strong>Chave de API</strong></li>
                  <li>Copie a chave (sandbox ou produção)</li>
                  <li>Cole no campo acima</li>
                </ol>
              </div>

              <div className="pt-3 border-t">
                <h3 className="font-medium text-gray-900 mb-1">🔔 Configurando Webhooks</h3>
                <ol className="text-sm text-gray-600 space-y-1 list-decimal list-inside ml-4">
                  <li>No painel do Asaas, vá em <strong>Configurações → Webhooks</strong></li>
                  <li>Clique em <strong>+ Novo Webhook</strong></li>
                  <li>Cole a URL do webhook (copiada acima)</li>
                  <li>Selecione os eventos:
                    <ul className="ml-6 mt-1 space-y-0.5">
                      <li>✓ PAYMENT_RECEIVED (Pagamento recebido)</li>
                      <li>✓ PAYMENT_CONFIRMED (Pagamento confirmado)</li>
                      <li>✓ PAYMENT_OVERDUE (Pagamento vencido)</li>
                      <li>✓ PAYMENT_DELETED (Pagamento cancelado)</li>
                    </ul>
                  </li>
                  <li>Salve e ative o webhook</li>
                </ol>
              </div>

              <div className="pt-3 border-t">
                <h3 className="font-medium text-gray-900 mb-1">💳 Métodos de Pagamento</h3>
                <p className="text-sm text-gray-600">
                  O Asaas suporta os seguintes métodos de pagamento:
                </p>
                <ul className="text-sm text-gray-600 space-y-1 mt-2 ml-4">
                  <li>🔷 <strong>PIX</strong> - Pagamento instantâneo</li>
                  <li>📄 <strong>Boleto Bancário</strong> - Até 3 dias úteis</li>
                  <li>💳 <strong>Cartão de Crédito</strong> - Aprovação imediata</li>
                </ul>
              </div>

              <div className="pt-3 border-t">
                <h3 className="font-medium text-gray-900 mb-1">🔗 Links Úteis</h3>
                <div className="space-y-2">
                  <a 
                    href="https://www.asaas.com" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700"
                  >
                    <ExternalLink className="w-4 h-4" />
                    Painel do Asaas
                  </a>
                  <a 
                    href="https://docs.asaas.com" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700"
                  >
                    <ExternalLink className="w-4 h-4" />
                    Documentação da API
                  </a>
                  <a 
                    href="https://sandbox.asaas.com" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-700"
                  >
                    <ExternalLink className="w-4 h-4" />
                    Ambiente Sandbox (Testes)
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Diferenças Sandbox vs Produção */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">🆚 Sandbox vs Produção</h2>
            
            <div className="grid md:grid-cols-2 gap-4">
              {/* Sandbox */}
              <div className="border border-yellow-200 rounded-lg p-4 bg-yellow-50">
                <h3 className="font-medium text-yellow-900 mb-2">🧪 Sandbox (Testes)</h3>
                <ul className="text-sm text-yellow-800 space-y-1">
                  <li>✓ Não processa pagamentos reais</li>
                  <li>✓ Use para desenvolvimento</li>
                  <li>✓ API Key começa com <code className="bg-yellow-100 px-1 rounded">$aact_test_...</code></li>
                  <li>✓ Simula aprovações/rejeições</li>
                </ul>
              </div>

              {/* Produção */}
              <div className="border border-green-200 rounded-lg p-4 bg-green-50">
                <h3 className="font-medium text-green-900 mb-2">🚀 Produção</h3>
                <ul className="text-sm text-green-800 space-y-1">
                  <li>✓ Processa pagamentos reais</li>
                  <li>✓ Use após testes completos</li>
                  <li>✓ API Key começa com <code className="bg-green-100 px-1 rounded">$aact_...</code></li>
                  <li>⚠️ Cobranças são efetivas</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default AsaasConfig;
