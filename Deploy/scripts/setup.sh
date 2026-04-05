#!/bin/bash
# =============================================================================
# Script de Inicialização do SYMYAH em EC2
# =============================================================================
# Este script prepara o ambiente EC2 para execução do SYMYAH
# =============================================================================

set -e

echo "=============================================="
echo "SYMYAH - Script de Setup para EC2"
echo "=============================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para log
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# Verificar se está rodando como root
# =============================================================================
if [ "$EUID" -ne 0 ]; then 
    log_error "Por favor execute como root ou use sudo"
    exit 1
fi

# =============================================================================
# Atualizar sistema
# =============================================================================
log_info "Atualizando pacotes do sistema..."
yum update -y || apt-get update && apt-get upgrade -y

# =============================================================================
# Instalar Docker
# =============================================================================
log_info "Verificando instalação do Docker..."
if ! command -v docker &> /dev/null; then
    log_info "Instalando Docker..."
    yum install -y docker || apt-get install -y docker.io
    systemctl start docker
    systemctl enable docker
else
    log_info "Docker já está instalado"
fi

# =============================================================================
# Instalar Docker Compose
# =============================================================================
log_info "Verificando instalação do Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    log_info "Instalando Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
else
    log_info "Docker Compose já está instalado"
fi

# =============================================================================
# Adicionar usuário ao grupo docker
# =============================================================================
log_info "Configurando permissões do Docker..."
usermod -aG docker ec2-user 2>/dev/null || usermod -aG docker ubuntu 2>/dev/null || true

# =============================================================================
# Criar diretório de aplicação
# =============================================================================
APP_DIR="/opt/symyah"
log_info "Criando diretório da aplicação em $APP_DIR..."
mkdir -p $APP_DIR

# =============================================================================
# Configurar arquivo .env
# =============================================================================
if [ ! -f "$APP_DIR/.env" ]; then
    log_info "Criando arquivo .env a partir do exemplo..."
    cp .env.example $APP_DIR/.env
    log_warn "IMPORTANTE: Edite o arquivo $APP_DIR/.env com suas configurações!"
else
    log_info "Arquivo .env já existe"
fi

# =============================================================================
# Configurar script de backup
# =============================================================================
log_info "Configurando script de backup..."
BACKUP_SCRIPT="/opt/symyah/scripts/backup.sh"
mkdir -p /opt/symyah/scripts

# =============================================================================
# Configurar systemd service
# =============================================================================
log_info "Configurando serviço systemd..."
cat > /etc/systemd/system/symyah.service << 'EOF'
[Unit]
Description=SYMYAH - Sistema de IA para Psicologia Clínica
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/symyah
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

# =============================================================================
# Configurar logrotate
# =============================================================================
log_info "Configurando logrotate..."
cat > /etc/logrotate.d/symyah << 'EOF'
/opt/symyah/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        /usr/bin/docker kill -s HUP symyah-nginx 2>/dev/null || true
    endscript
}
EOF

# =============================================================================
# Mensagens finais
# =============================================================================
echo ""
echo "=============================================="
log_info "Setup concluído com sucesso!"
echo "=============================================="
echo ""
echo "Próximos passos:"
echo "1. Copie seus arquivos para: $APP_DIR"
echo "2. Edite o arquivo .env com suas configurações"
echo "3. Execute: sudo systemctl enable symyah"
echo "4. Execute: sudo systemctl start symyah"
echo ""
echo "Para verificar o status: sudo systemctl status symyah"
echo "Para ver os logs: docker-compose logs -f"
echo ""
