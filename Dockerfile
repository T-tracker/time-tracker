FROM python:3.12-slim

# Системные зависимости для PostgreSQL
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot_requirements.txt .
RUN pip install --no-cache-dir -r bot_requirements.txt

COPY . .

CMD python start_bot.py & gunicorn "app:create_app()" --bind 0.0.0.0:10000

COPY start_bot.py .
