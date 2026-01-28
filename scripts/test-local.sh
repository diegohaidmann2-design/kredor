#!/bin/bash
# Script de Teste Local - Validar setup Docker antes do deploy
# Uso: ./scripts/test-local.sh

set -e

echo "🧪 Iniciando testes locais do Docker setup..."
echo "=================================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Verificar se arquivos Docker existem
echo ""
echo "📋 Verificando arquivos Docker..."
if [ -f "backend/Dockerfile" ]; then
    success "backend/Dockerfile encontrado"
else
    error "backend/Dockerfile não encontrado"
    exit 1
fi

if [ -f "frontend/Dockerfile" ]; then
    success "frontend/Dockerfile encontrado"
else
    error "frontend/Dockerfile não encontrado"
    exit 1
fi

if [ -f "docker-compose.dev.yml" ]; then
    success "docker-compose.dev.yml encontrado"
else
    error "docker-compose.dev.yml não encontrado"
    exit 1
fi

# Validar sintaxe do docker-compose
echo ""
echo "🔍 Validando sintaxe do docker-compose..."
if docker compose -f docker-compose.dev.yml config > /dev/null 2>&1; then
    success "docker-compose.dev.yml válido"
else
    error "docker-compose.dev.yml inválido"
    exit 1
fi

# Build das imagens (dev)
echo ""
echo "🔨 Construindo imagens Docker (pode demorar alguns minutos)..."
if docker compose -f docker-compose.dev.yml build 2>&1 | tee /tmp/docker-build.log; then
    success "Build concluído com sucesso"
else
    error "Falha no build das imagens"
    echo "Verifique o log em /tmp/docker-build.log"
    exit 1
fi

# Iniciar containers em modo dev
echo ""
echo "🚀 Iniciando containers em modo desenvolvimento..."
docker compose -f docker-compose.dev.yml up -d

# Aguardar containers iniciarem
echo ""
echo "⏳ Aguardando containers iniciarem (30 segundos)..."
sleep 30

# Verificar status dos containers
echo ""
echo "📊 Status dos containers:"
docker compose -f docker-compose.dev.yml ps

# Verificar se todos estão rodando
RUNNING=$(docker compose -f docker-compose.dev.yml ps | grep -c "Up" || true)
if [ "$RUNNING" -ge 3 ]; then
    success "Todos os containers estão rodando"
else
    warning "Alguns containers podem não estar rodando corretamente"
fi

# Teste de healthcheck do backend
echo ""
echo "🏥 Testando healthcheck do backend..."
sleep 10  # Aguardar backend inicializar completamente
if curl -f http://localhost:8001/health > /dev/null 2>&1; then
    success "Backend respondendo corretamente"
    curl -s http://localhost:8001/health | python3 -m json.tool || echo "{}"
else
    error "Backend não está respondendo"
    echo "Logs do backend:"
    docker logs jurofacil_backend_dev --tail=50
fi

# Teste do frontend
echo ""
echo "🎨 Testando frontend..."
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    success "Frontend respondendo corretamente"
else
    error "Frontend não está respondendo"
    echo "Logs do frontend:"
    docker logs jurofacil_frontend_dev --tail=50
fi

# Teste de conexão MongoDB
echo ""
echo "🗄️  Testando conexão com MongoDB..."
if docker exec jurofacil_mongodb_dev mongosh --eval "db.runCommand('ping')" > /dev/null 2>&1; then
    success "MongoDB funcionando corretamente"
else
    error "MongoDB não está respondendo"
fi

# Teste de conexão backend -> MongoDB
echo ""
echo "🔗 Testando conexão Backend → MongoDB..."
if docker exec jurofacil_backend_dev python -c "from config import client; print(client.server_info())" > /dev/null 2>&1; then
    success "Backend consegue conectar ao MongoDB"
else
    error "Backend não consegue conectar ao MongoDB"
fi

# Executar seeder
echo ""
read -p "❓ Deseja executar o seeder (criar dados iniciais)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📊 Executando seeder..."
    docker exec jurofacil_backend_dev python -m seeds.seeder
fi

# Resumo final
echo ""
echo "=================================================="
echo "🎉 Testes locais concluídos!"
echo ""
echo "📋 Acessos (Desenvolvimento):"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8001"
echo "   Docs API:  http://localhost:8001/docs"
echo "   MongoDB:   localhost:27017"
echo ""
echo "👤 Credenciais:"
echo "   Admin:     admin@sgej.com / admin123"
echo "   Usuário:   usuario@teste.com / senha123"
echo ""
echo "📊 Comandos úteis:"
echo "   Logs:      docker compose -f docker-compose.dev.yml logs -f"
echo "   Parar:     docker compose -f docker-compose.dev.yml down"
echo "   Restart:   docker compose -f docker-compose.dev.yml restart"
echo ""
success "Setup Docker validado e funcionando!"
echo ""
