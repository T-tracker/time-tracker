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
    # При старте пробуем имя из телеграма
    username_to_send = user.username if user.username else user.first_name
    
    await update.message.reply_text("🔎 Ищу твой аккаунт...")
    
    success, user_data = api_client.authenticate_telegram_user(user.id, username_to_send)
    
    if not success:
        await update.message.reply_text(
            "😞 Автоматический вход не сработал.\n"
            "Пожалуйста, напиши команду login с твоим именем на сайте:\n\n"
            "👉 `/login Maria`\n"
            "(Замени Maria на свой логин)",
            parse_mode='Markdown'
        )
        return

    await load_and_greet(update, user.id, user_data.get('username', 'User'))

async def manual_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Введи имя! Пример: `/login Maria`", parse_mode='Markdown')
        return

    site_username = context.args[0]
    user_id = update.effective_user.id
    
    await update.message.reply_text(f"🔄 Пробую привязать аккаунт '{site_username}'...")
    
    # Принудительно отправляем имя с сайта
    success, user_data = api_client.authenticate_telegram_user(user_id, site_username)
    
    if success:
        # Проверяем, совпало ли имя
        real_name = user_data.get('username')
        if real_name.lower() == site_username.lower():
            await update.message.reply_text("✅ Успешно привязано!")
            await load_and_greet(update, user_id, real_name)
        else:
            await update.message.reply_text(f"🤨 Странно, сервер вернул имя '{real_name}'. Попробуй еще раз.")
    else:
        await update.message.reply_text(f"❌ Пользователь '{site_username}' не найден на сайте. Проверь регистр и создала ли ты аккаунт.")

async def load_and_greet(update, telegram_id, username):
    categories = api_client.get_user_categories(telegram_id)
    state_manager.update_categories(telegram_id, categories)
    state = state_manager.get_state(telegram_id)
    
    if not categories:
        await update.message.reply_text(
            f"👋 Привет, {username}!\n"
            "⚠️ Я вошел в аккаунт, но категорий в нем нет.\n"
            "Если ты уверена, что они есть - значит я вошел не в тот аккаунт.\n"
            "Напиши `/login ТВОЕ_ТОЧНОЕ_ИМЯ`"
        )
        return

    keyboard = get_categories_keyboard(state)
    await update.message.reply_text(
        f"👋 Привет, {username}!\nНайдено категорий: {len(categories)}", 
        reply_markup=keyboard
    )

def get_categories_keyboard(state):
    if not state.categories: return ReplyKeyboardRemove()
    names = [c['name'] for c in state.categories]
    buttons = [names[i:i+2] for i in range(0, len(names), 2)]
    buttons.append(["⏹️ Остановить всё"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

async def handle_activity_switch(update, state, new_category=None):
    user_id = update.effective_user.id
    message_parts = []
    
    if state.current_activity:
        end_time = round_to_next_15(datetime.now())
        start_time = state.current_activity['start_time']
        
        if end_time > start_time:
            saved = api_client.save_event(
                telegram_id=user_id,
                category_id=state.current_activity['id'],
                start_time=start_time,
                end_time=end_time
            )
            status = "✅ Сохранено" if saved else "❌ Ошибка сохранения"
            
            diff = end_time - start_time
            minutes = int(diff.total_seconds() / 60)
            
            message_parts.append(
                f"{status}: {state.current_activity['name']}\n"
                f"🕒 {minutes} мин"
            )
        else:
            message_parts.append(f"⚠️ {state.current_activity['name']} - слишком короткая запись.")
    
    if new_category:
        start_t = round_to_next_15(datetime.now())
        state.start_activity(new_category['id'], new_category['name'], start_t)
        message_parts.append(f"🚀 <b>{new_category['name']}</b> начата в {start_t.strftime('%H:%M')}")
    else:
        state.stop_activity()
        message_parts.append("🛑 Стоп.")

    await update.message.reply_text("\n".join(message_parts), parse_mode='HTML')

async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = state_manager.get_state(user_id)
    text = update.message.text

    if text == "⏹️ Остановить всё":
        await handle_activity_switch(update, state, new_category=None)
        return

    category = next((c for c in state.categories if c['name'] == text), None)
    if category:
        await handle_activity_switch(update, state, new_category=category)
    else:
        # Если прислали текст, которого нет в кнопках, может это попытка логина?
        if text.lower().startswith("login"):
             await update.message.reply_text("Для входа используй команду слэш: `/login Имя`", parse_mode='Markdown')
        else:
             await update.message.reply_text("Выбери категорию из меню.")

def main():
    logger.info("Checking API...")
    time.sleep(3) 
    if api_client.check_connection():
        logger.info("✅ API Online")
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", manual_login))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category))
    
    app.run_polling()

if __name__ == "__main__":
    main()
