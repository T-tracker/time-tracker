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
    
    # 1. Сначала ищем по Telegram ID (самый надежный способ)
    user = User.query.filter_by(telegram_id=telegram_id).first()
    
    # 2. Если не нашли, ищем по username и привязываем ID
    if not user and username:
        user = User.query.filter_by(username=username).first()
        if user:
            user.telegram_id = telegram_id
            db.session.commit()
    
    if user:
        return jsonify({
            'status': 'authenticated', 
            'user_id': user.id, 
            'username': user.username
        }), 200
    
    return jsonify({'status': 'needs_registration'}), 404

@api_bp.route('/telegram/categories', methods=['GET'])
def telegram_categories():
    # Получаем ID из заголовка (надежнее, чем username)
    telegram_id = request.headers.get('X-Telegram-ID')
    
    if not telegram_id:
        return jsonify({'categories': []}), 400

    user = User.query.filter_by(telegram_id=str(telegram_id)).first()
    
    if not user:
        return jsonify({'categories': []}), 404

    cats = Category.query.filter_by(user_id=user.id).all()
    # Сортируем по имени для удобства
    cats.sort(key=lambda x: x.name)
    
    result = [{'id': c.id, 'name': c.name, 'color': c.color} for c in cats]
    return jsonify({'categories': result})

@api_bp.route('/telegram/event', methods=['POST'])
def create_telegram_event():
    data = request.json
    telegram_id = data.get('telegram_id')
    
    user = User.query.filter_by(telegram_id=str(telegram_id)).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    try:
        event = Event(
            user_id=user.id,
            category_id=data['category_id'],
            start_time=datetime.fromisoformat(data['start_time']),
            end_time=datetime.fromisoformat(data['end_time']),
            type='fact',      # Помечаем как факт
            source='telegram' # Помечаем источник
        )
        
        db.session.add(event)
        db.session.commit()
        return jsonify({'status': 'success', 'id': event.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
