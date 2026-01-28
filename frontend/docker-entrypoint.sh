#!/bin/sh
# Script para injetar variáveis de ambiente no build do React

set -e

# Arquivo JavaScript que será gerado com as variáveis de ambiente
ENV_JS_FILE="/usr/share/nginx/html/env-config.js"

echo "🔧 Gerando configuração de ambiente..."

# Criar arquivo com variáveis de ambiente
cat <<EOF > "$ENV_JS_FILE"
window._env_ = {
  REACT_APP_BACKEND_URL: "${REACT_APP_BACKEND_URL:-http://localhost:8001}"
};
EOF

echo "✅ Configuração de ambiente criada:"
cat "$ENV_JS_FILE"

# Executar comando padrão do nginx
exec "$@"
