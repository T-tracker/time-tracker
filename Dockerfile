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

# Правильный способ: создаем скрипт инициализации
RUN echo '#!/bin/bash\n\
python -c "import sys; sys.path.insert(0, \"/app\")\n\
from app.models import db\n\
from run import app\n\
with app.app_context():\n\
    db.create_all()\n\
    print(\"✅ Database tables created!\")"\n\
exec gunicorn run:app --bind 0.0.0.0:${PORT:-10000}' > /app/start.sh \
    && chmod +x /app/start.sh

CMD ["/app/start.sh"]
