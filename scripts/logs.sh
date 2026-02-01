#!/bin/bash
# Script para visualizar logs dos containers
# Uso: ./scripts/logs.sh [backend|frontend|mongodb|nginx|all]

SERVICE=${1:-all}
COMPOSE_FILE="docker-compose.prod.yml"

echo "📊 Visualizando logs do Gestor Cred - Serviço: $SERVICE"
echo "=================================================="

case "$SERVICE" in
    backend)
        docker compose -f "$COMPOSE_FILE" logs -f backend
        ;;
    frontend)
        docker compose -f "$COMPOSE_FILE" logs -f frontend
        ;;
    mongodb)
        docker compose -f "$COMPOSE_FILE" logs -f mongodb
        ;;
    nginx)
        docker compose -f "$COMPOSE_FILE" logs -f nginx
        ;;
    all)
        docker compose -f "$COMPOSE_FILE" logs -f
        ;;
    *)
        echo "❌ Serviço inválido: $SERVICE"
        echo "Opções: backend, frontend, mongodb, nginx, all"
        exit 1
        ;;
esac
