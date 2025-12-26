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

# Создаем отдельный скрипт для инициализации БД
RUN echo 'from app.models import db\nfrom run import app\nwith app.app_context():\n    db.create_all()\n    print("Database initialized")' > init_db.py

CMD ["sh", "-c", "python init_db.py && gunicorn run:app --bind 0.0.0.0:${PORT}"]
