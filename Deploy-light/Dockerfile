# Dockerfile para SYMYAH - Versão Light (t3.small - 2GB RAM)
# Otimizado para baixo consumo de memória

# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Instalar apenas dependências essenciais
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Criar ambiente virtual
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar requirements e instalar apenas o essencial
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Baixar apenas o necessário do NLTK
RUN python -m nltk.downloader -d /opt/nltk_data punkt

# =============================================================================
# Stage 2: Production Minimal
# =============================================================================
FROM python:3.11-slim as production

WORKDIR /app

# Instalar apenas bibliotecas mínimas de sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copiar ambiente virtual
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar dados do NLTK
COPY --from=builder /opt/nltk_data /opt/nltk_data
ENV NLTK_DATA=/opt/nltk_data

# Copiar apenas arquivos essenciais
COPY app.py .
COPY anonimizer_functions.py .
COPY requirements.txt .

# Copiar módulos essenciais (apenas produção)
COPY core/ core/
COPY database/ database/
COPY utils/ utils/
COPY analysis/ analysis/

# Criar usuário não-root
RUN groupadd -r symyah && useradd -r -g symyah symyah && \
    chown -R symyah:symyah /app && \
    chown -R symyah:symyah /opt/nltk_data

USER symyah

# Variáveis de ambiente otimizadas para memória
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    NLTK_DATA=/opt/nltk_data \
    # Otimizações de memória para Python
    PYTHONMALLOC=malloc \
    MALLOC_MMAP_THRESHOLD_=1000000 \
    MALLOC_TRIM_THRESHOLD_=1000000

# Expor porta
EXPOSE 8000

# Health check leve
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Comando com apenas 1 worker para economizar memória
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
