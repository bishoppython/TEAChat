#!/bin/bash
# ============================================
# Script de Limpeza e Build Otimizado SYMYAH
# ============================================

echo "🧹 Limpando recursos do Docker para liberar espaço..."

# Parar e remover containers em execução
docker compose down 2>/dev/null

# Remover imagens órfãs
docker image prune -af --filter "until=24h" 2>/dev/null

# Limpar cache do buildx
docker buildx prune -f 2>/dev/null

# Limpar volumes não utilizados (cuidado!)
# docker volume prune -f 2>/dev/null

# Mostrar espaço disponível
echo ""
echo "📊 Espaço em disco disponível:"
df -h /var/lib/docker 2>/dev/null || df -h

echo ""
echo "🚀 Iniciando build otimizado..."
docker compose build --no-cache

echo ""
echo "✅ Build completo! Para iniciar os serviços:"
echo "   docker compose up -d"
