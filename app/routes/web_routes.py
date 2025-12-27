# app/routes/web_routes.py
from flask import Blueprint, jsonify, request, render_template
from flask_login import current_user, login_required
from app import db
from app.models import Category, Event
from datetime import datetime, timedelta

# ====== Blueprint для веб-страниц ======
web_pages_bp = Blueprint('web_pages', __name__)

# ====== Blueprint для API расписания ======
schedule_api_bp = Blueprint('schedule_api', __name__, url_prefix='/api/v1')  # ДОБАВЛЕН url_prefix

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
    categories_list = [cat.to_dict() for cat in categories]

    return jsonify({
        'status': 'success',
        'count': len(categories_list),
        'categories': categories_list
    })


# ========== ДОБАВЛЕН ПОСТ-РОУТ ==========
@schedule_api_bp.route('/categories', methods=['POST'])
@login_required
def create_category():
    """Создать новую категорию"""
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({'error': 'Category name is required'}), 400
    
    # Проверка уникальности
    existing = Category.query.filter_by(
        user_id=current_user.id,
        name=data['name'].strip()
    ).first()
    
    if existing:
        return jsonify({'error': 'Category already exists'}), 409
    
    # Создание категории
    category = Category(
        user_id=current_user.id,
        name=data['name'].strip(),
        color=data.get('color', '#4361ee'),
        description=data.get('description', '')
    )
    
    db.session.add(category)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'category': category.to_dict(),
        'message': f'Category "{category.name}" created successfully'
    }), 201


@schedule_api_bp.route('/events', methods=['POST'])
@login_required
def create_event():
    """Создать новое событие (план) из веб-интерфейса"""
    data = request.get_json()

    # Проверяем обязательные поля
    required = ['category_id', 'start_time', 'end_time']
    if not all(field in data for field in required):
        return jsonify({'error': 'Missing required fields'}), 400

    # Проверяем, что категория принадлежит пользователю
    category = Category.query.filter_by(
        id=data['category_id'],
        user_id=current_user.id
    ).first()

    if not category:
        return jsonify({'error': 'Category not found'}), 404

    # Создаём событие (по умолчанию type='plan', source='web')
    event = Event(
        user_id=current_user.id,
        category_id=data['category_id'],
        start_time=datetime.fromisoformat(data['start_time']),
        end_time=datetime.fromisoformat(data['end_time']),
        type=data.get('type', 'plan'),
        source='web'
    )

    db.session.add(event)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'event_id': event.id,
        'message': 'Event created successfully'
    }), 201


# ======== НОВЫЕ ЭНДПОИНТЫ ========

@schedule_api_bp.route('/week', methods=['GET'])
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
                    'Пятница', 'Саббота', 'Воскресенье'][i],
            'date': day_date.strftime('%d.%m.%Y'),
            'full_date': day_date.strftime('%Y-%m-%d'),
            'short_name': ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'][i]
        })
    
    week_number = today.isocalendar()[1]
    current_week = f"{today.year}-W{week_number:02d}"
    
    return jsonify({
        'status': 'success',
        'week': {
            'year': today.year,
            'week_number': week_number,
            'iso_week': current_week,
            'start_date': start_of_week.strftime('%Y-%m-%d'),
            'end_date': (start_of_week + timedelta(days=6)).strftime('%Y-%m-%d'),
            'days': days
        }
    })


# ========== ИСПРАВЛЕН РОУТ ==========
@schedule_api_bp.route('/events/week/<week_id>', methods=['GET'])
@schedule_api_bp.route('/events/week', methods=['GET'])
@login_required
def get_week_events(week_id=None):
    """Получить события недели (поддерживает оба формата URL)"""
    # Если передан week_id в формате "2025-W52"
    if week_id:
        try:
            year_str, week_str = week_id.split('-W')
            year = int(year_str)
            week = int(week_str)
        except ValueError:
            return jsonify({'error': 'Invalid week format. Use: YYYY-Www'}), 400
    else:
        # Или используем query параметры
        year = request.args.get('year', type=int)
        week = request.args.get('week', type=int)
        
        # Если не указаны - текущая неделя
        if not year or not week:
            today = datetime.now().date()
            year, week, _ = today.isocalendar()
    
    # Рассчитываем начало и конец недели
    start_of_week = datetime.strptime(f'{year}-W{week:02d}-1', "%Y-W%W-%w")
    end_of_week = start_of_week + timedelta(days=6)
    
    # Получаем события пользователя за эту неделю
    events = Event.query.filter(
        Event.user_id == current_user.id,
        Event.start_time >= start_of_week,
        Event.start_time <= end_of_week + timedelta(days=1)
    ).order_by(Event.start_time).all()
    
    events_list = [event.to_dict() for event in events]
    
    return jsonify({
        'status': 'success',
        'week': {
            'year': year,
            'week_number': week,
            'start_date': start_of_week.strftime('%Y-%m-%d'),
            'end_date': end_of_week.strftime('%Y-%m-%d')
        },
        'count': len(events_list),
        'events': events_list
    })
