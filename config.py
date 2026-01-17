import os
from datetime import timedelta
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "BD_Kursach"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    raw_url = os.environ.get("DATABASE_URL")

    if not raw_url:
        # Локальный фолбэк
        SQLALCHEMY_DATABASE_URI = "sqlite:///time_tracker.db"
        SQLALCHEMY_ENGINE_OPTIONS = {}
    else:
        # 1) Нормализуем схему для SQLAlchemy
        if raw_url.startswith("postgres://"):
            raw_url = raw_url.replace("postgres://", "postgresql://", 1)

        # 2) Добавляем порт 5432, если его нет, и sslmode=require в query
        u = urlparse(raw_url)

        # если порт не указан — ставим 5432
        netloc = u.netloc
        if u.port is None:
            # urlparse хранит username/password/host отдельно, но netloc нам надо собрать обратно
            userinfo = ""
            if u.username:
                userinfo += u.username
                if u.password:
                    userinfo += f":{u.password}"
                userinfo += "@"

            host = u.hostname or ""
            netloc = f"{userinfo}{host}:5432"

        # query params
        q = dict(parse_qsl(u.query, keep_blank_values=True))
        q.setdefault("sslmode", "require")

        fixed_url = urlunparse((
            u.scheme,
            netloc,
            u.path,
            u.params,
            urlencode(q),
            u.fragment
        ))

        SQLALCHEMY_DATABASE_URI = fixed_url

        # 3) Настройки движка — для стабильности на Render
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "connect_args": {
                "sslmode": "require",
                "connect_timeout": 10,
                # keepalive помогает при "SSL closed unexpectedly"
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            },
        }
