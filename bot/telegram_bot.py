import logging
import asyncio
from datetime import datetime, timedelta
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler, 
    MessageHandler,
    filters,
    ContextTypes,
    CallbackContext
)
from collections import defaultdict

from bot.config import BOT_TOKEN
from bot.states import state_manager
from bot.utils import round_to_next_15, calculate_15min_slots

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Категории по умолчанию
DEFAULT_CATEGORIES = [
    "💼 Работа",
    "📚 Учёба", 
    "🏃 Спорт",
    "🎮 Отдых",
    "🍽️ Еда",
    "🚌 Транспорт",
    "⏹️ Остановить всё"
]

# Хранилище завершённых активностей (временное, до подключения бэкенда)
activity_history = defaultdict(list)  # user_id -> list of activities

def get_categories_keyboard():
    keyboard = [DEFAULT_CATEGORIES[i:i+2] for i in range(0, len(DEFAULT_CATEGORIES), 2)]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

async def start(update, context):
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "📌 **Доступные команды:**\n"
        "/start - это сообщение\n"
        "/status - текущая активность\n"
        "/stats - статистика за сегодня\n"
        "/export - экспорт всех активностей\n"
        "/cancel - остановить всё\n\n"
        "📱 **Как использовать:**\n"
        "1. Выбери категорию - начнётся отсчёт\n"
        "2. Когда закончишь - выбери новую\n"
        "3. Всё округляется до 15 минут\n\n"
        "⏰ **Напоминания:**\n"
        "• Бот предупредит, если активность > 4 часов\n"
        "• Начало в следующий 15-минутный слот",
        parse_mode='Markdown',
        reply_markup=get_categories_keyboard()
    )

async def handle_category(update, context):
    user = update.effective_user
    category = update.message.text
    current_time = datetime.now()
    
    state = state_manager.get_state(user.id)
    state.last_update = current_time
    
    # Остановка
    if category == "⏹️ Остановить всё":
        if state.is_tracking:
            await stop_current_activity(update, state, current_time)
        else:
            await update.message.reply_text("Сейчас ничего не отслеживается.")
        return
    
    # Завершаем предыдущую активность если есть
    if state.is_tracking and state.current_category:
        await finish_previous_activity(update, state, current_time, user.id)
    
    # Начинаем новую
    start_time = round_to_next_15(current_time)
    state.start_activity(category, start_time)
    
    # Уведомление о начале
    delay = (start_time - current_time).total_seconds()
    
    if delay > 60:  # Если начало через больше минуты
        message = (
            f"⏳ **Запланировано:** {category}\n"
            f"🕐 Начнётся в: {start_time.strftime('%H:%M')}\n"
            f"⏱️ Через: {int(delay/60)} минут\n\n"
            f"_Продолжай свои дела до {start_time.strftime('%H:%M')}_"
        )
        await update.message.reply_text(message, parse_mode='Markdown')
        
        # Напоминание когда время наступит
        reminder_time = start_time - timedelta(seconds=10)
        context.job_queue.run_once(
            send_reminder,
            when=reminder_time,
            data={'user_id': user.id, 'category': category, 'chat_id': update.effective_chat.id},
            name=f"reminder_{user.id}"
        )
    else:
        message = (
            f"🚀 **Начата активность:** {category}\n"
            f"🕐 Время: {start_time.strftime('%H:%M')}\n\n"
            f"_Работай продуктивно! Когда закончишь - выбери новую категорию_"
        )
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=get_categories_keyboard())
    
    # Напоминание через 4 часа
    warning_time = start_time + timedelta(hours=4)
    context.job_queue.run_once(
        send_long_activity_warning,
        when=warning_time,
        data={'user_id': user.id, 'chat_id': update.effective_chat.id, 'category': category},
        name=f"warning_{user.id}"
    )
    
    state_manager.save_states()

async def send_reminder(context):
    """Напоминание о начале активности"""
    job = context.job
    user_id = job.data['user_id']
    category = job.data['category']
    chat_id = job.data['chat_id']
    
    state = state_manager.get_state(user_id)
    if state.is_tracking and state.current_category == category:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ **Время начать:** {category}\n"
                 f"Активность началась! Удачи! 🚀",
            parse_mode='Markdown'
        )

async def send_long_activity_warning(context):
    """Предупреждение о слишком длинной активности"""
    job = context.job
    user_id = job.data['user_id']
    chat_id = job.data['chat_id']
    category = job.data['category']
    
    state = state_manager.get_state(user_id)
    if state.is_tracking and state.current_category == category:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ **Внимание!**\n"
                 f"Активность '{category}' длится уже 4 часа.\n"
                 f"Может, стоит сделать перерыв? ☕",
            parse_mode='Markdown'
        )

async def finish_previous_activity(update, state, end_time: datetime, user_id: int):
    """Завершает предыдущую активность и сохраняет историю"""
    if not state.start_time:
        return
    
    rounded_end = round_to_next_15(end_time)
    slots = calculate_15min_slots(state.start_time, rounded_end)
    
    # Сохраняем в историю
    activity = {
        'category': state.current_category,
        'start': state.start_time,
        'end': rounded_end,
        'duration': (rounded_end - state.start_time).total_seconds() / 60,
        'slots': len(slots)
    }
    activity_history[user_id].append(activity)
    
    # Уведомляем пользователя
    duration_minutes = int((rounded_end - state.start_time).total_seconds() / 60)
    slots_text = f"{len(slots)} × 15 мин." if len(slots) > 1 else "15 мин."
    
    await update.message.reply_text(
        f"✅ **Завершено:** {state.current_category}\n"
        f"⏱️ Длительность: {duration_minutes} мин. ({slots_text})\n"
        f"🕐 Время: {state.start_time.strftime('%H:%M')} - {rounded_end.strftime('%H:%M')}\n\n"
        f"_Хорошая работа!_ ✨",
        parse_mode='Markdown'
    )
    
    # Логируем
    logger.info(f"User {user_id} finished {state.current_category}: {duration_minutes}min")
    state.stop_activity()

async def stop_current_activity(update, state, end_time: datetime):
    await finish_previous_activity(update, state, end_time, update.effective_user.id)
    await update.message.reply_text(
        "🛑 Все активности остановлены.",
        reply_markup=get_categories_keyboard()
    )

async def status(update, context):
    """Текущий статус"""
    user = update.effective_user
    state = state_manager.get_state(user.id)
    
    if state.is_tracking:
        current_time = datetime.now()
        duration = (current_time - state.start_time).total_seconds() / 60
        hours = int(duration // 60)
        minutes = int(duration % 60)
        
        message = (
            f"📊 **Текущий статус:**\n\n"
            f"📌 Активность: {state.current_category}\n"
            f"⏱️ Длительность: {hours}ч {minutes}м\n"
            f"🕐 Начало: {state.start_time.strftime('%H:%M')}\n"
            f"📅 Дата: {state.start_time.strftime('%d.%m.%Y')}\n\n"
        )
        
        if duration > 240:  # 4 часа
            message += "⚠️ *Активность длится более 4 часов!*\n"
        
        message += "_Используй кнопки ниже для управления_"
    else:
        today_activities = activity_history.get(user.id, [])
        total_today = sum(a['duration'] for a in today_activities)
        
        message = (
            f"📊 **Статус:** Отслеживание не активно\n"
            f"📈 Сегодня: {int(total_today)} мин. ({len(today_activities)} активностей)\n\n"
            f"Выбери категорию чтобы начать! 🚀"
        )
    
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=get_categories_keyboard())

async def stats_command(update, context):
    """Статистика за сегодня"""
    user = update.effective_user
    today = datetime.now().date()
    
    # Фильтруем сегодняшние активности
    today_activities = [
        a for a in activity_history.get(user.id, [])
        if a['start'].date() == today
    ]
    
    if not today_activities:
        await update.message.reply_text(
            "📊 **Статистика за сегодня**\n"
            "Активностей ещё нет. Начни отслеживать! 🚀",
            parse_mode='Markdown'
        )
        return
    
    # Группируем по категориям
    category_stats = {}
    for activity in today_activities:
        cat = activity['category']
        if cat not in category_stats:
            category_stats[cat] = 0
        category_stats[cat] += activity['duration']
    
    # Формируем сообщение
    total_minutes = sum(category_stats.values())
    total_hours = total_minutes / 60
    
    message = f"📊 **Статистика за {today.strftime('%d.%m.%Y')}**\n\n"
    message += f" Всего времени: {int(total_minutes)} мин. ({total_hours:.1f} ч)\n"
    message += f" Активностей: {len(today_activities)}\n\n"
    
    # Сортируем по убыванию времени
    sorted_categories = sorted(category_stats.items(), key=lambda x: x[1], reverse=True)
    
    for category, minutes in sorted_categories:
        hours = minutes / 60
        percentage = (minutes / total_minutes * 100) if total_minutes > 0 else 0
        message += f"• {category}: {int(minutes)} мин. ({hours:.1f} ч) - {percentage:.1f}%\n"
    
    message += f"\n_Хорошая продуктивность! 💪_"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def export_command(update, context):
    """Экспорт всех сегодняшних активностей"""
    user = update.effective_user
    today = datetime.now().date()
    
    today_activities = [
        a for a in activity_history.get(user.id, [])
        if a['start'].date() == today
    ]
    
    if not today_activities:
        await update.message.reply_text(
            "📋 **Экспорт активностей**\n"
            "Сегодня активностей ещё нет.",
            parse_mode='Markdown'
        )
        return
    
    # Формируем текстовый экспорт
    export_text = f"📋 АКТИВНОСТИ ЗА {today.strftime('%d.%m.%Y')}\n"
    export_text += "=" * 40 + "\n\n"
    
    for i, activity in enumerate(today_activities, 1):
        start_time = activity['start'].strftime('%H:%M')
        end_time = activity['end'].strftime('%H:%M')
        duration = int(activity['duration'])
        
        export_text += f"{i}. {activity['category']}\n"
        export_text += f"   Время: {start_time} - {end_time} ({duration} мин.)\n"
        export_text += f"   Слотов: {activity['slots']} × 15 мин.\n"
        
        # Добавляем прогресс-бар
        slots_visual = "█" * min(activity['slots'], 10)  # Максимум 10 блоков
        if activity['slots'] > 10:
            slots_visual += f" (+{activity['slots']-10})"
        export_text += f"   [{slots_visual}]\n\n"
    
    # Итоги
    total_minutes = sum(a['duration'] for a in today_activities)
    total_slots = sum(a['slots'] for a in today_activities)
    
    export_text += "=" * 40 + "\n"
    export_text += f"ИТОГО: {len(today_activities)} активностей, "
    export_text += f"{total_minutes} мин., {total_slots} слотов\n"
    
    # Отправляем как отдельное сообщение с фиксированным шрифтом
    await update.message.reply_text(
        f"```\n{export_text}\n```",
        parse_mode='MarkdownV2',
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Также отправляем краткую версию
    await update.message.reply_text(
        f"📤 Экспортировано {len(today_activities)} активностей\n"
        f"⏱ Общее время: {int(total_minutes)} минут\n"
        f"Дата: {today.strftime('%d.%m.%Y')}",
        reply_markup=get_categories_keyboard()
    )

async def cancel(update, context):
    """Отмена всех активностей"""
    user = update.effective_user
    state = state_manager.get_state(user.id)
    
    if state.is_tracking:
        current_time = datetime.now()
        await finish_previous_activity(update, state, current_time, user.id)
    
    # Очищаем все напоминания для этого пользователя
    current_jobs = context.job_queue.get_jobs_by_name(f"reminder_{user.id}")
    for job in current_jobs:
        job.schedule_removal()
    
    current_warnings = context.job_queue.get_jobs_by_name(f"warning_{user.id}")
    for job in current_warnings:
        job.schedule_removal()
    
    await update.message.reply_text(
        "🗑️ Все активности отменены, напоминания очищены.",
        reply_markup=ReplyKeyboardRemove()
    )

def main():
    # Очищаем просроченные состояния при старте
    state_manager.cleanup_expired()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("export", export_command))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Обработчик выбора категории
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_category
    ))
    
    logger.info("...")
    application.run_polling()

def run():
    """Функция для запуска бота извне"""
    main()

if __name__ == '__main__':
    run()  # Для локального запуска
