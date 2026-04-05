# 📦 Resumo dos Arquivos de Deploy

Este arquivo lista **todos** os arquivos de deploy criados para o projeto Symyah.

---

## 📅 Resumo da Sessão - Fevereiro 2026

### ✅ O Que Foi Feito Hoje

| Etapa | Descrição |
|-------|-----------|
| 1 | Configuração do AWS CLI |
| 2 | Criação dos scripts de deploy manual (`aws-deploy/`) |
| 3 | Criação dos workflows do GitHub Actions (`.github/workflows/`) |
| 4 | Documentação completa (README, guias rápidos) |
| 5 | Configuração de CI/CD para deploy automático |

### 📁 Arquivos Criados

**Total: 15 arquivos**

- 8 scripts em `aws-deploy/`
- 5 arquivos em `.github/workflows/`
- 2 arquivos de documentação na raiz

### 🚀 Próximo Passo (Amanhã)

```bash
# 1. Verificar AWS CLI
aws sts get-caller-identity

# 2. Instalar postgresql-client
sudo apt-get install -y postgresql-client

# 3. Exportar variáveis
export GOOGLE_API_KEY="sua_key"
export SECRET_KEY="sua_secret"

# 4. Primeiro deploy manual
bash aws-deploy/deploy-all.sh

# 5. Configurar secrets no GitHub
```

---

---

## 🗂️ Estrutura Completa

```
/mnt/Dados/01 - MESTRADO/01 - MESTRADO - NOVA ABORDAGEM/01 - SYMYAH/Anderson_Configurado_BKP/
│
├── 📄 DEPLOY_AWS.md                      # Guia rápido de deploy na AWS
├── 📄 CI_CD_SETUP.md                     # Este arquivo (resumo geral)
│
├── 📁 aws-deploy/                        # Scripts de deploy manual
│   ├── README.md                         # Documentação completa
│   ├── 01-setup.sh                       # Setup inicial na AWS
│   ├── 02-build-push.sh                  # Build e push Docker
│   ├── 03-deploy-apprunner.sh            # Deploy no App Runner
│   ├── 04-create-rds.sh                  # Criação do RDS
│   ├── 05-enable-pgvector.sh             # Habilitar pgvector
│   ├── deploy-all.sh                     # Deploy automático (todos)
│   └── cleanup.sh                        # Remover recursos
│
└── 📁 .github/workflows/                 # GitHub Actions (CI/CD)
    ├── README.md                         # Documentação dos workflows
    ├── CONFIGURACAO_RAPIDA.md            # Guia rápido de configuração
    ├── deploy-aws.yml                    # Workflow de deploy automático
    ├── ci-tests.yml                      # Workflow de testes
    └── secrets.example                   # Exemplo de secrets
```

---

## 📋 Arquivos Principais

### **1. Deploy Manual (aws-deploy/)**

| Arquivo | Descrição | Tempo |
|---------|-----------|-------|
| `01-setup.sh` | Cria recursos iniciais na AWS | 1 min |
| `02-build-push.sh` | Build e push das imagens Docker | 3-5 min |
| `03-deploy-apprunner.sh` | Deploy no App Runner | 3-5 min |
| `04-create-rds.sh` | Cria RDS PostgreSQL | 5-10 min |
| `05-enable-pgvector.sh` | Habilita pgvector no banco | 1 min |
| `deploy-all.sh` | **Executa tudo automaticamente** | 15-20 min |
| `cleanup.sh` | Remove todos os recursos | 2-3 min |

---

### **2. Deploy Automático (.github/workflows/)**

| Arquivo | Descrição | Gatilho |
|---------|-----------|---------|
| `deploy-aws.yml` | Deploy automático em produção | Push na main |
| `ci-tests.yml` | Testes e validação | Pull Request |

---

## 🚀 Fluxos de Trabalho

### **Fluxo 1: Deploy Manual Inicial**

```bash
# Primeiro deploy (cria todos os recursos)
bash aws-deploy/deploy-all.sh
```

**Quando usar:** Primeira vez, ou quando precisar criar recursos do zero.

---

### **Fluxo 2: Deploy Automático (CI/CD)**

```
git push origin main
      │
      ▼
GitHub Actions (automático)
      │
      ▼
Build → ECR → App Runner
```

**Quando usar:** Após cada commit na branch main.

---

### **Fluxo 3: Deploy de Emergência**

```bash
# Rollback para versão anterior
docker tag symyah-api:previous symyah-api:latest
docker push <ECR_URI>:latest

# Ou via AWS Console
# App Runner → Service → Update → Selecionar imagem anterior
```

---

## 🔑 Secrets Necessários

### **No GitHub (7 secrets)**

| Nome | Descrição | Obrigatório |
|------|-----------|-------------|
| `AWS_ACCESS_KEY_ID` | Access Key da AWS | ✅ |
| `AWS_SECRET_ACCESS_KEY` | Secret Access Key | ✅ |
| `AWS_REGION` | Região (us-east-1) | ✅ |
| `DATABASE_URL` | Connection string do RDS | ✅ |
| `GOOGLE_API_KEY` | API Key Google AI | ✅ |
| `SECRET_KEY` | Chave secreta JWT | ✅ |
| `OPENAI_API_KEY` | API Key OpenAI | ⚠️ Opcional |

---

## 💰 Custos Estimados

| Serviço | Custo Mensal |
|---------|-------------|
| App Runner (1 vCPU, 2GB) | ~$50-70 |
| RDS (db.t3.micro, 20GB) | ~$15-20 |
| ECR (500MB) | ~$0.50 |
| CloudWatch Logs | ~$1-2 |
| GitHub Actions | Grátis (2000 min/mês) |
| **Total** | **~$65-95/mês** |

---

## ⏱️ Tempos de Deploy

| Tipo | Tempo |
|------|-------|
| Primeiro deploy (manual) | 15-20 min |
| Deploy automático (CI/CD) | 5-8 min |
| Rollback | 2-3 min |

---

## 📊 Comandos Úteis

### **Deploy**

```bash
# Deploy completo manual
bash aws-deploy/deploy-all.sh

# Deploy passo a passo
bash aws-deploy/01-setup.sh
bash aws-deploy/02-build-push.sh
bash aws-deploy/04-create-rds.sh
bash aws-deploy/05-enable-pgvector.sh
bash aws-deploy/03-deploy-apprunner.sh
```

---

### **Monitoramento**

```bash
# Status do App Runner
aws apprunner describe-service \
  --service-name symyah-api \
  --region us-east-1

# Logs em tempo real
aws logs tail /aws/apprunner/symyah-api --follow

# URL do serviço
aws apprunner describe-service \
  --service-name symyah-api \
  --region us-east-1 \
  --query Service.ServiceUrl --output text
```

---

### **Cleanup**

```bash
# Remover tudo
bash aws-deploy/cleanup.sh

# Remover apenas App Runner
SERVICE_ARN=$(aws apprunner list-services \
  --region us-east-1 \
  --query "Services[?ServiceName=='symyah-api'].ServiceArn" \
  --output text)
aws apprunner delete-service --service-arn $SERVICE_ARN
```

---

## 🔍 Troubleshooting Rápido

| Problema | Solução |
|----------|---------|
| "Service not found" | Execute `deploy-all.sh` primeiro |
| "No credentials" | Configure secrets no GitHub |
| "ECR not found" | Execute `01-setup.sh` |
| "Health check failed" | Verifique logs do App Runner |
| "Permission denied" | Verifique IAM policies |

---

## 📞 Documentação Completa

| Documento | Local |
|-----------|-------|
| Guia de Deploy AWS | `DEPLOY_AWS.md` |
| Documentação Completa | `aws-deploy/README.md` |
| Configuração CI/CD | `.github/workflows/README.md` |
| Configuração Rápida | `.github/workflows/CONFIGURACAO_RAPIDA.md` |

---

## ✅ Checklist de Implantação

### **Primeira Vez**

- [ ] AWS CLI instalado e configurado
- [ ] Docker instalado
- [ ] PostgreSQL client instalado
- [ ] Variáveis de ambiente exportadas
- [ ] Executar `bash aws-deploy/deploy-all.sh`
- [ ] Testar health check
- [ ] Configurar secrets no GitHub
- [ ] Testar deploy automático

### **Deploys Seguintes**

- [ ] Fazer commit na main
- [ ] Push para GitHub
- [ ] Acompanhar Actions no GitHub
- [ ] Testar endpoint após deploy

---

## 🎯 Próximos Passos

1. **Leia** `DEPLOY_AWS.md` para visão geral
2. **Execute** `bash aws-deploy/deploy-all.sh` para primeiro deploy
3. **Configure** secrets no GitHub
4. **Teste** deploy automático com um commit

---

**Última atualização:** Fevereiro 2026
