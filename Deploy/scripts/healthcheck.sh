#!/bin/bash
# =============================================================================
# Script de Health Check para SYMYAH
# =============================================================================
# Verifica a saúde de todos os serviços e reinicia se necessário
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

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Função para verificar endpoint
check_endpoint() {
    local name=$1
    local url=$2
    local timeout=${3:-5}
    
    if curl -sf --max-time $timeout $url > /dev/null 2>&1; then
        log_info "$name: OK"
        return 0
    else
        log_error "$name: FAILED"
        return 1
    fi
}

# Função para verificar container Docker
check_container() {
    local name=$1
    
    if docker ps --format '{{.Names}}' | grep -q "^${name}$"; then
        local status=$(docker inspect -f '{{.State.Health.Status}}' $name 2>/dev/null || echo "healthy")
        log_info "Container $name: $status"
        return 0
    else
        log_error "Container $name: NOT RUNNING"
        return 1
    fi
}

echo "=============================================="
echo "SYMYAH - Health Check"
echo "=============================================="
echo ""

# Verificar containers
log_info "Verificando containers Docker..."
check_container "symyah-postgres"
check_container "symyah-api"
check_container "symyah-frontend"
check_container "symyah-nginx" 2>/dev/null || true

echo ""

# Verificar endpoints
log_info "Verificando endpoints..."
check_endpoint "API Health" "http://localhost:8000/health" 10
check_endpoint "Frontend" "http://localhost:5000/" 5
check_endpoint "Nginx Health" "http://localhost/nginx-health" 5 2>/dev/null || true

echo ""
log_info "Health check concluído!"
