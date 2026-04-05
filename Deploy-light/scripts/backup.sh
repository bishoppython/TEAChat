#!/bin/bash
# =============================================================================
# Backup para t3.small
# =============================================================================

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

BACKUP_DIR="/opt/symyah/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/symyah_backup_$DATE.sql.gz"

mkdir -p $BACKUP_DIR

# Carregar .env
if [ -f "/opt/symyah/.env" ]; then
    export $(grep -v '^#' /opt/symyah/.env | xargs)
fi

DB_NAME=${POSTGRES_DB:-symyah_db}
DB_USER=${POSTGRES_USER:-symyah_user}
DB_PASSWORD=${POSTGRES_PASSWORD}

log_info "Backup do banco: $DB_NAME"

PGPASSWORD=$DB_PASSWORD pg_dump -h localhost -U $DB_USER -d $DB_NAME | gzip > $BACKUP_FILE

if [ $? -eq 0 ]; then
    log_info "Backup criado: $BACKUP_FILE"
    # Manter apenas 7 backups (economia de disco)
    find $BACKUP_DIR -name "symyah_backup_*.sql.gz" -mtime +7 -delete
else
    log_error "Falha no backup"
    exit 1
fi

log_info "Backup concluído!"
