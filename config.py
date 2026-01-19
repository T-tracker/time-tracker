import os
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "BD_Kursach"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # Если задано — пробуем Postgres, если нет — SQLite
    raw_url = os.environ.get("DATABASE_URL")

    # Нормализуем URL для SQLAlchemy
    if raw_url and raw_url.startswith("postgres://"):
        raw_url = raw_url.replace("postgres://", "postgresql://", 1)

    # Подготовим Postgres URL (добавим порт и sslmode=require), если он есть
    postgres_url = None
    if raw_url and raw_url.startswith("postgresql://"):
        u = urlparse(raw_url)

        # порт 5432, если не указан
        netloc = u.netloc
        if u.port is None:
            userinfo = ""
            if u.username:
                userinfo += u.username
                if u.password:
                    userinfo += f":{u.password}"
                userinfo += "@"
            host = u.hostname or ""
            netloc = f"{userinfo}{host}:5432"

        q = dict(parse_qsl(u.query, keep_blank_values=True))
        q.setdefault("sslmode", "require")

        postgres_url = urlunparse((
            u.scheme,
            netloc,
            u.path,
            u.params,
            urlencode(q),
            u.fragment
        ))

    # По умолчанию ставим SQLite (она всегда доступна)
    # Если Postgres реально доступен — мы переключимся на него из app/__init__.py
    SQLALCHEMY_DATABASE_URI = "sqlite:///time_tracker.db"

    # Настройки движка (для SQLite можно оставить пустыми)
    SQLALCHEMY_ENGINE_OPTIONS = {}

    # Сохраним Postgres URL в конфиге, чтобы create_app мог попробовать подключиться
    POSTGRES_DATABASE_URI = postgres_url
