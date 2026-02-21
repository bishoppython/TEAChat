# Instruções para Dockerização do Sistema de Psicologia Clínica

Baseado na análise do código, aqui estão as configurações do `Dockerfile` e `docker-compose.yml` para o seu sistema de IA clínica:

## Dockerfile

```Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Expor porta
EXPOSE 8000

# Executar a aplicação
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## docker-compose.yml

```yaml
version: '3.8'

services:
  # API Backend
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/clinica_ai
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SECRET_KEY=${SECRET_KEY:-your-default-secret-key-change-in-production}
      - DEFAULT_MODEL=${DEFAULT_MODEL:-gpt-3.5-turbo}
    depends_on:
      - db
    volumes:
      - ./uploads:/app/uploads  # Para uploads de arquivos
    restart: unless-stopped

  # Aplicação Frontend Flask
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.flask
    ports:
      - "5000:5000"
    environment:
      - API_BASE_URL=http://api:8000
      - FLASK_SECRET_KEY=${FLASK_SECRET_KEY:-change-this-in-production-flask-key}
    depends_on:
      - api
    restart: unless-stopped

  # Banco de Dados PostgreSQL com extensão pgvector
  db:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_DB: clinica_ai
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db:/docker-entrypoint-initdb.d  # Para scripts de inicialização personalizados
    restart: unless-stopped

volumes:
  postgres_data:
```

## Dockerfile.flask (para o frontend Flask)

```Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY frontFlask/requirements_flask.txt .
RUN pip install --no-cache-dir -r requirements_flask.txt

# Copiar código da aplicação Flask
COPY frontFlask/ .

# Expor porta
EXPOSE 5000

# Executar a aplicação Flask
CMD ["python", "flask_frontend.py"]
```

## Instruções:

1. Crie um arquivo `.env` com suas chaves de API e segredos:
```
GOOGLE_API_KEY=sua_chave_api_google
OPENAI_API_KEY=sua_chave_api_openai
SECRET_KEY=sua_chave_secreta_para_jwt
FLASK_SECRET_KEY=sua_chave_secreta_flask
```

2. Execute o sistema com:
```bash
docker-compose up -d
```

3. Acesse a aplicação:
- API: http://localhost:8000
- Frontend: http://localhost:5000

## Observações:
- O sistema utiliza PostgreSQL com pgvector para busca de similaridade vetorial
- Tanto a API quanto o frontend estão containerizados
- Os dados do banco de dados persistem usando volumes do Docker
- Variáveis de ambiente são carregadas do arquivo `.env`
- O frontend Flask se comunica com o backend FastAPI via rede interna
- Uploads de arquivos são armazenados em um volume compartilhado

Essa configuração permite que os usuários acessem o sistema através de um navegador via o frontend Flask na porta 5000, enquanto a API backend roda na porta 8000.