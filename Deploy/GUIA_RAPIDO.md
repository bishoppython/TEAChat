# 🚀 Guia Rápido de Deploy - SYMYAH

## Resumo em 5 Passos

### 1️⃣ Criar EC2
```
- Amazon Linux 2023 ou Ubuntu 22.04
- t3.medium (mínimo) ou t3.large (recomendado)
- 30 GB storage
- Abrir portas 22, 80, 443
```

### 2️⃣ Transferir Arquivos
```bash
scp -i chave.pem -r Deploy/ ec2-user@IP_EC2:~/symyah-deploy/
```

### 3️⃣ Configurar Ambiente
```bash
cd ~/symyah-deploy/Deploy
cp .env.example .env
nano .env  # Edite com suas chaves de API e senhas
```

### 4️⃣ Executar Setup
```bash
chmod +x scripts/*.sh
sudo ./scripts/setup.sh
./scripts/deploy.sh
```

### 5️⃣ Acessar
```
API: http://IP_EC2:8000
Frontend: http://IP_EC2:5000
```

---

## Comandos Essenciais

```bash
# Ver status
docker-compose ps

# Ver logs
docker-compose logs -f

# Parar
docker-compose down

# Iniciar
docker-compose up -d

# Backup
sudo ./scripts/backup.sh

# Health check
./scripts/healthcheck.sh
```

---

## Configuração Mínima do .env

```bash
POSTGRES_PASSWORD=sua_senha_forte
GOOGLE_API_KEY=sua_key_google
OPENAI_API_KEY=sua_key_openai
SECRET_KEY=gerar_com_python_secrets
```

Gerar SECRET_KEY:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Problemas Comuns

**Erro de permissão:**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

**Porta já em uso:**
```bash
sudo netstat -tulpn | grep :8000
sudo kill -9 PID
```

**Container não inicia:**
```bash
docker-compose logs nome_container
```

---

Para documentação completa, veja `README.md`
