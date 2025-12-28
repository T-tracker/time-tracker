import os
import sys
import subprocess
import time
import signal
import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_web():
    """Запуск веб-приложения через gunicorn"""
    logger.info("🌐 Запуск веб-приложения...")
    
    cmd = [
        "gunicorn",
        "run:app",  # Используем run.py как точку входа
        "--bind", "0.0.0.0:10000",
        "--workers", "1",
        "--timeout", "120",
        "--access-logfile", "-",
        "--error-logfile", "-"
    ]
    
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def run_bot():
    """Запуск Telegram бота"""
    logger.info("🤖 Запуск Telegram бота...")
    
    from start_bot import main as bot_main
    bot_main()

def check_web_health():
    """Проверка, что веб-приложение запустилось"""
    for i in range(10):  # Пробуем 10 раз
        try:
            response = requests.get("http://localhost:10000/health", timeout=2)
            if response.status_code == 200:
                logger.info(f"✅ Веб-приложение доступно (попытка {i+1})")
                return True
        except:
            logger.info(f"⏳ Ожидание веб-приложения... (попытка {i+1})")
            time.sleep(2)
    
    logger.warning("⚠️ Веб-приложение не ответило, но запускаем бота...")
    return False

def main():
    """Запуск обоих сервисов"""
    logger.info("🚀 Запуск Time Tracker системы...")
    
    # Проверяем токен бота
    if not os.environ.get('BOT_TOKEN'):
        logger.warning("⚠️ BOT_TOKEN не найден, запускаю только веб")
        web_process = run_web()
        web_process.wait()
        return
    
    # Запускаем веб
    logger.info("1. Запускаю веб-приложение...")
    web_process = run_web()
    
    # Ждём и проверяем запуск веба
    logger.info("2. Ожидание запуска веб-приложения...")
    time.sleep(3)
    
    if check_web_health():
        logger.info("✅ Веб-приложение готово")
    else:
        logger.warning("⚠️ Веб-приложение не отвечает, но продолжаем...")
    
    # Запускаем бота
    logger.info("3. Запускаю Telegram бота...")
    try:
        # Запускаем бота (блокирующий вызов)
        run_bot()
    except KeyboardInterrupt:
        logger.info("\n🛑 Остановка по запросу пользователя...")
    except Exception as e:
        logger.error(f"❌ Ошибка бота: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Завершаем веб-процесс
        logger.info("🧹 Остановка веб-приложения...")
        web_process.terminate()
        web_process.wait()
        logger.info("👋 Завершение работы")

if __name__ == '__main__':
    main()
