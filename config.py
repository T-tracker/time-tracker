import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or ''
    
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    # КРИТИЧЕСКИ ВАЖНО: преобразовать postgres:// в postgresql://
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # ИСПРАВЛЕНО: Правильный fallback или логирование ошибки
    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
        print(f" * Используется PostgreSQL: {DATABASE_URL[:50]}...")  # Логируем первые 50 символов
    else:
        # Лучше упасть с понятной ошибкой, чем молча использовать SQLite
        raise ValueError(
            "Переменная окружения DATABASE_URL не установлена!\n"
            "Установите её в Render: Settings → Environment Variables\n"
            "Или проверьте строку подключения в PostgreSQL → Connections"
        )
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Временно ВКЛЮЧИТЕ для отладки!
