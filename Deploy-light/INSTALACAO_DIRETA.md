# Instalação Direta (Sem Docker) - t3.small

Para **t3.small com 2GB RAM**, a instalação direta é mais eficiente que Docker.

---

## 🚀 Método Rápido (Script Automático)

### 1. Transferir Arquivos (se ainda não fez)

```bash
# Na sua máquina local:
scp -i chave.pem -r Deploy-light/ ubuntu@IP_EC2:/opt/symyah/
```

### 2. Rodar Script de Instalação

```bash
# No EC2:
cd /opt/symyah/Deploy-light

# Tornar executável
chmod +x install-direct.sh

# Executar instalação
./install-direct.sh
```

O script vai:
- Instalar Python, PostgreSQL e dependências
- Criar swap de 4GB (se necessário)
- Configurar banco de dados
- Criar ambiente virtual
- Instalar todos os pacotes Python
- Criar serviço systemd

### 3. Editar .env

```bash
nano .env
```

**Adicione suas chaves:**

```bash
GOOGLE_API_KEY=sua_google_api_key
OPENAI_API_KEY=sua_openai_api_key
```

### 4. Iniciar Serviço

```bash
sudo systemctl start symyah
sudo systemctl status symyah
```

### 5. Testar

```bash
curl http://localhost:8000/health
```

---

## 📋 Método Manual (Passo-a-Passo)

Se preferir fazer manualmente:

### 1. Instalar Dependências

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv \
    postgresql postgresql-contrib libpq-dev \
    git curl wget build-essential python3-dev

# Amazon Linux
sudo yum update -y
sudo yum install -y python3 pip python3-devel \
    postgresql postgresql-server postgresql-devel \
    git curl wget gcc
```

### 2. Configurar PostgreSQL

```bash
# Iniciar
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Criar usuário e banco
sudo -u postgres psql << EOF
CREATE USER symyah_user WITH PASSWORD 'senha_forte_aqui';
CREATE DATABASE symyah_db OWNER symyah_user;
GRANT ALL PRIVILEGES ON DATABASE symyah_db TO symyah_user;
\q
EOF

# Instalar pgvector
sudo -u postgres psql -d symyah_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Importar schema
psql -h localhost -U symyah_user -d symyah_db -f database/schema.sql
```

### 3. Ambiente Virtual Python

```bash
cd /opt/symyah/Deploy-light

# Criar venv
python3 -m venv venv
source venv/bin/activate

# Atualizar pip
pip install --upgrade pip
```

### 4. Instalar Pacotes (em etapas)

```bash
# Etapa 1: Core
pip install fastapi uvicorn pydantic python-dotenv python-multipart
pip install python-jose[cryptography] passlib[argon2] PyJWT requests

# Etapa 2: Database
pip install psycopg2-binary pgvector

# Etapa 3: IA
pip install google-generativeai openai
pip install langchain==0.2.3 langchain-community==0.2.4 langchain-core==0.2.5
pip install sentence-transformers tiktoken nltk

# Etapa 4: Utilitários
pip install numpy pandas PyPDF2 python-docx

# NLTK data
python -m nltk.downloader punkt
```

### 5. Configurar .env

```bash
cp .env.example .env
nano .env
```

```bash
DATABASE_URL=postgresql://symyah_user:senha@localhost:5432/symyah_db
GOOGLE_API_KEY=sua_key
OPENAI_API_KEY=sua_key
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
```

### 6. Criar Serviço

```bash
sudo nano /etc/systemd/system/symyah.service
```

```ini
[Unit]
Description=SYMYAH API
After=network.target postgresql.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/symyah/Deploy-light
Environment="PATH=/opt/symyah/Deploy-light/venv/bin"
ExecStart=/opt/symyah/Deploy-light/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### 7. Iniciar

```bash
sudo systemctl daemon-reload
sudo systemctl enable symyah
sudo systemctl start symyah
sudo systemctl status symyah
```

---

## 🔧 Comandos Úteis

```bash
# Ver status
sudo systemctl status symyah

# Ver logs
journalctl -u symyah -f

# Reiniciar
sudo systemctl restart symyah

# Parar
sudo systemctl stop symyah

# Ativar ambiente virtual manualmente
source venv/bin/activate

# Rodar manualmente (sem systemd)
source venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8000
```

---

## ✅ Vantagens vs Docker

| Instalação Direta | Docker |
|------------------|--------|
| ✅ Menos uso de memória | ❌ Overhead do Docker |
| ✅ Mais rápido | ❌ Build demorado |
| ✅ Debug mais fácil | ❌ Logs fragmentados |
| ✅ Atualizações simples | ❌ Rebuild necessário |

---

## 🐛 Troubleshooting

### PostgreSQL não conecta

```bash
# Verificar status
sudo systemctl status postgresql

# Ver logs
sudo journalctl -u postgresql

# Testar conexão
psql -h localhost -U symyah_user -d symyah_db
```

### Erro de import Python

```bash
# Ativar venv
source venv/bin/activate

# Verificar pacotes
pip list

# Reinstalar se necessário
pip install -r requirements.txt
```

### Serviço não inicia

```bash
# Ver logs do systemd
journalctl -u symyah -n 50

# Testar manualmente
source venv/bin/activate
python app.py
```

---

## 📊 Uso de Memória (t3.small)

| Componente | Memória |
|------------|---------|
| PostgreSQL | ~150 MB |
| API (uvicorn) | ~400-600 MB |
| Sistema | ~500 MB |
| **Total** | **~1.1 GB** |

**Sobra**: ~900 MB para operações

---

**Esta versão é ideal para t3.small!**
