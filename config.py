import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "BD_Kursach"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    db_url = os.environ.get("DATABASE_URL")

    # Локальный фолбэк
    if not db_url:
        SQLALCHEMY_DATABASE_URI = "sqlite:///time_tracker.db"
        SQLALCHEMY_ENGINE_OPTIONS = {}
    else:
        # Render часто отдаёт postgres://..., SQLAlchemy ожидает postgresql://...
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        SQLALCHEMY_DATABASE_URI = db_url

        # ВАЖНО: SSL и стабильность коннекта задаём через engine options
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,       # проверяет соединение перед использованием
            "pool_recycle": 300,         # пересоздаёт коннекты каждые 5 минут
            "connect_args": {
                "sslmode": "require",    # железно требует SSL
            },
        }
