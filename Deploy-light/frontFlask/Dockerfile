# Dockerfile para Frontend Flask SYMYAH
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

# Variáveis de ambiente
ENV FLASK_APP=flask_frontend.py \
    FLASK_ENV=production \
    PYTHONUNBUFFERED=1

# Expor porta
EXPOSE 5000

# Comando para iniciar
CMD ["python", "flask_frontend.py"]
