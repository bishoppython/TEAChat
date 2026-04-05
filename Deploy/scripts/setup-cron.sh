#!/bin/bash
# =============================================================================
# Script de Instalação do Cron Job de Backup
# =============================================================================
# Configura backup automático diário do banco de dados
# =============================================================================

set -e

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

echo "=============================================="
echo "SYMYAH - Configurar Backup Automático"
echo "=============================================="
echo ""

# Diretório do script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="$SCRIPT_DIR/backup.sh"

# Verificar se script de backup existe
if [ ! -f "$BACKUP_SCRIPT" ]; then
    log_error "Script de backup não encontrado em $BACKUP_SCRIPT"
    exit 1
fi

# Tornar executável
chmod +x "$BACKUP_SCRIPT"

# Criar diretório de backups
BACKUP_DIR="/opt/symyah/backups"
log_info "Criando diretório de backups: $BACKUP_DIR"
mkdir -p $BACKUP_DIR

# Configurar cron job
log_info "Configurando cron job para backup diário às 03:00..."

# Cron job: backup diário às 3 da manhã
CRON_JOB="0 3 * * * cd /opt/symyah/Deploy && /opt/symyah/Deploy/scripts/backup.sh >> /var/log/symyah_backup.log 2>&1"

# Adicionar ao crontab do root
(crontab -l 2>/dev/null | grep -v "backup.sh"; echo "$CRON_JOB") | crontab -

log_info "Cron job configurado com sucesso!"

# Verificar cron jobs existentes
echo ""
log_info "Cron jobs atuais:"
crontab -l

echo ""
echo "=============================================="
log_info "Backup automático configurado!"
echo "=============================================="
echo ""
echo "O backup será executado diariamente às 03:00"
echo "Os backups serão salvos em: $BACKUP_DIR"
echo ""
echo "Para verificar o log de backups:"
echo "  tail -f /var/log/symyah_backup.log"
echo ""
echo "Para executar backup manual:"
echo "  sudo $BACKUP_SCRIPT"
echo ""
