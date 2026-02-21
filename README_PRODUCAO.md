# SYMYAH - Sistema de IA para Psicologia Clínica

> **Versão**: 1.0.0  
> **Status**: Produção

Sistema RAG (Retrieval-Augmented Generation) com integração Google Gemini e OpenAI para assistência em psicologia clínica e psicopedagogia.

---

## 📋 Propósito do Projeto

O **SYMYAH** é um sistema de inteligência artificial projetado para auxiliar psicólogos clínicos e psicopedagogos no:

- **Gestão de Pacientes**: Armazenamento e organização de informações clínicas
- **Recuperação Inteligente**: Busca semântica em documentos clínicos usando embeddings vetoriais
- **Geração de Respostas**: Produção de respostas contextualizadas baseadas em dados do paciente
- **Anonimização de Dados**: Proteção automática de informações sensíveis (CPF, e-mail, telefone, etc.)
- **Alertas Inteligentes**: Detecção proativa de padrões clínicos relevantes
- **Acompanhamento Evolutivo**: Análise de progresso terapêutico ao longo do tempo

---

## 🏗️ Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Flask                           │
│              (Interface Web do Usuário)                     │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP/REST API
┌─────────────────────▼───────────────────────────────────────┐
│                   Backend FastAPI                           │
│  • Autenticação JWT  • Endpoints REST  • Upload de Arquivos │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│               Core - Sistema de IA Clínica                  │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │   RAG System │  │  Gemini API  │  │  OpenAI Fallback│   │
│  └──────────────┘  └──────────────┘  └─────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │  Alertas     │  │  Anonimização│  │  Métricas       │   │
│  │  Inteligentes│  │  de Dados    │  │  de Qualidade   │   │
│  └──────────────┘  └──────────────┘  └─────────────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│          PostgreSQL + pgvector (Banco de Dados)             │
│  • users  • patients  • documents  • audit_log  • history  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Stack Tecnológico

### Backend
| Tecnologia | Versão | Finalidade |
|------------|--------|------------|
| **Python** | 3.9+ | Linguagem principal |
| **FastAPI** | latest | Framework API REST |
| **PostgreSQL** | 14+ | Banco de dados relacional |
| **pgvector** | 0.5+ | Busca por similaridade vetorial |

### IA & Processamento
| Tecnologia | Finalidade |
|------------|------------|
| **Google Gemini API** | Embeddings e geração de respostas (primário) |
| **OpenAI API** | Fallback para embeddings |
| **LangChain** | Orquestração de pipelines RAG |
| **Sentence Transformers** | Embeddings locais (fallback) |
| **PyTorch** | Inferência de modelos |

### Frontend
| Tecnologia | Finalidade |
|------------|------------|
| **Flask** | Servidor web da interface |
| **Bootstrap 5** | Framework CSS responsivo |
| **Jinja2** | Templates HTML |
| **Plotly** | Visualizações e gráficos |

### Segurança & Utilidades
| Tecnologia | Finalidade |
|------------|------------|
| **PyJWT** | Autenticação com tokens JWT |
| **Passlib + Argon2** | Hash de senhas |
| **NLTK** | Processamento de linguagem para anonimização |
| **PyPDF2, python-docx** | Leitura de documentos |

---

## 📦 Estrutura de Arquivos para Produção

### ✅ Arquivos Essenciais (Produção)

```
Anderson_Configurado_BKP/
├── app.py                          # API principal FastAPI
├── requirements.txt                # Dependências Python
├── .env.example                    # Template de variáveis de ambiente
├── anonimizer_functions.py         # Anonimização de dados sensíveis
│
├── core/                           # Lógica principal do sistema
│   ├── clinical_ai_system.py       # Sistema integrador de IA
│   ├── rag_system.py               # Sistema de recuperação RAG
│   ├── gemini_interface.py         # Interface Google Gemini
│   ├── openai_interface.py         # Interface OpenAI
│   ├── model_selector.py           # Seleção automática de modelos
│   ├── user_knowledge_base.py      # Base de conhecimento do usuário
│   ├── local_response_generator.py # Geração local de respostas
│   ├── alert_detector.py           # Detector de alertas inteligentes
│   └── lora_tuner.py               # Ajuste fino LoRA (opcional)
│
├── database/                       # Camada de dados
│   ├── db_manager.py               # Gerenciador de banco de dados
│   ├── schema.sql                  # Esquema do banco
│   └── metrics_schema.sql          # Esquema de métricas
│
├── utils/                          # Utilitários
│   ├── embedding_generator.py      # Geração de embeddings (multi-modelo)
│   ├── metrics_calculator.py       # Cálculo de métricas de qualidade
│   ├── text_processor.py           # Processamento de texto
│   └── response_formatter.py       # Formatação de respostas
│
├── analysis/                       # Análise clínica
│   ├── __init__.py
│   ├── clinical_evolution_analyzer.py  # Análise de evolução
│   ├── evolution_metrics_calculator.py # Métricas de evolução
│   ├── smart_alerts_system.py      # Sistema de alertas
│   ├── therapy_recommendation_agent.py # Recomendações terapêuticas
│   └── data_classes.py             # Classes de dados
│
└── frontFlask/                     # Frontend web
    ├── flask_frontend.py           # Servidor Flask
    ├── requirements_flask.txt      # Dependências do Flask
    ├── templates/                  # Templates HTML
    └── static/                     # Arquivos estáticos (CSS, JS, imgs)
```

### ❌ Arquivos de Desenvolvimento (NÃO incluir em Produção)

| Arquivo | Motivo |
|---------|--------|
| `test_*.py` | Scripts de teste unitário |
| `fix_*.py` | Scripts de correção pontual |
| `check_*.py` | Scripts de verificação de schema |
| `ensure_tables.py` | Setup inicial de tabelas |
| `setup_db.py` | Configuração de banco de dados |
| `demo_*.py` | Demonstrações |
| `investigate_issue.py` | Debug de issues |
| `direct_schema_update.py` | Migração de schema |
| `update_*.py` | Scripts de atualização |
| `verify_schema.py` | Verificação de schema |
| `recreate_documents_table.py` | Recriação de tabelas |
| `testes/` | Diretório de testes |
| `__pycache__/` | Cache Python (gerado automaticamente) |
| `env/` | Ambiente virtual local |

---

## 🚀 Instalação para Produção

### Pré-requisitos

- **Python 3.9 ou superior**
- **PostgreSQL 14+** com extensão **pgvector**
- **Google API Key** (obrigatória)
- **OpenAI API Key** (opcional, recomendado para fallback)

### Passo 1: Clonar o Repositório

```bash
git clone <url-do-repositorio>
cd Anderson_Configurado_BKP
```

### Passo 2: Criar Ambiente Virtual

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### Passo 3: Instalar Dependências

```bash
# Dependências do backend
pip install -r requirements.txt

# Dependências do frontend (opcional)
pip install -r frontFlask/requirements_flask.txt
```

### Passo 4: Configurar PostgreSQL com pgvector

**Opção A - Docker (Recomendado):**

```bash
docker run -d \
  --name postgres-symyah \
  -e POSTGRES_PASSWORD=sua_senha_forte \
  -e POSTGRES_DB=symyah_db \
  -p 5432:5432 \
  ankane/pgvector:latest
```

**Opção B - Instalação Nativa (Ubuntu/Debian):**

```bash
# Instalar PostgreSQL
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Instalar pgvector
sudo apt-get install postgresql-server-dev-all
cd /tmp
git clone --branch v0.7.0 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Criar banco de dados
sudo -u postgres psql -c "CREATE DATABASE symyah_db;"
sudo -u postgres psql -d symyah_db -c "CREATE EXTENSION vector;"
```

### Passo 5: Configurar Variáveis de Ambiente

```bash
cp .env.example .env
```

Edite o arquivo `.env`:

```bash
# Google API Key (obrigatória)
GOOGLE_API_KEY=sua_chave_google_aqui

# OpenAI API Key (opcional, recomendado)
OPENAI_API_KEY=sua_chave_openai_aqui

# Database Configuration
DATABASE_URL=postgresql://usuario:senha@localhost:5432/symyah_db

# Configurações do Servidor
HOST=0.0.0.0
PORT=8000

# Configurações RAG
RAG_TOP_K=4
RAG_MIN_SIMILARITY=0.5
CHUNK_SIZE=500
CHUNK_OVERLAP=50

# Segurança (mude em produção!)
SECRET_KEY=sua_chave_secreta_forte_aqui
```

### Passo 6: Inicializar o Banco de Dados

```bash
# Conectar ao banco e aplicar o schema
psql -h localhost -U usuario -d symyah_db -f database/schema.sql
psql -h localhost -U usuario -d symyah_db -f database/metrics_schema.sql
```

---

## ▶️ Executando o Sistema

### Backend (API FastAPI)

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Iniciar servidor API
python app.py

# Ou usando uvicorn diretamente
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

**A API estará disponível em:** `http://localhost:8000`

**Documentação Swagger:** `http://localhost:8000/docs`

### Frontend (Flask)

```bash
# Navegar até o diretório do frontend
cd frontFlask

# Iniciar servidor Flask
python flask_frontend.py

# Ou usar o script de inicialização
./run_flask.sh
```

**O frontend estará disponível em:** `http://localhost:5000`

---

## 🔌 Endpoints da API

### Autenticação

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/login` | POST | Autenticar usuário |
| `/register` | POST | Registrar novo usuário |
| `/refresh` | POST | Renovar token de acesso |
| `/logout` | POST | Invalidar sessão |

### Consultas

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/query` | POST | Consultar sistema de IA |
| `/patient_profile` | POST | Obter perfil do paciente |
| `/assessment` | POST | Realizar avaliação clínica |

### Documentos

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/add_document` | POST | Adicionar documento clínico |
| `/upload_document` | POST | Upload de arquivo (PDF, DOCX, etc.) |
| `/history/documents` | GET | Listar histórico de documentos |

### Pacientes

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/patient/create` | POST | Criar novo paciente |
| `/patients/list` | GET | Listar pacientes do usuário |
| `/patient/{patient_id}` | GET | Obter detalhes do paciente |
| `/patient/{patient_id}` | PUT | Atualizar paciente |

### Histórico

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/history/queries` | GET | Histórico de consultas |
| `/history/assessments` | GET | Histórico de avaliações |
| `/history/uploads` | GET | Histórico de uploads |
| `/history/stats` | GET | Estatísticas de uso |

### Métricas

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/metrics/quality/{query_id}` | GET | Métricas de qualidade |
| `/metrics/aggregated` | GET | Métricas agregadas |
| `/metrics/leaderboard` | GET | Ranking de modelos |

---

## 🔒 Segurança

### Multi-tenancy
- Cada usuário acessa apenas seus próprios dados
- Isolamento por `owner_id` em todas as tabelas
- Foreign keys garantem integridade referencial

### Autenticação
- Tokens JWT com expiração configurável
- Refresh tokens para renovação automática
- Senhas com hash Argon2

### Anonimização
- Dados sensíveis são automaticamente anonimizados:
  - CPF → `<CPF>`
  - E-mail → `<EMAIL>`
  - Telefone → `<PHONE>`
  - Endereço → `<ADDRESS>`
  - Datas → `<DATE>`
  - Idades → `<AGE_RANGE>`

### Audit Log
- Todas as consultas são registradas
- Rastreabilidade completa para conformidade

---

## 📊 Monitoramento e Métricas

O sistema calcula automaticamente:

- **Latência**: Tempo de resposta das requisições
- **Custo**: Estimativa de custos com APIs
- **Precisão de Recuperação**: Qualidade dos documentos recuperados
- **Faithfulness**: Adequação da resposta ao contexto
- **Relevância da Resposta**: Qualidade da resposta gerada
- **Legibilidade**: Índice Flesch de facilidade de leitura

---

## 🐛 Troubleshooting

### Erro: "Could not find extension vector"

```sql
-- Conectar ao banco e criar a extensão
psql -d symyah_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Erro: "GOOGLE_API_KEY not found"

Verifique se o arquivo `.env` está configurado corretamente:

```bash
cat .env | grep GOOGLE_API_KEY
```

### Erro: "Connection refused" no PostgreSQL

Verifique se o banco está rodando:

```bash
# Docker
docker ps | grep postgres

# Systemd
sudo systemctl status postgresql
```

---

## 📝 Licença

[Inserir informações de licença aqui]

---

## 🤝 Contribuindo

1. Fork o repositório
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

---

## 📞 Suporte

Para dúvidas e suporte, entre em contato através do e-mail: [seu-email@dominio.com]

---

**Desenvolvido para auxiliar profissionais de psicologia clínica e psicopedagogia.**
