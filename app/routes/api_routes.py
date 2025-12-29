from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Category, Event
from datetime import datetime

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/telegram/auth', methods=['POST'])
def telegram_auth():
    data = request.json
    telegram_id = str(data.get('telegram_id'))
    username = data.get('username')

    # Ищем пользователя по Telegram ID
    user = User.query.filter_by(telegram_id=telegram_id).first()
    
    # Если не нашли по ID, ищем по username (привязка при первом входе)
    if not user and username:
        user = User.query.filter_by(username=username).first()
        if user:
            user.telegram_id = telegram_id
            db.session.commit()

    if user:
        return jsonify({
            'status': 'authenticated', 
            'user_id': user.id, 
            'username': user.username,
            'has_categories': len(user.categories) > 0
        }), 200
    
    # Если пользователя нет вообще — отправляем на регистрацию
    return jsonify({
        'status': 'needs_registration', 
        'registration_url': 'https://time-tracker-2-pfld.onrender.com/register'
    }), 404

@api_bp.route('/telegram/categories', methods=['GET'])
def telegram_categories():
    # Получаем ID пользователя из заголовков запроса
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Просто возвращаем то, что реально создал пользователь
    categories = [
        {'id': c.id, 'name': c.name, 'color': c.color} 
        for c in user.categories
    ]
    
    return jsonify({'categories': categories})

@api_bp.route('/telegram/events', methods=['POST'])
def create_telegram_event():
    data = request.json
    try:
        new_event = Event(
            user_id=data['user_id'],
            category_id=data['category_id'],
            start_time=datetime.fromisoformat(data['start_time']),
            end_time=datetime.fromisoformat(data['end_time']),
            event_type=data.get('event_type', 'fact'),
            description=data.get('description', '')
        )
        db.session.add(new_event)
        db.session.commit()
        return jsonify({'status': 'created', 'id': new_event.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
