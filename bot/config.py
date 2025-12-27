# bot/config.py - ИСПРАВЛЕННЫЙ ВАРИАНТ
import os

# 1. Пробуем получить из переменных окружения Render
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# 2. Если нет, пробуем получить из TELEGRAM_BOT_TOKEN (для совместимости)
if not BOT_TOKEN:
    BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# 3. Если всё ещё нет, пробуем загрузить из .env (ТОЛЬКО для локальной разработки)
if not BOT_TOKEN:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        BOT_TOKEN = os.environ.get('BOT_TOKEN') or os.environ.get('TELEGRAM_BOT_TOKEN')
    except ImportError:
        pass  # dotenv не установлен

# 4. НИКАКИХ ОШИБОК ПРИ ОТСУТСТВИИ ТОКЕНА!
# run.py сам проверит наличие токена и решит, запускать ли бота

# Дополнительные настройки
BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:5000')
