#!/bin/bash

# ============================================
# BUILD & PUSH - Compilar e enviar imagens
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."  # Voltar para raiz do projeto

# Carregar variáveis de ambiente
source aws-deploy/.env.aws

REGION="${REGION:-us-east-1}"

echo "============================================"
echo "🐳 BUILD & PUSH - Imagens Docker"
echo "============================================"
echo "Região: $REGION"
echo ""

# 1. Login no ECR
echo "🔑 Obtendo token de login no ECR..."
aws ecr get-login-password --region $REGION | \
    docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

echo "   ✅ Login realizado com sucesso"
echo ""

# 2. Build da API
echo "🔨 Build da API..."
docker build -t ${PROJECT_NAME}-api:latest -f Dockerfile .

echo "   ✅ Build da API concluído"
echo ""

# 3. Taggeando imagem da API
echo "🏷️  Taggeando imagem da API..."
docker tag ${PROJECT_NAME}-api:latest ${ECR_API_URI}:latest
docker tag ${PROJECT_NAME}-api:latest ${ECR_API_URI}:$(date +%Y%m%d-%H%M%S)

echo "   ✅ Tags criadas"
echo ""

# 4. Push da API para ECR
echo "📤 Push da API para ECR..."
docker push ${ECR_API_URI}:latest
docker push ${ECR_API_URI}:$(date +%Y%m%d-%H%M%S)

echo "   ✅ Push da API concluído"
echo ""

# 5. Build e push do Frontend (se existir)
if [ -d "frontFlask" ]; then
    echo "🔨 Build do Frontend..."
    docker build -t ${PROJECT_NAME}-frontend:latest -f frontFlask/Dockerfile frontFlask
    
    echo "   ✅ Build do Frontend concluído"
    echo ""
    
    echo "🏷️  Taggeando imagem do Frontend..."
    docker tag ${PROJECT_NAME}-frontend:latest ${ECR_FRONTEND_URI}:latest
    docker tag ${PROJECT_NAME}-frontend:latest ${ECR_FRONTEND_URI}:$(date +%Y%m%d-%H%M%S)
    
    echo "   ✅ Tags criadas"
    echo ""
    
    echo "📤 Push do Frontend para ECR..."
    docker push ${ECR_FRONTEND_URI}:latest
    docker push ${ECR_FRONTEND_URI}:$(date +%Y%m%d-%H%M%S)
    
    echo "   ✅ Push do Frontend concluído"
    echo ""
else
    echo "ℹ️  Pasta frontFlask não encontrada - pulando build do frontend"
    echo ""
fi

echo "============================================"
echo "✅ Imagens enviadas com sucesso!"
echo "============================================"
echo ""
echo "📦 Imagens no ECR:"
echo "   API: ${ECR_API_URI}:latest"
if [ -d "frontFlask" ]; then
    echo "   Frontend: ${ECR_FRONTEND_URI}:latest"
fi
echo ""
echo "➡️  Próximo passo: bash aws-deploy/04-create-rds.sh"
echo "============================================"
