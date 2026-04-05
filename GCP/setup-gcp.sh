#!/bin/bash
# =============================================================================
# setup-gcp.sh — Script de setup inicial para GCP
# TEAChat / SYMYAH — Sistema de IA para Psicologia Clínica
#
# COMO USAR:
#   1. Edite as variáveis na seção "CONFIGURAÇÃO" abaixo
#   2. Execute: chmod +x GCP/setup-gcp.sh && bash GCP/setup-gcp.sh
#
# O script irá:
#   - Autenticar no GCP
#   - Habilitar as APIs necessárias
#   - Criar o repositório no Artifact Registry
#   - Criar os secrets no Secret Manager
#   - Fazer o primeiro build e deploy
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURAÇÃO — Edite estas variáveis antes de executar
# =============================================================================
GCP_PROJECT_ID="SEU_PROJECT_ID_AQUI"       # Ex: meu-projeto-123456
GCP_REGION="us-central1"                    # Região (us-central1 tem melhor free tier)
SERVICE_NAME="teachat-api"
REPO_NAME="teachat"
IMAGE_NAME="api"

# Valores dos Secrets — preencha com seus valores reais
OPENAI_API_KEY_VALUE=""
GOOGLE_API_KEY_VALUE=""
DATABASE_URL_VALUE=""                       # Cole a URL do Neon.tech aqui
SECRET_KEY_VALUE="$(openssl rand -hex 32)"  # Gera uma chave aleatória automaticamente
# =============================================================================

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[AVISO]${NC} $1"; }
log_error()   { echo -e "${RED}[ERRO]${NC} $1"; exit 1; }

# Verificar dependências
check_deps() {
    log_info "Verificando dependências..."
    command -v gcloud >/dev/null 2>&1 || log_error "gcloud CLI não encontrado. Instale em: https://cloud.google.com/sdk/docs/install"
    command -v docker >/dev/null 2>&1 || log_error "Docker não encontrado."
    log_success "Dependências verificadas."
}

# Validar configuração
validate_config() {
    log_info "Validando configuração..."
    [[ "$GCP_PROJECT_ID" == "SEU_PROJECT_ID_AQUI" ]] && log_error "Configure a variável GCP_PROJECT_ID antes de executar!"
    [[ -z "$DATABASE_URL_VALUE" ]] && log_error "Configure a variável DATABASE_URL_VALUE (URL do Neon.tech)!"
    log_success "Configuração válida."
}

# Autenticação e configuração do projeto
setup_project() {
    log_info "Configurando projeto GCP: $GCP_PROJECT_ID"
    gcloud config set project "$GCP_PROJECT_ID"
    gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev" --quiet
    log_success "Projeto configurado."
}

# Habilitar APIs necessárias
enable_apis() {
    log_info "Habilitando APIs necessárias..."
    gcloud services enable \
        run.googleapis.com \
        artifactregistry.googleapis.com \
        cloudbuild.googleapis.com \
        secretmanager.googleapis.com \
        --project="$GCP_PROJECT_ID"
    log_success "APIs habilitadas."
}

# Criar repositório no Artifact Registry
create_registry() {
    log_info "Criando repositório no Artifact Registry..."
    if gcloud artifacts repositories describe "$REPO_NAME" \
        --location="$GCP_REGION" \
        --project="$GCP_PROJECT_ID" >/dev/null 2>&1; then
        log_warn "Repositório '$REPO_NAME' já existe. Pulando criação."
    else
        gcloud artifacts repositories create "$REPO_NAME" \
            --repository-format=docker \
            --location="$GCP_REGION" \
            --description="Repositório de imagens Docker do TEAChat/SYMYAH" \
            --project="$GCP_PROJECT_ID"
        log_success "Repositório criado: $REPO_NAME"
    fi
}

# Criar secrets no Secret Manager
create_secrets() {
    log_info "Criando secrets no Secret Manager..."

    create_or_update_secret "OPENAI_API_KEY"  "$OPENAI_API_KEY_VALUE"
    create_or_update_secret "GOOGLE_API_KEY"  "$GOOGLE_API_KEY_VALUE"
    create_or_update_secret "DATABASE_URL"     "$DATABASE_URL_VALUE"
    create_or_update_secret "SECRET_KEY"       "$SECRET_KEY_VALUE"

    log_success "Secrets configurados no Secret Manager."
    log_warn "Anote a SECRET_KEY gerada automaticamente: $SECRET_KEY_VALUE"
}

create_or_update_secret() {
    local SECRET_NAME="$1"
    local SECRET_VALUE="$2"

    if [[ -z "$SECRET_VALUE" ]]; then
        log_warn "Valor vazio para '$SECRET_NAME'. Secret não será criado."
        return
    fi

    if gcloud secrets describe "$SECRET_NAME" --project="$GCP_PROJECT_ID" >/dev/null 2>&1; then
        log_warn "Secret '$SECRET_NAME' já existe. Adicionando nova versão..."
        echo -n "$SECRET_VALUE" | gcloud secrets versions add "$SECRET_NAME" \
            --data-file=- \
            --project="$GCP_PROJECT_ID"
    else
        echo -n "$SECRET_VALUE" | gcloud secrets create "$SECRET_NAME" \
            --data-file=- \
            --project="$GCP_PROJECT_ID"
        log_success "Secret '$SECRET_NAME' criado."
    fi
}

# Conceder permissão ao Cloud Run para ler os secrets
grant_secret_permissions() {
    log_info "Configurando permissões do Secret Manager para Cloud Run..."
    PROJECT_NUMBER=$(gcloud projects describe "$GCP_PROJECT_ID" --format="value(projectNumber)")
    CLOUD_RUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

    gcloud projects add-iam-policy-binding "$GCP_PROJECT_ID" \
        --member="serviceAccount:${CLOUD_RUN_SA}" \
        --role="roles/secretmanager.secretAccessor" \
        --condition=None \
        --quiet
    log_success "Permissões de secrets configuradas."
}

# Build e deploy via Cloud Build
build_and_deploy() {
    log_info "Iniciando build e deploy via Cloud Build..."
    # Voltar para raiz do projeto para o build
    cd "$(dirname "$0")/.."

    gcloud builds submit \
        --config="GCP/cloudbuild.yaml" \
        --project="$GCP_PROJECT_ID" \
        --substitutions="_REGION=${GCP_REGION},_SERVICE_NAME=${SERVICE_NAME},_REPO_NAME=${REPO_NAME},_IMAGE_NAME=${IMAGE_NAME}" \
        .

    log_success "Build e deploy concluídos!"
}

# Exibir URL do serviço
show_service_url() {
    log_info "Obtendo URL do serviço..."
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$GCP_REGION" \
        --project="$GCP_PROJECT_ID" \
        --format="value(status.url)" 2>/dev/null || echo "")

    if [[ -n "$SERVICE_URL" ]]; then
        log_success "=========================================="
        log_success "Deploy concluído com sucesso!"
        log_success "URL da API: ${SERVICE_URL}"
        log_success "Health Check: ${SERVICE_URL}/health"
        log_success "Documentação: ${SERVICE_URL}/docs"
        log_success "=========================================="
    fi
}

# --- Execução principal ---
main() {
    echo ""
    echo "=============================================="
    echo "  TEAChat/SYMYAH — Setup GCP Free Tier"
    echo "=============================================="
    echo ""

    check_deps
    validate_config
    setup_project
    enable_apis
    create_registry
    create_secrets
    grant_secret_permissions
    build_and_deploy
    show_service_url
}

main "$@"
