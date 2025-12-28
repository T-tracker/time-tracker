# start_bot.py
import os
import sys
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Запуск Telegram бота"""
    # Проверяем токен
    bot_token = os.environ.get('BOT_TOKEN')
    if not bot_token:
        logger.warning("⚠️ BOT_TOKEN not found in environment")
        logger.warning("Add BOT_TOKEN to Render Environment Variables")
        return
    
    logger.info(f"✅ BOT_TOKEN found ({len(bot_token)} chars)")
    
    try:
        # Добавляем путь для импорта
        sys.path.insert(0, os.path.dirname(__file__))
        
        # Проверяем конфиг
        from bot.config import BOT_TOKEN as config_token
        if not config_token:
            logger.error("❌ BOT_TOKEN empty in bot.config!")
            return
        
        logger.info("🤖 Starting Telegram bot...")
        
        # Запускаем бота
        from bot.telegram_bot import main as bot_main
        bot_main()
        
    except Exception as e:
        logger.error(f"❌ Bot error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
