# ⚙️ Configuração do CI/CD - Guia Rápido

Este guia mostra como configurar o deploy automático em **5 minutos**.

---

## 📋 Checklist de Configuração

### **1. AWS - Criar Usuário IAM (2 minutos)**

```bash
# Ou via Console AWS:
# IAM → Users → Create user → symyah-deployer

aws iam create-user --user-name symyah-deployer

# Anexar políticas
aws iam attach-user-policy \
  --user-name symyah-deployer \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

> ⚠️ **Nota:** Para produção, use políticas mais restritivas.

---

### **2. AWS - Criar Access Keys (1 minuto)**

```bash
# Criar chaves de acesso
aws iam create-access-key --user-name symyah-deployer

# Saída:
# {
#   "AccessKey": {
#     "AccessKeyId": "AKIA...",
#     "SecretAccessKey": "..."
#   }
# }
```

🔐 **Salve estas credenciais!** Elas só aparecem uma vez.

---

### **3. GitHub - Adicionar Secrets (2 minutos)**

1. Vá até seu repositório no GitHub
2. **Settings** → **Secrets and variables** → **Actions**
3. **New repository secret**

Adicione estes secrets:

| Nome | Valor |
|------|-------|
| `AWS_ACCESS_KEY_ID` | `AKIA...` (do passo 2) |
| `AWS_SECRET_ACCESS_KEY` | `wJalr...` (do passo 2) |
| `AWS_REGION` | `us-east-1` |
| `DATABASE_URL` | `postgresql://postgres:senha@endpoint.rds.amazonaws.com:5432/symyah_db` |
| `GOOGLE_API_KEY` | `sua_google_api_key` |
| `SECRET_KEY` | `sua_secret_key` |
| `OPENAI_API_KEY` | `sua_openai_key` (opcional) |

---

### **4. GitHub - Configurar Environment (Opcional - 1 minuto)**

1. **Settings** → **Environments**
2. **New environment**
3. Nome: `production`
4. (Opcional) Adicione revisores

---

### **5. Primeiro Deploy Manual (10-15 minutos)**

Antes do deploy automático, faça o primeiro deploy manual:

```bash
# 1. Tornar scripts executáveis
chmod +x aws-deploy/*.sh

# 2. Executar deploy completo
bash aws-deploy/deploy-all.sh
```

Isso cria:
- ✅ Repositórios ECR
- ✅ Instância RDS
- ✅ Serviço App Runner

---

## ✅ Testando o Deploy Automático

Após configurar tudo:

```bash
# 1. Fazer uma alteração no código
echo "# Teste" >> README.md

# 2. Commit e push
git add .
git commit -m "Teste de deploy automático"
git push origin main

# 3. Acompanhar no GitHub
# Actions → Deploy para AWS App Runner → Ver execução
```

---

## 🔍 Verificando o Deploy

### **No GitHub**

1. Abra a aba **Actions**
2. Clique no workflow em execução
3. Veja o log de cada job

### **Na AWS**

```bash
# Ver status do App Runner
aws apprunner describe-service \
  --service-name symyah-api \
  --region us-east-1

# Ver URL do serviço
aws apprunner describe-service \
  --service-name symyah-api \
  --region us-east-1 \
  --query Service.ServiceUrl --output text

# Testar health check
curl https://$(aws apprunner describe-service \
  --service-name symyah-api \
  --region us-east-1 \
  --query Service.ServiceUrl --output text)/health
```

---

## 🚨 Problemas Comuns

### **"Service not found"**

O App Runner ainda não foi criado. Execute:

```bash
bash aws-deploy/deploy-all.sh
```

---

### **"No credentials found"**

Verifique os secrets no GitHub:

1. **Settings** → **Secrets and variables** → **Actions**
2. Confirme que `AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY` existem
3. Verifique se não há espaços ou quebras de linha

---

### **"ECR repository not found"**

Execute o setup:

```bash
bash aws-deploy/01-setup.sh
```

---

### **"Permission denied"**

Verifique as permissões do usuário IAM:

```bash
aws iam list-attached-user-policies --user-name symyah-deployer
```

Deve ter pelo menos:
- `AdministratorAccess` (ou políticas equivalentes)

---

## 📊 Fluxo do Deploy Automático

```
Push na main ──▶ GitHub Actions ──▶ Build Docker ──▶ ECR ──▶ App Runner
   │                                                        │
   │                                                        ▼
   │                                               Health Check
   │                                                        │
   ▼                                                        ▼
Commit                       ✅ Sucesso ou ❌ Falha (notificação)
```

---

## 🎯 Próximos Passos

1. ✅ Configurar secrets no GitHub
2. ✅ Fazer primeiro deploy manual
3. ✅ Testar push na main
4. ✅ Monitorar primeiro deploy automático

---

## 📞 Links Úteis

- [GitHub Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [AWS IAM Users](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users_create.html)
- [App Runner Console](https://console.aws.amazon.com/apprunner/)

---

**Tempo total de configuração:** ~5-10 minutos  
**Primeiro deploy:** ~15-20 minutos

---

**Última atualização:** Fevereiro 2026
