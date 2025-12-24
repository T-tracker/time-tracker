from flask import Blueprint, jsonify, request, render_template
from flask_login import current_user, login_required
from app import db
from app.models import Category, Event
from datetime import datetime, timedelta

# ====== Blueprint для веб-страниц ======
web_pages_bp = Blueprint('web_pages', __name__)

# ====== Blueprint для API расписания ======
schedule_api_bp = Blueprint('schedule_api', __name__)

# ======== ВЕБ-СТРАНИЦЫ ========

@web_pages_bp.route('/schedule')
@login_required
def schedule_page():
    """Страница с недельным расписанием"""
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    
    days = []
    for i in range(7):
        day_date = start_of_week + timedelta(days=i)
        days.append({
            'name': ['Понедельник', 'Вторник', 'Среда', 'Четверг', 
                    'Пятница', 'Суббота', 'Воскресенье'][i],
            'date': day_date.strftime('%d.%m.%Y'),
            'full_date': day_date.strftime('%Y-%m-%d'),
            'short_name': ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'][i]
        })
    
    week_number = today.isocalendar()[1]
    current_week = f"{today.year}-W{week_number:02d}"
    
    return render_template('schedule.html', 
                          days=days, 
                          current_week=current_week)

# ======== API РАСПИСАНИЯ ========

@schedule_api_bp.route('/categories', methods=['GET'])
@login_required
def get_categories():
    """Получить ВСЕ категории текущего пользователя"""
    try:
        categories = Category.query.filter_by(user_id=current_user.id).all()
        
        return jsonify({
            'status': 'success',
            'count': len(categories),
            'categories': [{
                'id': cat.id,
                'name': cat.name,
                'color': cat.color,
                'description': cat.description or ''
            } for cat in categories]
        })
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

@schedule_api_bp.route('/events/week/<week_string>', methods=['GET'])
@login_required
def get_week_events(week_string):
    """Получить события недели"""
    try:
        # Парсим строку недели
        year, week = map(int, week_string.replace('W', '-').split('-'))
        
        # Находим первый день недели
        first_day = datetime.strptime(f'{year}-W{week:02d}-1', "%Y-W%W-%w")
        start_of_week = first_day.date()
        end_of_week = start_of_week + timedelta(days=6)
        
        # Получаем события
        events = Event.query.filter(
            Event.user_id == current_user.id,
            Event.start_time >= start_of_week,
            Event.start_time <= end_of_week + timedelta(days=1)
        ).order_by(Event.start_time).all()
        
        return jsonify({
            'success': True,
            'status': 'success',
            'week': week_string,
            'start_date': start_of_week.isoformat(),
            'end_date': end_of_week.isoformat(),
            'events': [{
                'id': e.id,
                'category_id': e.category_id,
                'type': e.type,
                'start_time': e.start_time.isoformat() if e.start_time else None,
                'end_time': e.end_time.isoformat() if e.end_time else None,
                'description': e.description or ''
            } for e in events]
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'success': False, 'status': 'error'}), 400

@schedule_api_bp.route('/events', methods=['POST'])
@login_required
def create_event():
    """Создать новое событие"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided', 'success': False}), 400
        
        required_fields = ['category_id', 'start_time', 'end_time']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing field: {field}', 'success': False}), 400
        
        # Проверяем, что категория принадлежит пользователю
        category = Category.query.filter_by(
            id=data['category_id'],
            user_id=current_user.id
        ).first()
        
        if not category:
            return jsonify({'error': 'Category not found', 'success': False}), 404
        
        # Парсим даты
        start_time = datetime.fromisoformat(data['start_time'].replace('Z', ''))
        end_time = datetime.fromisoformat(data['end_time'].replace('Z', ''))
        
        # Создаем событие
        event = Event(
            user_id=current_user.id,
            category_id=data['category_id'],
            type=data.get('type', 'plan'),
            start_time=start_time,
            end_time=end_time,
            description=data.get('description', ''),
            source='web'
        )
        
        db.session.add(event)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'status': 'success',
            'event': {
                'id': event.id,
                'category_id': event.category_id,
                'type': event.type,
                'start_time': event.start_time.isoformat() if event.start_time else None,
                'end_time': event.end_time.isoformat() if event.end_time else None,
                'description': event.description or ''
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'success': False, 'status': 'error'}), 500

@schedule_api_bp.route('/bulk-events', methods=['POST'])
@login_required
def create_bulk_events():
    """Массовое создание событий"""
    try:
        data = request.get_json()
        
        if not data or 'events' not in data:
            return jsonify({'error': 'No events provided', 'success': False}), 400
        
        created_events = []
        
        for event_data in data['events']:
            # Проверяем обязательные поля
            if not all(k in event_data for k in ['category_id', 'start_time', 'end_time']):
                continue
            
            # Проверяем категорию
            category = Category.query.filter_by(
                id=event_data['category_id'],
                user_id=current_user.id
            ).first()
            
            if not category:
                continue
            
            # Парсим даты
            start_time = datetime.fromisoformat(event_data['start_time'].replace('Z', ''))
            end_time = datetime.fromisoformat(event_data['end_time'].replace('Z', ''))
            
            event = Event(
                user_id=current_user.id,
                category_id=event_data['category_id'],
                type=event_data.get('type', 'plan'),
                start_time=start_time,
                end_time=end_time,
                description=event_data.get('description', ''),
                source='bulk_web'
            )
            
            db.session.add(event)
            created_events.append(event)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'status': 'success',
            'count': len(created_events),
            'events': [{
                'id': e.id,
                'category_id': e.category_id,
                'type': e.type,
                'start_time': e.start_time.isoformat() if e.start_time else None,
                'end_time': e.end_time.isoformat() if e.end_time else None
            } for e in created_events]
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'success': False, 'status': 'error'}), 500

@schedule_api_bp.route('/events/<int:event_id>', methods=['DELETE'])
@login_required
def delete_event(event_id):
    """Удалить событие"""
    try:
        event = Event.query.filter_by(
            id=event_id,
            user_id=current_user.id
        ).first()
        
        if not event:
            return jsonify({'error': 'Event not found', 'success': False}), 404
        
        db.session.delete(event)
        db.session.commit()
        
        return jsonify({'success': True, 'status': 'success', 'message': 'Event deleted'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e), 'success': False, 'status': 'error'}), 500
