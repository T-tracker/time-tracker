from flask import Blueprint, request, jsonify
from flask_login import login_required
from app import db
from app.models import User, Category, Event
from app.auth import telegram_auth_required
from datetime import datetime, timedelta

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/telegram/auth', methods=['POST'])
def telegram_auth():
    data = request.json
    telegram_id = str(data.get('telegram_id'))
    
    # Ищем тебя по ID или по имени Maria
    user = User.query.filter((User.telegram_id == telegram_id) | (User.username == 'Maria')).first()
    
    if user:
        # Привязываем ID, если он еще не привязан
        if not user.telegram_id:
            user.telegram_id = telegram_id
            db.session.commit()
            
        has_cats = Category.query.filter_by(user_id=user.id).count() > 0
        return jsonify({
            'status': 'authenticated',
            'user_id': user.id,
            'username': user.username,
            'has_categories': has_cats
        }), 200
    
    return jsonify({'status': 'needs_registration'}), 404

@api_bp.route('/telegram/categories', methods=['GET'])
@telegram_auth_required
def telegram_categories():
    # Берем пользователя, которого нашел декоратор @telegram_auth_required
    user = request.current_user
    
    # Находим ВСЕ его категории
    categories = Category.query.filter_by(user_id=user.id).all()
    
    if not categories:
        return jsonify({
            'categories': [{'id': 0, 'name': 'Категорий пока нет', 'color': '#cccccc'}],
            'quick_replies': []
        })

    return jsonify({
        'categories': [{'id': cat.id, 'name': cat.name, 'color': cat.color} for cat in categories],
        'quick_replies': [{'text': cat.name, 'callback_data': f'cat_{cat.id}'} for cat in categories]
    })

@api_bp.route('/telegram/events', methods=['POST'])
@telegram_auth_required
def telegram_create_event():
    user = request.current_user
    data = request.json
    
    # Автоматическое округление до 15 минут
    now = datetime.utcnow()
    # Логика округления:
    minutes = (now.minute // 15) * 15
    start_time = now.replace(minute=minutes, second=0, microsecond=0)
    
    event = Event(
        user_id=user.id,
        category_id=data.get('category_id'),
        type='fact',
        start_time=start_time,
        end_time=start_time + timedelta(minutes=15), # По умолчанию 15 мин
        source='telegram'
    )
    db.session.add(event)
    db.session.commit()
    return jsonify({'status': 'success', 'message': f'Записано в {category_id}!'}), 201
