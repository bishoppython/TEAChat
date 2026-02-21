# Documentação do Projeto: Sistema de IA para Psicologia Clínica

## Sumário
1. [Visão Geral](#visão-geral)
2. [Tecnologias Utilizadas](#tecnologias-utilizadas)
3. [Arquitetura do Projeto](#arquitetura-do-projeto)
4. [Backend](#backend)
5. [Frontend](#frontend)
6. [Funcionalidades](#funcionalidades)
   - [Perfil do Paciente](#perfil-do-paciente)
7. [Execução do Projeto](#execução-do-projeto)

## Visão Geral

O Sistema de IA para Psicologia Clínica é uma aplicação completa que combina Recuperação Aumentada por Geração (RAG) com modelos LoRA e integração Google Gemini. O sistema foi projetado para auxiliar psicólogos clínicos e psicopedagogos no gerenciamento de informações de pacientes, recuperação de documentos clínicos relevantes e geração de respostas contextualmente apropriadas com base em dados específicos do paciente.

## Tecnologias Utilizadas

### Backend
- **Python 3.9+** - Linguagem principal de programação
- **FastAPI** - Framework web para criação da API REST
- **PostgreSQL** - Banco de dados relacional
- **pgvector** - Extensão para PostgreSQL que permite busca vetorial
- **Google Gemini API** - Para geração de embeddings e respostas
- **OpenAI API** - Como fallback para embeddings
- **Pydantic** - Validação de dados
- **JWT** - Autenticação e autorização
- **Passlib/Argon2** - Hashing de senhas

### Processamento de Dados e IA
- **LangChain** - Framework para aplicações com LLMs
- **Transformers** - Modelos de linguagem
- **Torch (PyTorch)** - Framework de aprendizado profundo
- **PEFT** - Parameter-Efficient Fine-Tuning
- **Sentence Transformers** - Modelos para embeddings de frases
- **Qdrant** - Banco de dados vetorial
- **Tiktoken** - Tokenizador para modelos OpenAI

### Processamento de Documentos
- **PyPDF2** - Leitura de arquivos PDF
- **python-docx** - Leitura de arquivos DOCX
- **python-pptx** - Leitura de arquivos PPTX
- **Pandas** - Manipulação de dados
- **NumPy** - Computação científica

### Frontend
- **Flask** - Framework web para o frontend tradicional
- **Streamlit** - Framework para o frontend interativo
- **Bootstrap 5** - Framework CSS para design responsivo
- **Jinja2** - Template engine para Flask

### Outras Bibliotecias
- **Requests** - Para requisições HTTP
- **psycopg2-binary** - Driver PostgreSQL para Python
- **python-dotenv** - Gerenciamento de variáveis de ambiente
- **uvicorn** - Servidor ASGI para FastAPI
- **tiktoken** - Tokenizador para modelos OpenAI
- **sentence-transformers** - Modelos para embeddings de frases

## Arquitetura do Projeto

```
├── app.py                      # API principal com FastAPI
├── frontend.py                 # Frontend Streamlit
├── requirements.txt            # Dependências Python
├── .env.example               # Exemplo de variáveis de ambiente
├── core/                      # Lógica central do sistema
│   ├── clinical_ai_system.py   # Sistema completo de IA clínica
│   ├── rag_system.py          # Sistema RAG para recuperação
│   ├── gemini_interface.py    # Interface com Google Gemini
│   ├── user_knowledge_base.py # Base de conhecimento do usuário
│   ├── local_response_generator.py # Gerador local de respostas
│   └── ...                    # Outros módulos de IA
├── database/                  # Componentes de banco de dados
│   ├── db_manager.py          # Gerenciador de conexão com DB
│   └── schema.sql             # Esquema do banco de dados
├── utils/                     # Utilitários
│   ├── embedding_generator.py # Gerador de embeddings
│   ├── text_processor.py      # Processador de texto clínico
│   └── ...                    # Outros utilitários
└── frontFlask/                # Frontend Flask
    ├── flask_frontend.py      # Servidor Flask
    ├── templates/             # Templates HTML
    └── static/                # Arquivos estáticos (CSS, JS, imagens)
```

## Backend

### Componentes Principais

#### 1. API FastAPI (app.py)
A API principal utiliza FastAPI para fornecer endpoints RESTful para todas as funcionalidades do sistema:

- **Autenticação JWT**: Sistema de login, registro e tokens de acesso/refresh
- **Endpoints CRUD**: Para pacientes, documentos e consultas
- **Upload de Arquivos**: Aceita PDF, DOCX, TXT, CSV e outros formatos
- **Consultas RAG**: Sistema completo para perguntas e respostas baseadas em contexto

#### 2. Sistema RAG (core/rag_system.py)
Implementação do sistema de Recuperação Aumentada por Geração específico para aplicações clínicas:

- **Recuperação de Documentos**: Busca vetorial baseada em similaridade
- **Chunking de Texto**: Divisão automática de documentos longos
- **Geração de Embeddings**: Integração com Google Gemini, OpenAI e fallback local
- **Construção de Contexto**: Combinação de documentos relevantes para respostas
- **Isolamento de Usuário**: Garante que usuários só acessem seus próprios dados

#### 3. Gerenciador de Banco de Dados (database/db_manager.py)
Camada de abstração para interação com PostgreSQL + pgvector:

- **Conexão Segura**: Gerenciamento de conexões com pool de conexões
- **Operações CRUD**: Para usuários, pacientes, documentos e logs
- **Busca Vetorial**: Consultas semânticas usando embeddings
- **Controle de Acesso**: Garante que usuários só acessem seus próprios dados
- **Fallback**: Busca por palavras-chave quando embeddings falham

#### 4. Sistema de IA Clínica (core/clinical_ai_system.py)
Integração completa dos componentes do sistema:

- **Processamento de Consultas**: Coordenação entre RAG e modelos de geração
- **Gestão de Pacientes**: Criação, atualização e recuperação de perfis
- **Avaliação Clínica**: Sistema de avaliação estruturada
- **Geração de Relatórios**: Relatórios clínicos baseados em dados armazenados

### Banco de Dados
O sistema utiliza PostgreSQL com a extensão pgvector para busca vetorial:

#### Estrutura das Tabelas
- **users**: Armazena informações de usuários (psicólogos/psicopedagogos)
- **patients**: Informações de pacientes associadas a usuários
- **patient_sensitivities**: Perfis de sensibilidade específicos dos pacientes
- **documents**: Fragmentos de documentos com embeddings vetoriais
- **audit_log**: Histórico de consultas para auditoria

#### Recursos de Segurança
- **Chaves Estrangeiras**: Garantem integridade referencial
- **Índices Vetoriais**: Otimizam busca semântica
- **Triggers**: Validam consistência de dados
- **Isolamento Multi-inquilino**: Usuários só acessam dados próprios

## Frontend

### 1. Frontend Flask (frontFlask/flask_frontend.py)
Interface web completa com design responsivo e autenticação:

- **Autenticação Completa**: Login, registro e gerenciamento de sessão
- **Interface de Dashboard**: Visão geral das estatísticas do usuário
- **Gerenciamento de Pacientes**: Cadastro, visualização e edição
- **Sistema de Consultas**: Interface para perguntas e respostas
- **Upload de Documentos**: Interface para envio de arquivos
- **Avaliação Clínica**: Sistema de avaliação estruturada
- **Design Responsivo**: Compatível com desktops e dispositivos móveis

#### Templates
- **Base Template**: Layout consistente com Bootstrap 5
- **Dashboard**: Estatísticas e atalhos para funcionalidades
- **Formulários**: Para cadastro de pacientes, documentos e consultas
- **Páginas de Perfil**: Informações detalhadas de pacientes

### 2. Frontend Streamlit (frontend.py)
Interface interativa para demonstração e uso rápido:

- **Interface Simples**: Design limpo e focado em usabilidade
- **Autenticação Integrada**: Sistema de login e registro
- **Navegação por Abas**: Organização clara das funcionalidades
- **Feedback Visual**: Mensagens e métricas em tempo real
- **Upload Interativo**: Interface amigável para envio de arquivos

## Funcionalidades

### Autenticação e Autorização
- **Registro de Usuários**: Novos usuários podem se registrar no sistema
- **Login Seguro**: Autenticação com hashing de senhas
- **Tokens JWT**: Sessões seguras com validade configurável
- **Controle de Acesso**: Garante que usuários só acessem seus dados

### Gerenciamento de Pacientes
- **Cadastro de Pacientes**: Informações pessoais e clínicas detalhadas
- **Perfis de Sensibilidade**: Registros de sensibilidades sensoriais
- **Histórico Clínico**: Acesso a todos documentos e interações
- **Busca e Filtragem**: Recuperação eficiente de informações

### Perfil do Paciente
O sistema oferece uma visão completa e organizada das informações de cada paciente, com as seguintes características:

#### Informações Básicas
- **Identificação**: ID do paciente, nome completo, primeiro nome e sobrenome
- **Dados Pessoais**: Idade, data de nascimento e status (ativo)
- **Características Clínicas**: Diagnóstico, neurotipo, nível/escolaridade

#### Detalhes Clínicos
- **Descrição Completa**: Campo detalhado com informações clínicas relevantes
- **Sensibilidades e Observações**: Lista de sensibilidades sensoriais e observações clínicas importantes
- **Estatísticas**: Quantidade de documentos associados, número de sensibilidades registradas e data de cadastro

#### Funcionalidades Associadas
- **Visualização Completa**: Tela dedicada com todas as informações organizadas
- **Ações Rápidas**: Links diretos para edição, consultas específicas, avaliações clínicas e upload de documentos
- **Integração com Documentos**: Conexão direta com documentos e histórico do paciente

#### Endpoint de Acesso
- **Endpoint**: `POST /patient_profile`
- **Proteção**: Requer autenticação JWT
- **Retorno**: Informações completas do paciente incluindo sensibilidades e estatísticas

### Sistema de Avaliação Clínica
- **Avaliação Personalizada**: Avaliações adaptadas ao perfil do paciente
- **Evidência Recuperada**: Referências a documentos relevantes no banco de dados
- **Pontuação de Confiança**: Indicador da qualidade e confiabilidade das respostas
- **Relatórios Automatizados**: Sumários clínicos baseados em dados do paciente

### Sistema de Upload de Documentos
- **Formatos Suportados**: PDF, DOCX, TXT, CSV e outros formatos de texto
- **Processamento Automático**: Extração de texto, limpeza e divisão em blocos (chunks)
- **Indexação Vetorial**: Documentos são indexados para busca semântica eficiente
- **Associação ao Paciente**: Documentos são ligados a pacientes específicos

### Sistema de Histórico e Auditoria
- **Histórico de Consultas**: Registro completo de todas as interações do usuário
- **Histórico de Avaliações**: Armazenamento de avaliações clínicas realizadas
- **Histórico de Uploads**: Rastreamento de todos os documentos carregados
- **Histórico de Documentos**: Controle de alterações e versões de documentos
- **Sistema de Métricas**: Avaliação de qualidade, latência e custo das respostas
- **Classificação de Modelos**: Comparação de desempenho entre diferentes modelos de IA

### Sistema de Gestão de Pacientes
- **CRUD Completo**: Criação, leitura, atualização e exclusão de perfis de pacientes
- **Edição em Tempo Real**: Atualização imediata das informações dos pacientes
- **Associação de Documentos**: Vinculação de documentos ao histórico clínico
- **Sensibilidades e Observações**: Registro detalhado de particularidades do paciente

### Sistema de Métricas e Qualidade
- **Métricas de Qualidade**: Avaliação da acuracidade e relevância das respostas
- **Métricas de Latência**: Monitoramento do tempo de resposta do sistema
- **Métricas de Custo**: Controle de custos associados ao uso de APIs de IA
- **Métricas de Fidedignidade**: Verificação da consistência das respostas com os documentos
- **Métricas de Relevância**: Avaliação da pertinência das respostas às consultas
- **Classificação de Modelos**: Ranqueamento de modelos por desempenho

### Processamento de Documentos
- **Upload de Arquivos**: Suporte a PDF, DOCX, TXT, CSV e outros formatos
- **Processamento Automático**: Extração de texto e limpeza de caracteres especiais
- **Chunking Inteligente**: Divisão de documentos longos em partes gerenciáveis
- **Armazenamento Vetorial**: Documentos indexados para busca semântica

### Sistema de Consultas RAG
- **Busca Semântica**: Recuperação baseada em embeddings vetoriais
- **Contextualização**: Respostas adaptadas ao perfil do paciente
- **Recuperação Relevante**: Documentos selecionados com base na similaridade
- **Geração de Respostas**: Baseada em contexto e experiência clínica

### Avaliação Clínica
- **Sistema Estruturado**: Avaliações baseadas em protocolos clínicos
- **Evidência Recuperada**: Referências a documentos relevantes
- **Pontuação de Confiança**: Indicador da qualidade das respostas
- **Relatórios Automatizados**: Sumários clínicos baseados em dados

### Auditoria e Conformidade
- **Registro de Consultas**: Todos os acessos são registrados
- **Histórico de Interações**: Rastreamento completo de atividades
- **Conformidade Clínica**: Atendimento a requisitos de privacidade
- **Análise de Uso**: Estatísticas de utilização do sistema

## Execução do Projeto

### Pré-requisitos
- Python 3.9 ou superior
- PostgreSQL com extensão pgvector
- Chave de API do Google Gemini
- (Opcional) Chave de API da OpenAI

### Passo a Passo de Execução

#### 1. Configuração do Ambiente
```bash
# Clonar ou copiar os arquivos do projeto

# Criar e ativar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
```

#### 2. Configuração do Banco de Dados
```bash
# Opção A: Configurar PostgreSQL local com pgvector
sudo apt-get install postgresql postgresql-contrib
# Instalar extensão pgvector manualmente ou usar distribuição compatível

# Opção B: Usar PostgreSQL com pgvector via Docker
docker run -d --name postgres-vector -e POSTGRES_PASSWORD=sua_senha -p 5432:5432 ankane/pgvector
```

#### 3. Configuração de Variáveis de Ambiente
```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar .env e adicionar as variáveis necessárias:
GOOGLE_API_KEY=sua_chave_api_google
DATABASE_URL=postgresql://usuario:senha@localhost:5432/banco_clinico
SECRET_KEY=chave_secreta_para_jwt
```

#### 4. Iniciar o Backend (API FastAPI)
```bash
# Certificar-se de que o ambiente virtual está ativado
source venv/bin/activate

# Iniciar o servidor de API
python app.py
# ou usando uvicorn diretamente
uvicorn app:app --host 0.0.0.0 --port 8000
```

#### 5. Executar os Frontends

##### Frontend Flask
```bash
# Em outro terminal, com o mesmo ambiente virtual ativado
cd frontFlask
python flask_frontend.py
# Acessar em http://localhost:5000
```

##### Frontend Streamlit (Alternativo)
```bash
# Em outro terminal, com o mesmo ambiente virtual ativado
streamlit run frontend.py
# Acessar em http://localhost:8501 (ou conforme indicado no terminal)
```

### Verificação de Funcionamento

1. **API Backend (FastAPI)**:
   - Acessar `http://localhost:8000` para verificar o status
   - Acessar `http://localhost:8000/docs` para visualizar a documentação da API

2. **Frontend**:
   - Acessar `http://localhost:5000` (Flask) ou `http://localhost:8501` (Streamlit)
   - Realizar login com credenciais válidas
   - Testar funcionalidades básicas como cadastro de paciente e consulta

### Configuração Opcional

#### Variáveis de Configuração Adicionais
```bash
# Configurações RAG
RAG_TOP_K=4
RAG_MIN_SIMILARITY=0.5
CHUNK_SIZE=500
CHUNK_OVERLAP=50

# Configurações de Servidor
HOST=0.0.0.0
PORT=8000
FLASK_PORT=5000

# Configurações de Modelos
DEFAULT_MODEL=gpt-3.5-turbo
MAX_CONTEXT_TOKENS=2048
```

### Solução de Problemas

#### Conexão com Banco de Dados
- Verificar se PostgreSQL está em execução
- Confirmar que a string de conexão DATABASE_URL está correta
- Validar que a extensão pgvector está instalada

#### Chaves de API
- Confirmar que GOOGLE_API_KEY está configurada corretamente
- Verificar permissões e saldo na conta Google Cloud

#### Upload de Arquivos
- Garantir que o diretório temporário tenha permissões adequadas
- Verificar limites de tamanho de arquivo configurados

#### Embeddings
- Confirmar que as dimensões estão corretas (768 para Gemini)
- Verificar fallbacks para OpenAI e modelos locais