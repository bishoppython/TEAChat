# SYMYAH - Deploy Light (t3.small - 2GB RAM)

Versão otimizada para instâncias **AWS EC2 t3.small** com 2GB de RAM.

---

## ⚙️ Configurações da Instância

| Recurso | Configuração |
|---------|-------------|
| **Instância** | t3.small |
| **vCPU** | 2 |
| **RAM** | 2 GB |
| **Storage** | 20 GB GP3 |
| **Custo/mês** | ~$15 |

---

## 📋 Otimizações Incluídas

### 1. Swap de 4GB
- Criado automaticamente pelo script de setup
- Previne OOM (Out Of Memory)

### 2. PostgreSQL Otimizado
```
shared_buffers = 128MB
effective_cache_size = 512MB
work_mem = 4MB
max_connections = 50
```

### 3. API com Worker Único
- Apenas 1 worker uvicorn
- Consumo de memória reduzido

### 4. Limites de Memória
| Serviço | Limite |
|---------|--------|
| PostgreSQL | 512 MB |
| API | 1 GB |

---

## 🚀 Passo-a-Passo

### 1. Criar EC2 t3.small

```
- Amazon Linux 2023 ou Ubuntu 22.04
- t3.small (2 vCPU, 2GB RAM)
- 20 GB storage
- Security Group: portas 22, 80, 443
```

### 2. Transferir Arquivos

```bash
scp -i chave.pem -r Deploy-light/ ec2-user@IP_EC2:~/symyah/
```

### 3. Configurar Ambiente

```bash
cd ~/symyah/Deploy-light
cp .env.example .env
nano .env
```

**Edite o .env:**
```bash
POSTGRES_PASSWORD=sua_senha_forte
GOOGLE_API_KEY=sua_key
OPENAI_API_KEY=sua_key
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
```

### 4. Executar Setup

```bash
chmod +x scripts/*.sh
sudo ./scripts/setup.sh
```

### 5. Deploy

```bash
./scripts/deploy.sh
```

### 6. Verificar

```bash
./scripts/healthcheck.sh
```

---

## 📊 Monitoramento

### Verificar Memória

```bash
# Memória total
free -h

# Uso por container
docker stats

# Swap em uso
swapon --show
```

### Logs

```bash
# Logs em tempo real
docker-compose logs -f

# API
docker-compose logs api

# PostgreSQL
docker-compose logs postgres
```

---

## ⚠️ Limitações do t3.small

### O que funciona:
- ✅ API FastAPI completa
- ✅ PostgreSQL com pgvector
- ✅ Consultas RAG
- ✅ Integração OpenAI/Google

### O que foi removido:
- ❌ Frontend Flask (use a API diretamente)
- ❌ Nginx reverse proxy
- ❌ Múltiplos workers

### Recomendações:

1. **Não execute outros serviços** na mesma instância
2. **Monitore o uso de memória** regularmente
3. **Use swap** (já configurado automaticamente)
4. **Evite múltiplas requisições simultâneas**

---

## 🔧 Comandos Úteis

```bash
# Iniciar
docker-compose up -d

# Parar
docker-compose down

# Reiniciar
docker-compose restart

# Ver status
docker-compose ps

# Ver logs
docker-compose logs -f

# Backup manual
sudo ./scripts/backup.sh

# Health check
./scripts/healthcheck.sh
```

---

## 📈 Upgrade de Recursos

Se precisar de mais recursos:

### Para t3.medium (4GB RAM):
```bash
# 1. Pare a instância no Console AWS
# 2. Mude para t3.medium
# 3. Inicie a instância
# 4. Use o Deploy normal (pasta Deploy/)
```

---

## 🐛 Troubleshooting

### Container crashando (OOM)

```bash
# Verificar se é OOM
dmesg | grep -i "killed process"

# Aumentar swap (se necessário)
sudo fallocate -l 2G /swapfile2
sudo chmod 600 /swapfile2
sudo mkswap /swapfile2
sudo swapon /swapfile2
```

### Lentidão

```bash
# Verificar uso de CPU
top

# Verificar processos Docker
docker stats

# Verificar I/O
iostat -x 1 5
```

### PostgreSQL não inicia

```bash
# Verificar logs
docker-compose logs postgres

# Aumentar tempo de espera
# Edite docker-compose.yml: start_period: 120s
```

---

## 💰 Custo Estimado

| Recurso | Custo/mês |
|---------|-----------|
| EC2 t3.small | $15.17 |
| EBS 20GB GP3 | $2 |
| Transferência | $3-10 |
| **Total** | **~$20-27/mês** |

---

## ✅ Checklist

- [ ] Instância t3.small criada
- [ ] Swap configurado (4GB)
- [ ] .env configurado
- [ ] Setup executado
- [ ] Deploy realizado
- [ ] Health check passou
- [ ] Monitoramento configurado

---

**Versão:** 1.0 (Light)  
**Última atualização:** Março 2026
