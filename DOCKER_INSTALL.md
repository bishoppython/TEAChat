# 🐳 Guia de Instalação Docker - SYMYAH

## ⚠️ Erro: No Space Left on Device

Se você enfrentou o erro `Errno 28] No space left on device`, siga estas soluções:

### Solução 1: Limpar Espaço do Docker (Recomendado)

```bash
# Executar script de limpeza
chmod +x build-optimized.sh
./build-optimized.sh
```

### Solução 2: Limpeza Manual

```bash
# Parar containers
docker compose down

# Remover imagens não utilizadas
docker image prune -a --force

# Remover caches de build
docker builder prune -a --force

# Verificar espaço
df -h
docker system df
```

### Solução 3: Mover Docker para Outro Disco

Se `/var/lib/docker` está em partição pequena:

```bash
# Parar Docker
sudo systemctl stop docker

# Mover para outro disco (ex: /mnt/dados)
sudo rsync -avz /var/lib/docker/ /mnt/dados/docker/

# Editar daemon.json
sudo nano /etc/docker/daemon.json

# Adicionar:
{
  "data-root": "/mnt/dados/docker"
}

# Reiniciar Docker
sudo systemctl start docker
```

---

## 📦 Instalação do Docker (Ubuntu)

### Passo 1: Instalar Docker

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependências
sudo apt install -y ca-certificates curl gnupg

# Criar diretório para chave GPG
sudo install -m 0755 -d /etc/apt/keyrings

# Adicionar chave do Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Adicionar repositório
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Adicionar usuário ao grupo docker
sudo usermod -aG docker $USER

# Habilitar serviço
sudo systemctl enable docker
sudo systemctl start docker
```

> ⚠️ **Importante:** Faça logout e login para aplicar permissões do grupo docker.

---

## 🚀 Executar o Projeto

### Passo 1: Configurar Variáveis de Ambiente

```bash
cp .env.example .env
nano .env
```

Edite com suas credenciais:
- `POSTGRES_PASSWORD`
- `GOOGLE_API_KEY`
- `OPENAI_API_KEY` (opcional)
- `SECRET_KEY`

### Passo 2: Build Otimizado

```bash
# Usar script de build otimizado
./build-optimized.sh
```

### Passo 3: Iniciar Serviços

```bash
docker compose up -d
```

### Passo 4: Verificar Status

```bash
# Ver containers
docker compose ps

# Ver logs
docker compose logs -f
```

---

## 📊 Tamanho Estimado das Imagens

| Imagem | Tamanho Aproximado |
|--------|-------------------|
| `ankane/pgvector` | ~500 MB |
| `symyah-api` (otimizado) | ~800 MB - 1.2 GB |
| `symyah-frontend` | ~150 MB |

**Total estimado:** ~1.5 - 2 GB (vs 5-8 GB anterior)

---

## 🔧 Troubleshooting

### Erro: Espaço Insuficiente

```bash
# Verificar espaço
df -h
docker system df

# Limpar recursos
docker system prune -a --volumes --force
```

### Erro: Build Falha no pip install

```bash
# Aumentar timeout do Docker
export DOCKER_BUILDKIT=0
docker compose build --progress=plain
```

### Verificar Logs Detalhados

```bash
# Build com verbose
docker compose build --progress=plain --no-cache

# Ver logs do container
docker logs symyah-api
```

---

## 🎯 Otimizações Aplicadas

1. ✅ **Removido cache do pip** (`--no-cache-dir`)
2. ✅ **Versões fixas** das dependências (evita download de versões maiores)
3. ✅ **Removido multi-stage build** (reduz complexidade)
4. ✅ **Apenas dependências essenciais** no requirements.txt
5. ✅ **Imagem slim** como base (python:3.11-slim)
6. ✅ **Limpeza de apt** após instalação

### Dependências Removidas (não essenciais)

- ❌ `torch` (muito grande, não usado em produção)
- ❌ `transformers`, `peft`, `bitsandbytes`, `accelerate`, `trl` (LoRA desativado)
- ❌ `langchain-*` (múltiplos pacotes grandes)
- ❌ `qdrant-client`, `sentence-transformers` (não usados)
- ❌ `streamlit`, `flask` (apenas frontend Flask necessário)
- ❌ `pandas`, `scikit-learn` (não essenciais)
- ❌ `pytest` (apenas desenvolvimento)

---

## 📝 Comandos Úteis

```bash
# Parar serviços
docker compose down

# Parar e remover volumes (CUIDADO: apaga dados!)
docker compose down -v

# Reconstruir apenas API
docker compose build api

# Ver uso de disco do Docker
docker system df

# Monitorar recursos
docker stats
```
