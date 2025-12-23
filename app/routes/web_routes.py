# app/routes/web_routes.py
from flask import Blueprint, jsonify, request, render_template
from flask_login import current_user, login_required
from app import db
from app.models import Category, Event
from datetime import datetime, timedelta

# ====== Blueprint для веб-страниц ======
web_pages_bp = Blueprint('web_pages', __name__)

# ====== Blueprint для API расписания ======
schedule_api_bp = Blueprint('schedule_api', __name__)  # Убрал url_prefix

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


@web_bp.route('/categories', methods=['GET'])
def get_categories():
    """ВСЕГДА работающий эндпоинт - с тестовыми данными"""
    # Пытаемся получить из БД, если не получается - возвращаем тестовые
    try:
        # Проверяем, есть ли БД и таблицы
        categories = Category.query.filter_by(user_id=1).all()
        if categories:
            # БД работает - возвращаем реальные данные
            categories_list = [cat.to_dict() for cat in categories]
            return jsonify({
                'status': 'success',
                'source': 'database',
                'categories': categories_list
            })
    except Exception as e:
        # БД не работает - возвращаем тестовые данные
        print(f"⚠️ БД недоступна, используем тестовые данные: {e}")
# ======== API РАСПИСАНИЯ ========

@schedule_api_bp.route('/categories', methods=['GET'])
@login_required
def get_categories():
    """Получить ВСЕ категории текущего пользователя"""
    categories = Category.query.filter_by(user_id=current_user.id).all()
    categories_list = [cat.to_dict() for cat in categories]

    # Тестовые данные (всегда работают)
    return jsonify({
        'status': 'success',
        'source': 'mock_data',
        'categories': [
            {'id': 1, 'name': 'РАБОТА', 'color': '#FF0000', 'code': 'WORK'},
            {'id': 2, 'name': 'УЧЁБА', 'color': '#00FF00', 'code': 'STUDY'},
            {'id': 3, 'name': 'ОТДЫХ', 'color': '#0000FF', 'code': 'REST'},
            {'id': 4, 'name': 'СПОРТ', 'color': '#FF00FF', 'code': 'SPORT'},
            {'id': 5, 'name': 'ХОББИ', 'color': '#FFFF00', 'code': 'HOBBY'}
        ]
    })

@web_bp.route('/events', methods=['POST'])
@schedule_api_bp.route('/events', methods=['POST'])
@login_required

def create_event():
    """Создание события - логируем, но не сохраняем в БД"""
    data = request.get_json()

    # Логируем что пришло (для отладки)
    print(f"📨 Получено событие: {data}")

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


    # Возвращаем успех (даже если БД нет)
    return jsonify({
        'status': 'success',
        'message': 'Событие получено (тестовый режим)',
        'received_data': data,
        'event_id': 999  # Фиктивный ID
    }), 201


@web_bp.route('/health', methods=['GET'])
def health_check():
    """Проверка работы API"""
    return jsonify({
        'status': 'healthy',
        'backend': 'Backend 2 Web API',
        'timestamp': datetime.utcnow().isoformat(),
        'endpoints': ['/categories', '/events', '/health']
    })
        'event_id': event.id,
        'message': 'Event created successfully'
    }), 201



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
                    'Пятница', 'Суббота', 'Воскресенье'][i],
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


@schedule_api_bp.route('/events/week', methods=['GET'])
@login_required
def get_week_events():
    """Получить события текущей недели"""
    # Получаем параметры недели (необязательно)
    year = request.args.get('year', type=int)
    week = request.args.get('week', type=int)
    
    # Если параметры не указаны, используем текущую неделю
    if not year or not week:
        today = datetime.now().date()
        year, week, _ = today.isocalendar()
    else:
        # Находим дату по году и номеру недели
        first_day = datetime.strptime(f'{year}-W{week:02d}-1', "%Y-W%W-%w").date()
    
    # Рассчитываем начало и конец недели
    start_of_week = datetime.strptime(f'{year}-W{week:02d}-1', "%Y-W%W-%w") if year and week else \
                    datetime.now().date() - timedelta(days=datetime.now().date().weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Получаем события пользователя за эту неделю
    events = Event.query.filter(
        Event.user_id == current_user.id,
        Event.start_time >= start_of_week,
        Event.start_time <= end_of_week + timedelta(days=1)  # +1 день чтобы включить события до конца дня
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
