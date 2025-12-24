from flask import Blueprint, jsonify, request, render_template
from flask_login import current_user, login_required
from app import db
from app.models import Category, Event, Template
from datetime import datetime, timedelta

# ====== Blueprint для веб-страниц ======
web_pages_bp = Blueprint('web_pages', __name__)

# ====== Blueprint для API расписания ======
schedule_api_bp = Blueprint('schedule_api', __name__, url_prefix='/api/schedule')

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
    categories = Category.query.filter_by(user_id=current_user.id).all()
    
    return jsonify({
        'status': 'success',
        'count': len(categories),
        'categories': [{
            'id': cat.id,
            'name': cat.name,
            'color': cat.color,
            'description': cat.description
        } for cat in categories]
    })

@schedule_api_bp.route('/categories', methods=['POST'])
@login_required
def create_category():
    """Создать новую категорию"""
    data = request.get_json()
    
    if not data.get('name'):
        return jsonify({'error': 'Name is required'}), 400
    
    category = Category(
        name=data['name'],
        color=data.get('color', '#4361ee'),
        description=data.get('description', ''),
        user_id=current_user.id
    )
    
    db.session.add(category)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'category': {
            'id': category.id,
            'name': category.name,
            'color': category.color,
            'description': category.description
        }
    }), 201

@schedule_api_bp.route('/events', methods=['GET'])
@login_required
def get_events():
    """Получить события за период"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Event.query.filter_by(user_id=current_user.id)
    
    if start_date:
        query = query.filter(Event.start_time >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(Event.start_time <= datetime.fromisoformat(end_date))
    
    events = query.order_by(Event.start_time).all()
    
    return jsonify({
        'status': 'success',
        'events': [{
            'id': e.id,
            'category_id': e.category_id,
            'type': e.type,
            'start_time': e.start_time.isoformat(),
            'end_time': e.end_time.isoformat(),
            'description': e.description,
            'source': e.source
        } for e in events]
    })

@schedule_api_bp.route('/events', methods=['POST'])
@login_required
def create_event():
    """Создать новое событие"""
    data = request.get_json()
    
    required_fields = ['category_id', 'start_time', 'end_time']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Проверяем, что категория принадлежит пользователю
    category = Category.query.filter_by(
        id=data['category_id'],
        user_id=current_user.id
    ).first()
    
    if not category:
        return jsonify({'error': 'Category not found'}), 404
    
    # Создаем событие
    event = Event(
        user_id=current_user.id,
        category_id=data['category_id'],
        type=data.get('type', 'plan'),
        start_time=datetime.fromisoformat(data['start_time'].replace(' ', 'T')),
        end_time=datetime.fromisoformat(data['end_time'].replace(' ', 'T')),
        description=data.get('description', ''),
        source='web'
    )
    
    db.session.add(event)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'event': {
            'id': event.id,
            'category_id': event.category_id,
            'type': event.type,
            'start_time': event.start_time.isoformat(),
            'end_time': event.end_time.isoformat(),
            'description': event.description
        }
    }), 201

@schedule_api_bp.route('/events/<int:event_id>', methods=['PUT'])
@login_required
def update_event(event_id):
    """Обновить событие"""
    data = request.get_json()
    
    event = Event.query.filter_by(
        id=event_id,
        user_id=current_user.id
    ).first()
    
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    # Обновляем поля
    if 'category_id' in data:
        event.category_id = data['category_id']
    if 'type' in data:
        event.type = data['type']
    if 'start_time' in data:
        event.start_time = datetime.fromisoformat(data['start_time'].replace(' ', 'T'))
    if 'end_time' in data:
        event.end_time = datetime.fromisoformat(data['end_time'].replace(' ', 'T'))
    if 'description' in data:
        event.description = data['description']
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'event': {
            'id': event.id,
            'category_id': event.category_id,
            'type': event.type,
            'start_time': event.start_time.isoformat(),
            'end_time': event.end_time.isoformat(),
            'description': event.description
        }
    })

@schedule_api_bp.route('/events/<int:event_id>', methods=['DELETE'])
@login_required
def delete_event(event_id):
    """Удалить событие"""
    event = Event.query.filter_by(
        id=event_id,
        user_id=current_user.id
    ).first()
    
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    
    db.session.delete(event)
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': 'Event deleted'})

@schedule_api_bp.route('/week/<week_string>', methods=['GET'])
@login_required
def get_week_events(week_string):
    """Получить события недели"""
    try:
        year, week = map(int, week_string.replace('W', '-').split('-'))
        # Находим первый день недели
        first_day = datetime.strptime(f'{year}-W{week:02d}-1', "%Y-W%W-%w")
        start_of_week = first_day.date()
        end_of_week = start_of_week + timedelta(days=6)
        
        events = Event.query.filter(
            Event.user_id == current_user.id,
            Event.start_time >= start_of_week,
            Event.start_time <= end_of_week + timedelta(days=1)
        ).order_by(Event.start_time).all()
        
        return jsonify({
            'status': 'success',
            'week': week_string,
            'start_date': start_of_week.isoformat(),
            'end_date': end_of_week.isoformat(),
            'events': [{
                'id': e.id,
                'category_id': e.category_id,
                'type': e.type,
                'start_time': e.start_time.isoformat(),
                'end_time': e.end_time.isoformat(),
                'description': e.description,
                'source': e.source
            } for e in events]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@schedule_api_bp.route('/bulk-events', methods=['POST'])
@login_required
def create_bulk_events():
    """Массовое создание событий"""
    data = request.get_json()
    
    if not data.get('events'):
        return jsonify({'error': 'No events provided'}), 400
    
    created_events = []
    
    for event_data in data['events']:
        # Проверяем, что категория принадлежит пользователю
        category = Category.query.filter_by(
            id=event_data['category_id'],
            user_id=current_user.id
        ).first()
        
        if not category:
            continue  # Пропускаем, если категория не найдена
        
        event = Event(
            user_id=current_user.id,
            category_id=event_data['category_id'],
            type=event_data.get('type', 'plan'),
            start_time=datetime.fromisoformat(event_data['start_time'].replace(' ', 'T')),
            end_time=datetime.fromisoformat(event_data['end_time'].replace(' ', 'T')),
            description=event_data.get('description', ''),
            source='bulk_web'
        )
        
        db.session.add(event)
        created_events.append(event)
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'count': len(created_events),
        'events': [{
            'id': e.id,
            'category_id': e.category_id,
            'type': e.type,
            'start_time': e.start_time.isoformat(),
            'end_time': e.end_time.isoformat()
        } for e in created_events]
    }), 201

# ======== ТЕПЛЫЕ ЭНДПОИНТЫ ========

@schedule_api_bp.route('/current-week', methods=['GET'])
@login_required
def get_current_week():
    """Получить данные о текущей неделе"""
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    
    days = []
    for i in range(7):
        day_date = start_of_week + timedelta(days=i)
        days.append({
            'name': ['Понедельник', 'Вторник', 'Среда', 'Четверг', 
                    'Пятница', 'Суббота', 'Воскресенье'][i],
            'date': day_date.strftime('%d.%m.%Y'),
            'full_date': day_date.isoformat(),
            'short_name': ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'][i]
        })
    
    week_number = today.isocalendar()[1]
    
    return jsonify({
        'status': 'success',
        'week': {
            'year': today.year,
            'week_number': week_number,
            'iso_week': f"{today.year}-W{week_number:02d}",
            'start_date': start_of_week.isoformat(),
            'end_date': (start_of_week + timedelta(days=6)).isoformat(),
            'days': days
        }
    })
