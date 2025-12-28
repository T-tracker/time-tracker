import logging
import asyncio
from datetime import datetime, timedelta
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler, 
    MessageHandler,
    filters,
    ContextTypes,
    CallbackContext,
    CallbackQueryHandler
)

from bot.config import BOT_TOKEN
from bot.states import state_manager
from bot.utils import round_to_next_15, calculate_15min_slots
from bot.api_client import api_client  # Новый импорт

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start с авторизацией"""
    user = update.effective_user
    telegram_id = user.id
    
    # Проверяем авторизацию
    state = state_manager.get_state(telegram_id)
    
    if not state.api_user_data:
        # Пытаемся авторизоваться
        success, user_data = api_client.authenticate_telegram_user(
            telegram_id=telegram_id,
            username=user.username or user.first_name
        )
        
        if not success:
            if 'needs_registration' in user_data:
                # Пользователь не зарегистрирован в веб-приложении
                registration_url = user_data.get('registration_url', 'https://time-tracker-z6co.onrender.com/register')
                await update.message.reply_text(
                    f"👋 Привет, {user.first_name}!\n\n"
                    f"📝 *Требуется регистрация в веб-приложении*\n"
                    f"Для использования бота нужно:\n"
                    f"1. Зарегистрироваться здесь: {registration_url}\n"
                    f"2. В профиле указать Telegram ID: `{telegram_id}`\n"
                    f"3. Создать хотя бы одну категорию\n\n"
                    f"После этого возвращайся в бот! ✅",
                    parse_mode='Markdown',
                    reply_markup=ReplyKeyboardRemove()
                )
                return
            else:
                # Ошибка подключения
                await update.message.reply_text(
                    "⚠️ *Ошибка подключения*\n"
                    "Не могу соединиться с сервером. Попробуйте позже.",
                    parse_mode='Markdown'
                )
                return
        
        # Сохраняем данные пользователя
        state_manager.update_user_data(telegram_id, user_data)
        state = state_manager.get_state(telegram_id)  # Обновляем state
        
        # Загружаем категории пользователя
        if user_data.get('has_categories'):
            categories = api_client.get_user_categories(state.user_id)
            state_manager.update_categories(telegram_id, categories)
    
    # Приветствие после успешной авторизации
    await send_welcome_message(update, state)

async def send_welcome_message(update: Update, state):
    """Отправка приветственного сообщения"""
    user = update.effective_user
    
    # Получаем актуальные категории
    categories = api_client.get_user_categories(state.user_id)
    state_manager.update_categories(user.id, categories)
    
    if not categories:
        # У пользователя нет категорий
        await update.message.reply_text(
            f"👋 Добро пожаловать, {user.first_name}!\n\n"
            f"📝 *Создайте категории в веб-приложении*\n"
            f"Для использования бота нужно:\n"
            f"1. Зайдите в веб-приложение\n"
            f"2. Создайте категории в разделе 'Категории'\n"
            f"3. Вернитесь в бот и нажмите /start\n\n"
            f"📲 *Бот будет:*\n"
            f"• Отслеживать время с округлением до 15 мин\n"
            f"• Заполнять колонку 'Факт' в расписании\n"
            f"• Сохранять все данные в вашем аккаунте",
            parse_mode='Markdown',
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Формируем клавиатуру с категориями пользователя
    keyboard = get_categories_keyboard(state)
    
    await update.message.reply_text(
        f"👋 *С возвращением, {user.first_name}!*\n\n"
        f"📊 *Ваши категории:* {len(categories)} шт.\n"
        f"⏱️ *Округление:* до 15 минут\n"
        f"💾 *Сохранение:* в вашем расписании\n\n"
        f"📌 *Как использовать:*\n"
        f"1. Выбери категорию - начнётся отсчёт\n"
        f"2. Когда закончишь - выбери новую\n"
        f"3. Время округляется автоматически\n\n"
        f"📱 *Команды:*\n"
        f"/status - текущая активность\n"
        f"/stats - статистика\n"
        f"/stop - остановить всё\n"
        f"/categories - обновить категории",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

def get_categories_keyboard(state) -> ReplyKeyboardMarkup:
    """Создаёт клавиатуру с категориями пользователя"""
    if not state.categories:
        return ReplyKeyboardRemove()
    
    # Берем только названия категорий
    category_names = [cat['name'] for cat in state.categories[:10]]  # Ограничиваем 10
    
    # Добавляем кнопку остановки
    category_names.append("⏹️ Остановить всё")
    
    # Разбиваем на строки по 2 кнопки
    keyboard = [category_names[i:i+2] for i in range(0, len(category_names), 2)]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора категории"""
    user = update.effective_user
    telegram_id = user.id
    selected_category_name = update.message.text
    current_time = datetime.now()
    
    state = state_manager.get_state(telegram_id)
    
    # Проверяем авторизацию
    if not state.api_user_data:
        await update.message.reply_text(
            "⚠️ *Требуется авторизация*\n"
            "Пожалуйста, нажмите /start",
            parse_mode='Markdown'
        )
        return
    
    # Обработка кнопки "Остановить всё"
    if selected_category_name == "⏹️ Остановить всё":
        if state.is_tracking:
            await stop_current_activity(update, state, current_time, telegram_id)
        else:
            await update.message.reply_text("Сейчас ничего не отслеживается.")
        return
    
    # Ищем выбранную категорию
    selected_category = None
    for cat in state.categories:
        if cat['name'] == selected_category_name:
            selected_category = cat
            break
    
    if not selected_category:
        await update.message.reply_text(
            f"❌ *Категория не найдена*\n"
            f"'{selected_category_name}' не найдена в вашем списке.\n"
            f"Используйте /categories для обновления списка.",
            parse_mode='Markdown'
        )
        return
    
    # Округляем время начала
    start_time = round_to_next_15(current_time)
    
    # Если есть активная категория - завершаем её
    if state.is_tracking and state.current_category_id:
        await finish_previous_activity(update, state, current_time, telegram_id)
    
    # Начинаем новую активность
    state.start_activity(
        category_id=selected_category['id'],
        category_name=selected_category['name'],
        start_time=start_time
    )
    state_manager.save_states()
    
    # Уведомление пользователя
    await send_activity_started_message(update, selected_category, start_time, current_time, context)

async def send_activity_started_message(update: Update, category: dict, start_time: datetime, 
                                       current_time: datetime, context: ContextTypes.DEFAULT_TYPE):
    """Отправка сообщения о начале активности"""
    delay = (start_time - current_time).total_seconds()
    
    if delay > 60:  # Если начало через больше минуты
        message = (
            f"⏳ **Запланировано:** {category['name']}\n"
            f"🕐 Начнётся в: {start_time.strftime('%H:%M')}\n"
            f"⏱️ Через: {int(delay/60)} минут\n\n"
            f"_Продолжай свои дела до {start_time.strftime('%H:%M')}_"
        )
        await update.message.reply_text(message, parse_mode='Markdown')
    else:
        message = (
            f"🚀 **Начата активность:** {category['name']}\n"
            f"🕐 Время: {start_time.strftime('%H:%M')}\n"
            f"🎨 Цвет: {category.get('color', '#4361ee')}\n\n"
            f"_Работай продуктивно!_"
        )
        await update.message.reply_text(message, parse_mode='Markdown')
    
    # Напоминание через 4 часа
    warning_time = start_time + timedelta(hours=4)
    context.job_queue.run_once(
        send_long_activity_warning,
        when=warning_time,
        data={'telegram_id': update.effective_user.id, 
              'chat_id': update.effective_chat.id, 
              'category_name': category['name']},
        name=f"warning_{update.effective_user.id}"
    )

async def finish_previous_activity(update: Update, state, end_time: datetime, telegram_id: int):
    """Завершает предыдущую активность и сохраняет через API"""
    if not state.start_time or not state.current_category_id:
        return
    
    # Округляем время окончания
    rounded_end = round_to_next_15(end_time)
    
    # Сохраняем событие через API
    success, result = api_client.create_event(
        user_id=state.user_id,
        category_id=state.current_category_id,
        start_time=state.start_time,
        end_time=rounded_end,
        event_type='fact',
        description=f"Автоматически создано ботом"
    )
    
    if success:
        duration_minutes = int((rounded_end - state.start_time).total_seconds() / 60)
        
        await update.message.reply_text(
            f"✅ **Завершено:** {state.current_category_name}\n"
            f"⏱️ Длительность: {duration_minutes} мин.\n"
            f"🕐 Время: {state.start_time.strftime('%H:%M')} - {rounded_end.strftime('%H:%M')}\n"
            f"💾 Сохранено в ваше расписание\n\n"
            f"_Хорошая работа!_ ✨",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"⚠️ **Завершено:** {state.current_category_name}\n"
            f"❌ *Ошибка сохранения:* {result.get('error', 'Unknown error')}\n"
            f"Активность завершена, но не сохранена.",
            parse_mode='Markdown'
        )
    
    # Останавливаем активность в состоянии
    state.stop_activity()
    state_manager.save_states()

async def stop_current_activity(update: Update, state, end_time: datetime, telegram_id: int):
    """Остановить текущую активность"""
    if state.is_tracking:
        await finish_previous_activity(update, state, end_time, telegram_id)
    
    # Очищаем напоминания
    await clear_user_jobs(update, context)
    
    await update.message.reply_text(
        "🛑 Все активности остановлены.",
        reply_markup=get_categories_keyboard(state)
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Текущий статус"""
    user = update.effective_user
    telegram_id = user.id
    state = state_manager.get_state(telegram_id)
    
    # Проверяем авторизацию
    if not state.api_user_data:
        await update.message.reply_text(
            "⚠️ *Требуется авторизация*\n"
            "Пожалуйста, нажмите /start",
            parse_mode='Markdown'
        )
        return
    
    if state.is_tracking:
        current_time = datetime.now()
        duration = (current_time - state.start_time).total_seconds() / 60
        hours = int(duration // 60)
        minutes = int(duration % 60)
        
        message = (
            f"📊 **Текущий статус:**\n\n"
            f"📌 Активность: {state.current_category_name}\n"
            f"⏱️ Длительность: {hours}ч {minutes}м\n"
            f"🕐 Начало: {state.start_time.strftime('%H:%M')}\n"
            f"📅 Дата: {state.start_time.strftime('%d.%m.%Y')}\n"
            f"🆔 ID категории: {state.current_category_id}\n\n"
        )
        
        if duration > 240:  # 4 часа
            message += "⚠️ *Активность длится более 4 часов!*\n"
        
        message += "_Используй кнопки ниже для управления_"
    else:
        message = (
            f"📊 **Статус:** Отслеживание не активно\n\n"
            f"👤 Пользователь: {state.api_user_data.get('username', 'Unknown')}\n"
            f"📂 Категорий: {len(state.categories)} шт.\n\n"
            f"Выбери категорию чтобы начать! 🚀"
        )
    
    await update.message.reply_text(
        message, 
        parse_mode='Markdown', 
        reply_markup=get_categories_keyboard(state)
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика (упрощённая версия - нужно будет доработать с API)"""
    user = update.effective_user
    telegram_id = user.id
    state = state_manager.get_state(telegram_id)
    
    if not state.api_user_data:
        await update.message.reply_text(
            "⚠️ *Требуется авторизация*\n"
            "Пожалуйста, нажмите /start",
            parse_mode='Markdown'
        )
        return
    
    # TODO: Реализовать получение статистики через API
    # Пока простой ответ
    if state.is_tracking:
        current_time = datetime.now()
        duration = int((current_time - state.start_time).total_seconds() / 60)
        
        message = (
            f"📊 **Текущая активность:**\n\n"
            f"• {state.current_category_name}\n"
            f"• Длится: {duration} минут\n"
            f"• Начало: {state.start_time.strftime('%H:%M')}\n\n"
            f"📈 *Полная статистика скоро будет доступна*"
        )
    else:
        message = (
            f"📊 **Статистика**\n\n"
            f"Сейчас активностей нет.\n"
            f"Все данные сохраняются в вашем расписании.\n\n"
            f"📲 *В будущем:*\n"
            f"• Статистика за день/неделю\n"
            f"• Графики активности\n"
            f"• Отчёты по категориям"
        )
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновить список категорий"""
    user = update.effective_user
    telegram_id = user.id
    state = state_manager.get_state(telegram_id)
    
    if not state.api_user_data:
        await update.message.reply_text(
            "⚠️ *Требуется авторизация*\n"
            "Пожалуйста, нажмите /start",
            parse_mode='Markdown'
        )
        return
    
    # Загружаем свежие категории
    categories = api_client.get_user_categories(state.user_id)
    state_manager.update_categories(telegram_id, categories)
    
    if not categories:
        await update.message.reply_text(
            "📝 *Категории не найдены*\n\n"
            "Создайте категории в веб-приложении:\n"
            "1. Зайдите в раздел 'Категории'\n"
            "2. Создайте нужные категории\n"
            "3. Вернитесь в бот\n\n"
            "Без категорий бот не сможет работать.",
            parse_mode='Markdown'
        )
        return
    
    # Формируем список категорий
    category_list = "\n".join([f"• {cat['name']} ({cat.get('color', '#4361ee')})" 
                              for cat in categories[:15]])  # Показываем первые 15
    
    if len(categories) > 15:
        category_list += f"\n• ... и ещё {len(categories) - 15} категорий"
    
    await update.message.reply_text(
        f"📂 **Ваши категории:** {len(categories)} шт.\n\n"
        f"{category_list}\n\n"
        f"📌 *Как использовать:*\n"
        f"Просто выберите категорию из клавиатуры ниже",
        parse_mode='Markdown',
        reply_markup=get_categories_keyboard(state)
    )

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stop - остановить всё"""
    user = update.effective_user
    telegram_id = user.id
    state = state_manager.get_state(telegram_id)
    current_time = datetime.now()
    
    if not state.api_user_data:
        await update.message.reply_text(
            "⚠️ *Требуется авторизация*\n"
            "Пожалуйста, нажмите /start",
            parse_mode='Markdown'
        )
        return
    
    if state.is_tracking:
        await stop_current_activity(update, state, current_time, telegram_id)
    else:
        await update.message.reply_text(
            "✅ Сейчас ничего не отслеживается.\n"
            "Все активности уже остановлены.",
            reply_markup=get_categories_keyboard(state)
        )

async def clear_user_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очистить все jobs для пользователя"""
    user = update.effective_user
    
    # Очищаем напоминания
    reminder_jobs = context.job_queue.get_jobs_by_name(f"reminder_{user.id}")
    for job in reminder_jobs:
        job.schedule_removal()
    
    # Очищаем предупреждения
    warning_jobs = context.job_queue.get_jobs_by_name(f"warning_{user.id}")
    for job in warning_jobs:
        job.schedule_removal()
    
    logger.info(f"Cleared jobs for user {user.id}")

async def send_long_activity_warning(context: ContextTypes.DEFAULT_TYPE):
    """Предупреждение о слишком длинной активности"""
    job = context.job
    telegram_id = job.data['telegram_id']
    chat_id = job.data['chat_id']
    category_name = job.data['category_name']
    
    state = state_manager.get_state(telegram_id)
    if state.is_tracking and state.current_category_name == category_name:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ **Внимание!**\n"
                 f"Активность '{category_name}' длится уже 4 часа.\n"
                 f"Может, стоит сделать перерыв? ☕",
            parse_mode='Markdown'
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ *Произошла ошибка*\n"
                "Попробуйте ещё раз или нажмите /start",
                parse_mode='Markdown'
            )
    except:
        pass

def main():
    """Основная функция запуска бота"""
    # Очищаем просроченные состояния при старте
    state_manager.cleanup_expired()
    
    # Проверяем подключение к API
    logger.info("Checking API connection...")
    if api_client.check_connection():
        logger.info("✅ API connection successful")
    else:
        logger.warning("⚠️ API connection failed - some features may not work")
    
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("categories", categories_command))
    application.add_handler(CommandHandler("stop", stop_command))
    
    # Обработчик выбора категории
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_category
    ))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    logger.info("🤖 Bot starting...")
    application.run_polling()

def run():
    """Функция для запуска бота извне"""
    main()

№if __name__ == '__main__':
  #  run()
