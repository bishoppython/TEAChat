#!/bin/bash

# ============================================
# ECS FARGATE - Deploy do Serviço (Alternativa ao App Runner)
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

source aws-deploy/.env.aws

REGION="${REGION:-us-east-1}"
SERVICE_NAME="${PROJECT_NAME}-api"
CLUSTER_NAME="${PROJECT_NAME}-cluster"
CONTAINER_NAME="${PROJECT_NAME}-container"
TASK_NAME="${PROJECT_NAME}-task"

if [ -z "$DB_ENDPOINT" ] || [ -z "$DB_PASSWORD" ]; then
    echo "❌ Erro: Variáveis do banco de dados não estão configuradas"
    exit 1
fi

DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_ENDPOINT}:${DB_PORT}/${DB_NAME}"

echo "============================================"
echo "🚀 DEPLOY - AWS ECS Fargate"
echo "============================================"
echo "Região: $REGION"
echo "Cluster: $CLUSTER_NAME"
echo "Serviço: $SERVICE_NAME"
echo ""

# 1. Criar Cluster ECS
echo "📦 Criando cluster ECS..."
aws ecs create-cluster --cluster-name $CLUSTER_NAME --region $REGION 2>/dev/null || echo "   ℹ️  Cluster já existe"
echo "   ✅ Cluster criado"
echo ""

# 2. Criar Task Role
echo "🔐 Criando IAM Role para Task..."
aws iam create-role \
    --role-name ${PROJECT_NAME}-task-role \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ecs-tasks.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }' 2>/dev/null || echo "   ℹ️  Task role já existe"

aws iam attach-role-policy \
    --role-name ${PROJECT_NAME}-task-role \
    --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess 2>/dev/null || true
echo "   ✅ Task role configurada"
echo ""

# 3. Criar Execution Role
echo "🔐 Criando Execution Role..."
aws iam create-role \
    --role-name ${PROJECT_NAME}-execution-role \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ecs-tasks.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }' 2>/dev/null || echo "   ℹ️  Execution role já existe"

aws iam attach-role-policy \
    --role-name ${PROJECT_NAME}-execution-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy 2>/dev/null || true
echo "   ✅ Execution role configurada"
echo ""

# 4. Obter VPC e Subnets
echo "🌐 Obtendo configurações de rede..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text --region $REGION)
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].SubnetId' --output text --region $REGION | awk '{print $1","$2}')
SECURITY_GROUP_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=${PROJECT_NAME}-rds-sg" --query 'SecurityGroups[0].GroupId' --output text --region $REGION)

# Criar Security Group para o serviço
SERVICE_SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=${PROJECT_NAME}-service-sg" --query 'SecurityGroups[0].GroupId' --output text --region $REGION 2>/dev/null || echo "")

if [ -z "$SERVICE_SG_ID" ] || [ "$SERVICE_SG_ID" == "None" ]; then
    SERVICE_SG_ID=$(aws ec2 create-security-group \
        --group-name ${PROJECT_NAME}-service-sg \
        --description "Security group for ECS service" \
        --vpc-id $VPC_ID \
        --region $REGION \
        --query 'GroupId' --output text)
    
    aws ec2 authorize-security-group-ingress \
        --group-id $SERVICE_SG_ID \
        --protocol tcp \
        --port 8000 \
        --cidr 0.0.0.0/0 \
        --region $REGION
fi

echo "   ✅ Rede configurada"
echo ""

# 5. Registrar Task Definition
echo "📝 Criando Task Definition..."
aws ecs register-task-definition \
    --family $TASK_NAME \
    --network-mode awsvpc \
    --requires-compatibilities FARGATE \
    --cpu "1024" \
    --memory "2048" \
    --execution-role-arn arn:aws:iam::${ACCOUNT_ID}:role/${PROJECT_NAME}-execution-role \
    --task-role-arn arn:aws:iam::${ACCOUNT_ID}:role/${PROJECT_NAME}-task-role \
    --container-definitions "[{
        \"name\": \"$CONTAINER_NAME\",
        \"image\": \"${ECR_API_URI}:latest\",
        \"essential\": true,
        \"portMappings\": [{
            \"containerPort\": 8000,
            \"hostPort\": 8000,
            \"protocol\": \"tcp\"
        }],
        \"environment\": [
            {\"name\": \"DATABASE_URL\", \"value\": \"$DATABASE_URL\"},
            {\"name\": \"HOST\", \"value\": \"0.0.0.0\"},
            {\"name\": \"PORT\", \"value\": \"8000\"}
        ],
        \"logConfiguration\": {
            \"logDriver\": \"awslogs\",
            \"options\": {
                \"awslogs-group\": \"/ecs/$TASK_NAME\",
                \"awslogs-region\": \"$REGION\",
                \"awslogs-stream-prefix\": \"ecs\"
            }
        }
    }]" \
    --region $REGION

echo "   ✅ Task Definition criada"
echo ""

# 6. Criar CloudWatch Log Group
echo "📊 Criando log group..."
aws logs create-log-group --log-group-name "/ecs/$TASK_NAME" --region $REGION 2>/dev/null || echo "   ℹ️  Log group já existe"
echo "   ✅ Log group configurado"
echo ""

# 7. Criar Serviço ECS
echo "🚀 Criando serviço ECS..."
SERVICE_ARN=$(aws ecs create-service \
    --cluster $CLUSTER_NAME \
    --service-name $SERVICE_NAME \
    --task-definition $TASK_NAME \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],securityGroups=[$SERVICE_SG_ID],assignPublicIp=ENABLED}" \
    --region $REGION \
    --query 'service.serviceArn' --output text 2>/dev/null || echo "")

if [ -n "$SERVICE_ARN" ] && [ "$SERVICE_ARN" != "None" ]; then
    echo "   ✅ Serviço criado: $SERVICE_ARN"
else
    echo "   ℹ️  Serviço já existe, atualizando..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --task-definition $TASK_NAME \
        --force-new-deployment \
        --region $REGION
    echo "   ✅ Serviço atualizado"
fi
echo ""

# 8. Aguardar serviço ficar estável
echo "⏳ Aguardando serviço ficar disponível..."
for i in {1..30}; do
    STATUS=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $REGION \
        --query 'services[0].status' --output text 2>/dev/null || echo "UNKNOWN")
    
    RUNNING=$(aws ecs describe-services \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $REGION \
        --query 'services[0].runningCount' --output text 2>/dev/null || echo "0")
    
    echo "   Status: $STATUS | Running: $RUNNING/1 ($i/30)"
    
    if [ "$STATUS" == "ACTIVE" ] && [ "$RUNNING" == "1" ]; then
        echo "   ✅ Serviço está rodando!"
        break
    fi
    
    sleep 10
done
echo ""

# 9. Obter IP público da tarefa
echo "📍 Obtendo endpoint do serviço..."
TASK_ARN=$(aws ecs list-tasks --cluster $CLUSTER_NAME --service-name $SERVICE_NAME --region $REGION --query 'taskArns[0]' --output text 2>/dev/null || echo "")

if [ -n "$TASK_ARN" ] && [ "$TASK_ARN" != "None" ]; then
    TASK_IP=$(aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks $TASK_ARN --region $REGION --query 'tasks[0].attachments[0].details[?name==`privateIPv4Address`].value' --output text 2>/dev/null || echo "N/A")
    echo "   IP da tarefa: $TASK_IP"
fi

echo ""
echo "============================================"
echo "✅ DEPLOY CONCLUÍDO COM SUCESSO!"
echo "============================================"
echo ""
echo "📊 Resumo:"
echo "   Cluster: $CLUSTER_NAME"
echo "   Serviço: $SERVICE_NAME"
echo "   Task: $TASK_NAME"
echo "   Porta: 8000"
echo ""
echo "🧪 Testar API:"
echo "   # Aguarde 2-3 minutos para a tarefa iniciar"
echo "   curl http://<TASK_IP>:8000/health"
echo ""
echo "📝 Comandos úteis:"
echo "   # Ver logs:"
echo "   aws logs tail /ecs/$TASK_NAME --follow --region $REGION"
echo ""
echo "   # Ver status do serviço:"
echo "   aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $REGION"
echo ""
echo "   # Parar serviço:"
echo "   aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --desired-count 0 --region $REGION"
echo ""
echo "   # Reiniciar serviço:"
echo "   aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force-new-deployment --region $REGION"
echo ""
echo "============================================"
