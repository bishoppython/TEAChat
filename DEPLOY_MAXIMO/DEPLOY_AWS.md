# 🚀 Guia de Deploy - Produção

Este documento descreve as opções de deploy em produção para o projeto **Symyah**.

---

## 📋 Índice

- [Opção 1: AWS App Runner + RDS (Recomendada)](#opção-1-aws-app-runner--rds-recomendada)
- [Estrutura de Arquivos](#estrutura-de-arquivos)
- [Pré-requisitos](#pré-requisitos)
- [Deploy Rápido](#deploy-rápido)
- [Deploy Passo a Passo](#deploy-passo-a-passo)
- [Custos Estimados](#custos-estimados)
- [Troubleshooting](#troubleshooting)

---

## Opção 1: AWS App Runner + RDS (Recomendada)

### Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                         AWS                                 │
│                                                             │
│  ┌─────────────────────────────────────────────────┐       │
│  │           AWS App Runner                        │       │
│  │  ┌─────────────────┐    ┌─────────────────┐    │       │
│  │  │   FastAPI       │    │   Frontend      │    │       │
│  │  │   (Port 8000)   │    │   (Flask)       │    │       │
│  │  └────────┬────────┘    └─────────────────┘    │       │
│  └───────────┼─────────────────────────────────────┘       │
│              │                                              │
│              ▼                                              │
│  ┌─────────────────────────────────────────┐               │
│  │      RDS PostgreSQL 15 + pgvector       │               │
│  └─────────────────────────────────────────┘               │
│                                                             │
│  ┌──────────────┐     ┌──────────────────┐                 │
│  │     ECR      │     │  CloudWatch      │                 │
│  │  (imagens)   │     │   (logs)         │                 │
│  └──────────────┘     └──────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### Vantagens

| ✅ | Descrição |
|---|-----------|
| **Serverless** | Sem gerenciar servidores EC2 |
| **Auto-scaling** | Escala automática baseada em demanda |
| **HTTPS automático** | Certificado SSL gerenciado |
| **pgvector nativo** | RDS PostgreSQL 15+ já suporta |
| **Fácil deploy** | Scripts automatizados |
| **Custo justo** | Paga pelo uso real |

---

## Estrutura de Arquivos

```
aws-deploy/
├── README.md              # Documentação completa
├── 01-setup.sh            # Setup inicial na AWS
├── 02-build-push.sh       # Build e push das imagens
├── 03-deploy-apprunner.sh # Deploy no App Runner
├── 04-create-rds.sh       # Criação do RDS PostgreSQL
├── 05-enable-pgvector.sh  # Habilita pgvector
├── deploy-all.sh          # Deploy completo (todos os passos)
└── cleanup.sh             # Remove todos os recursos
```

---

## Pré-requisitos

### 1. AWS CLI Configurado

```bash
# Instalar AWS CLI (Linux)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configurar
aws configure
```

### 2. Docker

```bash
# Verificar instalação
docker --version
```

### 3. PostgreSQL Client

```bash
sudo apt-get update && sudo apt-get install -y postgresql-client
```

### 4. Variáveis de Ambiente

```bash
export GOOGLE_API_KEY="sua_google_api_key"
export SECRET_KEY="sua_secret_key"
export OPENAI_API_KEY="sua_openai_key"  # opcional
```

---

## Deploy Rápido

```bash
# 1. Tornar scripts executáveis
chmod +x aws-deploy/*.sh

# 2. Executar deploy completo
bash aws-deploy/deploy-all.sh
```

⏱️ **Tempo estimado:** 15-20 minutos

---

## Deploy Passo a Passo

### Passo 1: Setup Inicial

```bash
bash aws-deploy/01-setup.sh
```

**O que faz:**
- Cria bucket S3
- Cria IAM Role para App Runner
- Cria repositórios ECR
- Configura Security Groups e VPC

---

### Passo 2: Build e Push

```bash
bash aws-deploy/02-build-push.sh
```

**O que faz:**
- Login no ECR
- Build das imagens Docker
- Push para o ECR

---

### Passo 3: Criar RDS

```bash
bash aws-deploy/04-create-rds.sh
```

**O que faz:**
- Cria instância RDS PostgreSQL 15
- Configura subnets e security groups
- ⏱️ Tempo: 5-10 minutos

---

### Passo 4: Habilitar pgvector

```bash
bash aws-deploy/05-enable-pgvector.sh
```

**O que faz:**
- Habilita extensão pgvector
- Cria database `symyah_db`
- Executa schemas (se existirem)

---

### Passo 5: Deploy no App Runner

```bash
bash aws-deploy/03-deploy-apprunner.sh
```

**O que faz:**
- Cria serviço no App Runner
- Configura auto-scaling e health checks
- ⏱️ Tempo: 3-5 minutos

---

## Testando o Deploy

### Health Check

```bash
source aws-deploy/.env.aws
curl https://$APP_RUNNER_SERVICE_URL/health
```

### Testar API

```bash
# Listar pacientes
curl https://$APP_RUNNER_SERVICE_URL/api/patients

# Criar paciente
curl -X POST https://$APP_RUNNER_SERVICE_URL/api/patients \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Patient", "email": "test@example.com"}'
```

---

## Custos Estimados

### Mensal

| Serviço | Configuração | Custo |
|---------|-------------|-------|
| App Runner | 1 vCPU, 2GB RAM | ~$50-70 |
| RDS | db.t3.micro, 20GB | ~$15-20 |
| ECR | 500MB | ~$0.50 |
| CloudWatch Logs | - | ~$1-2 |
| **Total** | | **~$65-95/mês** |

### Como Economizar

```bash
# Pausar serviço (não cobra computação)
aws apprunner pause-service --service-arn <service-arn> --region us-east-1

# Retomar serviço
aws apprunner resume-service --service-arn <service-arn> --region us-east-1
```

---

## Monitoramento

### Status do Serviço

```bash
aws apprunner describe-service \
  --service-name symyah-api \
  --region us-east-1
```

### Logs em Tempo Real

```bash
aws logs tail /aws/apprunner/symyah-api --follow --region us-east-1
```

### Operações

```bash
SERVICE_ARN=$(aws apprunner list-services \
  --region us-east-1 \
  --query "Services[?ServiceName=='symyah-api'].ServiceArn" \
  --output text)

aws apprunner list-operations --service-arn $SERVICE_ARN --region us-east-1
```

---

## Cleanup

### Remover Tudo

```bash
bash aws-deploy/cleanup.sh
```

⚠️ **Atenção:** Remove TODOS os recursos criados.

### Remover Manualmente

```bash
# App Runner
aws apprunner delete-service --service-arn <arn> --region us-east-1

# RDS
aws rds delete-db-instance \
  --db-instance-identifier symyah-postgres \
  --skip-final-snapshot \
  --region us-east-1

# ECR
aws ecr delete-repository --repository-name symyah-api --force --region us-east-1
```

---

## Troubleshooting

### Erro: "AWS CLI não está configurado"

```bash
aws configure
```

---

### Erro: "psql não encontrado"

```bash
sudo apt-get update && sudo apt-get install -y postgresql-client
```

---

### Erro: "Acesso negado ao ECR"

```bash
# Verificar permissões da IAM Role
aws iam list-attached-role-policies --role-name symyah-apprunner-role
```

---

### Erro: "RDS não aceita conexão"

```bash
# Verificar Security Group
aws ec2 describe-security-groups --group-ids $SG_ID --region us-east-1

# Verificar se RDS é público
aws rds describe-db-instances \
  --db-instance-identifier symyah-postgres \
  --query 'DBInstances[0].PubliclyAccessible'
```

---

### Erro: "pgvector não encontrado"

```bash
# Habilitar extensão
psql -h $DB_ENDPOINT -U postgres -d symyah_db \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## Outras Opções de Deploy

### Opção 2: AWS EC2 + Docker Compose

- Mais simples (igual ambiente local)
- Custo menor (~$20-30/mês)
- Requer gerenciamento manual

### Opção 3: AWS ECS + Fargate

- Mais controle que App Runner
- Melhor para múltiplos serviços
- Custo similar ao App Runner

### Opção 4: Google Cloud Platform

- Cloud Run + Cloud SQL
- Documentação disponível em `gcp-deploy/`

### Opção 5: Azure

- Azure Container Apps + Azure Database for PostgreSQL
- Documentação disponível em `azure-deploy/`

---

## 📞 Suporte

- **Documentação Completa:** `aws-deploy/README.md`
- **AWS App Runner:** https://docs.aws.amazon.com/apprunner/
- **RDS PostgreSQL:** https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html
- **pgvector:** https://github.com/pgvector/pgvector

---

**Última atualização:** Fevereiro 2026
