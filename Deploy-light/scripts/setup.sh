#!/bin/bash
# =============================================================================
# Script de Setup para t3.small (2GB RAM)
# =============================================================================
# Configura swap e otimizações de memória
# =============================================================================

set -e

echo "=============================================="
echo "SYMYAH - Setup para t3.small (2GB RAM)"
echo "=============================================="

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [ "$EUID" -ne 0 ]; then 
    log_error "Execute como root ou use sudo"
    exit 1
fi

# =============================================================================
# Atualizar sistema
# =============================================================================
log_info "Atualizando sistema..."
yum update -y 2>/dev/null || apt-get update && apt-get upgrade -y

# =============================================================================
# Configurar SWAP (CRÍTICO para t3.small)
# =============================================================================
log_info "Configurando SWAP de 4GB..."

# Verificar se já existe swap
if [ -f /swapfile ]; then
    log_warn "Swap já existe, pulando..."
else
    # Criar swap de 4GB
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    
    # Tornar permanente
    echo '/swapfile none swap sw 0 0' | tee -a /etc/fstab
    
    # Configurar swappiness (usar swap mais cedo)
    sysctl vm.swappiness=60
    echo 'vm.swappiness=60' | tee -a /etc/sysctl.conf
    
    log_info "Swap de 4GB configurada com sucesso!"
fi

# =============================================================================
# Instalar Docker
# =============================================================================
log_info "Verificando Docker..."
if ! command -v docker &> /dev/null; then
    log_info "Instalando Docker..."
    yum install -y docker 2>/dev/null || apt-get install -y docker.io
    systemctl start docker
    systemctl enable docker
else
    log_info "Docker já instalado"
fi

# =============================================================================
# Instalar Docker Compose
# =============================================================================
log_info "Verificando Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    log_info "Instalando Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
else
    log_info "Docker Compose já instalado"
fi

# =============================================================================
# Configurar permissões
# =============================================================================
log_info "Configurando permissões do Docker..."
usermod -aG docker ec2-user 2>/dev/null || usermod -aG docker ubuntu 2>/dev/null || true

# =============================================================================
# Otimizações de memória
# =============================================================================
log_info "Aplicando otimizações de memória..."

# Reduzir uso de memória do sysctl
sysctl vm.dirty_ratio=20 2>/dev/null || true
sysctl vm.dirty_background_ratio=10 2>/dev/null || true
echo 'vm.dirty_ratio=20' | tee -a /etc/sysctl.conf 2>/dev/null || true
echo 'vm.dirty_background_ratio=10' | tee -a /etc/sysctl.conf 2>/dev/null || true

# =============================================================================
# Criar diretório
# =============================================================================
APP_DIR="/opt/symyah"
log_info "Criando diretório $APP_DIR..."
mkdir -p $APP_DIR

# =============================================================================
# Configurar systemd
# =============================================================================
log_info "Configurando serviço systemd..."
cat > /etc/systemd/system/symyah.service << 'EOF'
[Unit]
Description=SYMYAH - Sistema de IA (t3.small)
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
# Mensagens finais
# =============================================================================
echo ""
echo "=============================================="
log_info "Setup concluído!"
echo "=============================================="
echo ""
echo "⚠️  IMPORTANTE: Esta versão é otimizada para t3.small (2GB RAM)"
echo ""
echo "Próximos passos:"
echo "1. Copie os arquivos para: $APP_DIR"
echo "2. Edite o arquivo .env com suas configurações"
echo "3. Execute: sudo systemctl enable symyah"
echo "4. Execute: sudo systemctl start symyah"
echo ""
echo "Para verificar: sudo systemctl status symyah"
echo "Para logs: docker-compose logs -f"
echo ""
echo "⚠️  DICA: Monitore o uso de memória com 'free -h' e 'docker stats'"
echo ""
