FROM python:3.12-slim

# Системные зависимости для PostgreSQL
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаем таблицы при запуске
CMD ["sh", "-c", "python -c 'from app.models import db; from run import app; with app.app_context(): db.create_all()' && gunicorn run:app --bind 0.0.0.0:${PORT}"]
