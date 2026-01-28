#!/bin/bash
# Script de Deploy Automatizado para Gestor Cred
# Uso: ./scripts/deploy.sh [prod|dev]

set -e

ENVIRONMENT=${1:-prod}
COMPOSE_FILE="docker-compose.${ENVIRONMENT}.yml"

echo "🚀 Iniciando deploy do Gestor Cred - Ambiente: $ENVIRONMENT"
echo "=================================================="

# Verificar se docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não encontrado. Instale o Docker primeiro."
    exit 1
fi

# Verificar se docker compose está instalado
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose não encontrado. Instale o Docker Compose primeiro."
    exit 1
fi

# Verificar se arquivo compose existe
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ Arquivo $COMPOSE_FILE não encontrado."
    exit 1
fi

# Verificar arquivo .env para produção
if [ "$ENVIRONMENT" == "prod" ] && [ ! -f "backend/.env.prod" ]; then
    echo "❌ Arquivo backend/.env.prod não encontrado."
    echo "📝 Copie backend/.env.example para backend/.env.prod e configure."
    exit 1
fi

# Fazer backup antes do deploy (apenas produção)
if [ "$ENVIRONMENT" == "prod" ]; then
    echo "📦 Criando backup do banco de dados..."
    ./scripts/backup.sh || echo "⚠️  Backup falhou, mas continuando..."
fi

# Build das imagens
echo "🔨 Construindo imagens Docker..."
docker compose -f "$COMPOSE_FILE" build --no-cache

# Parar containers antigos
echo "🛑 Parando containers antigos..."
docker compose -f "$COMPOSE_FILE" down

# Iniciar novos containers
echo "🚀 Iniciando containers..."
docker compose -f "$COMPOSE_FILE" up -d

# Aguardar containers ficarem healthy
echo "⏳ Aguardando containers ficarem saudáveis..."
sleep 10

# Verificar status
echo "🔍 Verificando status dos containers..."
docker compose -f "$COMPOSE_FILE" ps

# Executar seeder (apenas primeira vez)
read -p "❓ Executar seeder (dados iniciais)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📊 Executando seeder..."
    docker exec jurofacil_backend python -m seeds.seeder
fi

echo ""
echo "✅ Deploy concluído com sucesso!"
echo ""
echo "📋 Próximos passos:"
if [ "$ENVIRONMENT" == "dev" ]; then
    echo "   Frontend: http://localhost:3000"
    echo "   Backend:  http://localhost:8001"
    echo "   MongoDB:  localhost:27017"
else
    echo "   Frontend: https://jurofacil.com"
    echo "   Backend:  https://api.jurofacil.com"
fi
echo ""
echo "📊 Visualizar logs:"
echo "   docker compose -f $COMPOSE_FILE logs -f"
echo ""
