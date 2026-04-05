#!/bin/bash
# =============================================================================
# Instalação Direta do SYMYAH (Sem Docker)
# Para t3.small - 2GB RAM
# =============================================================================

set -e

echo "=============================================="
echo "SYMYAH - Instalação Direta (Sem Docker)"
echo "=============================================="

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Verificar se está na pasta correta
if [ ! -f "app.py" ]; then
    log_error "Execute este script na pasta do projeto (onde está app.py)"
    exit 1
fi

# =============================================================================
# 1. Instalar dependências do sistema
# =============================================================================
log_info "Instalando dependências do sistema..."

# Detectar sistema
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    OS="unknown"
fi

case $OS in
    ubuntu|debian)
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip python3-venv \
            postgresql postgresql-contrib libpq-dev \
            git curl wget build-essential python3-dev
        ;;
    amzn|amazon)
        sudo yum update -y
        sudo yum install -y python3 pip python3-devel \
            postgresql postgresql-server postgresql-devel \
            git curl wget gcc
        sudo systemctl initdb postgresql || true
        ;;
    *)
        log_warn "Sistema não reconhecido: $OS"
        log_info "Tente instalar manualmente python3, pip e postgresql"
        ;;
esac

# =============================================================================
# 2. Configurar Swap (se necessário)
# =============================================================================
SWAP=$(swapon --show | wc -l)
if [ "$SWAP" -eq 0 ]; then
    log_info "Criando swap de 4GB..."
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    log_info "Swap criada!"
else
    log_info "Swap já configurada"
fi

# =============================================================================
# 3. Configurar PostgreSQL
# =============================================================================
log_info "Configurando PostgreSQL..."

# Iniciar PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Gerar senha aleatória para o banco
DB_PASSWORD=$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16)
log_info "Senha do banco gerada: $DB_PASSWORD"

# Criar usuário e banco (pode falhar se já existir)
sudo -u postgres psql << EOF || true
CREATE USER symyah_user WITH PASSWORD '$DB_PASSWORD';
CREATE DATABASE symyah_db OWNER symyah_user;
GRANT ALL PRIVILEGES ON DATABASE symyah_db TO symyah_user;
GRANT ALL ON SCHEMA public TO symyah_user;
\q
EOF

# Aguardar PostgreSQL
sleep 2

# Instalar extensão pgvector
log_info "Instalando extensão pgvector..."
sudo -u postgres psql -d symyah_db -c "CREATE EXTENSION IF NOT EXISTS vector;" || true

# Importar schema
log_info "Importando schema do banco..."
PGPASSWORD=$DB_PASSWORD psql -h localhost -U symyah_user -d symyah_db -f database/schema.sql || true
PGPASSWORD=$DB_PASSWORD psql -h localhost -U symyah_user -d symyah_db -f database/metrics_schema.sql || true

# =============================================================================
# 4. Criar ambiente virtual Python
# =============================================================================
log_info "Criando ambiente virtual Python..."

python3 -m venv venv
source venv/bin/activate

# Atualizar pip
pip install --upgrade pip

# =============================================================================
# 5. Instalar dependências Python (em etapas para economizar memória)
# =============================================================================
log_info "Instalando dependências Python (etapa 1/4)..."
pip install --no-cache-dir fastapi uvicorn pydantic python-dotenv python-multipart

log_info "Instalando dependências Python (etapa 2/4)..."
pip install --no-cache-dir python-jose[cryptography] passlib[argon2] PyJWT requests

log_info "Instalando dependências Python (etapa 3/4)..."
pip install --no-cache-dir psycopg2-binary pgvector

log_info "Instalando dependências Python (etapa 4/4)..."
pip install --no-cache-dir google-generativeai openai langchain==0.2.3
pip install --no-cache-dir langchain-community==0.2.4 langchain-core==0.2.5
pip install --no-cache-dir sentence-transformers tiktoken nltk

log_info "Instalando utilitários..."
pip install --no-cache-dir numpy pandas PyPDF2 python-docx

# Baixar NLTK data
python -m nltk.downloader punkt

# =============================================================================
# 6. Criar arquivo .env
# =============================================================================
log_info "Configurando arquivo .env..."

if [ ! -f ".env" ]; then
    cp .env.example .env
    
    # Gerar SECRET_KEY
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    # Atualizar .env
    sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$DB_PASSWORD/" .env
    sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
    sed -i "s|DATABASE_URL=.*|DATABASE_URL=postgresql://symyah_user:$DB_PASSWORD@localhost:5432/symyah_db|" .env
    
    log_info ".env criado! EDITE COM SUAS CHAVES DE API!"
    log_warn "IMPORTANTE: Execute 'nano .env' e adicione GOOGLE_API_KEY e OPENAI_API_KEY"
else
    log_info ".env já existe"
fi

# =============================================================================
# 7. Criar serviço systemd
# =============================================================================
log_info "Criando serviço systemd..."

sudo tee /etc/systemd/system/symyah.service > /dev/null << EOF
[Unit]
Description=SYMYAH API - Psicologia Clínica
After=network.target postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin"
ExecStart=$(pwd)/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

# Limites de memória para t3.small
MemoryLimit=1G

[Install]
WantedBy=multi-user.target
EOF

# Recarregar e iniciar
sudo systemctl daemon-reload
sudo systemctl enable symyah

# =============================================================================
# Mensagens finais
# =============================================================================
echo ""
echo "=============================================="
log_info "Instalação concluída!"
echo "=============================================="
echo ""
echo "⚠️  PRÓXIMOS PASSOS IMPORTANTES:"
echo ""
echo "1. Edite o arquivo .env com suas chaves de API:"
echo "   nano .env"
echo "   - Adicione GOOGLE_API_KEY=sua_key"
echo "   - Adicione OPENAI_API_KEY=sua_key"
echo ""
echo "2. Inicie o serviço:"
echo "   sudo systemctl start symyah"
echo ""
echo "3. Verifique o status:"
echo "   sudo systemctl status symyah"
echo ""
echo "4. Teste a API:"
echo "   curl http://localhost:8000/health"
echo ""
echo "5. Acesse no navegador:"
echo "   http://IP_DO_EC2:8000/docs"
echo ""
echo "=============================================="
echo "Senha do banco (salve em local seguro): $DB_PASSWORD"
echo "=============================================="
echo ""
