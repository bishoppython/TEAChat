#!/bin/bash
# =============================================================================
# Script de Deploy para t3.small
# =============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "=============================================="
echo "SYMYAH - Deploy (t3.small)"
echo "=============================================="
echo ""

# Verificar memória disponível
MEM_AVAILABLE=$(free -m | awk '/^Mem:/{print $7}')
log_info "Memória disponível: ${MEM_AVAILABLE}MB"

if [ "$MEM_AVAILABLE" -lt 800 ]; then
    log_warn "Memória baixa (${MEM_AVAILABLE}MB). Considere parar outros processos."
fi

# Verificar .env
if [ ! -f ".env" ]; then
    log_error ".env não encontrado!"
    log_info "Copie .env.example para .env e configure"
    exit 1
fi

# Parar serviços
log_info "Parando serviços existentes..."
docker-compose down 2>/dev/null || true

# Limpar containers
log_info "Limpando containers..."
docker container prune -f

# Build
log_info "Construindo imagem (isso pode demorar)..."
docker-compose build

# Iniciar
log_info "Iniciando serviços..."
docker-compose up -d

# Aguardar
log_info "Aguardando inicialização (60s)..."
sleep 60

# Status
log_info "Status dos serviços:"
docker-compose ps

echo ""
log_info "Deploy concluído!"
echo ""
echo "API: http://localhost:8000"
echo "Logs: docker-compose logs -f"
echo ""
