# 📦 Pasta DEPLOY_MAXIMO - Pacote Completo de Deploy

**Versão:** 2.0.0 - Somente APIs (Fallback Local DESATIVADO)  
**Última atualização:** Março de 2026

---

## ⚠️ IMPORTANTE: Configuração de Fallback

**Fallback local está DESATIVADO.** O sistema usa exclusivamente:
- **OpenAI** como provedor PRIMÁRIO
- **Google Gemini** como provedor de FALLBACK

Consulte `CHANGELOG_FALLBACK_LOCAL_DESATIVADO.md` para detalhes.

---

## 📁 Estrutura de Arquivos

```
DEPLOY_MAXIMO/
├── 📄 DESCRICAO_PROJETO.txt       # Descrição completa do projeto
├── 📄 README.md                    # Documentação principal
├── 📄 DOCUMENTACAO.md              # Documentação detalhada
├── 📄 arquitetura.md               # Arquitetura do sistema
├── 📄 DEPLOY.md                    # Guia de deploy
├── 📄 DEPLOY_AWS.md                # Deploy na AWS
├── 📄 requirements.txt             # Dependências Python
├── 📄 docker-compose.yml           # Configuração Docker
├── 📄 Dockerfile                   # Dockerfile principal
├── 📄 Dockerfile.prod              # Dockerfile de produção
├── 📄 .env.example                 # Exemplo de variáveis de ambiente
├── 📄 .gitignore                   # Ignorar arquivos git
├── 📄 app.py                       # API principal (FastAPI)
├── 📄 frontend.py                  # Frontend Streamlit
├── 📄 anonimizer_functions.py      # Funções de anonimização
│
├── 📁 core/                        # Lógica central do sistema
│   ├── clinical_ai_system.py       # Sistema completo de IA clínica
│   ├── rag_system.py               # Sistema RAG
│   ├── gemini_interface.py         # Interface Google Gemini
│   ├── user_knowledge_base.py      # Base de conhecimento
│   ├── local_response_generator.py # Gerador local de respostas
│   └── ...                         # Outros módulos
│
├── 📁 database/                    # Banco de dados
│   ├── db_manager.py               # Gerenciador de DB
│   ├── schema.sql                  # Esquema do banco
│   └── metrics_schema.sql          # Esquema de métricas
│
├── 📁 utils/                       # Utilitários
│   ├── embedding_generator.py      # Gerador de embeddings
│   ├── text_processor.py           # Processador de texto
│   ├── metrics_calculator.py       # Calculadora de métricas
│   └── ...
│
├── 📁 analysis/                    # Análise clínica
│   └── clinical_intelligence.py    # Sistema de inteligência clínica
│
└── 📁 frontFlask/                  # Frontend Flask
    ├── flask_frontend.py           # Servidor Flask
    ├── templates/                  # Templates HTML
    └── static/                     # Arquivos estáticos
```

---

## 🚀 Como Fazer Deploy

### Opção 1: Docker (Recomendado)

```bash
# 1. Navegar até a pasta
cd DEPLOY_MAXIMO

# 2. Copiar arquivo de ambiente
cp .env.example .env

# 3. Editar .env com suas credenciais
# - GOOGLE_API_KEY
# - DATABASE_URL
# - SECRET_KEY

# 4. Iniciar containers
docker-compose up -d

# 5. Acessar
# API: http://localhost:8000
# Frontend: http://localhost:5000
# Docs API: http://localhost:8000/docs
```

### Opção 2: Manual (Sem Docker)

```bash
# 1. Navegar até a pasta
cd DEPLOY_MAXIMO

# 2. Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas credenciais

# 5. Iniciar API
python app.py

# 6. Iniciar Frontend (em outro terminal)
python frontend.py
# ou
cd frontFlask && python flask_frontend.py
```

---

## 🔑 Variáveis de Ambiente Obrigatórias

Edite o arquivo `.env` com suas credenciais:

```bash
# Google API Key (obrigatória)
GOOGLE_API_KEY=sua_chave_aqui

# OpenAI API Key (opcional)
OPENAI_API_KEY=sua_chave_aqui

# Database URL (obrigatória)
DATABASE_URL=postgresql://usuario:senha@localhost:5432/banco

# Secret Key para JWT (obrigatória)
SECRET_KEY=sua_chave_secreta_aqui
```

---

## 📋 Pré-requisitos

- **Python 3.9+**
- **PostgreSQL com pgvector** (ou usar Docker)
- **Google Gemini API Key**
- **(Opcional) OpenAI API Key**

---

## 📊 Stack Tecnológica

| Componente | Tecnologia | Provedor |
|------------|------------|----------|
| Backend | Python + FastAPI | - |
| Banco de Dados | PostgreSQL + pgvector | - |
| IA/LLM - Primário | OpenAI API | **PRIMÁRIO** |
| IA/LLM - Fallback | Google Gemini API | **FALLBACK** |
| Frontend | Streamlit + Flask + Bootstrap 5 | - |
| Deploy | Docker + Docker Compose | - |

**Nota:** Modelos locais estão **DESATIVADOS**.

---

## 🔒 Segurança

- Autenticação JWT
- Hashing de senhas com Argon2
- Isolamento de dados por usuário
- Anonimização de dados sensíveis
- Auditoria completa de operações

---

## 📞 Suporte

Para mais informações, consulte:
- `DOCUMENTACAO.md` - Documentação completa
- `arquitetura.md` - Detalhes da arquitetura
- `DEPLOY.md` - Guia de deploy
- `DEPLOY_AWS.md` - Deploy na AWS

---

**Versão:** Production-Ready  
**Última atualização:** Março de 2026
