#!/bin/bash

# ============================================
# APP RUNNER - Deploy do Serviço
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."  # Voltar para raiz do projeto

# Carregar variáveis de ambiente
source aws-deploy/.env.aws

REGION="${REGION:-us-east-1}"
SERVICE_NAME="${PROJECT_NAME}-api"

echo "============================================"
echo "🚀 DEPLOY - AWS App Runner"
echo "============================================"
echo "Região: $REGION"
echo "Serviço: $SERVICE_NAME"
echo ""

# Verificar se as variáveis necessárias estão definidas
if [ -z "$DB_ENDPOINT" ] || [ -z "$DB_PASSWORD" ]; then
    echo "❌ Erro: Variáveis do banco de dados não estão configuradas"
    echo "Execute primeiro: bash aws-deploy/04-create-rds.sh"
    exit 1
fi

# Construir DATABASE_URL
DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_ENDPOINT}:${DB_PORT}/${DB_NAME}"

echo "📊 Configurações:"
echo "   Endpoint RDS: $DB_ENDPOINT"
echo "   Database: $DB_NAME"
echo "   Image: ${ECR_API_URI}:latest"
echo ""

# 1. Verificar se a imagem existe no ECR
echo "🔍 Verificando imagem no ECR..."
if ! aws ecr describe-images --repository-name ${PROJECT_NAME}-api --image-ids imageTag=latest --region $REGION > /dev/null 2>&1; then
    echo "❌ Erro: Imagem não encontrada no ECR"
    echo "Execute primeiro: bash aws-deploy/02-build-push.sh"
    exit 1
fi
echo "   ✅ Imagem encontrada"
echo ""

# 2. Criar configuração de auto-scaling
echo "📈 Criando configuração de auto-scaling..."
AUTO_SCALING_ARN=$(aws apprunner create-auto-scaling-configuration \
    --min-connections 1 \
    --max-connections 5 \
    --region $REGION \
    --query AutoScalingConfigurationArn --output text 2>/dev/null || \
    aws apprunner list-auto-scaling-configurations \
        --region $REGION \
        --query 'AutoScalingConfigurations[0].AutoScalingConfigurationArn' --output text)

echo "   ✅ Auto-scaling configurado"
echo ""

# 3. Verificar se serviço já existe
echo "🔍 Verificando existência do serviço..."
SERVICE_ARN=$(aws apprunner list-services \
    --region $REGION \
    --query "Services[?ServiceName=='$SERVICE_NAME'].ServiceArn" --output text 2>/dev/null)

if [ -n "$SERVICE_ARN" ] && [ "$SERVICE_ARN" != "None" ]; then
    echo "   ℹ️  Serviço já existe, atualizando..."
    
    # Atualizar serviço existente
    aws apprunner update-service \
        --service-arn $SERVICE_ARN \
        --source-configuration ImageRepository=\
Type=ECR,\
ImageIdentifier=${ECR_API_URI}:latest,\
ImageConfiguration=\
{Port=8000,\
Runtime=python3,\
StartCommand="uvicorn app:app --host 0.0.0.0 --port 8000",\
EnvironmentVariables=\
[{Name=DATABASE_URL,Value="$DATABASE_URL"},\
{Name=HOST,Value="0.0.0.0"},\
{Name=PORT,Value="8000"},\
{Name=RAG_TOP_K,Value="4"},\
{Name=RAG_MIN_SIMILARITY,Value="0.5"}]} \
        --instance-configuration Cpu=1024,Memory=2048 \
        --auto-scaling-configuration-arn $AUTO_SCALING_ARN \
        --health-check-configuration Protocol=HTTP,Path=/health,Interval=30,Timeout=5,HealthyThreshold=2,UnhealthyThreshold=3 \
        --region $REGION
    
    echo "   ✅ Serviço atualizado"
else
    echo "   📝 Criando novo serviço..."
    
    # Criar novo serviço
    RESULT=$(aws apprunner create-service \
        --service-name $SERVICE_NAME \
        --source-configuration ImageRepository=\
Type=ECR,\
ImageIdentifier=${ECR_API_URI}:latest,\
ImageConfiguration=\
{Port=8000,\
Runtime=python3,\
StartCommand="uvicorn app:app --host 0.0.0.0 --port 8000",\
EnvironmentVariables=\
[{Name=DATABASE_URL,Value="$DATABASE_URL"},\
{Name=HOST,Value="0.0.0.0"},\
{Name=PORT,Value="8000"},\
{Name=RAG_TOP_K,Value="4"},\
{Name=RAG_MIN_SIMILARITY,Value="0.5"}]} \
        --instance-configuration Cpu=1024,Memory=2048 \
        --auto-scaling-configuration-arn $AUTO_SCALING_ARN \
        --health-check-configuration Protocol=HTTP,Path=/health,Interval=30,Timeout=5,HealthyThreshold=2,UnhealthyThreshold=3 \
        --network-configuration EgressConfiguration=EgressType=DEFAULT \
        --observability-configuration ObservabilityEnabled=true \
        --region $REGION)
    
    echo "   ✅ Serviço criado"
fi

echo ""
echo "⏳ Aguardando deploy do App Runner (isso pode levar alguns minutos)..."
echo ""

# 4. Aguardar deploy
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    SERVICE_STATUS=$(aws apprunner describe-service \
        --service-arn $(aws apprunner list-services --region $REGION --query "Services[?ServiceName=='$SERVICE_NAME'].ServiceArn" --output text) \
        --region $REGION \
        --query Service.Status --output text 2>/dev/null || echo "UNKNOWN")
    
    echo "   Status: $SERVICE_STATUS ($(($ATTEMPT + 1))/$MAX_ATTEMPTS)"
    
    if [ "$SERVICE_STATUS" == "RUNNING" ]; then
        echo ""
        echo "   ✅ Serviço está rodando!"
        break
    elif [ "$SERVICE_STATUS" == "FAILED" ]; then
        echo ""
        echo "   ❌ Erro no deploy do serviço"
        aws apprunner describe-service \
            --service-arn $(aws apprunner list-services --region $REGION --query "Services[?ServiceName=='$SERVICE_NAME'].ServiceArn" --output text) \
            --region $REGION \
            --query Service.InstanceConfiguration --output text
        exit 1
    fi
    
    sleep 30
    ATTEMPT=$((ATTEMPT + 1))
done

# 5. Obter URL do serviço
echo ""
echo "📍 Obtendo URL do serviço..."
SERVICE_URL=$(aws apprunner describe-service \
    --service-arn $(aws apprunner list-services --region $REGION --query "Services[?ServiceName=='$SERVICE_NAME'].ServiceArn" --output text) \
    --region $REGION \
    --query Service.ServiceUrl --output text)

# Atualizar .env.aws
sed -i "s|^APP_RUNNER_SERVICE_URL=.*|APP_RUNNER_SERVICE_URL=$SERVICE_URL|" aws-deploy/.env.aws

echo ""
echo "============================================"
echo "✅ Deploy concluído com sucesso!"
echo "============================================"
echo ""
echo "🌐 URL do serviço: https://$SERVICE_URL"
echo ""
echo "🧪 Teste o endpoint de health:"
echo "   curl https://$SERVICE_URL/health"
echo ""
echo "📊 Ver logs do serviço:"
echo "   aws apprunner list-operations --service-arn <service-arn> --region $REGION"
echo ""
echo "⏸️  Para parar o serviço (não cobra computação):"
echo "   aws apprunner pause-service --service-arn <service-arn> --region $REGION"
echo ""
echo "▶️  Para iniciar o serviço:"
echo "   aws apprunner resume-service --service-arn <service-arn> --region $REGION"
echo ""
echo "============================================"
