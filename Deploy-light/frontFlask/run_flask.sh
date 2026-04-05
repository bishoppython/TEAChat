#!/bin/bash

# Script para executar o frontend Flask

echo "=================================="
echo "Frontend Flask - Sistema de IA"
echo "=================================="
echo ""

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado. Por favor, instale Python 3.8 ou superior."
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"
echo ""

# Verificar se as dependências estão instaladas
echo "📦 Verificando dependências..."
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask não encontrado. Instalando dependências..."
    pip install -r requirements_flask.txt
else
    echo "✅ Dependências OK"
fi
echo ""

# Verificar se o backend está rodando
echo "🔍 Verificando backend..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend está rodando"
else
    echo "⚠️  Backend não detectado em http://localhost:8000"
    echo "   Certifique-se de iniciar o backend antes de usar o frontend"
fi
echo ""

# Criar diretório de templates se não existir
if [ ! -d "templates" ]; then
    echo "⚠️  Diretório 'templates' não encontrado!"
    echo "   Certifique-se de ter todos os arquivos HTML na pasta 'templates'"
    exit 1
fi

echo "=================================="
echo "🚀 Iniciando servidor Flask..."
echo "=================================="
echo ""
echo "📍 URL: http://localhost:5000"
echo "🛑 Para parar o servidor, pressione Ctrl+C"
echo ""

# Iniciar o servidor Flask
python3 frontend_flask.py
