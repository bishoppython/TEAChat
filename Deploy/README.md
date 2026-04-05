# SYMYAH - Deploy em Produção AWS EC2

Sistema de IA para Psicologia Clínica com RAG + LoRA

## 📋 Visão Geral

Este pacote contém todos os arquivos necessários para deploy do SYMYAH em um servidor EC2 da AWS usando Docker. A aplicação é containerizada e inclui:

- **PostgreSQL com pgvector** - Banco de dados vetorial
- **API FastAPI** - Backend de IA clínica
- **Frontend Flask** - Interface web
- **Nginx** - Reverse proxy (opcional)

---

## 📁 Estrutura de Pastas

```
Deploy/
├── app.py                      # Aplicação principal FastAPI
├── anonimizer_functions.py     # Funções de anonimização
├── requirements.txt            # Dependências Python
├── Dockerfile                  # Dockerfile da API
├── docker-compose.yml          # Orquestração de containers
├── .env.example                # Modelo de configuração
├── .env.production.example     # Modelo para produção
├── core/                       # Módulos principais de IA
│   ├── clinical_ai_system.py
│   ├── rag_system.py
│   ├── openai_interface.py
│   └── ...
├── database/                   # Gerenciamento de banco de dados
│   ├── db_manager.py
│   ├── schema.sql
│   └── metrics_schema.sql
├── utils/                      # Utilitários
│   ├── embedding_generator.py
│   └── metrics_calculator.py
├── analysis/                   # Análise clínica
│   ├── clinical_evolution_analyzer.py
│   └── smart_alerts_system.py
├── frontFlask/                 # Frontend Flask
│   ├── flask_frontend.py
│   ├── Dockerfile
│   ├── templates/
│   └── static/
├── nginx/                      # Configuração Nginx
│   └── nginx.conf
└── scripts/                    # Scripts de suporte
    ├── setup.sh               # Setup inicial do EC2
    ├── deploy.sh              # Deploy da aplicação
    ├── backup.sh              # Backup do banco de dados
    └── healthcheck.sh         # Verificação de saúde
```

---

## 🚀 Passo-a-Passo para Deploy em EC2

### Pré-requisitos

- Conta AWS configurada
- AWS CLI instalado e configurado
- Acesso SSH ao seu terminal

---

### Passo 1: Criar Instância EC2

1. **Acesse o Console AWS**
   - Vá para o serviço EC2
   - Clique em "Launch Instance"

2. **Configure a Instância**
   - **Nome:** `symyah-server`
   - **AMI:** Amazon Linux 2023 ou Ubuntu Server 22.04 LTS
   - **Tipo de Instância:** 
     - Mínimo: `t3.medium` (2 vCPU, 4GB RAM)
     - Recomendado: `t3.large` (2 vCPU, 8GB RAM)
   - **Par de Chaves:** Selecione ou crie um novo par de chaves
   - **Security Group:**
     - SSH (22) - Sua rede
     - HTTP (80) - 0.0.0.0/0
     - HTTPS (443) - 0.0.0.0/0 (opcional)

3. **Configurar Storage**
   - Mínimo: 30 GB GP3

4. **Launch a instância**

---

### Passo 2: Conectar à Instância

```bash
# Conecte-se via SSH
ssh -i sua-chave.pem ec2-user@SEU_IP_PUBLICO

# Para Ubuntu
ssh -i sua-chave.pem ubuntu@SEU_IP_PUBLICO
```

---

### Passo 3: Preparar o Ambiente

```bash
# Atualizar o sistema
sudo yum update -y              # Amazon Linux
# ou
sudo apt-get update && sudo apt-get upgrade -y  # Ubuntu

# Instalar Git
sudo yum install -y git         # Amazon Linux
# ou
sudo apt-get install -y git     # Ubuntu
```

---

### Passo 4: Transferir Arquivos para o EC2

**Opção A: Usando SCP**

```bash
# Do seu computador local
scp -i sua-chave.pem -r Deploy/ ec2-user@SEU_IP_PUBLICO:~/symyah-deploy/
```

**Opção B: Usando AWS S3**

```bash
# No seu computador local, crie um zip
cd Deploy
zip -r ../symyah-deploy.zip .

# Envie para o S3
aws s3 cp symyah-deploy.zip s3://SEU_BUCKET/

# No EC2, baixe do S3
aws s3 cp s3://SEU_BUCKET/symyah-deploy.zip .
unzip symyah-deploy.zip -d symyah-deploy/
```

**Opção C: Clonar do Git (se aplicável)**

```bash
# No EC2
git clone SEU_REPOSITORIO.git symyah-deploy
cd symyah-deploy/Deploy
```

---

### Passo 5: Configurar Variáveis de Ambiente

```bash
# Navegue até o diretório
cd ~/symyah-deploy/Deploy

# Copie o arquivo de exemplo
cp .env.example .env

# Edite o arquivo .env
nano .env
```

**Configure as seguintes variáveis:**

```bash
# Banco de Dados
POSTGRES_DB=symyah_db
POSTGRES_USER=symyah_user
POSTGRES_PASSWORD=SUA_SENHA_FORTE_AQUI

# Google API Key (Obrigatória)
GOOGLE_API_KEY=sua_google_api_key_aqui

# OpenAI API Key (Recomendada)
OPENAI_API_KEY=sua_openai_api_key_aqui

# Segurança (Gere uma nova chave)
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
```

---

### Passo 6: Executar Script de Setup

```bash
# Tornar os scripts executáveis
chmod +x scripts/*.sh

# Executar setup (como root)
sudo ./scripts/setup.sh
```

Este script irá:
- Instalar Docker
- Instalar Docker Compose
- Configurar permissões
- Criar serviço systemd

---

### Passo 7: Realizar o Deploy

```bash
# Executar script de deploy
./scripts/deploy.sh
```

Ou manualmente:

```bash
# Build das imagens
docker-compose build

# Iniciar serviços
docker-compose up -d

# Verificar status
docker-compose ps

# Ver logs
docker-compose logs -f
```

---

### Passo 8: Verificar se Está Funcionando

```bash
# Health check da API
curl http://localhost:8000/health

# Health check do frontend
curl http://localhost:5000/

# Verificar containers
docker ps
```

---

### Passo 9: Configurar Security Group

No Console AWS, edite o Security Group da instância:

| Tipo      | Protocolo | Porta | Origem     | Descrição |
|-----------|-----------|-------|------------|-----------|
| HTTP      | TCP       | 80    | 0.0.0.0/0  | Web       |
| HTTPS     | TCP       | 443   | 0.0.0.0/0  | Web Seguro|
| SSH       | TCP       | 22    | Sua IP     | SSH       |

---

### Passo 10: Acessar a Aplicação

```
# API Backend
http://SEU_IP_PUBLICO:8000

# Frontend
http://SEU_IP_PUBLICO:5000

# Com Nginx (se configurado)
http://SEU_IP_PUBLICO/
```

---

## 🔧 Comandos Úteis

### Gerenciar Serviços

```bash
# Iniciar
docker-compose up -d

# Parar
docker-compose down

# Reiniciar
docker-compose restart

# Ver logs
docker-compose logs -f

# Ver logs de um serviço específico
docker-compose logs -f api
```

### Backup do Banco de Dados

```bash
# Executar backup manual
sudo ./scripts/backup.sh

# Os backups são salvos em: /opt/symyah/backups/
```

### Health Check

```bash
# Verificar saúde dos serviços
./scripts/healthcheck.sh
```

### Atualizar Aplicação

```bash
# Parar serviços
docker-compose down

# Pull das novas imagens (se aplicável)
docker-compose pull

# Rebuild
docker-compose build --no-cache

# Iniciar
docker-compose up -d
```

---

## 🔒 Configurações de Segurança

### 1. HTTPS com SSL

Para produção, configure HTTPS:

```bash
# Instalar Certbot
sudo yum install -y certbot    # Amazon Linux
# ou
sudo apt-get install -y certbot python3-certbot-nginx  # Ubuntu

# Gerar certificado
sudo certbot certonly --standalone -d seu-dominio.com

# Os certificados serão salvos em:
# /etc/letsencrypt/live/seu-dominio.com/
```

Edite `nginx/nginx.conf` e descomente a seção HTTPS.

### 2. Firewall

```bash
# Configurar firewall (Ubuntu)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 3. Monitoramento

```bash
# Instalar CloudWatch Agent (Amazon Linux)
sudo yum install -y amazon-cloudwatch-agent

# Configurar e iniciar
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -c file:/path/to/config.json -s
```

---

## 📊 Monitoramento e Logs

### Verificar Logs

```bash
# Logs da API
docker-compose logs api

# Logs do banco de dados
docker-compose logs postgres

# Logs do frontend
docker-compose logs frontend

# Logs em tempo real
docker-compose logs -f
```

### Métricas

Acesse o endpoint de health:

```bash
curl http://localhost:8000/health
```

---

## 🐛 Troubleshooting

### Containers não iniciam

```bash
# Verificar logs de erro
docker-compose logs

# Verificar uso de recursos
docker stats

# Reiniciar serviços
docker-compose restart
```

### Erro de conexão com banco de dados

```bash
# Verificar se PostgreSQL está saudável
docker-compose ps postgres

# Verificar logs do banco
docker-compose logs postgres

# Testar conexão
docker-compose exec api python -c "from database.db_manager import DatabaseManager; DatabaseManager()"
```

### Porta já em uso

```bash
# Verificar portas em uso
sudo netstat -tulpn | grep LISTEN

# Matar processo
sudo kill -9 PID
```

### Espaço em disco

```bash
# Limpar imagens antigas
docker image prune -a

# Limpar volumes órfãos
docker volume prune

# Verificar uso de disco
df -h
docker system df
```

---

## 📈 Escalabilidade

### Aumentar Recursos da Instância

1. Pare a instância no Console AWS
2. Altere o tipo da instância (ex: t3.large → t3.xlarge)
3. Inicie a instância

### Auto Scaling

Configure Auto Scaling Group no AWS:

1. Crie um Launch Template
2. Configure Auto Scaling Group
3. Defina políticas de scaling baseadas em CPU/Memória

### Load Balancer

Para múltiplas instâncias:

1. Crie um Application Load Balancer
2. Registre as instâncias EC2
3. Configure health checks

---

## 💰 Custos Estimados (AWS)

| Recurso              | Configuração      | Custo Mensal (aprox.) |
|---------------------|-------------------|----------------------|
| EC2 t3.medium       | 2 vCPU, 4GB RAM   | $30-40               |
| EC2 t3.large        | 2 vCPU, 8GB RAM   | $60-80               |
| EBS GP3 30GB        | Storage           | $3                   |
| Transferência Dados | Variável          | $5-20                |
| **Total**           |                   | **$40-150/mês**      |

---

## 📞 Suporte

Para issues e dúvidas:

1. Verifique os logs: `docker-compose logs -f`
2. Execute health check: `./scripts/healthcheck.sh`
3. Consulte a documentação em `DOCUMENTACAO.md`

---

## ✅ Checklist de Deploy

- [ ] Instância EC2 criada
- [ ] Security Group configurado
- [ ] Arquivos transferidos para EC2
- [ ] Arquivo `.env` configurado
- [ ] Docker e Docker Compose instalados
- [ ] Serviços iniciados com `docker-compose up -d`
- [ ] Health check passou
- [ ] API acessível externamente
- [ ] Frontend acessível externamente
- [ ] Backup configurado (cron job)
- [ ] HTTPS configurado (produção)
- [ ] Monitoramento configurado

---

## 📝 License

Este projeto é parte do trabalho de mestrado em Psicologia Clínica.

---

**Versão:** 1.0.0  
**Última atualização:** Março 2026
