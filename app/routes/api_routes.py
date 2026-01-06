from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Category, Event
from datetime import datetime, timedelta
from sqlalchemy import func
from flask_login import login_required, current_user

# Создаем Blueprint. Обрати внимание, префикс /api/v1
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# ==========================================
#              WEB ENDPOINTS
# ==========================================

@api_bp.route('/web/save_schedule', methods=['POST'])
@login_required
def save_schedule():
    """
    Сохраняет расписание (план) целиком за неделю.
    Принимает JSON:
    {
        "week_start": "2023-10-30",
        "events": [
            {"day": 0, "time": "10:00", "category_id": 1},
            {"day": 1, "time": "14:00", "category_id": 2}
        ]
    }
    """
    data = request.json
    week_start_str = data.get('week_start')
    events_data = data.get('events', [])

    if not week_start_str:
        return jsonify({'error': 'week_start is required'}), 400

    try:
        # 1. Определяем границы недели
        week_start_date = datetime.strptime(week_start_str, '%Y-%m-%d').date()
        week_start_dt = datetime.combine(week_start_date, datetime.min.time())
        week_end_dt = week_start_dt + timedelta(days=7)

        # 2. Удаляем СТАРЫЙ ПЛАН (только type='plan') за эту неделю
        # Мы не трогаем 'fact' (то, что пришло из Телеграма или отмечено как сделанное)
        db.session.query(Event).filter(
            Event.user_id == current_user.id,
            Event.start_time >= week_start_dt,
            Event.start_time < week_end_dt,
            Event.type == 'plan',
            Event.source == 'web'  # Удаляем только то, что создано в вебе
        ).delete()

        # 3. Создаем НОВЫЕ события
        new_events = []
        for item in events_data:
            day_index = int(item['day'])  # 0 = Понедельник
            time_str = item['time']       # "09:00"
            category_id = int(item['category_id'])

            # Вычисляем точную дату и время начала
            event_date = week_start_date + timedelta(days=day_index)
            start_dt = datetime.combine(event_date, datetime.strptime(time_str, "%H:%M").time())
            
            # По умолчанию событие длится 1 час (для сетки)
            end_dt = start_dt + timedelta(hours=1)

            event = Event(
                user_id=current_user.id,
                category_id=category_id,
                start_time=start_dt,
                end_time=end_dt,
                type='plan',   # Это план
                source='web'
            )
            db.session.add(event)
            new_events.append(event)

        db.session.commit()
        print(f"✅ Saved {len(new_events)} events for user {current_user.username}")
        return jsonify({'status': 'success', 'count': len(new_events)}), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error saving schedule: {e}")
        return jsonify({'error': str(e)}), 500


# ==========================================
#            TELEGRAM ENDPOINTS
# ==========================================

@api_bp.route('/telegram/auth', methods=['POST'])
def telegram_auth():
    data = request.json
    telegram_id = str(data.get('telegram_id'))
    username = data.get('username', '').strip()
    
    print(f"🔐 Auth attempt: ID={telegram_id}, Name={username}")

    user_final = None

    # 1. Ищем по имени
    if username:
        user_by_name = User.query.filter(func.lower(User.username) == func.lower(username)).first()
        if user_by_name:
            # Отвязываем старого пользователя от этого ID, если был
            conflict_user = User.query.filter_by(telegram_id=telegram_id).first()
            if conflict_user and conflict_user.id != user_by_name.id:
                conflict_user.telegram_id = None
                db.session.add(conflict_user)
            
            # Привязываем
            user_by_name.telegram_id = telegram_id
            db.session.add(user_by_name)
            db.session.commit()
            user_final = user_by_name

    # 2. Ищем по ID
    if not user_final:
        user_final = User.query.filter_by(telegram_id=telegram_id).first()

    if user_final:
        return jsonify({
            'status': 'authenticated', 
            'user_id': user_final.id, 
            'username': user_final.username
        }), 200
    
    return jsonify({'status': 'needs_registration'}), 404

@api_bp.route('/telegram/categories', methods=['GET'])
def telegram_categories():
    telegram_id = request.args.get('telegram_id')
    if not telegram_id:
        return jsonify({'categories': []}), 400

    user = User.query.filter_by(telegram_id=str(telegram_id)).first()
    if not user:
        return jsonify({'categories': []}), 404

    cats = Category.query.filter_by(user_id=user.id).all()
    cats.sort(key=lambda x: x.id, reverse=True)
    
    result = [{'id': c.id, 'name': c.name, 'color': c.color} for c in cats]
    return jsonify({'categories': result})

@api_bp.route('/telegram/event', methods=['POST'])
def create_telegram_event():
    data = request.json
    telegram_id = str(data.get('telegram_id'))
    
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    try:
        start = datetime.fromisoformat(data['start_time'])
        end = datetime.fromisoformat(data['end_time'])

        event = Event(
            user_id=user.id,
            category_id=data['category_id'],
            start_time=start,
            end_time=end,
            type='fact',    # Из телеграма всегда приходит ФАКТ
            source='telegram'
        )
        
        db.session.add(event)
        db.session.commit()
        return jsonify({'status': 'success', 'id': event.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
