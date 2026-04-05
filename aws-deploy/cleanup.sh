#!/bin/bash

# ============================================
# CLEANUP - Remover todos os recursos
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."  # Voltar para raiz do projeto

# Carregar variáveis de ambiente
source aws-deploy/.env.aws

REGION="${REGION:-us-east-1}"

echo "============================================"
echo "🗑️  CLEANUP - Remover recursos da AWS"
echo "============================================"
echo ""
echo "⚠️  ATENÇÃO: Isso irá remover TODOS os recursos criados!"
echo ""
echo "Recursos que serão removidos:"
echo "  - Serviço App Runner: ${PROJECT_NAME}-api"
echo "  - Instância RDS: ${PROJECT_NAME}-postgres"
echo "  - Repositórios ECR: ${PROJECT_NAME}-api, ${PROJECT_NAME}-frontend"
echo "  - Security Group: ${PROJECT_NAME}-rds-sg"
echo "  - DB Subnet Group: ${PROJECT_NAME}-subnet-group"
echo "  - DB Parameter Group: ${PROJECT_NAME}-pgvector-params"
echo "  - IAM Role: ${PROJECT_NAME}-apprunner-role"
echo "  - Bucket S3: $BUCKET_NAME"
echo ""

# Perguntar confirmação
read -p "Tem certeza que deseja continuar? Digite 'SIM' para confirmar: " -r
echo ""
if [[ ! $REPLY =~ ^SIM$ ]]; then
    echo "Cleanup cancelado."
    exit 0
fi

echo ""
echo "🗑️  Iniciando cleanup..."
echo ""

# 1. Parar e deletar serviço App Runner
echo "1️⃣  Deletando serviço App Runner..."
SERVICE_ARN=$(aws apprunner list-services \
    --region $REGION \
    --query "Services[?ServiceName=='${PROJECT_NAME}-api'].ServiceArn" \
    --output text 2>/dev/null || echo "")

if [ -n "$SERVICE_ARN" ] && [ "$SERVICE_ARN" != "None" ]; then
    aws apprunner delete-service --service-arn $SERVICE_ARN --region $REGION
    echo "   ⏳ Aguardando deleção do serviço..."
    aws apprunner wait service-deleted --service-arn $SERVICE_ARN --region $REGION 2>/dev/null || true
    echo "   ✅ Serviço deletado"
else
    echo "   ℹ️  Serviço não encontrado"
fi
echo ""

# 2. Deletar instância RDS
echo "2️⃣  Deletando instância RDS..."
aws rds delete-db-instance \
    --db-instance-identifier ${PROJECT_NAME}-postgres \
    --skip-final-snapshot \
    --region $REGION 2>/dev/null && \
    echo "   ⏳ Aguardando deleção do RDS..." && \
    aws rds wait db-instance-deleted \
        --db-instance-identifier ${PROJECT_NAME}-postgres \
        --region $REGION 2>/dev/null || \
    echo "   ℹ️  RDS não encontrado ou já deletado"
echo ""

# 3. Deletar DB Subnet Group
echo "3️⃣  Deletando DB Subnet Group..."
aws rds delete-db-subnet-group \
    --db-subnet-group-name ${PROJECT_NAME}-subnet-group \
    --region $REGION 2>/dev/null || \
    echo "   ℹ️  Subnet group não encontrado"
echo ""

# 4. Deletar DB Parameter Group
echo "4️⃣  Deletando DB Parameter Group..."
aws rds delete-db-parameter-group \
    --db-parameter-group-name ${PROJECT_NAME}-pgvector-params \
    --region $REGION 2>/dev/null || \
    echo "   ℹ️  Parameter group não encontrado"
echo ""

# 5. Deletar repositórios ECR
echo "5️⃣  Deletando repositórios ECR..."
aws ecr delete-repository \
    --repository-name ${PROJECT_NAME}-api \
    --force \
    --region $REGION 2>/dev/null || \
    echo "   ℹ️  Repositório API não encontrado"

aws ecr delete-repository \
    --repository-name ${PROJECT_NAME}-frontend \
    --force \
    --region $REGION 2>/dev/null || \
    echo "   ℹ️  Repositório Frontend não encontrado"
echo ""

# 6. Deletar Security Group
echo "6️⃣  Deletando Security Group..."
aws ec2 delete-security-group \
    --group-id $SG_ID \
    --region $REGION 2>/dev/null || \
    echo "   ℹ️  Security group não encontrado"
echo ""

# 7. Remover políticas da IAM Role e deletar
echo "7️⃣  Deletando IAM Role..."
aws iam detach-role-policy \
    --role-name ${PROJECT_NAME}-apprunner-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess 2>/dev/null || true

aws iam detach-role-policy \
    --role-name ${PROJECT_NAME}-apprunner-role \
    --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess 2>/dev/null || true

aws iam detach-role-policy \
    --role-name ${PROJECT_NAME}-apprunner-role \
    --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite 2>/dev/null || true

aws iam delete-role \
    --role-name ${PROJECT_NAME}-apprunner-role \
    --region $REGION 2>/dev/null || \
    echo "   ℹ️  IAM Role não encontrada"
echo ""

# 8. Esvaziar e deletar bucket S3
echo "8️⃣  Deletando bucket S3..."
if [ -n "$BUCKET_NAME" ] && [ "$BUCKET_NAME" != "" ]; then
    aws s3 rm s3://$BUCKET_NAME --recursive 2>/dev/null || true
    aws s3 rb s3://$BUCKET_NAME 2>/dev/null || \
        echo "   ℹ️  Bucket não encontrado"
fi
echo ""

# 9. Deletar CloudWatch Logs (opcional)
echo "9️⃣  Limpando CloudWatch Logs..."
aws logs describe-log-groups --log-group-name-prefix "/aws/apprunner/${PROJECT_NAME}" --region $REGION --query 'logGroups[*].logGroupName' --output text 2>/dev/null | \
    xargs -I {} aws logs delete-log-group --log-group-name {} --region $REGION 2>/dev/null || true
echo ""

echo "============================================"
echo "✅ Cleanup concluído!"
echo "============================================"
echo ""
echo "📝 Nota: Alguns recursos podem levar alguns minutos para serem completamente removidos."
echo ""
echo "Para verificar recursos remanescentes:"
echo "   aws apprunner list-services --region $REGION"
echo "   aws rds describe-db-instances --region $REGION"
echo "   aws ecr describe-repositories --region $REGION"
echo ""
