import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or ''
    
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    # КРИТИЧЕСКИ ВАЖНО: преобразовать postgres:// в postgresql://
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or 'sqlite:///time-tracker-db.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
