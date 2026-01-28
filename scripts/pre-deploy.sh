#!/bin/bash
# Script de pré-deploy - Validações antes do deploy
# Uso: ./scripts/pre-deploy.sh [prod|dev]

set -e

ENVIRONMENT=${1:-prod}
ERRORS=0

echo "🔍 Verificando pré-requisitos para deploy..."
echo "=================================================="

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não instalado"
    ERRORS=$((ERRORS+1))
else
    echo "✅ Docker instalado: $(docker --version)"
fi

# Verificar Docker Compose
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose não instalado"
    ERRORS=$((ERRORS+1))
else
    echo "✅ Docker Compose instalado: $(docker compose version)"
fi

# Verificar arquivo compose
COMPOSE_FILE="docker-compose.${ENVIRONMENT}.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ Arquivo $COMPOSE_FILE não encontrado"
    ERRORS=$((ERRORS+1))
else
    echo "✅ Arquivo $COMPOSE_FILE encontrado"
fi

# Verificar .env para produção
if [ "$ENVIRONMENT" == "prod" ]; then
    if [ ! -f "backend/.env.prod" ]; then
        echo "❌ Arquivo backend/.env.prod não encontrado"
        echo "   Copie backend/.env.example para backend/.env.prod"
        ERRORS=$((ERRORS+1))
    else
        echo "✅ Arquivo backend/.env.prod encontrado"
        
        # Verificar se variáveis críticas estão configuradas
        if grep -q "GERAR_CHAVE" backend/.env.prod; then
            echo "⚠️  Variáveis de ambiente contêm valores de exemplo!"
            echo "   Configure JWT_SECRET_KEY e FIELD_ENCRYPTION_KEY"
            ERRORS=$((ERRORS+1))
        fi
    fi
    
    # Verificar SSL certificates
    if [ ! -f "nginx/ssl/fullchain.pem" ] || [ ! -f "nginx/ssl/privkey.pem" ]; then
        echo "⚠️  Certificados SSL não encontrados em nginx/ssl/"
        echo "   Configure SSL antes do deploy em produção"
        ERRORS=$((ERRORS+1))
    else
        echo "✅ Certificados SSL encontrados"
    fi
fi

# Verificar Dockerfiles
if [ ! -f "backend/Dockerfile" ]; then
    echo "❌ backend/Dockerfile não encontrado"
    ERRORS=$((ERRORS+1))
else
    echo "✅ backend/Dockerfile encontrado"
fi

if [ ! -f "frontend/Dockerfile" ]; then
    echo "❌ frontend/Dockerfile não encontrado"
    ERRORS=$((ERRORS+1))
else
    echo "✅ frontend/Dockerfile encontrado"
fi

# Verificar portas disponíveis (apenas produção)
if [ "$ENVIRONMENT" == "prod" ]; then
    if lsof -Pi :80 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Porta 80 já está em uso"
        ERRORS=$((ERRORS+1))
    else
        echo "✅ Porta 80 disponível"
    fi
    
    if lsof -Pi :443 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "⚠️  Porta 443 já está em uso"
        ERRORS=$((ERRORS+1))
    else
        echo "✅ Porta 443 disponível"
    fi
fi

# Verificar espaço em disco
AVAILABLE_SPACE=$(df -h . | awk 'NR==2 {print $4}')
echo "✅ Espaço disponível: $AVAILABLE_SPACE"

echo ""
echo "=================================================="
if [ $ERRORS -eq 0 ]; then
    echo "✅ Todas as verificações passaram!"
    echo "   Você pode prosseguir com o deploy."
    exit 0
else
    echo "❌ $ERRORS erro(s) encontrado(s)!"
    echo "   Corrija os problemas antes de fazer deploy."
    exit 1
fi
