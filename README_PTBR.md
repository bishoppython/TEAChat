# Documentação do Sistema de RAG + LoRA para Psicologia Clínica

## Visão Geral

Este é um sistema de inteligência artificial para psicologia clínica que combina Geração Aumentada por Recuperação (RAG) com modelos LoRA e integração Google Gemini. O sistema foi projetado para auxiliar psicólogos clínicos e psicopedagogos no gerenciamento de informações de pacientes, recuperação de documentos clínicos relevantes e geração de respostas contextualmente apropriadas com base em dados específicos do paciente.

### Recursos Principais

- **Sistema RAG Multi-fonte**: Combina Google Gemini, OpenAI e geração local de embeddings
- **Base de Conhecimento Específica por Paciente**: Armazena e recupera informações clínicas específicas do paciente
- **Gerenciamento de Documentos**: Lida com vários formatos de documentos (PDF, DOCX, TXT, CSV, etc.)
- **Ferramentas de Avaliação Clínica**: Fornece recursos de avaliação clínica estruturada
- **Suporte Multi-inquilino**: Controle de acesso seguro com isolamento entre usuário e paciente
- **Registro de Auditoria**: Rastreia todas as consultas e respostas para fins de conformidade
- **Sistemas Alternativos Avançados**: Múltiplas camadas alternativas incluindo opções de IA local quando os serviços de IA primários estão indisponíveis

## Arquitetura

O sistema consiste em diversos componentes principais:

1. **Camada de API**: API REST baseada no FastAPI servindo como interface principal
2. **Sistema RAG**: ClinicalRAGSystem lida com recuperação de documentos e correspondência de similaridade
3. **Gerador de Embeddings**: Sistema de multi-nível com fallbacks do Google Gemini → OpenAI → Local
4. **Banco de Dados**: PostgreSQL com extensão pgvector para busca de similaridade vetorial
5. **Base de Conhecimento do Usuário**: Gerenciamento abrangente de contexto do paciente
6. **Interfaces Clínicas**: Integração Google Gemini para geração de respostas

## Pré-requisitos

- Python 3.9 ou superior
- Banco de dados PostgreSQL com extensão pgvector
- Chave de API do Google (para embeddings e Gemini)
- (Opcional) Chave de API da OpenAI como fallback
- (Opcional) Modelos locais

## Instalação

1. **Clonar o repositório** (se aplicável) ou copiar os arquivos
2. **Criar e ativar um ambiente virtual**:

```bash
python3 -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. **Instalar dependências**:

```bash
pip install -r requirements.txt
```

4. **Configurar PostgreSQL com pgvector**:

Para Ubuntu/Debian:
```bash
sudo apt-get install postgresql postgresql-contrib
# Instalar extensão pgvector - isso pode exigir compilação a partir da fonte
# ou usando uma distribuição PostgreSQL que inclua pgvector
```

Para Docker:
```bash
docker run -d --name postgres-vector -e POSTGRES_PASSWORD=sua_senha -p 5432:5432 ankane/pgvector
```

5. **Configurar variáveis de ambiente**:

Crie um arquivo `.env` baseado no `.env.example`:

```bash
# Chave de API do Google (obrigatória para embeddings)
GOOGLE_API_KEY=sua_chave_api_google_aqui

# Chave de API da OpenAI (opcional, mas recomendada)
OPENAI_API_KEY=sua_chave_api_openai_aqui

# Configuração do Banco de Dados (obrigatória)
DATABASE_URL=postgresql://usuario:senha@localhost:5432/banco_clinico

DEFAULT_MODEL=gpt-3.5-turbo

# Configuração do RAG
MAX_CONTEXT_TOKENS=2048
RAG_TOP_K=4
RAG_MIN_SIMILARITY=0.5

# Configuração de Treinamento
TRAINING_BATCH_SIZE=4
CHUNK_SIZE=500
CHUNK_OVERLAP=50

# Configuração do Servidor
HOST=0.0.0.0
PORT=8000
```

6. **Inicializar o banco de dados**:

O sistema criará automaticamente as tabelas ao iniciar, usando o esquema de `database/schema.sql`.

## Executando a API Backend (Sem Frontend)

1. **Garantir que seu ambiente virtual esteja ativado**:
```bash
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

2. **Garantir que seu banco de dados esteja rodando** e PostgreSQL com pgvector esteja devidamente configurado

3. **Configurar suas variáveis de ambiente** no arquivo `.env`

4. **Iniciar o servidor de API**:

```bash
python app.py
```

Ou usando uvicorn diretamente:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

5. **A API estará acessível em**: `http://localhost:8000`

## Endpoints Disponíveis

### Verificação de Saúde
- `GET /` - Endpoint raiz com informações do sistema
- `GET /health` - Endpoint de verificação de saúde

### Sistema de Consulta
- `POST /query` - Consultar o sistema de IA clínica
- Corpo da requisição:
  ```json
  {
    "query": "Sua pergunta aqui",
    "owner_id": 1,
    "patient_id": "paciente123",
    "use_openai": true,
    "model": "gpt-3.5-turbo",
    "k": 4,
    "min_similarity": 0.1
  }
  ```

### Gerenciamento de Documentos
- `POST /add_document` - Adicionar documento clínico
- `POST /upload_document` - Fazer upload de arquivo de documento (PDF, DOCX, etc.)
- Requisição: dados de formulário multipart com arquivo, owner_id, patient_id, title

### Informações do Paciente
- `POST /patient_profile` - Obter informações de perfil do paciente
- `POST /assessment` - Executar avaliação clínica
- `POST /patient/create` - Criar novo paciente
- `PUT /patient/{patient_id}` - Atualizar informações de paciente existente
- `GET /patients/list` - Listar todos os pacientes para o usuário logado
- `GET /patient/{patient_id}` - Obter detalhes completos do paciente
- `GET /api/user/{user_id}/patients` - Obter pacientes do usuário específico (usado pelo frontend Flask)

### Autenticação
- `POST /login` - Autenticar usuário e obter tokens de acesso/refresh
- `POST /register` - Registrar novo usuário e obter tokens de acesso/refresh
- `POST /refresh` - Renovar token de acesso usando token de refresh
- `POST /logout` - Logout do usuário (invalidação de token no lado do cliente)

### Gerenciamento de Cache
- `POST /user/{owner_id}/refresh_cache` - Atualizar cache de dados do usuário incluindo lista de pacientes

### Gerenciamento de Histórico
- `GET /history/queries` - Obter histórico de consultas do usuário
- `PUT /history/queries/{query_id}` - Atualizar um registro de consulta
- `DELETE /history/queries/{query_id}` - Excluir um registro de consulta
- `GET /history/assessments` - Obter histórico de avaliações clínicas do usuário
- `PUT /history/assessments/{assessment_id}` - Atualizar um registro de avaliação
- `DELETE /history/assessments/{assessment_id}` - Excluir um registro de avaliação
- `GET /history/uploads` - Obter histórico de uploads de arquivos do usuário
- `PUT /history/uploads/{upload_id}` - Atualizar um registro de upload
- `DELETE /history/uploads/{upload_id}` - Excluir um registro de upload do histórico
- `GET /history/documents` - Obter histórico de documentos do usuário
- `PUT /history/documents/{history_id}` - Atualizar um registro de histórico de documento
- `DELETE /history/documents/{history_id}` - Excluir um registro de histórico de documento
- `GET /history/stats` - Obter estatísticas de histórico para o usuário

### Métricas e Avaliação de Qualidade
- `GET /metrics/quality/{query_id}` - Obter métricas de qualidade para uma consulta específica
- `GET /metrics/aggregated` - Obter métricas agregadas para um período
- `POST /metrics/evaluate_response` - Avaliar qualidade da resposta (para testes/validação)
- `GET /metrics/leaderboard` - Obter classificação de modelos por qualidade

### Outros Endpoints
- `GET /models` - Listar modelos disponíveis
- `GET /api/user/{owner_id}/stats` - Obter estatísticas de usuário
- `GET /api/user/{owner_id}/context` - Obter contexto do usuário

## Esquema do Banco de Dados

O sistema utiliza PostgreSQL com extensão pgvector para busca de similaridade vetorial:

- `users` - Contas de terapeutas/usuários
- `patients` - Informações de pacientes vinculadas a usuários
- `patient_sensitivities` - Perfis de sensibilidade do paciente
- `documents` - Fragmentos de documentos com embeddings vetoriais
- `audit_log` - Registro de consultas e respostas para conformidade

## Configuração

### Chaves de API
- **Chave de API do Google**: Obrigatória para Gemini e embeddings
- **Chave de API da OpenAI**: Opcional como fallback para embeddings
- O sistema usa uma abordagem em camadas: Google Gemini → OpenAI → Embeddings locais

### Configuração do RAG
- `RAG_TOP_K`: Número de documentos a recuperar (padrão: 4)
- `RAG_MIN_SIMILARITY`: Limiar mínimo de similaridade (padrão: 0.5)
- `CHUNK_SIZE`: Tamanho dos fragmentos de texto ao dividir documentos (padrão: 500)
- `CHUNK_OVERLAP`: Sobreposição entre fragmentos (padrão: 50)

### Uso de Modelos
O sistema utiliza principalmente modelos Google Gemini para:
- Geração de embeddings (usando modelo `text-embedding-004`)
- Geração de respostas (usando modelo `gemini-2.5-flash-lite`)

## Tipos de Arquivos Suportados para Upload

O sistema suporta upload e processamento dos seguintes tipos de arquivos:
- Arquivos PDF
- Arquivos DOCX e DOC
- Arquivos TXT
- Arquivos CSV

## Segurança

- Arquitetura multi-inquilino garante que usuários só possam acessar seus próprios dados
- Dados do paciente são isolados por owner_id
- Todas as consultas são registradas para fins de auditoria
- Restrições de chave estrangeira no banco de dados garantem integridade dos dados

## Solução de Problemas

### Problemas Comuns

1. **Conexão com Banco de Dados**: Garanta que PostgreSQL esteja rodando e a string de conexão esteja correta
2. **Falta do pgvector**: O sistema requer extensão pgvector para busca de similaridade vetorial
3. **Chaves de API**: Verifique se a chave de API do Google está devidamente configurada para embeddings e Gemini
4. **Dimensões de Embeddings**: Garanta consistência nas dimensões de embeddings (Gemini: 768, OpenAI: 1536)

### Registro de Logs
O sistema registra eventos importantes para ajudar na depuração:
- Processamento de consultas
- Ingestão de documentos
- Falhas de API
- Geração de embeddings

## Desenvolvimento

O sistema foi projetado para ser modular com clara separação entre:
- Camada de API (`app.py`)
- Lógica de negócios (`core/clinical_ai_system.py`)
- Sistema RAG (`core/rag_system.py`)
- Operações de banco de dados (`database/db_manager.py`)
- Geração de embeddings (`utils/embedding_generator.py`)

## Frontend (Opcional)

Um frontend Streamlit está disponível em `frontend.py` que fornece uma interface amigável para o sistema. Para rodar o frontend:

```bash
streamlit run frontend.py
```

## Contribuição

1. Faça um fork do repositório
2. Crie um branch de feature
3. Faça suas alterações
4. Adicione testes se aplicável
5. Submeta um pull request

## Licença

[Especifique informações de licença aqui se aplicável]