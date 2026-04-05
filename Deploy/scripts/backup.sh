#!/bin/bash
# =============================================================================
# Script de Backup do Banco de Dados SYMYAH
# =============================================================================
# Realiza backup do PostgreSQL e armazena em local seguro
# =============================================================================

set -e

# Configurações
BACKUP_DIR="/opt/symyah/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/symyah_backup_$DATE.sql.gz"
RETENTION_DAYS=30

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Criar diretório de backup
mkdir -p $BACKUP_DIR

# Carregar variáveis de ambiente do .env
if [ -f "/opt/symyah/.env" ]; then
    export $(grep -v '^#' /opt/symyah/.env | xargs)
fi

# Valores padrão
DB_NAME=${POSTGRES_DB:-symyah_db}
DB_USER=${POSTGRES_USER:-symyah_user}
DB_PASSWORD=${POSTGRES_PASSWORD}

log_info "Iniciando backup do banco de dados: $DB_NAME"

# Realizar backup
PGPASSWORD=$DB_PASSWORD pg_dump -h localhost -U $DB_USER -d $DB_NAME | gzip > $BACKUP_FILE

if [ $? -eq 0 ]; then
    log_info "Backup criado com sucesso: $BACKUP_FILE"
    
    # Remover backups antigos
    log_info "Removendo backups com mais de $RETENTION_DAYS dias..."
    find $BACKUP_DIR -name "symyah_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
    
    # Listar backups existentes
    log_info "Backups existentes:"
    ls -lh $BACKUP_DIR/*.sql.gz 2>/dev/null || echo "Nenhum backup encontrado"
else
    log_error "Falha ao criar backup"
    exit 1
fi

echo ""
log_info "Backup concluído!"
