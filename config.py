import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'BD_Kursach'

    # Получаем DATABASE_URL из переменных окружения
    database_url = os.environ.get('DATABASE_URL')

    # ⚠️ ВАЖНО: Render иногда дает 'postgres://', а SQLAlchemy требует 'postgresql://'
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    # Используем PostgreSQL если есть DATABASE_URL, иначе SQLite
    SQLALCHEMY_DATABASE_URI = database_url or 'sqlite:///time_tracker.db'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False