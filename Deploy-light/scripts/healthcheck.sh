#!/bin/bash
# =============================================================================
# Health Check para t3.small
# =============================================================================

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "=============================================="
echo "SYMYAH - Health Check (t3.small)"
echo "=============================================="
echo ""

# Verificar containers
log_info "Containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""

# Verificar memória
log_info "Uso de memória:"
free -h

echo ""

# Verificar endpoints
log_info "Endpoints:"

if curl -sf --max-time 10 http://localhost:8000/health > /dev/null 2>&1; then
    log_info "API (8000): OK"
else
    log_error "API (8000): FAILED"
fi

if curl -sf --max-time 5 http://localhost:5432 > /dev/null 2>&1; then
    log_info "PostgreSQL (5432): OK"
else
    log_error "PostgreSQL (5432): FAILED"
fi

echo ""
log_info "Health check concluído!"
