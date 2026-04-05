#!/bin/bash
# =============================================================================
# push-to-github.sh — Envia o projeto para git@github.com:bishoppython/TEAChat.git
#
# USO: bash GCP/push-to-github.sh "mensagem do commit"
# =============================================================================

set -euo pipefail

REMOTE="git@github.com:bishoppython/TEAChat.git"
BRANCH="main"
COMMIT_MSG="${1:-"feat: atualização do projeto TEAChat"}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Verificar se estamos no diretório correto
if [ ! -f "app.py" ]; then
    echo -e "${RED}[ERRO]${NC} Execute a partir da raiz do projeto (onde está o app.py)."
    echo "Exemplo: bash GCP/push-to-github.sh"
    exit 1
fi

echo ""
echo "====================================================="
echo "  TEAChat — Push para GitHub"
echo "  Repositório: $REMOTE"
echo "====================================================="
echo ""

# Verificar remote
CURRENT_REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
if [ "$CURRENT_REMOTE" != "$REMOTE" ]; then
    echo -e "${YELLOW}[CONFIG]${NC} Atualizando remote origin para: $REMOTE"
    git remote set-url origin "$REMOTE"
fi

# Verificar se há algo para commitar
if git diff --quiet && git diff --cached --quiet && [ -z "$(git status --porcelain)" ]; then
    echo -e "${GREEN}[OK]${NC} Nada para commitar. Repositório está atualizado."
    exit 0
fi

# Mostrar o que será commitado
echo -e "${YELLOW}[STATUS]${NC} Arquivos que serão incluídos no commit:"
git status --short

echo ""
read -r -p "Confirmar o commit com a mensagem: \"$COMMIT_MSG\"? [S/n] " confirm
confirm="${confirm:-S}"
if [[ ! "$confirm" =~ ^[Ss]$ ]]; then
    echo "Operação cancelada."
    exit 0
fi

# Adicionar arquivos ao staging (respeitando o .gitignore)
echo -e "${YELLOW}[GIT]${NC} Adicionando arquivos..."
git add .

# Verificar se há algo no staging após o git add
if git diff --cached --quiet; then
    echo -e "${GREEN}[OK]${NC} Nada para commitar após aplicar .gitignore."
    exit 0
fi

# Commit
echo -e "${YELLOW}[GIT]${NC} Criando commit..."
git commit -m "$COMMIT_MSG"

# Push
echo -e "${YELLOW}[GIT]${NC} Enviando para o GitHub..."
git push origin "$BRANCH"

echo ""
echo -e "${GREEN}====================================================="
echo -e "  ✅ Sucesso! Projeto enviado para:"
echo -e "  https://github.com/bishoppython/TEAChat"
echo -e "  Branch: $BRANCH"
echo -e "=====================================================${NC}"
echo ""
echo "  O GitHub Actions iniciará o deploy automático."
echo "  Acompanhe em: https://github.com/bishoppython/TEAChat/actions"
echo ""
