# Arquitetura do Sistema de IA para Psicologia Clínica

## Visão Geral

O sistema de IA para Psicologia Clínica é uma aplicação baseada em RAG (Retrieval-Augmented Generation) que combina recuperação de documentos com geração de respostas baseadas em IA. A arquitetura segue princípios de microserviços com foco em segurança, privacidade e isolamento de dados clínicos.

## Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Camada de Apresentação                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   Web UI    │  │ Mobile App  │  │  API Docs   │  │ Admin Panel │       │
│  │ (Streamlit) │  │   (Futuro)  │  │ (Swagger)   │  │             │       │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Camada de API e Autenticação                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                      FastAPI Application Server                         ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   ││
│  │  │   Login     │  │   Query     │  │   Doc Mgmt  │  │   Patient   │   ││
│  │  │  Endpoint   │  │  Endpoint   │  │  Endpoint   │  │  Endpoint   │   ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   ││
│  │                                                                         ││
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        ││
│  │  │Authentication   │  │ Authorization   │  │ Rate Limiting   │        ││
│  │  │   Service       │  │   Service       │  │   Service       │        ││
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Camada de Negócios e Lógica                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                   Clinical AI System Core                               ││
│  │  ┌─────────────────────────────────────────────────────────────────────┐││
│  │  │                     Main Components                                 │││
│  │  ├─────────────────┬─────────────────┬─────────────────┬───────────────┤││
│  │  │ Clinical AI     │ Clinical RAG    │ User Knowledge  │ Model         │││
│  │  │ System          │ System          │ Base            │ Selector      │││
│  │  └─────────────────┴─────────────────┴─────────────────┴───────────────┘││
│  │                                                                         ││
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        ││
│  │  │ LoRA Tuner      │  │ Gemini          │  │ OpenAI          │        ││
│  │  │                 │  │ Interface       │  │ Interface       │        ││
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        ││
│  │                                                                         ││
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        ││
│  │  │ Local Response  │  │ Metrics         │  │ Response        │        ││
│  │  │ Generator       │  │ Calculator      │  │ Formatter       │        ││
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Camada de Processamento e IA                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                  AI Processing Components                               ││
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        ││
│  │  │ Embedding       │  │ Text Processor  │  │ Anonymizer      │        ││
│  │  │ Generator       │  │                 │  │ Functions       │        ││
│  │  │ (Cached)        │  │                 │  │                 │        ││
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        ││
│  │                                                                         ││
│  │  ┌─────────────────────────────────────────────────────────────────────┐││
│  │  │                    External AI Services                             │││
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│││
│  │  │  │ Google      │  │ OpenAI      │  │ Local       │  │ Fallback    ││││
│  │  │  │ Gemini      │  │ API         │  │ Models      │  │ Services    ││││
│  │  │  │ API         │  │             │  │             │  │             ││││
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘│││
│  │  └─────────────────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Camada de Dados e Armazenamento                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                      PostgreSQL Database                              ││
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        ││
│  │  │   Users Table   │  │  Patients       │  │ Documents       │        ││
│  │  │                 │  │  Table          │  │  Table (with    │        ││
│  │  │  (Therapists)   │  │                 │  │   vectors)      │        ││
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        ││
│  │                                                                         ││
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        ││
│  │  │ Audit Log       │  │ Patient         │  │ Clinical        │        ││
│  │  │  Table          │  │  Sensitivities  │  │  Assessments    │        ││
│  │  │                 │  │  Table          │  │  Table          │        ││
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘        ││
│  │                                                                         ││
│  │  ┌─────────────────────────────────────────────────────────────────────┐││
│  │  │                    pgvector Extension                               │││
│  │  │  ┌─────────────────────────────────────────────────────────────────┐│││
│  │  │  │  Vector Storage & Similarity Search                             ││││
│  │  │  │  (768-dim for Gemini, 1536-dim for OpenAI)                     ││││
│  │  │  └─────────────────────────────────────────────────────────────────┘│││
│  │  └─────────────────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Infraestrutura e Segurança                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────┐│
│  │ Load Balancer   │  │ Firewall        │  │ SSL/TLS         │  │ Backup  ││
│  │                 │  │                 │  │ Encryption      │  │ &       ││
│  │                 │  │                 │  │                 │  │ Recovery││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

## Componentes Principais

### 1. Camada de Apresentação
- **Web UI (Streamlit)**: Interface gráfica para interação com o sistema
- **API Documentation**: Documentação interativa da API (Swagger)
- **Admin Panel**: Painel administrativo para gerenciamento do sistema

### 2. Camada de API e Autenticação
- **FastAPI Application Server**: Servidor principal que expõe endpoints RESTful
- **Serviços de Autenticação**: Sistema de login e gerenciamento de sessões
- **Serviços de Autorização**: Controle de acesso baseado em permissões
- **Rate Limiting**: Controle de taxa de requisições para proteção contra abuso

### 3. Camada de Negócios e Lógica
- **Clinical AI System**: Componente central que coordena todas as funcionalidades
- **Clinical RAG System**: Sistema de recuperação aumentada por geração
- **User Knowledge Base**: Gerenciamento de contexto clínico específico de cada usuário
- **Model Selector**: Seletor inteligente de modelos com fallback automático

### 4. Camada de Processamento e IA
- **Embedding Generator**: Gerador de embeddings com cache e fallback
- **Text Processor**: Processador de texto clínico com chunking e pré-processamento
- **Anonymizer Functions**: Funções para anonimização automática de dados sensíveis
- **External AI Services**: Integração com APIs de IA (Google Gemini, OpenAI)

### 5. Camada de Dados e Armazenamento
- **PostgreSQL Database**: Banco de dados relacional com extensão pgvector
- **Tabelas Especializadas**: Users, Patients, Documents, Audit Log, etc.
- **pgvector Extension**: Armazenamento e busca de embeddings vetoriais

## Características de Segurança

### Isolamento de Tenant
- Cada terapeuta opera em ambiente isolado
- Controle de acesso baseado em owner_id
- Filtragem automática de dados por proprietário

### Anonimização de Dados
- Processamento automático de PII (informações pessoalmente identificáveis)
- Remoção de nomes, datas de nascimento e outros dados sensíveis
- Preservação da utilidade clínica dos dados

### Auditoria
- Registro completo de todas as consultas e operações
- Rastreamento de acesso e uso do sistema
- Conformidade com regulamentações de proteção de dados

## Estratégias de Fallback

### Tiered AI Approach
1. **Google Gemini**: Provedor primário para embeddings e geração
2. **OpenAI API**: Fallback quando Gemini não está disponível
3. **Local Models**: Opção local quando APIs externas falham
4. **RAG-only Responses**: Respostas baseadas apenas em recuperação quando IA não disponível

## Funcionalidades Adicionais

### Gerenciamento de Pacientes
- Criação e edição de perfis de pacientes
- Associação de documentos e histórico clínico
- Gerenciamento de sensibilidades e observações clínicas

### Sistema de Avaliação Clínica
- Avaliações personalizadas baseadas no histórico do paciente
- Recuperação de evidências relevantes nos documentos
- Pontuação de confiança para as respostas geradas

### Autenticação e Autorização
- Sistema JWT para gerenciamento de sessões
- Tokens de acesso e refresh com tempos configuráveis
- Controle de acesso baseado em propriedade dos dados

Esta arquitetura permite alta disponibilidade, escalabilidade e conformidade com regulamentações de proteção de dados clínicos.