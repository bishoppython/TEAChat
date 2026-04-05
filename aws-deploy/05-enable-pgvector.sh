#!/bin/bash

# ============================================
# ENABLE PGVECTOR - Habilitar extensão no RDS
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."  # Voltar para raiz do projeto

# Carregar variáveis de ambiente
source aws-deploy/.env.aws

REGION="${REGION:-us-east-1}"

echo "============================================"
echo "📦 HABILITAR PGVECTOR - RDS PostgreSQL"
echo "============================================"
echo "Endpoint: $DB_ENDPOINT"
echo "Database: $DB_NAME"
echo "Usuário: $DB_USER"
echo ""

# 1. Verificar se psql está instalado
echo "🔍 Verificando psql..."
if ! command -v psql &> /dev/null; then
    echo "   ❌ psql não encontrado"
    echo ""
    echo "   Instale com:"
    echo "   sudo apt-get update && sudo apt-get install -y postgresql-client"
    echo ""
    exit 1
fi

PSQL_VERSION=$(psql --version)
echo "   ✅ $PSQL_VERSION"
echo ""

# 2. Testar conexão
echo "🔌 Testando conexão com RDS..."
if ! PGPASSWORD="$DB_PASSWORD" psql -h "$DB_ENDPOINT" -U "$DB_USER" -d postgres -c "\q" 2>/dev/null; then
    echo "   ❌ Erro de conexão com RDS"
    echo ""
    echo "   Verifique:"
    echo "   - Security Group permite acesso na porta 5432"
    echo "   - RDS está com status 'available'"
    echo "   - Credenciais estão corretas em aws-deploy/.env.aws"
    exit 1
fi

echo "   ✅ Conexão estabelecida"
echo ""

# 3. Habilitar extensão pgvector
echo "📦 Habilitando extensão pgvector..."
if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_ENDPOINT" -U "$DB_USER" -d postgres -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>&1; then
    echo "   ✅ pgvector habilitado com sucesso"
else
    echo "   ⚠️  Aviso: Pode ser que pgvector já esteja habilitado ou haja permissões restritas"
fi
echo ""

# 4. Verificar se extensão foi criada
echo "🔍 Verificando extensão instalada..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_ENDPOINT" -U "$DB_USER" -d postgres -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
echo ""

# 5. Criar database do projeto (se não existir)
echo "🗄️  Verificando database $DB_NAME..."
DB_EXISTS=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_ENDPOINT" -U "$DB_USER" -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME';" 2>/dev/null | tr -d ' ')

if [ "$DB_EXISTS" != "1" ]; then
    echo "   📝 Criando database $DB_NAME..."
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_ENDPOINT" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;"
    echo "   ✅ Database criado"
else
    echo "   ✅ Database já existe"
fi
echo ""

# 6. Habilitar pgvector no database do projeto
echo "📦 Habilitando pgvector no database $DB_NAME..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_ENDPOINT" -U "$DB_USER" -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || echo "   ℹ️  Extensão já existe no database"
echo ""

# 7. Verificar versão do pgvector
echo "📊 Versão do pgvector:"
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_ENDPOINT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
echo ""

# 8. Executar schema do projeto (se existir)
if [ -f "database/schema.sql" ]; then
    echo "📄 Executando schema.sql..."
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_ENDPOINT" -U "$DB_USER" -d "$DB_NAME" -f database/schema.sql
    echo "   ✅ Schema executado com sucesso"
    echo ""
else
    echo "ℹ️  database/schema.sql não encontrado - pulando execução de schema"
    echo ""
fi

# 9. Executar metrics schema (se existir)
if [ -f "database/metrics_schema.sql" ]; then
    echo "📄 Executando metrics_schema.sql..."
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_ENDPOINT" -U "$DB_USER" -d "$DB_NAME" -f database/metrics_schema.sql
    echo "   ✅ Metrics schema executado com sucesso"
    echo ""
else
    echo "ℹ️  database/metrics_schema.sql não encontrado - pulando"
    echo ""
fi

echo "============================================"
echo "✅ PGVECTOR configurado com sucesso!"
echo "============================================"
echo ""
echo "📊 Resumo:"
echo "   Endpoint: $DB_ENDPOINT:$DB_PORT"
echo "   Database: $DB_NAME"
echo "   pgvector: habilitado"
echo ""
echo "🧪 Teste a conexão:"
echo "   psql -h $DB_ENDPOINT -U $DB_USER -d $DB_NAME"
echo ""
echo "➡️  Próximo passo: bash aws-deploy/03-deploy-apprunner.sh"
echo "============================================"
