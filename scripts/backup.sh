#!/bin/bash
# Script de Backup Automatizado para MongoDB
# Uso: ./scripts/backup.sh

set -e

BACKUP_DIR="./backups/mongodb"
DATE=$(date +%Y%m%d-%H%M%S)
CONTAINER_NAME="jurofacil_mongodb"

echo "📦 Iniciando backup do MongoDB..."
echo "=================================================="

# Criar diretório de backups
mkdir -p "$BACKUP_DIR"

# Verificar se container está rodando
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "❌ Container $CONTAINER_NAME não está rodando."
    exit 1
fi

# Executar backup
echo "🔄 Criando dump do banco de dados..."
docker exec "$CONTAINER_NAME" mongodump \
    --db=jurofacil \
    --out=/tmp/backup \
    --quiet

# Copiar backup para host
echo "📋 Copiando backup para host..."
docker cp "$CONTAINER_NAME:/tmp/backup" "$BACKUP_DIR/backup-$DATE"

# Limpar backup temporário no container
docker exec "$CONTAINER_NAME" rm -rf /tmp/backup

# Compactar backup
echo "🗜️  Compactando backup..."
tar -czf "$BACKUP_DIR/backup-$DATE.tar.gz" -C "$BACKUP_DIR" "backup-$DATE"
rm -rf "$BACKUP_DIR/backup-$DATE"

# Calcular tamanho
SIZE=$(du -h "$BACKUP_DIR/backup-$DATE.tar.gz" | cut -f1)

echo ""
echo "✅ Backup concluído com sucesso!"
echo "📁 Arquivo: $BACKUP_DIR/backup-$DATE.tar.gz"
echo "📊 Tamanho: $SIZE"
echo ""

# Limpar backups antigos (manter últimos 7 dias)
echo "🧹 Limpando backups antigos (>7 dias)..."
find "$BACKUP_DIR" -name "backup-*.tar.gz" -mtime +7 -delete
echo "✅ Limpeza concluída!"
