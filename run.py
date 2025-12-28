# В самое начало run.py добавь:
print("=" * 50)
print("🚨 RUN.PY IS EXECUTING!")
print("=" * 50)

import os
import sys
import threading
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_bot():
    """Запуск Telegram бота"""
    try:
        logger.info("🤖 Запускаю Telegram бота...")
        
        # Добавляем путь для импорта
        sys.path.insert(0, '/app')
        
        # Импортируем и запускаем бота
        from bot.telegram_bot import main
        main()
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

def run_web():
    """Запуск веб-приложения"""
    try:
        from app import create_app
        app = create_app()
        
        # Простой health-check
        @app.route('/health')
        def health():
            return {
                'status': 'healthy',
                'bot_running': 'bot_thread' in globals() and bot_thread.is_alive()
            }
        
        logger.info("🌐 Веб-приложение создано")
        return app
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска веб-приложения: {e}")
        # Создаём минимальное приложение для ошибки
        from flask import Flask
        app = Flask(__name__)
        
        @app.route('/')
        def error():
            return '<h1>Ошибка запуска</h1><p>Смотрите логи</p>'
        
        return app

if __name__ == '__main__':
    logger.info("🚀 Запускаю систему Time Tracker...")
    
    # Проверяем токен бота
    if os.environ.get('BOT_TOKEN'):
        logger.info("✅ BOT_TOKEN найден")
        
        # Запускаем бота в отдельном потоке
        global bot_thread
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        
        # Даём боту время на запуск
        time.sleep(3)
        
        if bot_thread.is_alive():
            logger.info("✅ Telegram бот запущен")
        else:
            logger.warning("⚠️ Поток бота не запустился")
    else:
        logger.warning("⚠️ BOT_TOKEN не найден, бот не запущен")
    
    # Запускаем веб-приложение
    app = run_web()
    
    # Для локального запуска
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
else:
    # Для gunicorn в Render
    app = run_web()
