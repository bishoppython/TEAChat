# Dockerfile otimizado para SYMYAH - Sistema de IA para Psicologia Clínica
# Foco: Minimizar uso de disco e tempo de build

FROM python:3.11-slim

WORKDIR /app

# Instalar apenas dependências de sistema essenciais
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Criar usuário não-root para segurança
RUN groupadd -r symyah && useradd -r -g symyah symyah

# Copiar requirements primeiro (para cache de layers)
COPY requirements.txt .

# Instalar dependências Python SEM cache (reduz tamanho em ~3-5GB)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código fonte essencial
COPY app.py .
COPY anonimizer_functions.py .
COPY core/ core/
COPY database/ database/
COPY utils/ utils/
COPY analysis/ analysis/

# Copiar frontend Flask (opcional)
COPY frontFlask/ frontFlask/

# Configurar permissões e criar home directory para NLTK
RUN chown -R symyah:symyah /app && \
    mkdir -p /home/symyah/nltk_data && \
    chown -R symyah:symyah /home/symyah

# Baixar apenas dados essenciais do NLTK
RUN python -m nltk.downloader -d /home/symyah/nltk_data punkt

# Mudar para usuário não-root
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
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Comando para iniciar
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
