# run.py - ТОЛЬКО веб, без бота!
print("=" * 50)
print("🚨 RUN.PY IS EXECUTING - WEB ONLY!")
print("=" * 50)

import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_web_app():
    """Создание веб-приложения"""
    try:
        from app import create_app
        app = create_app()

        from datetime import datetime
        
        # Простой health-check
        @app.route('/health')
        def health():
            return {
                'status': 'healthy',
                'service': 'web_only'
            }
        
        logger.info("🌐 Веб-приложение создано")
        return app
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания веб-приложения: {e}")
        # Создаём минимальное приложение для ошибки
        from flask import Flask
        app = Flask(__name__)
        
        @app.route('/')
        def error():
            return '<h1>Ошибка запуска</h1><p>Смотрите логи</p>'
        
        return app

# Создаём приложение для gunicorn
app = create_web_app()

if __name__ == '__main__':
    logger.info("🚀 Запускаю ТОЛЬКО веб-приложение...")
    
    # НЕ запускаем бота здесь!
    logger.info("ℹ️ Telegram бот запускается через start_bot.py")
    
    # Запускаем веб-приложение
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
