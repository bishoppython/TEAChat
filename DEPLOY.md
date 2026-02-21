# 🚀 Guia Rápido de Implantação - SYMYAH

Este guia fornece instruções passo-a-passo para implantar o SYMYAH em produção.

---

## 📋 Pré-requisitos

- Docker e Docker Compose instalados
- OU Python 3.9+ e PostgreSQL 14+ com pgvector
- Chave de API do Google (obrigatória)
- Chave de API da OpenAI (opcional, recomendado)

---

## Opção 1: Deploy com Docker (Recomendado)

### Passo 1: Clonar o Repositório

```bash
git clone <url-do-repositorio>
cd Anderson_Configurado_BKP
```

### Passo 2: Configurar Variáveis de Ambiente

```bash
cp .env.example .env
```

Edite o arquivo `.env`:

```bash
# Senha do PostgreSQL
POSTGRES_PASSWORD=sua_senha_forte_aqui

# Google API Key
GOOGLE_API_KEY=sua_chave_google_aqui

# OpenAI API Key (opcional)
OPENAI_API_KEY=sua_chave_openai_aqui

# Chave secreta para JWT
SECRET_KEY=sua_chave_secreta_forte_aqui
```

### Passo 3: Iniciar com Docker Compose

```bash
docker-compose up -d
```

### Passo 4: Verificar Status

```bash
docker-compose ps
```

### Passo 5: Acessar o Sistema

- **API**: http://localhost:8000
- **Documentação Swagger**: http://localhost:8000/docs
- **Frontend**: http://localhost:5000

### Comandos Úteis

```bash
# Ver logs
docker-compose logs -f api

# Parar serviços
docker-compose down

# Reiniciar serviços
docker-compose restart

# Rebuild após mudanças
docker-compose up -d --build
```

---

## Opção 2: Deploy Manual (Sem Docker)

### Passo 1: Instalar PostgreSQL com pgvector

**Ubuntu/Debian:**

```bash
# Instalar PostgreSQL
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib -y

# Instalar pgvector
sudo apt-get install postgresql-server-dev-all -y
cd /tmp
git clone --branch v0.7.0 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Iniciar PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Passo 2: Criar Banco de Dados

```bash
sudo -u postgres psql << EOF
CREATE DATABASE symyah_db;
CREATE USER symyah_user WITH PASSWORD 'sua_senha_forte_aqui';
GRANT ALL PRIVILEGES ON DATABASE symyah_db TO symyah_user;
\c symyah_db
CREATE EXTENSION vector;
EOF
```

### Passo 3: Aplicar Schema

```bash
PGPASSWORD='sua_senha_forte_aqui' psql -h localhost -U symyah_user -d symyah_db -f database/schema.sql
PGPASSWORD='sua_senha_forte_aqui' psql -h localhost -U symyah_user -d symyah_db -f database/metrics_schema.sql
```

### Passo 4: Configurar Ambiente

```bash
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
pip install -r frontFlask/requirements_flask.txt
```

### Passo 5: Configurar .env

```bash
cp .env.example .env
# Edite o arquivo .env com suas credenciais
```

### Passo 6: Iniciar Backend

```bash
python app.py
# Ou: uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Passo 7: Iniciar Frontend (em outro terminal)

```bash
cd frontFlask
python flask_frontend.py
```

---

## 🔒 Configurações de Segurança para Produção

### 1. HTTPS com Nginx (Reverse Proxy)

Instale o Nginx:

```bash
sudo apt-get install nginx -y
```

Configure `/etc/nginx/sites-available/symyah`:

```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://localhost:5000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. SSL com Let's Encrypt

```bash
sudo apt-get install certbot python3-certbot-nginx -y
sudo certbot --nginx -d seu-dominio.com
```

### 3. Firewall

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 4. Variáveis de Ambiente Seguras

Nunca commitar o arquivo `.env` no Git!

```bash
# No .gitignore
.env
*.env
```

---

## 📊 Monitoramento

### Health Checks

```bash
# API Health
curl http://localhost:8000/health

# Frontend Health
curl http://localhost:5000/health
```

### Logs

```bash
# Docker
docker-compose logs -f api
docker-compose logs -f frontend

# Systemd (se usar serviço)
sudo journalctl -u symyah-api -f
```

### Backup do Banco de Dados

```bash
# Backup diário (adicionar ao crontab)
0 2 * * * pg_dump -h localhost -U symyah_user symyah_db > /backups/symyah_$(date +\%Y\%m\%d).sql
```

---

## 🔄 Atualização

### Com Docker

```bash
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Manual

```bash
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart symyah-api
sudo systemctl restart symyah-frontend
```

---

## 🐛 Troubleshooting

### Erro: "Connection refused" no PostgreSQL

```bash
# Verificar se está rodando
sudo systemctl status postgresql

# Reiniciar
sudo systemctl restart postgresql
```

### Erro: "Extension vector not found"

```bash
# Conectar ao banco e criar extensão
psql -d symyah_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Erro: "GOOGLE_API_KEY not found"

Verifique o arquivo `.env`:

```bash
cat .env | grep GOOGLE_API_KEY
```

### API não responde

```bash
# Verificar logs
docker-compose logs api

# Verificar se porta está em uso
sudo lsof -i :8000

# Reiniciar serviço
docker-compose restart api
```

---

## 📞 Suporte

Para issues e dúvidas, abra um problema no repositório ou entre em contato com a equipe.

---

**Última atualização**: 2026-02-18  
**Versão**: 1.0.0
