# 🚀 Guia Rápido - t3.small (2GB RAM)

## Resumo em 5 Passos

### 1️⃣ Criar EC2 t3.small
```
- Amazon Linux 2023 ou Ubuntu 22.04
- t3.small (2 vCPU, 2GB RAM)
- 20 GB storage
- Portas: 22, 80, 443
```

### 2️⃣ Transferir Arquivos
```bash
scp -i chave.pem -r Deploy-light/ ec2-user@IP_EC2:~/symyah/
```

### 3️⃣ Configurar
```bash
cd ~/symyah/Deploy-light
cp .env.example .env
nano .env  # Edite chaves de API e senhas
```

### 4️⃣ Setup (cria swap de 4GB)
```bash
chmod +x scripts/*.sh
sudo ./scripts/setup.sh
```

### 5️⃣ Deploy
```bash
./scripts/deploy.sh
```

---

## Comandos Essenciais

```bash
# Ver status
docker-compose ps

# Ver memória
free -h
docker stats

# Ver logs
docker-compose logs -f

# Reiniciar
docker-compose restart

# Backup
sudo ./scripts/backup.sh

# Health check
./scripts/healthcheck.sh
```

---

## Configuração .env Mínima

```bash
POSTGRES_PASSWORD=sua_senha_forte
GOOGLE_API_KEY=sua_key_google
OPENAI_API_KEY=sua_key_openai
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
```

---

## ⚠️ Importante

- **Swap de 4GB** é criada automaticamente
- **Apenas 1 worker** na API (economia de memória)
- **Sem frontend Flask** - use a API diretamente
- **Monitore memória**: `free -h` e `docker stats`

---

## Acesso

```
API: http://IP_EC2:8000
Docs: http://IP_EC2:8000/docs
```

---

Para documentação completa, veja `README.md`
