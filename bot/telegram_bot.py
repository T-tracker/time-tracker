import logging
import time
from datetime import datetime
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
    # Передаем реальный username или first_name
    username_to_send = user.username if user.username else user.first_name
    
    success, user_data = api_client.authenticate_telegram_user(user.id, username_to_send)
    
    if not success:
        reg_url = "https://time-tracker-2-pfld.onrender.com/register"
        await update.message.reply_text(
            f"🚫 Я тебя не узнал.\n1. Убедись, что ты зарегистрирована на сайте: {reg_url}\n"
            f"2. Если никнеймы разные, укажи в профиле сайта Telegram ID: `{user.id}`", 
            parse_mode='Markdown'
        )
        return

    # Сохраняем данные пользователя
    state_manager.update_user_data(user.id, user_data)
    state = state_manager.get_state(user.id)
    
    # Получаем категории, используя ID пользователя Telegram
    categories = api_client.get_user_categories(user.id)
    state_manager.update_categories(user.id, categories)
    
    if not categories:
        await update.message.reply_text("В профиле пока нет категорий. Создай их на сайте!")
        return

    keyboard = get_categories_keyboard(state)
    await update.message.reply_text(
        f"👋 Привет, {user_data.get('username', 'User')}!\nКатегорий загружено: {len(categories)}", 
        reply_markup=keyboard
    )

def get_categories_keyboard(state):
    if not state.categories: 
        return ReplyKeyboardRemove()
    
    # Сортируем кнопки
    names = [c['name'] for c in state.categories]
    buttons = [names[i:i+2] for i in range(0, len(names), 2)]
    buttons.append(["⏹️ Остановить всё"]) # Кнопка стоп всегда внизу
    
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

async def handle_activity_switch(update, state, new_category=None):
    """Логика завершения старой активности и начала новой"""
    user_id = update.effective_user.id
    message_parts = []
    
    # 1. Если что-то уже шло - завершаем и сохраняем
    if state.current_activity:
        # Округляем время окончания (оно же время начала следующего действия)
        end_time = round_to_next_15(datetime.now())
        start_time = state.current_activity['start_time']
        
        # Защита от нулевых интервалов (если быстро нажать)
        if end_time > start_time:
            saved = api_client.save_event(
                telegram_id=user_id,
                category_id=state.current_activity['id'],
                start_time=start_time,
                end_time=end_time
            )
            status = "✅ Сохранено" if saved else "❌ Ошибка сохранения"
            duration = end_time - start_time
            minutes = int(duration.total_seconds() / 60)
            
            message_parts.append(
                f"{status}: {state.current_activity['name']}\n"
                f"🕒 {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')} ({minutes} мин)"
            )
        else:
            message_parts.append(f"⚠️ Активность {state.current_activity['name']} слишком короткая, не сохранено.")
    
    # 2. Начинаем новую активность (если есть)
    if new_category:
        start_t = round_to_next_15(datetime.now())
        state.start_activity(new_category['id'], new_category['name'], start_t)
        message_parts.append(f"\n🚀 <b>СТАРТ: {new_category['name']}</b>\nВремя начала: {start_t.strftime('%H:%M')}")
    else:
        state.stop_activity()
        message_parts.append("\n🛑 Всё остановлено.")

    await update.message.reply_text("\n".join(message_parts), parse_mode='HTML')


async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = state_manager.get_state(user_id)
    text = update.message.text

    # Обновляем список категорий при каждом клике (на случай изменений на сайте)
    # Можно убрать, если нагрузка большая, но для теста полезно
    # categories = api_client.get_user_categories(user_id)
    # state_manager.update_categories(user_id, categories)

    if text == "⏹️ Остановить всё":
        await handle_activity_switch(update, state, new_category=None)
        return

    # Ищем категорию по имени
    category = next((c for c in state.categories if c['name'] == text), None)
    
    if category:
        await handle_activity_switch(update, state, new_category=category)
    else:
        # Если прислали текст, который не является категорией
        await update.message.reply_text("Выбери категорию из меню 👇")


async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cats = api_client.get_user_categories(user.id)
    
    state_manager.update_categories(user.id, cats)
    state = state_manager.get_state(user.id)
    
    await update.message.reply_text(
        f"Список обновлен! Доступно категорий: {len(cats)}", 
        reply_markup=get_categories_keyboard(state)
    )

def main():
    logger.info("Checking API...")
    # Небольшая пауза при старте, чтобы веб успел подняться
    time.sleep(2) 
    
    if api_client.check_connection():
        logger.info("✅ Connected to Web API")
    else:
        logger.warning("⚠️ Could not connect to Web API (will retry)")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("categories", categories_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category))
    
    logger.info("Bot started polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
