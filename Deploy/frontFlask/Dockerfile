# Dockerfile para Frontend Flask SYMYAH
# Otimizado para produção em EC2 AWS

FROM python:3.11-slim

WORKDIR /app

# Instalar dependências de sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências
COPY requirements_flask.txt .
RUN pip install --no-cache-dir -r requirements_flask.txt

# Copiar código fonte
COPY flask_frontend.py .
COPY templates/ templates/
COPY static/ static/

# Criar usuário não-root para segurança
RUN groupadd -r symyah && useradd -r -g symyah symyah && \
    chown -R symyah:symyah /app

USER symyah

# Variáveis de ambiente
ENV FLASK_APP=flask_frontend.py \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=5000

# Expor porta
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Comando para iniciar
CMD ["python", "flask_frontend.py"]
