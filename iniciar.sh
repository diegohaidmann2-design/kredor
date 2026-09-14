#!/usr/bin/env bash
###############################################################################
# iniciar.sh - Sobe a aplicação GestorCred com todos os serviços
#   - MongoDB, Backend (FastAPI) e Frontend (React) via supervisor
#   - Verifica dependências, arquivos .env e faz health-check
#
# Uso:
#   ./iniciar.sh            # sobe tudo
#   ./iniciar.sh restart    # reinicia tudo
#   ./iniciar.sh status     # mostra status dos serviços
#   ./iniciar.sh logs       # mostra os últimos logs do backend/frontend
###############################################################################

set -euo pipefail

# ----- Cores -----
G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; B='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "${G}✔${NC} $*"; }
warn() { echo -e "${Y}⚠${NC} $*"; }
err()  { echo -e "${R}x${NC} $*"; }
info() { echo -e "${B}➜${NC} $*"; }

APP_DIR="/app"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
SERVICES="mongodb backend frontend"

cd "$APP_DIR"

# ----- Ação opcional -----
ACTION="${1:-start}"

show_status() {
  echo ""
  info "Status dos serviços:"
  sudo supervisorctl status $SERVICES || true
}

show_logs() {
  echo ""
  info "Últimas linhas do backend:"
  tail -n 40 /var/log/supervisor/backend.err.log 2>/dev/null || true
  echo ""
  info "Últimas linhas do frontend:"
  tail -n 40 /var/log/supervisor/frontend.err.log 2>/dev/null || true
}

if [ "$ACTION" = "status" ]; then show_status; exit 0; fi
if [ "$ACTION" = "logs" ]; then show_logs; exit 0; fi

echo ""
echo "==============================================="
echo "   GestorCred — inicialização de serviços"
echo "==============================================="

# ----- 1. Verificar arquivos .env -----
info "Verificando arquivos de ambiente..."
if [ ! -f "$BACKEND_DIR/.env" ]; then
  err "Arquivo $BACKEND_DIR/.env não encontrado. Crie-o antes de iniciar."
  exit 1
fi
ok "backend/.env encontrado"

if [ ! -f "$FRONTEND_DIR/.env" ]; then
  err "Arquivo $FRONTEND_DIR/.env não encontrado. Crie-o antes de iniciar."
  exit 1
fi
ok "frontend/.env encontrado"

# ----- 2. Instalar dependências (se necessário) -----
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  warn "node_modules ausente. Instalando dependências do frontend (yarn)..."
  ( cd "$FRONTEND_DIR" && yarn install )
  ok "Dependências do frontend instaladas"
fi

# ----- 3. Subir / reiniciar serviços via supervisor -----
if [ "$ACTION" = "restart" ]; then
  info "Reiniciando serviços: $SERVICES"
  sudo supervisorctl restart $SERVICES
else
  info "Iniciando serviços: $SERVICES"
  sudo supervisorctl start $SERVICES 2>/dev/null || sudo supervisorctl restart $SERVICES
fi

# ----- 4. Aguardar e verificar saúde -----
info "Aguardando serviços subirem..."
sleep 8

show_status

# Backend health-check
BACKEND_URL="http://localhost:8001/api/"
info "Health-check do backend em $BACKEND_URL"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL" || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
  ok "Backend respondendo (HTTP 200)"
else
  err "Backend não respondeu (HTTP $HTTP_CODE). Veja os logs:"
  tail -n 30 /var/log/supervisor/backend.err.log 2>/dev/null || true
fi

# Frontend check
info "Verificando frontend (porta 3000)..."
FE_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:3000" || echo "000")
if [ "$FE_CODE" = "200" ] || [ "$FE_CODE" = "304" ]; then
  ok "Frontend respondendo (HTTP $FE_CODE)"
else
  warn "Frontend retornou HTTP $FE_CODE (pode ainda estar compilando)."
fi

# ----- 5. Mostrar URL pública -----
PUBLIC_URL=$(grep -E '^REACT_APP_BACKEND_URL=' "$FRONTEND_DIR/.env" | cut -d '=' -f2- || true)
echo ""
echo "==============================================="
ok "GestorCred iniciado."
[ -n "$PUBLIC_URL" ] && echo -e "   URL da aplicação: ${G}${PUBLIC_URL}${NC}"
echo -e "   Backend (local):  http://localhost:8001/api/"
echo -e "   Frontend (local): http://localhost:3000"
echo "==============================================="
echo ""
echo "Dicas:"
echo "  ./iniciar.sh status   -> ver status dos serviços"
echo "  ./iniciar.sh restart  -> reiniciar tudo"
echo "  ./iniciar.sh logs     -> ver logs de backend/frontend"
