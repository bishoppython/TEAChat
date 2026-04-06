#!/bin/bash
# =============================================================================
# sync-secrets.sh — Lê o arquivo .env e envia todos os secrets para o GCP
#                   Secret Manager de uma só vez.
#
# USO:
#   bash GCP/sync-secrets.sh
#
# PRÉ-REQUISITOS:
#   - gcloud CLI autenticado (gcloud auth login)
#   - Arquivo .env preenchido na raiz do projeto
#   - GCP_PROJECT_ID configurado abaixo
# =============================================================================

set -euo pipefail

# ⚙️  Configure seu Project ID aqui
PROJECT_ID="${GCP_PROJECT_ID:-}"

# Secrets que serão enviados ao GCP Secret Manager
# (nomes devem bater exatamente com o que o cloudbuild.yaml espera)
SECRETS_TO_SYNC=(
  "OPENAI_API_KEY"
  "GOOGLE_API_KEY"
  "DATABASE_URL"
  "SECRET_KEY"
)

# Cores
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

log_ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[AVISO]${NC} $1"; }
log_err()  { echo -e "${RED}[ERRO]${NC} $1"; exit 1; }

# -----------------------------------------------------------------------
# Validações
# -----------------------------------------------------------------------
[[ -z "$PROJECT_ID" ]] && log_err "Configure GCP_PROJECT_ID no script ou exporte a variável."
[[ ! -f ".env" ]]      && log_err "Arquivo .env não encontrado. Execute na raiz do projeto."

command -v gcloud >/dev/null 2>&1 || log_err "gcloud CLI não encontrado."

echo ""
echo "========================================="
echo "  Sincronizando secrets → GCP Secret Manager"
echo "  Projeto: $PROJECT_ID"
echo "========================================="
echo ""

# -----------------------------------------------------------------------
# Habilitar Secret Manager (caso ainda não esteja)
# -----------------------------------------------------------------------
gcloud services enable secretmanager.googleapis.com --project="$PROJECT_ID" --quiet

# -----------------------------------------------------------------------
# Ler .env e criar/atualizar cada secret
# -----------------------------------------------------------------------
for SECRET_NAME in "${SECRETS_TO_SYNC[@]}"; do
  # Extrair o valor do .env (ignora linhas comentadas)
  SECRET_VALUE=$(grep -E "^${SECRET_NAME}=" .env | cut -d'=' -f2- | tr -d '\r')

  if [[ -z "$SECRET_VALUE" ]]; then
    log_warn "Valor vazio para '$SECRET_NAME' no .env — pulando."
    continue
  fi

  # Criar ou atualizar o secret
  if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo -n "$SECRET_VALUE" | gcloud secrets versions add "$SECRET_NAME" \
      --data-file=- --project="$PROJECT_ID" --quiet
    log_ok "Atualizado: $SECRET_NAME"
  else
    echo -n "$SECRET_VALUE" | gcloud secrets create "$SECRET_NAME" \
      --data-file=- --project="$PROJECT_ID" --quiet
    log_ok "Criado:     $SECRET_NAME"
  fi
done

echo ""
echo "========================================="
log_ok "Todos os secrets foram sincronizados!"
echo ""
echo "  Verifique em:"
echo "  https://console.cloud.google.com/security/secret-manager?project=${PROJECT_ID}"
echo "========================================="
echo ""

# -----------------------------------------------------------------------
# Opcional: Atualizar GCP_PROJECT_ID no GitHub via gh CLI
# -----------------------------------------------------------------------
if command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI encontrado. Atualizando GCP_PROJECT_ID no repositório..."
  gh secret set GCP_PROJECT_ID --body "$PROJECT_ID" 2>/dev/null && \
    log_ok "GitHub secret GCP_PROJECT_ID atualizado." || \
    log_warn "Não foi possível atualizar o GitHub. Faça manualmente se necessário."
else
  log_warn "gh CLI não instalado — GitHub secrets devem ser configurados manualmente."
  echo "  Instale com: https://cli.github.com"
fi
