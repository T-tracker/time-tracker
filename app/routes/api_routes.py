from flask import Blueprint, request, jsonify
from flask_login import login_required
from app import db
from app.models import User, Category, Event, Template
from app.auth import telegram_auth_required
from datetime import datetime, timedelta
from flask_login import current_user
import re

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/telegram/auth', methods=['GET', 'POST'])
def telegram_auth():
    """Авторизация/регистрация через Telegram"""
    
    # 1. Проверка связи для бота
    if request.method == 'GET':
        return jsonify({
            'status': 'ok',
            'message': 'API is reachable'
        }), 200

    # 2. Логика авторизации (POST)
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    telegram_id = data.get('telegram_id')
    username = data.get('username')
    
    if not telegram_id:
        return jsonify({'error': 'telegram_id required'}), 400
    
    # Ищем пользователя
    user = User.query.filter_by(telegram_id=str(telegram_id)).first()
    
    if user:
        # Проверяем наличие категорий
        has_cats = Category.query.filter_by(user_id=user.id).count() > 0
        return jsonify({
            'status': 'authenticated',
            'user_id': user.id,
            'username': user.username,
            'has_categories': has_cats
        }), 200
    else:
        reg_url = f'https://time-tracker-2-pfld.onrender.com/register?telegram_id={telegram_id}'
        return jsonify({
            'status': 'needs_registration',
            'message': 'Please register via web first',
            'registration_url': reg_url
        }), 404

@api_bp.route('/telegram/categories', methods=['GET'])
@telegram_auth_required
def telegram_categories():
    """Получить категории пользователя для Telegram-бота"""
    user = request.current_user
    categories = Category.query.filter_by(user_id=user.id).all()
    
    # --- МАГИЧЕСКИЙ ХАК ДЛЯ МАШИ ---
    # Если в базе пусто, мы принудительно создаем кнопки, чтобы бот не занудствовал
    if not categories:
        fake_categories = [
            {'id': 999, 'name': '🆕 Категорий пока нет', 'color': '#FF0000'},
            {'id': 998, 'name': '🔄 Нажми /start ещё раз', 'color': '#00FF00'}
        ]
        return jsonify({
            'categories': fake_categories,
            'quick_replies': [
                {'text': cat['name'], 'callback_data': f"cat_{cat['id']}"}
                for cat in fake_categories
            ],
            # Добавляем инфо, чтобы понять какой это аккаунт в базе
            'debug_info': f"User ID: {user.id}, DB_TG_ID: {user.telegram_id}"
        })
    # --- КОНЕЦ ХАКА ---

    return jsonify({
        'categories': [{
            'id': cat.id,
            'name': cat.name,
            'color': cat.color
        } for cat in categories],
        'quick_replies': [
            {'text': cat.name, 'callback_data': f'cat_{cat.id}'}
            for cat in categories[:10]
        ]
    })

@api_bp.route('/telegram/events', methods=['POST'])
@telegram_auth_required
def telegram_create_event():
    """Создать событие из Telegram-бота"""
    user = request.current_user
    data = request.json
    
    time_input = data.get('time', '')
    category_id = data.get('category_id')
    event_type = data.get('type', 'fact')
    
    try:
        if '-' in time_input:
            start_str, end_str = time_input.split('-')
            start_time = parse_time(start_str.strip())
            end_time = parse_time(end_str.strip())
        else:
            duration = parse_duration(time_input)
            start_time = datetime.utcnow()
            end_time = start_time + duration
    except ValueError as e:
        return jsonify({'error': f'Invalid time format: {str(e)}'}), 400
    
    category = Category.query.filter_by(id=category_id, user_id=user.id).first()
    if not category:
        return jsonify({'error': 'Category not found'}), 404
    
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
        'message': f'Event added: {category.name}'
    }), 201

@api_bp.route('/telegram/quick', methods=['POST'])
@telegram_auth_required
def telegram_quick_event():
    user = request.current_user
    data = request.json
    code = data.get('code')
    duration_minutes = data.get('duration', 90)
    
    category = Category.query.filter_by(user_id=user.id).filter(
        (Category.name.ilike(f'%{code}%')) |
        (db.func.lower(Category.name) == code.lower())
    ).first()
    
    if not category:
        return jsonify({'error': f'Category not found: {code}'}), 404
    
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
        'category': category.name
    })

def parse_time(time_str):
    if ':' in time_str:
        hours, minutes = map(int, time_str.split(':'))
        now = datetime.utcnow()
        return now.replace(hour=hours % 24, minute=minutes, second=0, microsecond=0)
    raise ValueError(f"Can't parse time: {time_str}")

def parse_duration(duration_str):
    duration_str = duration_str.lower()
    match = re.search(r'[\d.]+', duration_str)
    val = float(match.group()) if match else 60
    
    if 'час' in duration_str or 'hour' in duration_str:
        return timedelta(hours=val)
    return timedelta(minutes=val)

@api_bp.route('/templates/<int:template_id>', methods=['DELETE'])
@login_required
def delete_template(template_id):
    template = Template.query.filter_by(id=template_id, user_id=current_user.id).first()
    if not template:
        return jsonify({'status': 'error', 'message': 'Шаблон не найден'}), 404
    db.session.delete(template)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Шаблон удален'})
