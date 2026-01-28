#!/bin/bash
# Script de Restore do MongoDB
# Uso: ./scripts/restore.sh <arquivo-backup.tar.gz>

set -e

BACKUP_FILE="$1"
CONTAINER_NAME="jurofacil_mongodb"

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ Uso: ./scripts/restore.sh <arquivo-backup.tar.gz>"
    echo ""
    echo "Backups disponíveis:"
    ls -lh ./backups/mongodb/*.tar.gz 2>/dev/null || echo "  Nenhum backup encontrado"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Arquivo não encontrado: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  ATENÇÃO: Este processo irá SUBSTITUIR os dados atuais!"
read -p "❓ Deseja continuar? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Operação cancelada."
    exit 0
fi

echo "🔄 Iniciando restore do MongoDB..."
echo "=================================================="

# Descompactar backup
echo "📦 Descompactando backup..."
TEMP_DIR=$(mktemp -d)
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

# Encontrar diretório do backup
BACKUP_DIR=$(find "$TEMP_DIR" -type d -name "jurofacil" | head -n 1)

if [ -z "$BACKUP_DIR" ]; then
    echo "❌ Diretório de backup não encontrado no arquivo."
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Copiar para container
echo "📋 Copiando backup para container..."
docker cp "$BACKUP_DIR" "$CONTAINER_NAME:/tmp/restore"

# Executar restore
echo "🔄 Restaurando banco de dados..."
docker exec "$CONTAINER_NAME" mongorestore \
    --db=jurofacil \
    --drop \
    /tmp/restore \
    --quiet

# Limpar
docker exec "$CONTAINER_NAME" rm -rf /tmp/restore
rm -rf "$TEMP_DIR"

echo ""
echo "✅ Restore concluído com sucesso!"
echo ""
