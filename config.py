import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "BD_Kursach"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # Render/Postgres URL
    db_url = os.environ.get("DATABASE_URL")

    # SQLAlchemy ожидает postgresql://, а Render иногда даёт postgres://
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    # Для Render Postgres обычно нужен SSL
    if db_url and "sslmode=" not in db_url:
        joiner = "&" if "?" in db_url else "?"
        db_url = f"{db_url}{joiner}sslmode=require"

    # Фолбэк на sqlite для локальной разработки
    SQLALCHEMY_DATABASE_URI = db_url or "sqlite:///time_tracker.db"
