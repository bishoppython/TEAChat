#!/bin/bash

# ============================================
# DEPLOY COMPLETO - Todos os passos
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."  # Voltar para raiz do projeto

echo "============================================"
echo "🎬 DEPLOY COMPLETO - AWS"
echo "============================================"
echo ""
echo "Este script executará todos os passos de deploy:"
echo "  1. Setup inicial na AWS"
echo "  2. Build e push das imagens Docker"
echo "  3. Criação do RDS PostgreSQL"
echo "  4. Habilitação do pgvector"
echo "  5. Deploy no App Runner"
echo ""
echo "⏱️  Tempo estimado: 15-20 minutos"
echo ""

# Verificar se AWS CLI está configurado
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ Erro: AWS CLI não está configurado"
    echo "Execute: aws configure"
    exit 1
fi

# Perguntar confirmação
read -p "Deseja continuar? (s/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[SsYy]$ ]]; then
    echo "Deploy cancelado."
    exit 0
fi

# Exportar variáveis de ambiente (edite conforme necessário)
export GOOGLE_API_KEY="${GOOGLE_API_KEY:-}"
export SECRET_KEY="${SECRET_KEY:-mude_esta_chave_em_producao}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"

if [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  GOOGLE_API_KEY não está definida"
    read -p "Deseja continuar mesmo assim? (s/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[SsYy]$ ]]; then
        echo "Deploy cancelado."
        exit 0
    fi
fi

echo ""
echo "============================================"
echo "1️⃣  SETUP INICIAL"
echo "============================================"
bash aws-deploy/01-setup.sh

echo ""
echo "============================================"
echo "2️⃣  BUILD E PUSH DAS IMAGENS"
echo "============================================"
bash aws-deploy/02-build-push.sh

echo ""
echo "============================================"
echo "3️⃣  CRIAÇÃO DO RDS POSTGRESQL"
echo "============================================"
bash aws-deploy/04-create-rds.sh

echo ""
echo "⏳ Aguardando RDS estar completamente disponível..."
sleep 30

echo ""
echo "============================================"
echo "4️⃣  HABILITAR PGVECTOR"
echo "============================================"
bash aws-deploy/05-enable-pgvector.sh

echo ""
echo "============================================"
echo "5️⃣  DEPLOY NO APP RUNNER"
echo "============================================"
bash aws-deploy/03-deploy-apprunner.sh

echo ""
echo "============================================"
echo "🎉 DEPLOY COMPLETO CONCLUÍDO!"
echo "============================================"
echo ""

# Carregar variáveis finais
source aws-deploy/.env.aws

echo "📊 Resumo do Deploy:"
echo "============================================"
echo "🌐 API URL: https://$APP_RUNNER_SERVICE_URL"
echo "🗄️  RDS Endpoint: $DB_ENDPOINT:$DB_PORT"
echo "📦 Database: $DB_NAME"
echo ""
echo "🧪 Teste a API:"
echo "   curl https://$APP_RUNNER_SERVICE_URL/health"
echo ""
echo "📊 Ver status do serviço:"
echo "   aws apprunner describe-service --service-name symyah-api --region us-east-1"
echo ""
echo "📝 Ver logs:"
echo "   aws logs tail /aws/apprunner/symyah-api --follow"
echo ""
echo "⏸️  Para parar o serviço (não cobra computação):"
echo "   aws apprunner pause-service --service-arn <service-arn> --region us-east-1"
echo ""
echo "🗑️  Para fazer cleanup completo:"
echo "   bash aws-deploy/cleanup.sh"
echo ""
echo "============================================"
