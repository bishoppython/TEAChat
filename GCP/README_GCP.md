# 🚀 Deploy no Google Cloud Platform (GCP) — Free Tier

**TEAChat / SYMYAH** — Sistema de IA para Psicologia Clínica

---

## 📁 Estrutura desta pasta

```
GCP/
├── Dockerfile.cloudrun    # Dockerfile ajustado para Cloud Run (porta 8080, 1 worker)
├── cloudbuild.yaml        # Pipeline Cloud Build: build → push → deploy
├── deploy-gcp.yml         # GitHub Actions: CI/CD automático no push para main
├── setup-gcp.sh           # Script de setup inicial (primeira vez)
├── .env.gcp.example       # Template de variáveis de ambiente
└── README_GCP.md          # Este arquivo
```

---

## 🏗️ Arquitetura

```
GitHub (push main)
       │
       ▼
GitHub Actions (deploy-gcp.yml)
       │  Build Docker image
       │  Push → Artifact Registry
       ▼
Cloud Run (Dockerfile.cloudrun)
   FastAPI + Uvicorn
   Porto 8080 | 512Mi RAM | 1 vCPU
       │
       ├── Secret Manager ──── OPENAI_API_KEY
       │                  ├── GOOGLE_API_KEY
       │                  ├── DATABASE_URL
       │                  └── SECRET_KEY
       │
       └── Neon.tech ──── PostgreSQL + pgvector (Free Tier externo)
```

---

## ⚡ Setup Inicial (Primeira vez)

### Pré-requisitos
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) instalado
- Conta GCP com projeto criado
- Docker instalado
- URL do banco Neon.tech em mãos

### Opção A: Script automático (recomendado)

```bash
# 1. Editar as variáveis no script
nano GCP/setup-gcp.sh

# 2. Dar permissão de execução e rodar
chmod +x GCP/setup-gcp.sh
bash GCP/setup-gcp.sh
```

### Opção B: Manual passo a passo

```bash
# 1. Autenticar
gcloud auth login
gcloud config set project SEU_PROJECT_ID

# 2. Habilitar APIs
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
    cloudbuild.googleapis.com secretmanager.googleapis.com

# 3. Criar repositório de imagens
gcloud artifacts repositories create teachat \
    --repository-format=docker \
    --location=us-central1

# 4. Criar secrets
echo -n "sk-sua-openai-key" | gcloud secrets create OPENAI_API_KEY --data-file=-
echo -n "sua-google-key"    | gcloud secrets create GOOGLE_API_KEY --data-file=-
echo -n "postgresql://..."  | gcloud secrets create DATABASE_URL --data-file=-
echo -n "$(openssl rand -hex 32)" | gcloud secrets create SECRET_KEY --data-file=-

# 5. Build e deploy (via Cloud Build)
gcloud builds submit --config=GCP/cloudbuild.yaml .
```

---

## 🔄 Deploy Manual (deploys subsequentes)

```bash
# Na raiz do projeto:
gcloud builds submit --config=GCP/cloudbuild.yaml --project=SEU_PROJECT_ID .
```

---

## 🤖 CI/CD Automático (GitHub Actions)

Ao fazer push para o branch `main`, o deploy é automático.

### Configurar secrets no GitHub

Vá em **Settings → Secrets and variables → Actions** e adicione:

| Secret | Valor |
|---|---|
| `GCP_PROJECT_ID` | ID do seu projeto GCP |
| `GCP_SA_KEY` | JSON da Service Account (ver abaixo) |

### Criar Service Account para o GitHub Actions

```bash
export PROJECT_ID="SEU_PROJECT_ID"
export SA_NAME="github-actions-sa"

# Criar service account
gcloud iam service-accounts create $SA_NAME \
    --display-name="GitHub Actions Deploy SA"

# Conceder permissões necessárias
for ROLE in roles/run.admin roles/storage.admin roles/artifactregistry.admin roles/iam.serviceAccountUser roles/secretmanager.secretAccessor; do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="$ROLE"
done

# Gerar chave JSON (colar no secret GCP_SA_KEY do GitHub)
gcloud iam service-accounts keys create gcp-sa-key.json \
    --iam-account="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

cat gcp-sa-key.json  # cole este conteúdo no secret do GitHub
rm gcp-sa-key.json   # remover após usar!
```

---

## 💰 Custos (Free Tier)

| Serviço | Uso estimado | Custo |
|---|---|---|
| Cloud Run | < 2M req/mês, escala para 0 | **$0** |
| Artifact Registry | < 0.5 GB | **$0** |
| Cloud Build | < 120 min/dia | **$0** |
| Secret Manager | 4 secrets, < 10K acessos | **$0** |
| Neon.tech | PostgreSQL + pgvector | **$0** |
| **Total** | | **$0/mês** |

---

## 🔍 Verificar o deploy

```bash
# Ver URL do serviço
gcloud run services describe teachat-api --region=us-central1 --format="value(status.url)"

# Ver logs em tempo real
gcloud run services logs tail teachat-api --region=us-central1

# Testar health check
curl https://SEU-SERVICO-URL/health
```

---

## ⚠️ Diferenças do ambiente local

| Característica | Local (Docker Compose) | GCP (Cloud Run) |
|---|---|---|
| Porta | 8000 | **8080** |
| Workers | 2 | **1** (escala horizontal) |
| PostgreSQL | Container local | **Neon.tech** (externo) |
| Secrets | Arquivo `.env` | **Secret Manager** |
| Escala | Manual | **Automática (0 a 2)** |
| Estado | Persistente | **Stateless** |
