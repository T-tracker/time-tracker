import os
import sys
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

print("=" * 60)
print("🔍 DEBUG STARTUP")
print("=" * 60)

# 1. Проверяем переменные окружения
print("1. Environment variables:")
print(f"   BOT_TOKEN: {'SET' if os.environ.get('BOT_TOKEN') else 'NOT SET'}")
print(f"   PORT: {os.environ.get('PORT')}")
print(f"   DATABASE_URL: {'SET' if os.environ.get('DATABASE_URL') else 'NOT SET'}")

# 2. Проверяем импорт bot/config
print("\n2. Testing bot/config import:")
try:
    from bot.config import BOT_TOKEN, BACKEND_URL
    print(f"   ✅ bot/config imported")
    print(f"   BOT_TOKEN in config: {'SET' if BOT_TOKEN else 'EMPTY'}")
    print(f"   BACKEND_URL: {BACKEND_URL}")
except Exception as e:
    print(f"   ❌ bot/config import failed: {e}")

# 3. Проверяем импорт app
print("\n3. Testing app import:")
try:
    from app import create_app
    print("   ✅ app imported successfully")
    
    # Пробуем создать приложение
    app = create_app()
    print("   ✅ Flask app created")
    
    # Проверяем роуты
    print(f"   Routes registered: {len(app.url_map._rules)}")
    
except Exception as e:
    print(f"   ❌ app import failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("=" * 60)
