#!/bin/bash
# =============================================================================
# Script de Deploy para SYMYAH
# =============================================================================
# Realiza o deploy da aplicação em produção
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

echo "=============================================="
echo "SYMYAH - Script de Deploy"
echo "=============================================="
echo ""

# Verificar se .env existe
if [ ! -f ".env" ]; then
    log_error "Arquivo .env não encontrado!"
    log_info "Copie .env.example para .env e configure:"
    echo "  cp .env.example .env"
    exit 1
fi

# Parar serviços existentes
log_info "Parando serviços existentes..."
docker-compose down 2>/dev/null || true

# Remover containers parados
log_info "Limpando containers parados..."
docker container prune -f

# Build das imagens
log_info "Construindo imagens Docker..."
docker-compose build --no-cache

# Iniciar serviços
log_info "Iniciando serviços..."
docker-compose up -d

# Aguardar inicialização
log_info "Aguardando inicialização dos serviços..."
sleep 30

# Verificar saúde dos serviços
log_info "Verificando saúde dos serviços..."
docker-compose ps

echo ""
log_info "Deploy concluído com sucesso!"
echo ""
echo "Para verificar os logs: docker-compose logs -f"
echo "Para acessar a API: http://localhost:8000"
echo "Para acessar o frontend: http://localhost:5000"
