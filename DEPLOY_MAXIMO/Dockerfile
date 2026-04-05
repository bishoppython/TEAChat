# Dockerfile para SYMYAH - Sistema de IA para Psicologia Clínica
# Este Dockerfile cria uma imagem otimizada para produção

# Stage 1: Build
FROM python:3.11-slim as builder

WORKDIR /app

# Instalar dependências de sistema necessárias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Criar ambiente virtual
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar apenas requirements primeiro (cache layer)
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Production
FROM python:3.11-slim as production

WORKDIR /app

# Criar usuário não-root para segurança
RUN groupadd -r symyah && useradd -r -g symyah symyah

# Instalar dependências de sistema mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copiar ambiente virtual do stage anterior
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar código fonte (apenas arquivos de produção)
COPY app.py .
COPY anonimizer_functions.py .
COPY requirements.txt .
COPY .env.example .

# Copiar módulos essenciais
COPY core/ core/
COPY database/ database/
COPY utils/ utils/
COPY analysis/ analysis/

# Copiar frontend Flask (opcional - remova se não usar)
COPY frontFlask/ frontFlask/

# Configurar permissões e criar home directory para NLTK
RUN chown -R symyah:symyah /app && \
    mkdir -p /home/symyah && \
    chown -R symyah:symyah /home/symyah

# Baixar dados do NLTK antecipadamente
RUN python -m nltk.downloader punkt

USER symyah

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    NLTK_DATA=/home/symyah/nltk_data

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Comando para iniciar a aplicação
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
