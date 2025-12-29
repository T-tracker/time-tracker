import os
import sys
import subprocess
import time
import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Берем порт, который дает Render, или 10000 по умолчанию
PORT = os.environ.get("PORT", "10000")

def run_web():
    """Запуск веб-приложения через gunicorn"""
    logger.info(f"🌐 Запуск веб-приложения на порту {PORT}...")
    
    cmd = [
        "gunicorn",
        "run:app",
        "--bind", f"0.0.0.0:{PORT}", # Привязываемся к динамическому порту
        "--workers", "1",
        "--timeout", "120",
        "--access-logfile", "-",
        "--error-logfile", "-"
    ]
    
    # Перенаправляем вывод в системный stdout, чтобы видеть логи в панели Render
    return subprocess.Popen(cmd)

def check_web_health():
    """Проверка, что веб-приложение запустилось"""
    # Проверяем либо /health, либо главную страницу /
    url = f"http://127.0.0.1:{PORT}/" 
    for i in range(15): 
        try:
            response = requests.get(url, timeout=2)
            # Если ответил любым кодом (даже 404), значит сервер поднялся
            if response.status_code < 500:
                logger.info(f"✅ Веб-сервер ответил (код {response.status_code})")
                return True
        except:
            logger.info(f"⏳ Ожидание веб-приложения... ({i+1}/15)")
            time.sleep(2)
    return False

def main():
    logger.info("🚀 Запуск Time Tracker системы...")
    
    # 1. Запуск Веба
    web_process = run_web()
    
    # 2. Проверка Веба
    if check_web_health():
        logger.info("✅ Веб-приложение успешно запущено")
    else:
        logger.warning("⚠️ Веб-приложение не ответило вовремя, но пробуем запустить бота")

    # 3. Запуск Бота
    if not os.environ.get('BOT_TOKEN'):
        logger.error("❌ BOT_TOKEN не найден! Бот не будет запущен.")
        web_process.wait()
    else:
        try:
            from start_bot import main as bot_main
            bot_main()
        except KeyboardInterrupt:
            logger.info("🛑 Остановка...")
        finally:
            web_process.terminate()

if __name__ == '__main__':
    main()
