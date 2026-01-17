import logging
import time
from datetime import datetime
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from bot.config import BOT_TOKEN
from bot.states import state_manager
from bot.utils import round_to_next_15, get_local_now
from bot.api_client import api_client

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ==========================
#     ВСПОМОГАТЕЛЬНОЕ
# ==========================

def get_categories_keyboard(state):
    """Собираем клавиатуру из категорий + кнопка стопа."""
    if not state.categories:
        return ReplyKeyboardRemove()

    names = [c['name'] for c in state.categories]
    # Делаем по 2 кнопки в ряд
    buttons = [names[i:i + 2] for i in range(0, len(names), 2)]
    buttons.append(["⏹️ Остановить всё"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


async def send_help(update: Update):
    """Отдельное сообщение со всеми функциями бота."""
    text = (
        "✨ <b>Что я умею</b>\n\n"
        "1️⃣ <b>Отслеживать время по категориям</b>\n"
        "   • Нажимаешь кнопку с категорией — я запускаю трекинг.\n"
        "   • Нажимаешь другую категорию — предыдущая закрывается,\n"
        "     время записывается в расписание (колонка «Факт»).\n"
        "   • Всё округляется по 15 минут:\n"
        "     ─ старт: в большую сторону (14:32 → 14:45)\n"
        "     ─ конец: тоже в большую сторону (15:17 → 15:30)\n\n"
        "2️⃣ <b>Команды</b>\n"
        "   • <code>/start</code> – войти и показать категории.\n"
        "   • <code>/login ИМЯ</code> – если автологин не сработал.\n"
        "   • <code>/refresh</code> – обновить список категорий из сайта.\n"
        "   • <code>/help</code> – показать это описание.\n\n"
        "3️⃣ <b>Кнопки</b>\n"
        "   • Категории – запуск / переключение активности.\n"
        "   • «⏹️ Остановить всё» – завершить текущую активность без запуска новой.\n\n"
        "Всё, что я сохраняю, видно в веб-приложении в колонке <b>«Факт»</b> расписания 🗓️"
    )
    await update.message.reply_text(text, parse_mode="HTML")


# ==========================
#   АВТОРИЗАЦИЯ / СТАРТ
# ==========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start:
      1) Пытаемся авторизоваться по username/first_name.
      2) Если получилось — грузим категории, показываем клавиатуру и help.
      3) Если нет — объясняем, как использовать /login.
    """
    user = update.effective_user
    username_to_send = user.username if user.username else user.first_name

    await update.message.reply_text("🔎 Ищу твой аккаунт...")

    success, user_data = api_client.authenticate_telegram_user(user.id, username_to_send)

    if not success:
        await update.message.reply_text(
            "😞 Автоматический вход не сработал.\n"
            "Пожалуйста, напиши команду login с твоим именем на сайте:\n\n"
            "👉 <code>/login Maria</code>\n"
            "(замени <code>Maria</code> на свой логин)",
            parse_mode='HTML'
        )
        return

    await load_and_greet(update, user.id, user_data.get('username', 'User'))
    await send_help(update)


async def manual_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /login ИМЯ_С_САЙТА – привязка телеграм-аккаунта к пользователю на сайте.
    """
    if not context.args:
        await update.message.reply_text(
            "⚠️ Введи имя! Пример: <code>/login Maria</code>",
            parse_mode='HTML'
        )
        return

    site_username = context.args[0]
    user_id = update.effective_user.id

    await update.message.reply_text(f"🔄 Пробую привязать аккаунт '{site_username}'...")

    success, user_data = api_client.authenticate_telegram_user(user_id, site_username)

    if success:
        real_name = user_data.get('username')
        if real_name and real_name.lower() == site_username.lower():
            await update.message.reply_text("✅ Успешно привязано!")
            await load_and_greet(update, user_id, real_name)
            await send_help(update)
        else:
            await update.message.reply_text(
                f"🤨 Странно, сервер вернул имя '{real_name}'. Попробуй еще раз."
            )
    else:
        await update.message.reply_text(
            f"❌ Пользователь '{site_username}' не найден на сайте.\n"
            "Проверь регистр и создала ли ты аккаунт."
        )


async def load_and_greet(update: Update, telegram_id: int, username: str):
    """
    Грузим категории из API, сохраняем в state, показываем клавиатуру.
    """
    categories = api_client.get_user_categories(telegram_id)
    state_manager.update_categories(telegram_id, categories)
    state = state_manager.get_state(telegram_id)

    if not categories:
        await update.message.reply_text(
            f"👋 Привет, {username}!\n"
            "⚠️ Я вошёл в аккаунт, но категорий в нём нет.\n"
            "Если ты уверена, что они есть, значит я вошёл не в тот аккаунт.\n"
            "Напиши <code>/login ТВОЕ_ТОЧНОЕ_ИМЯ</code>",
            parse_mode='HTML'
        )
        return

    keyboard = get_categories_keyboard(state)
    await update.message.reply_text(
        f"👋 Привет, {username}!\nНайдено категорий: {len(categories)}.",
        reply_markup=keyboard
    )


# ==========================
#    ОБНОВЛЕНИЕ КАТЕГОРИЙ
# ==========================

async def refresh_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /refresh – явно перезагрузить категории из веб-приложения.
    Полезно, если пользователь добавил/удалил категории на сайте.
    """
    user_id = update.effective_user.id
    await update.message.reply_text("🔄 Обновляю категории из профиля...")

    categories = api_client.get_user_categories(user_id)
    state_manager.update_categories(user_id, categories)
    state = state_manager.get_state(user_id)

    if not categories:
        await update.message.reply_text(
            "⚠️ Категорий с сайта не получено.\n"
            "Проверь, что они созданы в веб-приложении."
        )
        return

    keyboard = get_categories_keyboard(state)
    await update.message.reply_text(
        f"✅ Обновлено! Сейчас категорий: {len(categories)}",
        reply_markup=keyboard
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /help – просто показывает описание функций."""
    await send_help(update)


# ==========================
#     ЛОГИКА АКТИВНОСТЕЙ
# ==========================

async def handle_activity_switch(update: Update, state, new_category=None):
    """
    - Если уже что-то трекается:
        * заканчиваем его в момент сообщения,
        * округляя конец ВВЕРХ до 15 минут (по локальному времени),
        * сохраняем факт-событие через API.
    - Если передан new_category:
        * стартуем новую категорию с ВРЕМЕНИ ВВЕРХ до ближайших 15 минут (локально).
    - Если new_category=None:
        * просто стопим текущую активность.
    """
    user_id = update.effective_user.id
    message_parts = []

    # 1. Закрываем текущую активность, если она есть
    if state.is_tracking and state.start_time and state.current_category_id:
        # конец фиксируем по локальному времени пользователя
        end_time = round_to_next_15(get_local_now())
        start_time = state.start_time

        if end_time > start_time:
            saved = api_client.save_event(
                telegram_id=user_id,
                category_id=state.current_category_id,
                start_time=start_time,
                end_time=end_time
            )
            status = "✅ Сохранено" if saved else "❌ Ошибка сохранения"

            diff = end_time - start_time
            minutes = int(diff.total_seconds() / 60)

            message_parts.append(
                f"{status}: {state.current_category_name}\n"
                f"🕒 {minutes} мин "
                f"({start_time.strftime('%H:%M')}–{end_time.strftime('%H:%M')})"
            )
        else:
            message_parts.append(
                f"⚠️ {state.current_category_name} — слишком короткая запись."
            )

    # 2. Стартуем новую активность или стопим
    if new_category:
        # старт тоже по локальному времени пользователя
        start_t = round_to_next_15(get_local_now())
        state.start_activity(new_category['id'], new_category['name'], start_t)
        message_parts.append(
            f"🚀 <b>{new_category['name']}</b> начата в {start_t.strftime('%H:%M')}"
        )
    else:
        state.stop_activity()
        message_parts.append("🛑 Остановлено.")

    # сохраняем состояние на диск
    state_manager.save_states()

    await update.message.reply_text("\n".join(message_parts), parse_mode='HTML')


async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка обычного текстового сообщения:
      - если это кнопка «⏹️ Остановить всё» — просто стоп;
      - если совпало с названием категории — переключаемся;
      - если это что-то ещё — подсказываем про /login или /help.
    """
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
        if text.lower().startswith("login"):
            await update.message.reply_text(
                "Для входа используй команду со слэшем: <code>/login Имя</code>",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "Я тебя не понял 🙈\n"
                "Выбери категорию из клавиатуры или напиши <code>/help</code>.",
                parse_mode='HTML'
            )


# ==========================
#          MAIN
# ==========================

def main():
    logger.info("Checking API...")
    time.sleep(3)
    if api_client.check_connection():
        logger.info("✅ API Online")

    app = Application.builder().token(BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", manual_login))
    app.add_handler(CommandHandler("refresh", refresh_categories))
    app.add_handler(CommandHandler("help", help_command))

    # Любой текст – обработка категорий / стопа
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category))

    app.run_polling()


if __name__ == "__main__":
    main()
