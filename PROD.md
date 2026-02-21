# SYMYAH - Guia de Produção

> **Versão**: 1.0.0  
> **Finalidade**: Documentar arquivos e dependências essenciais para implantação em produção

---

## 📁 Estrutura de Arquivos para Produção

### ✅ Arquivos Essenciais (Raiz)

| Arquivo | Finalidade |
|---------|------------|
| `app.py` | API principal FastAPI |
| `anonimizer_functions.py` | Anonimização de dados sensíveis |
| `requirements.txt` | Dependências Python |
| `.env.example` | Template de variáveis de ambiente |
| `schema_update.sql` | Schema do banco de dados |

---

### ✅ Diretório `core/`

| Arquivo | Finalidade |
|---------|------------|
| `clinical_ai_system.py` | Orquestrador principal do sistema de IA |
| `rag_system.py` | Sistema RAG de recuperação de documentos |
| `gemini_interface.py` | Integração com Google Gemini API |
| `openai_interface.py` | Integração com OpenAI API (fallback) |
| `local_response_generator.py` | Geração de respostas local |
| `model_selector.py` | Seleção de modelos de IA |
| `user_knowledge_base.py` | Base de conhecimento do usuário |
| `alert_detector.py` | Detector de alertas clínicos |

---

### ✅ Diretório `database/`

| Arquivo | Finalidade |
|---------|------------|
| `db_manager.py` | Gerenciador de banco de dados PostgreSQL |
| `schema.sql` | Schema inicial do banco de dados |
| `metrics_schema.sql` | Schema para métricas de qualidade |

---

### ✅ Diretório `utils/`

| Arquivo | Finalidade |
|---------|------------|
| `embedding_generator.py` | Geração de embeddings com cache |
| `metrics_calculator.py` | Cálculo de métricas de qualidade |
| `response_formatter.py` | Formatação de respostas |
| `text_processor.py` | Processamento de texto |

---

### ✅ Diretório `analysis/`

| Arquivo | Finalidade |
|---------|------------|
| `__init__.py` | Inicialização do módulo |
| `clinical_evolution_analyzer.py` | Análise de evolução clínica |
| `data_classes.py` | Classes de dados |
| `evolution_metrics_calculator.py` | Calculadora de métricas de evolução |
| `smart_alerts_system.py` | Sistema de alertas inteligentes |
| `therapy_recommendation_agent.py` | Agente de recomendação terapêutica |

---

### ⚠️ Diretório `frontFlask/` (Opcional)

| Arquivo | Finalidade |
|---------|------------|
| `flask_frontend.py` | Frontend web Flask |
| `templates/*.html` | Templates HTML |
| `static/*` | Arquivos estáticos (CSS, JS, imagens) |
| `requirements_flask.txt` | Dependências do frontend |

> **Nota**: Este diretório é **opcional**. Remova se não for utilizar a interface web.

---

## 🗑️ O que NÃO incluir em Produção

| Arquivo/Diretório | Motivo |
|-------------------|--------|
| `testes/` | Apenas para desenvolvimento |
| `Dockerfile` | Apenas se não usar Docker |
| `docker-compose.yml` | Apenas se não usar Docker |
| `*.md` | Apenas documentação (exceto este arquivo) |
| `__pycache__/` | Cache Python (não versionar) |
| `env/` | Ambiente virtual (não versionar) |
| `.git/` | Controle de versão |
| `.qwen/` | Configurações do editor |
| `lora_tuner.py` | Apenas se usar fine-tuning LoRA |
| `local_embeddings.py` | Apenas se usar embeddings locais |
| `dataset_builder.py` | Apenas para construção de datasets |

---

## 📦 Estrutura de Diretórios Mínima

```
symyah-prod/
├── app.py
├── anonimizer_functions.py
├── requirements.txt
├── .env
├── schema_update.sql
│
├── core/
│   ├── clinical_ai_system.py
│   ├── rag_system.py
│   ├── gemini_interface.py
│   ├── openai_interface.py
│   ├── local_response_generator.py
│   ├── model_selector.py
│   ├── user_knowledge_base.py
│   └── alert_detector.py
│
├── database/
│   ├── db_manager.py
│   ├── schema.sql
│   └── metrics_schema.sql
│
├── utils/
│   ├── embedding_generator.py
│   ├── metrics_calculator.py
│   ├── response_formatter.py
│   └── text_processor.py
│
└── analysis/
    ├── __init__.py
    ├── clinical_evolution_analyzer.py
    ├── data_classes.py
    ├── evolution_metrics_calculator.py
    ├── smart_alerts_system.py
    └── therapy_recommendation_agent.py
```

---

## 🛠️ Dependências por Funcionalidade

| Funcionalidade | Módulos Necessários |
|----------------|---------------------|
| **API + RAG + Gemini** | `app.py`, `core/*`, `database/*`, `utils/embedding_generator.py` |
| **Anonimização** | `anonimizer_functions.py`, `utils/text_processor.py` |
| **Métricas de Qualidade** | `utils/metrics_calculator.py`, `analysis/*` |
| **Alertas Inteligentes** | `core/alert_detector.py`, `analysis/smart_alerts_system.py` |
| **Evolução Clínica** | `analysis/clinical_evolution_analyzer.py`, `analysis/evolution_metrics_calculator.py` |
| **Recomendação Terapêutica** | `analysis/therapy_recommendation_agent.py` |
| **Frontend Web** | `frontFlask/*` (opcional) |

---

## 🔧 Pré-requisitos do Sistema

### Dependências do Sistema Operacional

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    libpq-dev \
    libgomp1 \
    build-essential

# Fedora/RHEL
sudo dnf install -y \
    python3.11 \
    python3.11-devel \
    postgresql-devel \
    libgomp \
    gcc
```

### PostgreSQL + pgvector

```bash
# Instalar PostgreSQL
sudo apt-get install -y postgresql postgresql-contrib

# Instalar pgvector
cd /tmp
git clone --branch v0.7.0 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Habilitar extensão
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## 📋 Instalação em Produção

### 1. Criar ambiente virtual

```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 2. Instalar dependências Python

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

```bash
cp .env.example .env
nano .env
```

**Variáveis obrigatórias:**
```bash
GOOGLE_API_KEY=sua_chave_aqui
DATABASE_URL=postgresql://usuario:senha@localhost:5432/symyah_db
SECRET_KEY=sua_chave_secreta
```

### 4. Inicializar banco de dados

```bash
# Criar banco e usuário
sudo -u postgres psql -c "CREATE DATABASE symyah_db;"
sudo -u postgres psql -c "CREATE USER symyah_user WITH PASSWORD 'sua_senha';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE symyah_db TO symyah_user;"
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Executar schema
psql -U symyah_user -d symyah_db -f schema_update.sql
```

### 5. Iniciar aplicação

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## ⚠️ Considerações de Produção

| Item | Recomendação |
|------|--------------|
| **RAM** | Mínimo 8GB (recomendado 16GB+) |
| **CPU** | 4+ cores |
| **Disco** | 10GB+ para dependências e modelos |
| **GPU** | Opcional (acelera inferência) |
| **HTTPS** | Usar reverse proxy (nginx) |
| **Process Manager** | Usar systemd ou supervisor |
| **Backup** | Backup diário do PostgreSQL |

---

## 🔒 Segurança

- [ ] Alterar `SECRET_KEY` no `.env`
- [ ] Alterar senha do PostgreSQL
- [ ] Configurar firewall (porta 8000)
- [ ] Usar HTTPS em produção
- [ ] Não versionar `.env`
- [ ] Restringir CORS no `app.py`

---

## 📊 Monitoramento

Endpoints de saúde:
- `GET /` - Status da API
- `GET /health` - Health check (se implementado)

Logs:
- Verificar `stderr` e `stdout` do uvicorn
- Configurar log rotation

---

## 🔄 Atualização

```bash
# Parar aplicação
# Fazer backup do banco
# Atualizar código
git pull

# Reinstalar dependências
pip install -r requirements.txt --upgrade

# Aplicar migrations do banco
psql -U symyah_user -d symyah_db -f schema_update.sql

# Reiniciar aplicação
```

---

## 📞 Suporte

Para dúvidas sobre implantação, consulte:
- `README_PRODUCAO.md` - Guia completo de produção
- `DEPLOY.md` - Instruções de deploy
- `arquitetura.md` - Documentação da arquitetura
