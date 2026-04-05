#!/bin/bash

# ============================================
# SETUP - Configuração Inicial na AWS
# ============================================

set -e

REGION="us-east-1"
PROJECT_NAME="symyah"

echo "============================================"
echo "🔧 SETUP INICIAL - AWS"
echo "============================================"
echo "Região: $REGION"
echo "Projeto: $PROJECT_NAME"
echo ""

# 1. Verificar se AWS CLI está configurado
echo "📋 Verificando configuração AWS..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ Erro: AWS CLI não está configurado ou credenciais inválidas"
    echo "Execute: aws configure"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "✅ Conta AWS: $ACCOUNT_ID"
echo ""

# 2. Criar bucket S3 para artifacts (nome deve ser único)
BUCKET_NAME="${PROJECT_NAME}-${ACCOUNT_ID}-$(date +%Y%m%d%H%M%S)-artifacts"
echo "📦 Criando bucket S3: $BUCKET_NAME"
aws s3 mb s3://$BUCKET_NAME --region $REGION
echo ""

# 3. Criar IAM Role para App Runner
echo "🔐 Criando IAM Role para App Runner..."
aws iam create-role \
    --role-name ${PROJECT_NAME}-apprunner-role \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "tasks.apprunner.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }' 2>/dev/null || echo "   ℹ️  Role já existe"

# 4. Anexar políticas à role
echo "   📎 Anexando políticas à role..."
aws iam attach-role-policy \
    --role-name ${PROJECT_NAME}-apprunner-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess

aws iam attach-role-policy \
    --role-name ${PROJECT_NAME}-apprunner-role \
    --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess

aws iam attach-role-policy \
    --role-name ${PROJECT_NAME}-apprunner-role \
    --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite 2>/dev/null || true

echo "   ✅ Role configurada"
echo ""

# 5. Criar repositório ECR para API
echo "🐳 Criando repositório ECR para API..."
aws ecr create-repository \
    --repository-name ${PROJECT_NAME}-api \
    --region $REGION 2>/dev/null || echo "   ℹ️  Repositório já existe"

# 6. Criar repositório ECR para Frontend
echo "🐳 Criando repositório ECR para Frontend..."
aws ecr create-repository \
    --repository-name ${PROJECT_NAME}-frontend \
    --region $REGION 2>/dev/null || echo "   ℹ️  Repositório já existe"
echo ""

# 7. Obter VPC padrão
echo "🌐 Obtendo VPC padrão..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text --region $REGION)

if [ -z "$VPC_ID" ] || [ "$VPC_ID" == "None" ]; then
    echo "❌ Erro: VPC padrão não encontrada"
    exit 1
fi

echo "   ✅ VPC: $VPC_ID"
echo ""

# 8. Criar Security Group para RDS
echo "🔒 Criando Security Group para RDS..."
SG_EXISTS=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=${PROJECT_NAME}-rds-sg" \
    --query 'SecurityGroups[0].GroupId' \
    --output text \
    --region $REGION 2>/dev/null)

if [ "$SG_EXISTS" != "None" ] && [ -n "$SG_EXISTS" ]; then
    SG_ID=$SG_EXISTS
    echo "   ℹ️  Security Group já existe: $SG_ID"
else
    SG_ID=$(aws ec2 create-security-group \
        --group-name ${PROJECT_NAME}-rds-sg \
        --description "Security group para RDS do Symyah" \
        --vpc-id $VPC_ID \
        --region $REGION \
        --query 'GroupId' --output text)
    echo "   ✅ Security Group criado: $SG_ID"
fi
echo ""

# 9. Adicionar regra de inbound para PostgreSQL (porta 5432)
echo "   🔓 Adicionando regra de inbound (PostgreSQL 5432)..."
aws ec2 authorize-security-group-ingress \
    --group-id $SG_ID \
    --protocol tcp \
    --port 5432 \
    --cidr 0.0.0.0/0 \
    --region $REGION 2>/dev/null || echo "   ℹ️  Regra já existe"
echo ""

# 10. Criar grupo de parâmetros RDS para pgvector
echo "📊 Criando DB Parameter Group para pgvector..."
aws rds create-db-parameter-group \
    --db-parameter-group-name ${PROJECT_NAME}-pgvector-params \
    --db-family postgres15 \
    --description "PostgreSQL 15 com pgvector habilitado" \
    --region $REGION 2>/dev/null || echo "   ℹ️  Parameter group já existe"
echo ""

# 11. Salvar informações para próximos passos
echo "📝 Salvando configurações..."
cat > aws-deploy/.env.aws <<EOF
# AWS Configuration
REGION=$REGION
PROJECT_NAME=$PROJECT_NAME
ACCOUNT_ID=$ACCOUNT_ID

# S3 Bucket
BUCKET_NAME=$BUCKET_NAME

# VPC
VPC_ID=$VPC_ID
SG_ID=$SG_ID

# ECR URIs
ECR_API_URI=${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${PROJECT_NAME}-api
ECR_FRONTEND_URI=${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${PROJECT_NAME}-frontend

# RDS (será preenchido após criação)
DB_ENDPOINT=
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=
DB_NAME=symyah_db

# App Runner
APP_RUNNER_SERVICE_URL=
EOF

echo "✅ Setup concluído com sucesso!"
echo ""
echo "============================================"
echo "📄 Resumo:"
echo "============================================"
echo "   Bucket S3: $BUCKET_NAME"
echo "   VPC: $VPC_ID"
echo "   Security Group: $SG_ID"
echo "   ECR API: ${PROJECT_NAME}-api"
echo "   ECR Frontend: ${PROJECT_NAME}-frontend"
echo ""
echo "📄 Arquivo .env.aws criado em: aws-deploy/.env.aws"
echo ""
echo "➡️  Próximo passo: bash aws-deploy/02-build-push.sh"
echo "============================================"
