from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Category, Event
from datetime import datetime
from sqlalchemy import func

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/telegram/auth', methods=['POST'])
def telegram_auth():
    data = request.json
    telegram_id = str(data.get('telegram_id'))
    username = data.get('username', '').strip()
    
    # 1. Ищем по Telegram ID
    user = User.query.filter_by(telegram_id=telegram_id).first()
    
    # 2. Если не нашли, ищем по никнейму (без учета регистра!)
    if not user and username:
        user = User.query.filter(func.lower(User.username) == func.lower(username)).first()
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
    # БЕРЕМ ID ИЗ ПАРАМЕТРОВ URL (?telegram_id=123), А НЕ ИЗ ЗАГОЛОВКОВ
    telegram_id = request.args.get('telegram_id')
    
    if not telegram_id:
        print("❌ Ошибка: telegram_id не передан в URL")
        return jsonify({'categories': []}), 400

    user = User.query.filter_by(telegram_id=str(telegram_id)).first()
    
    if not user:
        print(f"❌ Ошибка: Пользователь с telegram_id={telegram_id} не найден")
        return jsonify({'categories': []}), 404

    cats = Category.query.filter_by(user_id=user.id).all()
    # Сортируем: сначала те, что созданы недавно
    cats.sort(key=lambda x: x.id, reverse=True)
    
    result = [{'id': c.id, 'name': c.name, 'color': c.color} for c in cats]
    print(f"✅ Найдено категорий для {user.username}: {len(result)}")
    return jsonify({'categories': result})

@api_bp.route('/telegram/event', methods=['POST'])
def create_telegram_event():
    data = request.json
    telegram_id = str(data.get('telegram_id'))
    
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    try:
        event = Event(
            user_id=user.id,
            category_id=data['category_id'],
            start_time=datetime.fromisoformat(data['start_time']),
            end_time=datetime.fromisoformat(data['end_time']),
            type='fact',
            source='telegram'
        )
        
        db.session.add(event)
        db.session.commit()
        return jsonify({'status': 'success', 'id': event.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
