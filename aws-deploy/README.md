# 🚀 Deploy na AWS - TEAChat

Este guia descreve o processo completo de deploy do projeto TEAChat na AWS usando **App Runner** + **RDS PostgreSQL com pgvector**.

---

## 📋 Arquitetura

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

---

## 📦 Pré-requisitos

1. **AWS CLI configurado**
   ```bash
   aws configure
   ```

2. **Docker instalado**
   ```bash
   docker --version
   ```

3. **PostgreSQL client (para configurar o banco)**
   ```bash
   sudo apt-get install -y postgresql-client
   ```

4. **Variáveis de ambiente necessárias**
   ```bash
   export GOOGLE_API_KEY="sua_google_api_key"
   export SECRET_KEY="sua_secret_key"
   export OPENAI_API_KEY="sua_openai_key"  # opcional
   ```

---

## 🎯 Scripts de Deploy

| Script | Descrição |
|--------|-----------|
| `01-setup.sh` | Configura recursos iniciais (ECR, IAM, Security Groups) |
| `02-build-push.sh` | Build e push das imagens Docker para ECR |
| `03-deploy-apprunner.sh` | Deploy da API no App Runner |
| `04-create-rds.sh` | Cria instância RDS PostgreSQL |
| `05-enable-pgvector.sh` | Habilita extensão pgvector e cria database |
| `deploy-all.sh` | Executa todos os passos automaticamente |
| `cleanup.sh` | Remove todos os recursos criados |

---

## 🚀 Deploy Passo a Passo

### **Opção A: Deploy Automático (Recomendado)**

```bash
# 1. Tornar scripts executáveis
chmod +x aws-deploy/*.sh

# 2. Executar deploy completo
bash aws-deploy/deploy-all.sh
```

⏱️ **Tempo estimado:** 15-20 minutos

---

### **Opção B: Deploy Manual (Passo a Passo)**

#### **Passo 1: Setup Inicial**

```bash
bash aws-deploy/01-setup.sh
```

**O que este script faz:**
- ✅ Cria bucket S3 para artifacts
- ✅ Cria IAM Role para App Runner
- ✅ Cria repositórios ECR (API e Frontend)
- ✅ Cria Security Group para RDS
- ✅ Cria DB Parameter Group para pgvector

**Saída:** Arquivo `aws-deploy/.env.aws` com as configurações

---

#### **Passo 2: Build e Push das Imagens**

```bash
bash aws-deploy/02-build-push.sh
```

**O que este script faz:**
- ✅ Login no ECR
- ✅ Build da imagem da API
- ✅ Build da imagem do Frontend (se existir)
- ✅ Push das imagens para ECR

---

#### **Passo 3: Criar RDS PostgreSQL**

```bash
bash aws-deploy/04-create-rds.sh
```

**O que este script faz:**
- ✅ Cria DB Subnet Group
- ✅ Configura Security Group (porta 5432)
- ✅ Cria instância RDS PostgreSQL 15 (db.t3.micro)
- ✅ Aguarda instância ficar disponível

**⏱️ Tempo estimado:** 5-10 minutos

**🔐 Importante:** Salve a senha gerada!

---

#### **Passo 4: Habilitar pgvector**

```bash
bash aws-deploy/05-enable-pgvector.sh
```

**O que este script faz:**
- ✅ Testa conexão com RDS
- ✅ Habilita extensão pgvector
- ✅ Cria database `TEAChat_db`
- ✅ Executa scripts de schema (se existirem)

---

#### **Passo 5: Deploy no App Runner**

```bash
bash aws-deploy/03-deploy-apprunner.sh
```

**O que este script faz:**
- ✅ Cria configuração de auto-scaling
- ✅ Cria serviço no App Runner
- ✅ Configura health check
- ✅ Aguarda deploy ficar pronto

**⏱️ Tempo estimado:** 3-5 minutos

---

## 🧪 Testando o Deploy

### **1. Testar endpoint de health**

```bash
source aws-deploy/.env.aws
curl https://$APP_RUNNER_SERVICE_URL/health
```

**Resposta esperada:**
```json
{"status": "healthy"}
```

---

### **2. Testar API**

```bash
# Listar pacientes
curl https://$APP_RUNNER_SERVICE_URL/api/patients

# Criar paciente (exemplo)
curl -X POST https://$APP_RUNNER_SERVICE_URL/api/patients \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Patient", "email": "test@example.com"}'
```

---

## 📊 Monitoramento

### **Ver status do serviço**

```bash
aws apprunner describe-service \
  --service-name TEAChat-api \
  --region us-east-1
```

### **Ver logs em tempo real**

```bash
# Listar log groups
aws logs describe-log-groups \
  --log-group-name-prefix "/aws/apprunner/TEAChat-api" \
  --region us-east-1

# Ver logs (substitua <log-group-name>)
aws logs tail <log-group-name> --follow --region us-east-1
```

### **Ver operações do serviço**

```bash
SERVICE_ARN=$(aws apprunner list-services \
  --region us-east-1 \
  --query "Services[?ServiceName=='TEAChat-api'].ServiceArn" \
  --output text)

aws apprunner list-operations --service-arn $SERVICE_ARN --region us-east-1
```

---

## 💰 Custos Estimados (Mensal)

| Serviço | Configuração | Custo Aprox. |
|---------|-------------|--------------|
| App Runner | 1 vCPU, 2GB RAM | ~$50-70 |
| RDS | db.t3.micro, 20GB | ~$15-20 |
| ECR | 500MB | ~$0.50 |
| CloudWatch Logs | ~$1-2 |
| **Total** | | **~$65-95/mês** |

> 💡 **Dica:** Use `aws apprunner pause-service` para parar o serviço quando não estiver em uso (não cobra computação).

---

## ⏸️ Pausar e Retomar Serviço

### **Pausar (não cobra computação)**

```bash
SERVICE_ARN=$(aws apprunner list-services \
  --region us-east-1 \
  --query "Services[?ServiceName=='TEAChat-api'].ServiceArn" \
  --output text)

aws apprunner pause-service --service-arn $SERVICE_ARN --region us-east-1
```

### **Retomar**

```bash
aws apprunner resume-service --service-arn $SERVICE_ARN --region us-east-1
```

---

## 🗑️ Cleanup (Remover Tudo)

```bash
bash aws-deploy/cleanup.sh
```

**⚠️ Atenção:** Isso remove **todos** os recursos criados, incluindo:
- Serviço App Runner
- Instância RDS
- Repositórios ECR
- Security Groups
- IAM Roles
- Bucket S3

---

## 🔧 Troubleshooting

### **Erro: "AWS CLI não está configurado"**

```bash
aws configure
```

---

### **Erro: "psql não encontrado"**

```bash
sudo apt-get update && sudo apt-get install -y postgresql-client
```

---

### **Erro: "Acesso negado ao ECR"**

Verifique se a IAM Role tem as permissões corretas:

```bash
aws iam list-attached-role-policies --role-name TEAChat-apprunner-role
```

---

### **Erro: "RDS não aceita conexão"**

1. Verifique Security Group:
   ```bash
   aws ec2 describe-security-groups --group-ids $SG_ID --region us-east-1
   ```

2. Verifique se RDS está público:
   ```bash
   aws rds describe-db-instances \
     --db-instance-identifier TEAChat-postgres \
     --query 'DBInstances[0].PubliclyAccessible'
   ```

---

### **Erro: "pgvector não encontrado"**

```bash
# Conectar ao banco e verificar
psql -h $DB_ENDPOINT -U postgres -d TEAChat_db -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# Se não existir, habilitar
psql -h $DB_ENDPOINT -U postgres -d TEAChat_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## 📝 Variáveis de Ambiente

O deploy configura automaticamente as seguintes variáveis no App Runner:

| Variável | Valor |
|----------|-------|
| `DATABASE_URL` | PostgreSQL connection string |
| `HOST` | 0.0.0.0 |
| `PORT` | 8000 |
| `RAG_TOP_K` | 4 |
| `RAG_MIN_SIMILARITY` | 0.5 |

Variáveis adicionais (edite `.env.aws` antes do deploy):

| Variável | Descrição |
|----------|-----------|
| `GOOGLE_API_KEY` | API Key para Google AI (obrigatório) |
| `OPENAI_API_KEY` | API Key para OpenAI (opcional) |
| `SECRET_KEY` | Chave secreta para JWT (obrigatório) |

---

## 🔐 Segurança

### **Melhores Práticas**

1. **Nunca commitar credenciais**
   ```bash
   # Adicionar ao .gitignore
   aws-deploy/.env.aws
   .aws/credentials
   ```

2. **Usar AWS Secrets Manager** (produção)
   ```bash
   aws secretsmanager create-secret \
     --name TEAChat/credentials \
     --secret-string '{"GOOGLE_API_KEY": "...", "SECRET_KEY": "..."}'
   ```

3. **Restringir Security Group**
   ```bash
   # Em vez de 0.0.0.0/0, use o security group do App Runner
   aws ec2 authorize-security-group-ingress \
     --group-id $SG_ID \
     --protocol tcp \
     --port 5432 \
     --source-group sg-apprunner \
     --region us-east-1
   ```

4. **Habilitar encryption no RDS**
   ```bash
   # Criar RDS com encryption
   aws rds create-db-instance \
     ... \
     --storage-encrypted \
     --kms-key-id alias/aws/rds
   ```

---

## 📞 Suporte

Para mais informações:

- [Documentação AWS App Runner](https://docs.aws.amazon.com/apprunner/)
- [Documentação RDS PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [Documentação pgvector](https://github.com/pgvector/pgvector)

---

**Última atualização:** Fevereiro 2026
