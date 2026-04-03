# Usa una versione leggera di Python
FROM python:3.13-slim

# Evita che Python scriva file .pyc sul disco e forza l'output dei log
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Installa le librerie di sistema necessarie (es. per il database Postgres)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Crea e imposta la cartella di lavoro dentro il container
WORKDIR /app

# Copia il file delle dipendenze e installale
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copia tutto il resto del codice del backend
COPY . /app/