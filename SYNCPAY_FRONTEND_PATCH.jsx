/* 
 * PATCH FRONTEND - Remover MercadoPago + Adicionar SyncPay
 * Aplicar em /app/frontend/src/pages/Configuracoes.js
 */

// ========== PASSO 1: DELETAR LINHAS 1058-1280 (Seção completa MercadoPago) ==========
// Use editor de texto e remova desde "Configuração Mercado Pago" até antes de "Configuração de Gateway Primário"

// ========== PASSO 2: SUBSTITUIR linha ~818 (opção estratégia MercadoPago) ==========
// TROCAR:
/*
<label className={`... 'mercadopago_only' ? 'border-blue-500 ...`}>
  ...
  <p className="font-medium">Somente Mercado Pago</p>
</label>
*/

// POR:
<label className={`relative flex flex-col p-4 border-2 rounded-lg cursor-pointer transition ${assinaturaGatewayConfig.estrategia === 'syncpay_only' ? 'border-cyan-500 bg-cyan-500/20' : 'border-border hover:border-border'}`}>
  <input
    type="radio"
    name="estrategia"
    value="syncpay_only"
    checked={assinaturaGatewayConfig.estrategia === 'syncpay_only'}
    onChange={handleAssinaturaGatewayChange}
    className="sr-only"
  />
  <div className="flex items-center mb-2">
    <div className="w-10 h-10 bg-cyan-500/30 rounded-full flex items-center justify-center mr-3">
      <span className="text-cyan-400 font-bold">⚡</span>
    </div>
    <p className="font-medium text-foreground">Somente SyncPay</p>
  </div>
  <p className="text-xs text-muted-foreground">Usar apenas SyncPay PIX (instantâneo)</p>
</label>

// ========== PASSO 3: ADICIONAR após linha ~1057 (após seção Asaas) ==========

{/* SyncPay PIX */}
<div className="bg-card rounded-lg shadow-md p-6 border-l-4 border-cyan-500">
  <div className="flex items-center justify-between mb-4">
    <h3 className="text-lg font-bold text-foreground flex items-center">
      <div className="w-8 h-8 bg-cyan-500/30 rounded-full flex items-center justify-center mr-3">
        <span className="text-cyan-400 font-bold">⚡</span>
      </div>
      SyncPay PIX Instantâneo
    </h3>
    <div className="flex items-center gap-4">
      {/* Modo Sandbox Toggle */}
      <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${
        assinaturaGatewayConfig.syncpay_ambiente === 'sandbox' 
          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' 
          : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
      }`}>
        <span className={`w-2 h-2 rounded-full ${
          assinaturaGatewayConfig.syncpay_ambiente === 'sandbox' ? 'bg-amber-400' : 'bg-emerald-400'
        }`}></span>
        {assinaturaGatewayConfig.syncpay_ambiente === 'sandbox' ? 'SANDBOX' : 'PRODUÇÃO'}
      </div>
      <label className="relative inline-flex items-center cursor-pointer">
        <input
          type="checkbox"
          name="syncpay_habilitado"
          checked={assinaturaGatewayConfig.syncpay_habilitado}
          onChange={handleAssinaturaGatewayChange}
          className="sr-only peer"
        />
        <div className="w-11 h-6 bg-muted rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-cyan-500"></div>
      </label>
    </div>
  </div>

  <div className="space-y-4">
    {/* Ambiente */}
    <div>
      <label className="block text-sm font-medium text-foreground mb-2">Ambiente</label>
      <select
        name="syncpay_ambiente"
        value={assinaturaGatewayConfig.syncpay_ambiente}
        onChange={handleAssinaturaGatewayChange}
        className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:ring-2 focus:ring-cyan-500"
      >
        <option value="sandbox">🧪 Sandbox (Testes)</option>
        <option value="producao">🚀 Produção</option>
      </select>
    </div>

    {/* Client ID */}
    <div>
      <label className="block text-sm font-medium text-foreground mb-2">
        Client ID UUID
        <span className="text-destructive ml-1">*</span>
      </label>
      <input
        type="password"
        name="syncpay_client_id"
        placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        value={assinaturaGatewayConfig.syncpay_client_id}
        onChange={handleAssinaturaGatewayChange}
        className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:ring-2 focus:ring-cyan-500"
      />
      <p className="text-xs text-muted-foreground mt-1">
        Obtenha em: <a href="https://app.sistemab2drop.com.br/dashboard" target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:underline">SyncPay Dashboard</a>
      </p>
    </div>

    {/* Client Secret */}
    <div>
      <label className="block text-sm font-medium text-foreground mb-2">
        Client Secret UUID
        <span className="text-destructive ml-1">*</span>
      </label>
      <input
        type="password"
        name="syncpay_client_secret"
        placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        value={assinaturaGatewayConfig.syncpay_client_secret}
        onChange={handleAssinaturaGatewayChange}
        className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:ring-2 focus:ring-cyan-500"
      />
    </div>

    {/* Webhook URL */}
    <div>
      <label className="block text-sm font-medium text-foreground mb-2">Webhook URL</label>
      <div className="bg-muted/50 border border-border rounded-md p-3">
        <code className="text-sm text-foreground break-all">
          {process.env.REACT_APP_BACKEND_URL}/api/assinaturas/webhook-syncpay
        </code>
        <button
          type="button"
          onClick={() => {
            navigator.clipboard.writeText(`${process.env.REACT_APP_BACKEND_URL}/api/assinaturas/webhook-syncpay`);
            alert('URL copiada!');
          }}
          className="mt-2 text-xs text-cyan-400 hover:underline"
        >
          📋 Copiar URL
        </button>
      </div>
      <p className="text-xs text-muted-foreground mt-1">
        Configure esta URL no painel SyncPay para receber notificações de pagamento
      </p>
    </div>

    {/* Webhook Secret */}
    <div>
      <label className="block text-sm font-medium text-foreground mb-2">
        Webhook Secret
        <span className="text-destructive ml-1">*</span>
      </label>
      <input
        type="password"
        name="syncpay_webhook_secret"
        placeholder="Chave secreta para validar webhooks (HMAC SHA256)"
        value={assinaturaGatewayConfig.syncpay_webhook_secret}
        onChange={handleAssinaturaGatewayChange}
        className="w-full px-3 py-2 bg-background border border-border rounded-md text-foreground focus:ring-2 focus:ring-cyan-500"
        required
      />
      <p className="text-xs text-muted-foreground mt-1">
        Use uma chave forte para validar assinatura dos webhooks
      </p>
    </div>

    {/* Informações */}
    <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-md p-4">
      <h4 className="font-medium text-cyan-400 mb-2">ℹ️ Como configurar:</h4>
      <ol className="text-sm text-muted-foreground space-y-1 list-decimal list-inside">
        <li>Acesse o <a href="https://app.sistemab2drop.com.br/dashboard" target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:underline">Dashboard SyncPay</a></li>
        <li>Copie o Client ID e Client Secret</li>
        <li>Gere uma chave secreta forte para webhooks</li>
        <li>Configure a Webhook URL no painel SyncPay</li>
        <li>Salve e teste com um pagamento PIX</li>
      </ol>
    </div>
  </div>
</div>
