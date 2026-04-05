# Dockerfile para SYMYAH - Sistema de IA para Psicologia Clínica
# Otimizado para produção em EC2 AWS
# Multi-stage build para imagem mínima e segura

# =============================================================================
# Stage 1: Builder - Compilação das dependências
# =============================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Instalar dependências de sistema necessárias para compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Criar ambiente virtual
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Baixar dados do NLTK antecipadamente
RUN python -m nltk.downloader -d /opt/nltk_data punkt

# =============================================================================
# Stage 2: Production - Imagem mínima para runtime
# =============================================================================
FROM python:3.11-slim as production

WORKDIR /app

# Instalar apenas bibliotecas de sistema necessárias para runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copiar ambiente virtual do stage anterior
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar dados do NLTK
COPY --from=builder /opt/nltk_data /opt/nltk_data
ENV NLTK_DATA=/opt/nltk_data

# Copiar código fonte essencial de produção
COPY app.py .
COPY anonimizer_functions.py .
COPY requirements.txt .

# Copiar módulos essenciais
COPY core/ core/
COPY database/ database/
COPY utils/ utils/
COPY analysis/ analysis/

# Criar usuário não-root para segurança
RUN groupadd -r symyah && useradd -r -g symyah symyah && \
    chown -R symyah:symyah /app && \
    chown -R symyah:symyah /opt/nltk_data

USER symyah

# Variáveis de ambiente de produção
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    NLTK_DATA=/opt/nltk_data

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Comando para iniciar a aplicação com uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
