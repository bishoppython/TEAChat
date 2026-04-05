# 🔄 CI/CD - GitHub Actions para AWS

Este documento descreve como configurar o deploy automático usando **GitHub Actions** e **AWS App Runner**.

---

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Workflows Criados](#workflows-criados)
- [Configuração dos Secrets](#configuração-dos-secrets)
- [Como Funciona](#como-funciona)
- [Gatilhos](#gatilhos)
- [Monitorando o Deploy](#monitorando-o-deploy)
- [Troubleshooting](#troubleshooting)

---

## Visão Geral

```
┌─────────────────────────────────────────────────────────────────┐
│                         GitHub                                  │
│                                                                 │
│  📝 Push/Commit (main) ──────┐                                 │
│                               ▼                               │
│  ┌─────────────────────────────────────────────────┐         │
│  │           GitHub Actions Workflow               │         │
│  │                                                 │         │
│  │  1. Checkout do código                          │         │
│  │  2. Build da imagem Docker                      │         │
│  │  3. Push para Amazon ECR                        │         │
│  │  4. Atualizar App Runner                        │         │
│  └─────────────────────────────────────────────────┘         │
│                               │                               │
└───────────────────────────────┼───────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                           AWS                                   │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │     ECR      │───▶│  App Runner  │───▶│   Internet   │     │
│  │  (imagem)    │    │   (deploy)   │    │  (HTTPS)     │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Workflows Criados

| Arquivo | Descrição | Gatilho |
|---------|-----------|---------|
| `deploy-aws.yml` | Deploy automático em produção | Push na `main` |
| `ci-tests.yml` | Testes e validação | Pull Request / branches dev |

---

## Configuração dos Secrets

### **Passo 1: Acessar Settings do Repositório**

1. Vá até seu repositório no GitHub
2. Clique em **Settings** (⚙️)
3. No menu lateral, clique em **Secrets and variables** → **Actions**

---

### **Passo 2: Adicionar Secrets da AWS**

Clique em **New repository secret** e adicione:

| Nome do Secret | Valor | Descrição |
|----------------|-------|-----------|
| `AWS_ACCESS_KEY_ID` | `AKIA...` | Access Key da AWS |
| `AWS_SECRET_ACCESS_KEY` | `wJalr...` | Secret Access Key |
| `AWS_REGION` | `us-east-1` | Região da AWS |

---

### **Passo 3: Adicionar Secrets da Aplicação**

| Nome do Secret | Valor | Descrição |
|----------------|-------|-----------|
| `DATABASE_URL` | `postgresql://...` | Connection string do RDS |
| `GOOGLE_API_KEY` | `sua_key` | API Key do Google AI |
| `SECRET_KEY` | `sua_secret` | Chave secreta para JWT |
| `OPENAI_API_KEY` | `sua_key` | API Key do OpenAI (opcional) |

---

### **Passo 4: Criar Environment (Opcional)**

Para maior segurança, crie um environment:

1. Em **Settings** → **Environments**
2. Clique em **New environment**
3. Nome: `production`
4. (Opcional) Adicione revisores ou branches de deploy

---

## Como Funciona

### **Workflow: Deploy para AWS**

```yaml
📝 Push na branch main
       │
       ▼
┌──────────────────┐
│ 1. Checkout      │ ← Baixa o código
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 2. AWS Credentials│ ← Configura acesso
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 3. Login ECR     │ ← Autentica no ECR
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 4. Build Docker  │ ← Compila imagem
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 5. Push ECR      │ ← Envia imagem
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 6. Update App    │ ← Atualiza deploy
│    Runner        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 7. Health Check  │ ← Testa endpoint
└──────────────────┘
```

---

## Gatilhos

### **Deploy Automático (deploy-aws.yml)**

| Evento | Branch | Descrição |
|--------|--------|-----------|
| `push` | `main`, `master` | Deploy automático |
| `workflow_dispatch` | - | Acionamento manual |

### **CI Tests (ci-tests.yml)**

| Evento | Branch | Descrição |
|--------|--------|-----------|
| `pull_request` | `main`, `master`, `develop` | Validação de PR |
| `push` | `develop`, `dev`, `feature/**` | Testes em dev |

---

## Monitorando o Deploy

### **No GitHub**

1. Vá até a aba **Actions** do repositório
2. Clique no workflow em execução
3. Veja o log de cada job em tempo real

```
┌────────────────────────────────────────┐
│  📊 Actions · Deploy para AWS App Run  │
├────────────────────────────────────────┤
│  ✅ build-and-push-api         2m 15s  │
│  ✅ deploy-apprunner           3m 42s  │
│  ✅ notify                       5s    │
└────────────────────────────────────────┘
```

---

### **Logs Detalhados**

Cada etapa tem logs detalhados:

```
✅ Checkout do código
   └─ 📄 Ver: https://github.com/.../commit/abc123

✅ Configurar AWS Credentials
   └─ 🔐 Account ID: 123456789012

✅ Login no Amazon ECR
   └─ 🐳 Login succeeded

✅ Build da imagem Docker
   └─ 🔨 Step 1/15: FROM python:3.11-slim
   └─ 🔨 Step 2/15: WORKDIR /app
   ...
   └─ ✅ Successfully built abc123def456

✅ Push da imagem para o ECR
   └─ 📤 The push refers to repository [...]

✅ Atualizar App Runner
   └─ 🚀 Service update initiated

✅ Health Check
   └─ 🧪 HTTP 200 OK
```

---

### **Na AWS**

```bash
# Ver status do App Runner
aws apprunner describe-service \
  --service-arn arn:aws:apprunner:us-east-1:ACCOUNT:service/symyah-api/XXX \
  --region us-east-1

# Ver operações recentes
aws apprunner list-operations \
  --service-arn arn:aws:apprunner:us-east-1:ACCOUNT:service/symyah-api/XXX \
  --region us-east-1

# Ver logs do App Runner
aws logs tail /aws/apprunner/symyah-api --follow --region us-east-1
```

---

## Acionamento Manual

Você pode acionar o deploy manualmente:

1. Vá em **Actions** → **Deploy para AWS App Runner**
2. Clique em **Run workflow**
3. Selecione a branch
4. Clique em **Run workflow**

---

## Status do Deploy

### **Sucesso**

```
✅ Deploy para AWS App Runner
   ✅ build-and-push-api (2m 15s)
   ✅ deploy-apprunner (3m 42s)
   ✅ notify (5s)
```

### **Falha**

```
❌ Deploy para AWS App Runner
   ✅ build-and-push-api (2m 15s)
   ❌ deploy-apprunner (1m 30s)
   ✅ notify (5s)
```

Clique no job falho para ver o erro.

---

## Troubleshooting

### **Erro: "No credentials found"**

**Solução:**
1. Verifique se os secrets estão configurados
2. Vá em **Settings** → **Secrets and variables** → **Actions**
3. Confirme que `AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY` existem

---

### **Erro: "Service not found"**

**Solução:**
O serviço App Runner ainda não existe. Execute o deploy manual primeiro:

```bash
bash aws-deploy/deploy-all.sh
```

---

### **Erro: "ECR repository not found"**

**Solução:**
Execute o script de setup para criar os repositórios:

```bash
bash aws-deploy/01-setup.sh
```

---

### **Erro: "Health check failed"**

**Causas possíveis:**
- API demorou para iniciar
- Endpoint `/health` não existe
- Erro na aplicação

**Solução:**
1. Verifique os logs do App Runner
2. Teste localmente: `curl http://localhost:8000/health`
3. Ajuste o timeout no workflow se necessário

---

### **Erro: "Permission denied"**

**Solução:**
Verifique as permissões da IAM Role:

```bash
aws iam list-attached-role-policies \
  --role-name symyah-apprunner-role
```

Políticas necessárias:
- `AWSAppRunnerServicePolicyForECRAccess`
- `CloudWatchLogsFullAccess`

---

## 📊 Métricas do Workflow

| Métrica | Valor |
|---------|-------|
| Tempo médio (build) | 2-3 minutos |
| Tempo médio (deploy) | 3-5 minutos |
| Total | 5-8 minutos |

---

## 🔒 Boas Práticas

| Prática | Descrição |
|---------|-----------|
| **Secrets** | Nunca commitar credenciais |
| **Environment** | Usar environments para produção |
| **Branch protection** | Proteger branch main |
| **Required reviewers** | Exigir aprovação para deploy |
| **Rollback** | Manter versões anteriores no ECR |

---

## 🎯 Próximos Passos

1. **Configurar secrets** no GitHub
2. **Fazer primeiro deploy manual** (para criar recursos)
3. **Testar workflow** com um commit
4. **Monitorar** primeiro deploy automático

---

## 📞 Links Úteis

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [AWS Credentials Action](https://github.com/aws-actions/configure-aws-credentials)
- [Amazon ECR Login Action](https://github.com/aws-actions/amazon-ecr-login)
- [App Runner API](https://docs.aws.amazon.com/apprunner/)

---

**Última atualização:** Fevereiro 2026
