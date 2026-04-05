#!/bin/bash

# ============================================
# RDS - Criar Banco de Dados PostgreSQL
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."  # Voltar para raiz do projeto

# Carregar variáveis de ambiente
source aws-deploy/.env.aws

REGION="${REGION:-us-east-1}"
DB_INSTANCE_IDENTIFIER="${PROJECT_NAME}-postgres"
DB_NAME="symyah_db"
DB_USER="postgres"

# ⚠️ GERAR SENHA ALEATÓRIA OU USAR VARIÁVEL DE AMBIENTE
if [ -n "$RDS_PASSWORD" ]; then
    DB_PASSWORD="$RDS_PASSWORD"
else
    # Gerar senha aleatória segura
    DB_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 20)
fi

DB_PORT="5432"

echo "============================================"
echo "🗄️  RDS - Criar Banco de Dados PostgreSQL"
echo "============================================"
echo "Região: $REGION"
echo "Instância: $DB_INSTANCE_IDENTIFIER"
echo "Database: $DB_NAME"
echo "Usuário: $DB_USER"
echo ""

# 1. Verificar se instância já existe
echo "🔍 Verificando se instância já existe..."
DB_STATUS=$(aws rds describe-db-instances \
    --db-instance-identifier $DB_INSTANCE_IDENTIFIER \
    --region $REGION \
    --query 'DBInstances[0].DBInstanceStatus' \
    --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$DB_STATUS" != "NOT_FOUND" ] && [ "$DB_STATUS" != "None" ]; then
    echo "   ℹ️  Instância já existe (Status: $DB_STATUS)"
    
    # Obter endpoint existente
    DB_ENDPOINT=$(aws rds describe-db-instances \
        --db-instance-identifier $DB_INSTANCE_IDENTIFIER \
        --region $REGION \
        --query 'DBInstances[0].Endpoint.Address' \
        --output text)
    
    echo "   ✅ Endpoint: $DB_ENDPOINT:$DB_PORT"
    echo ""
    echo "⚠️  A instância já existe. Pulando criação."
    echo "   Para recriar, delete a instância existente primeiro:"
    echo "   aws rds delete-db-instance --db-instance-identifier $DB_INSTANCE_IDENTIFIER --skip-final-snapshot --region $REGION"
    echo ""
else
    # 2. Obter subnets da VPC padrão
    echo "🌐 Obtendo subnets da VPC..."
    SUBNET_IDS=$(aws ec2 describe-subnets \
        --filters "Name=vpc-id,Values=$VPC_ID" \
        --query 'Subnets[*].SubnetId' \
        --output text \
        --region $REGION)
    
    if [ -z "$SUBNET_IDS" ] || [ "$SUBNET_IDS" == "None" ]; then
        echo "❌ Erro: Subnets não encontradas na VPC $VPC_ID"
        exit 1
    fi
    
    echo "   ✅ Subnets encontradas"
    echo ""
    
    # 3. Criar DB Subnet Group
    echo "📊 Criando DB Subnet Group..."
    SUBNET_GROUP_NAME="${PROJECT_NAME}-subnet-group"
    
    aws rds create-db-subnet-group \
        --db-subnet-group-name $SUBNET_GROUP_NAME \
        --db-subnet-group-description "Subnet group para RDS Symyah" \
        --subnet-ids $SUBNET_IDS \
        --region $REGION 2>/dev/null || echo "   ℹ️  Subnet group já existe"
    
    echo "   ✅ Subnet group configurado"
    echo ""
    
    # 4. Adicionar regra de inbound no Security Group
    echo "🔒 Configurando Security Group..."
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 5432 \
        --cidr 0.0.0.0/0 \
        --region $REGION 2>/dev/null || echo "   ℹ️  Regra já existe"
    
    echo "   ✅ Security Group configurado"
    echo ""
    
    # 5. Criar instância RDS
    echo "🗄️  Criando instância RDS PostgreSQL..."
    echo "   ⏳ Isso pode levar 5-10 minutos..."
    echo ""
    
    aws rds create-db-instance \
        --db-instance-identifier $DB_INSTANCE_IDENTIFIER \
        --db-instance-class db.t3.micro \
        --engine postgres \
        --engine-version 15.7 \
        --master-username $DB_USER \
        --master-user-password $DB_PASSWORD \
        --allocated-storage 20 \
        --storage-type gp2 \
        --db-subnet-group-name $SUBNET_GROUP_NAME \
        --vpc-security-group-ids $SG_ID \
        --db-parameter-group-name ${PROJECT_NAME}-pgvector-params \
        --publicly-accessible \
        --backup-retention-period 0 \
        --auto-minor-version-upgrade \
        --tags Key=Project,Value=Symyah \
        --region $REGION
    
    echo "   ✅ Instância criada, aguardando disponibilidade..."
    echo ""
    
    # 6. Aguardar RDS ficar disponível
    MAX_ATTEMPTS=40
    ATTEMPT=0
    
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        CURRENT_STATUS=$(aws rds describe-db-instances \
            --db-instance-identifier $DB_INSTANCE_IDENTIFIER \
            --region $REGION \
            --query 'DBInstances[0].DBInstanceStatus' \
            --output text 2>/dev/null || echo "UNKNOWN")
        
        echo "   Status: $CURRENT_STATUS ($(($ATTEMPT + 1))/$MAX_ATTEMPTS)"
        
        if [ "$CURRENT_STATUS" == "available" ]; then
            echo ""
            echo "   ✅ RDS está disponível!"
            break
        elif [ "$CURRENT_STATUS" == "failed" ]; then
            echo ""
            echo "   ❌ Erro na criação do RDS"
            exit 1
        fi
        
        sleep 30
        ATTEMPT=$((ATTEMPT + 1))
    done
    
    # 7. Obter endpoint do RDS
    DB_ENDPOINT=$(aws rds describe-db-instances \
        --db-instance-identifier $DB_INSTANCE_IDENTIFIER \
        --region $REGION \
        --query 'DBInstances[0].Endpoint.Address' \
        --output text)
    
    echo ""
    echo "✅ RDS criado com sucesso!"
    echo "📍 Endpoint: $DB_ENDPOINT:$DB_PORT"
fi

# 8. Atualizar .env.aws com informações do banco
echo ""
echo "📝 Atualizando configurações..."

# Criar backup do .env.aws
cp aws-deploy/.env.aws aws-deploy/.env.aws.bak

# Atualizar variáveis
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

# RDS Configuration
DB_ENDPOINT=$DB_ENDPOINT
DB_PORT=$DB_PORT
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_NAME=$DB_NAME

# App Runner
APP_RUNNER_SERVICE_URL=
EOF

echo "   ✅ Configurações salvas em aws-deploy/.env.aws"
echo ""

# 9. Instruções para habilitar pgvector
echo "============================================"
echo "✅ RDS configurado com sucesso!"
echo "============================================"
echo ""
echo "📦 PRÓXIMO PASSO: Habilitar extensão pgvector"
echo ""
echo "⚠️  IMPORTANTE: Execute os comandos abaixo para configurar o banco:"
echo ""
echo "   # Instalar cliente PostgreSQL (se não tiver)"
echo "   sudo apt-get install -y postgresql-client"
echo ""
echo "   # Habilitar extensão pgvector"
echo "   psql -h $DB_ENDPOINT -U $DB_USER -d postgres -c 'CREATE EXTENSION IF NOT EXISTS vector;'"
echo ""
echo "   # Criar database do projeto"
echo "   psql -h $DB_ENDPOINT -U $DB_USER -c 'CREATE DATABASE $DB_NAME;'"
echo ""
echo "   # Ou use o comando abaixo (automático):"
echo "   bash aws-deploy/05-enable-pgvector.sh"
echo ""
echo "🔐 SALVE ESTA SENHA:"
echo "   $DB_PASSWORD"
echo ""
echo "   (Ela também está salva em: aws-deploy/.env.aws)"
echo "============================================"
