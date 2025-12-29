import logging
import asyncio
import time
from datetime import datetime, timedelta
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from bot.config import BOT_TOKEN
from bot.states import state_manager
from bot.utils import round_to_next_15
from bot.api_client import api_client

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    success, user_data = api_client.authenticate_telegram_user(user.id, user.username or user.first_name)
    
    if not success:
        reg_url = "https://time-tracker-2-pfld.onrender.com/register"
        await update.message.reply_text(f"📝 Нужно зарегистрироваться: {reg_url}\nТвой ID: `{user.id}`", parse_mode='Markdown')
        return

    state_manager.update_user_data(user.id, user_data)
    state = state_manager.get_state(user.id)
    categories = api_client.get_user_categories(state.user_id)
    state_manager.update_categories(user.id, categories)
    
    keyboard = get_categories_keyboard(state)
    await update.message.reply_text(f"👋 С возвращением, {user.first_name}!\nКатегорий: {len(categories)}", reply_markup=keyboard)

def get_categories_keyboard(state):
    if not state.categories: return ReplyKeyboardRemove()
    names = [c['name'] for c in state.categories] + ["⏹️ Остановить всё"]
    buttons = [names[i:i+2] for i in range(0, len(names), 2)]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = state_manager.get_state(user_id)
    text = update.message.text

    if text == "⏹️ Остановить всё":
        state.stop_activity()
        await update.message.reply_text("🛑 Остановлено")
        return

    category = next((c for c in state.categories if c['name'] == text), None)
    if category:
        start_t = round_to_next_15(datetime.now())
        state.start_activity(category['id'], category['name'], start_t)
        await update.message.reply_text(f"🚀 Начато: {category['name']} с {start_t.strftime('%H:%M')}")

async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = state_manager.get_state(update.effective_user.id)
    cats = api_client.get_user_categories(state.user_id)
    state_manager.update_categories(update.effective_user.id, cats)
    await update.message.reply_text(f"Обновлено! Категорий: {len(cats)}", reply_markup=get_categories_keyboard(state))

def main():
    logger.info("Checking API...")
    for _ in range(3):
        if api_client.check_connection():
            logger.info("✅ Connected")
            break
        time.sleep(5)
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("categories", categories_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category))
    app.run_polling()

if __name__ == "__main__":
    main()
