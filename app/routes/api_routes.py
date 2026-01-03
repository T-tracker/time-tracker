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
    # Имя, которое пользователь ввел через /login (или ник из телеграма)
    username = data.get('username', '').strip()
    
    print(f"🔐 Auth attempt: ID={telegram_id}, Name={username}")

    user_final = None

    # 1. Сначала ищем пользователя по ИМЕНИ (если оно передано)
    # Это позволяет принудительно привязаться к "Maria", даже если ID занят "goryachy_supchik"
    if username:
        user_by_name = User.query.filter(func.lower(User.username) == func.lower(username)).first()
        if user_by_name:
            print(f"✅ Found user by name: {user_by_name.username}")
            # Если этот ID уже привязан к КОМУ-ТО ДРУГОМУ (призраку), отвязываем его
            conflict_user = User.query.filter_by(telegram_id=telegram_id).first()
            if conflict_user and conflict_user.id != user_by_name.id:
                print(f"⚠️ Unlinking ID from old user: {conflict_user.username}")
                conflict_user.telegram_id = None
                db.session.add(conflict_user)
            
            # Привязываем к правильному пользователю
            user_by_name.telegram_id = telegram_id
            db.session.add(user_by_name)
            db.session.commit()
            user_final = user_by_name

    # 2. Если по имени не нашли (или имя не передали), ищем по ID (авто-вход)
    if not user_final:
        user_final = User.query.filter_by(telegram_id=telegram_id).first()

    if user_final:
        print(f"🎉 Successfully authenticated: {user_final.username} (ID: {user_final.id})")
        return jsonify({
            'status': 'authenticated', 
            'user_id': user_final.id, 
            'username': user_final.username
        }), 200
    
    print("❌ User not found")
    return jsonify({'status': 'needs_registration'}), 404

@api_bp.route('/telegram/categories', methods=['GET'])
def telegram_categories():
    telegram_id = request.args.get('telegram_id')
    
    if not telegram_id:
        return jsonify({'categories': []}), 400

    user = User.query.filter_by(telegram_id=str(telegram_id)).first()
    
    if not user:
        print(f"❌ Категории: Пользователь с ID {telegram_id} не найден в БД")
        return jsonify({'categories': []}), 404

    cats = Category.query.filter_by(user_id=user.id).all()
    # Сортировка: новые в начале
    cats.sort(key=lambda x: x.id, reverse=True)
    
    result = [{'id': c.id, 'name': c.name, 'color': c.color} for c in cats]
    print(f"📂 Категории для {user.username}: {[c['name'] for c in result]}")
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
