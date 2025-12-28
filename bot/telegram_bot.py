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

# Продолжение в следующем сообщении...
