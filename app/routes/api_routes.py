from flask import Blueprint, request, jsonify
from flask_login import login_required
from app import db
from app.models import User, Category, Event, Template
from app.auth import telegram_auth_required
from datetime import datetime, timedelta
import re

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/telegram/auth', methods=['POST'])
def telegram_auth():
    """Авторизация/регистрация через Telegram"""
    data = request.json
    
    telegram_id = data.get('telegram_id')
    username = data.get('username')
    
    if not telegram_id:
        return jsonify({'error': 'telegram_id required'}), 400
    
    # Ищем пользователя
    user = User.query.filter_by(telegram_id=telegram_id).first()
    
    if user:
        # Пользователь уже существует
        return jsonify({
            'status': 'authenticated',
            'user_id': user.id,
            'username': user.username,
            'has_categories': Category.query.filter_by(user_id=user.id).count() > 0
        }), 200
    else:
        # Новый пользователь - нужно зарегистрироваться через веб
        return jsonify({
            'status': 'needs_registration',
            'message': 'Please complete registration via web interface first',
            'registration_url': f'https://time-tracker-z6co.onrender.com/register?telegram_id={telegram_id}'
        }), 404

@api_bp.route('/telegram/categories', methods=['GET'])
@telegram_auth_required
def telegram_categories():
    """Получить категории пользователя для Telegram-бота"""
    user = request.current_user
    categories = Category.query.filter_by(user_id=user.id).all()
    
    # Формат для inline-клавиатуры Telegram
    return jsonify({
        'categories': [{
            'id': cat.id,
            'name': cat.name,
            'color': cat.color
        } for cat in categories],
        'quick_replies': [
            {'text': cat.name, 'callback_data': f'cat_{cat.id}'}
            for cat in categories[:10]  # Ограничение для Telegram
        ]
    })

@api_bp.route('/telegram/events', methods=['POST'])
@telegram_auth_required
def telegram_create_event():
    """Создать событие из Telegram-бота"""
    user = request.current_user
    data = request.json
    
    # Поддержка разных форматов ввода времени
    time_input = data.get('time', '')
    category_id = data.get('category_id')
    event_type = data.get('type', 'fact')  # По умолчанию факт
    
    # Парсинг времени (пример: "14:30-16:00" или "2 часа")
    try:
        if '-' in time_input:
            # Формат "14:30-16:00"
            start_str, end_str = time_input.split('-')
            start_time = parse_time(start_str.strip())
            end_time = parse_time(end_str.strip())
        else:
            # Формат "2 часа" или "90 минут"
            duration = parse_duration(time_input)
            start_time = datetime.utcnow()
            end_time = start_time + duration
    except ValueError as e:
        return jsonify({'error': f'Invalid time format: {str(e)}'}), 400
    
    # Проверяем, что категория принадлежит пользователю
    category = Category.query.filter_by(
        id=category_id, 
        user_id=user.id
    ).first()
    
    if not category:
        return jsonify({'error': 'Category not found'}), 404
    
    # Создаем событие
    event = Event(
        user_id=user.id,
        category_id=category_id,
        type=event_type,
        start_time=start_time,
        end_time=end_time,
        source='telegram'
    )
    
    db.session.add(event)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'event_id': event.id,
        'message': f'Event added: {category.name} ({event_type})'
    }), 201

@api_bp.route('/telegram/quick', methods=['POST'])
@telegram_auth_required
def telegram_quick_event():
    """Быстрое создание события (например, по коду категории)"""
    user = request.current_user
    data = request.json
    
    code = data.get('code')  # Например, "ПАРА" или "ОБЕД"
    duration_minutes = data.get('duration', 90)  # По умолчанию 1,5 час
    
    # Ищем категорию по коду/сокращению
    category = Category.query.filter_by(user_id=user.id).filter(
        (Category.name.ilike(f'%{code}%')) |
        (db.func.lower(Category.name) == code.lower())
    ).first()
    
    if not category:
        return jsonify({'error': f'Category not found for code: {code}'}), 404
    
    # Создаем событие
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(minutes=int(duration_minutes))
    
    event = Event(
        user_id=user.id,
        category_id=category.id,
        type='fact',
        start_time=start_time,
        end_time=end_time,
        source='telegram_quick'
    )
    
    db.session.add(event)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'category': category.name,
        'duration': duration_minutes
    })

# Вспомогательные функции для парсинга времени
def parse_time(time_str):
    """Парсинг времени в формате '14:30' или '2:30 PM'"""
    # Простая реализация
    if ':' in time_str:
        hours, minutes = map(int, time_str.split(':'))
        now = datetime.utcnow()
        return now.replace(hour=hours % 24, minute=minutes, second=0, microsecond=0)
    raise ValueError(f"Can't parse time: {time_str}")

def parse_duration(duration_str):
    """Парсинг длительности '2 часа', '90 минут' и т.д."""
    duration_str = duration_str.lower()
    
    if 'час' in duration_str or 'hour' in duration_str:
        hours = float(re.search(r'[\d.]+', duration_str).group())
        return timedelta(hours=hours)
    elif 'мин' in duration_str or 'min' in duration_str:
        minutes = float(re.search(r'[\d.]+', duration_str).group())
        return timedelta(minutes=minutes)
    else:
        # По умолчанию считаем минутами
        minutes = float(re.search(r'[\d.]+', duration_str).group())
        return timedelta(minutes=minutes)

@api_bp.route('/templates/<int:template_id>', methods=['DELETE'])
@login_required
def delete_template(template_id):
    """Удалить шаблон"""
    template = Template.query.filter_by(
        id=template_id,
        user_id=current_user.id
    ).first()
    
    if not template:
        return jsonify({'status': 'error', 'message': 'Шаблон не найден'}), 404
    
    db.session.delete(template)
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Шаблон удален'})
