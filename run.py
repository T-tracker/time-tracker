# run.py
from app import create_app
import threading
import os
import sys
import logging
import time

# Настройка логирования для отладки
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_bot():
    """Запуск Telegram бота в отдельном потоке"""
    try:
        logger.info("🤖 Запускаю Telegram бота...")
        
        # Добавляем путь к модулю bot в sys.path
        bot_path = os.path.join(os.path.dirname(__file__), 'bot')
        if bot_path not in sys.path:
            sys.path.insert(0, bot_path)
        
        # Импортируем и запускаем бота
        from bot.bot import main as bot_main
        
        logger.info("✅ Модуль бота загружен успешно")
        
        # Запускаем бота (это блокирующая функция)
        bot_main()
        
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта бота: {e}")
        logger.error("Проверьте: 1) Существует ли файл bot/bot.py")
        logger.error("2) Добавлен ли python-telegram-bot в requirements.txt")
        logger.error("3) Есть ли __init__.py в папке bot/")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
        logger.error(f"Тип ошибки: {type(e).__name__}")

def run_web():
    """Запуск Flask веб-приложения"""
    try:
        app = create_app()
        
        # Отладочный маршрут
        @app.route('/debug/routes')
        def debug_routes():
            import json
            routes = []
            for rule in app.url_map.iter_rules():
                if rule.endpoint != 'static':
                    routes.append({
                        'endpoint': rule.endpoint,
                        'methods': list(rule.methods),
                        'path': str(rule)
                    })
            return json.dumps(routes, indent=2, ensure_ascii=False)
        
        @app.route('/health')
        def health_check():
            """Проверка работоспособности"""
            return {
                'status': 'healthy',
                'bot_running': bot_thread.is_alive() if 'bot_thread' in globals() else False,
                'service': 'time-tracker'
            }
        
        # Получаем порт из переменной окружения (Render использует $PORT)
        port = int(os.environ.get('PORT', 5000))
        host = os.environ.get('HOST', '0.0.0.0')
        
        logger.info(f"🌐 Запускаю веб-приложение на {host}:{port}")
        
        # Используем gunicorn для продакшена, werkzeug для разработки
        if os.environ.get('RENDER', False) or os.environ.get('PRODUCTION', False):
            # В продакшене Flask сам не запускается, gunicorn вызовет app напрямую
            return app
        else:
            # Для локальной разработки
            app.run(
                host=host,
                port=port,
                debug=True,
                use_reloader=False  # Важно! Иначе бот запустится дважды
            )
            
    except Exception as e:
        logger.error(f"❌ Ошибка запуска веб-приложения: {e}")
        raise

def main():
    """Главная функция запуска всей системы"""
    logger.info("🚀 Запускаю систему Time Tracker...")
    
    # Проверяем наличие токена бота
    bot_token = os.environ.get('BOT_TOKEN')
    if not bot_token:
        logger.warning("⚠️ BOT_TOKEN не найден в переменных окружения")
        logger.warning("Бот не будет запущен. Добавьте BOT_TOKEN в настройках Render.")
        # Запускаем только веб-приложение
        app = run_web()
        if isinstance(app, Flask):
            return app
        return
    
    logger.info("✅ BOT_TOKEN найден, запускаю бота...")
    
    # Запускаем бота в отдельном потоке
    global bot_thread
    bot_thread = threading.Thread(
        target=run_bot,
        daemon=True  # Демон-поток: завершится при завершении основного потока
    )
    bot_thread.start()
    
    # Даём боту время на инициализацию
    time.sleep(3)
    
    # Проверяем, запустился ли бот
    if bot_thread.is_alive():
        logger.info("✅ Telegram бот успешно запущен")
    else:
        logger.warning("⚠️ Поток бота не запустился")
    
    # Запускаем веб-приложение в основном потоке
    return run_web()

# Создаём объект app для gunicorn
try:
    from flask import Flask
    app = main()
    
    # Если main() вернул Flask-приложение (для продакшена)
    if isinstance(app, Flask):
        # Экспортируем app для gunicorn
        pass
    elif app is None:
        # app уже запущен в run_web()
        pass
        
except Exception as e:
    logger.error(f"❌ Критическая ошибка при запуске: {e}")
    
    # Создаём минимальное приложение для отображения ошибки
    from flask import Flask
    app = Flask(__name__)
    
    @app.route('/')
    def error_page():
        return f'''
        <h1>Ошибка запуска системы</h1>
        <p>{str(e)}</p>
        <p>Проверьте логи в Render для подробностей.</p>
        '''
    
    @app.route('/health')
    def health():
        return {'status': 'error', 'message': str(e)}, 500

if __name__ == '__main__':
    # Локальный запуск для тестирования
    print("\n" + "="*50)
    print("🚀 ЗАПУСК TIME TRACKER СИСТЕМЫ")
    print("="*50 + "\n")
    
    # Проверяем переменные окружения
    if not os.environ.get('BOT_TOKEN'):
        print("⚠️  ВНИМАНИЕ: BOT_TOKEN не установлен")
        print("   Бот не будет запущен. Установите переменную:")
        print("   export BOT_TOKEN='ваш_токен'")
        print("   или создайте файл .env с BOT_TOKEN=...\n")
    
    # Запускаем main
    result = main()
    
    # Если это локальный запуск и main вернул приложение
    if isinstance(result, Flask):
        print("\n" + "="*50)
        print("✅ Система запущена в режиме разработки")
        print("   Веб-приложение: http://localhost:5000")
        print("   Бот: запущен в фоновом режиме")
        print("="*50 + "\n")
