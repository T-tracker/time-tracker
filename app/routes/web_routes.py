# app/routes/web_routes.py
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
    # НЕ создаем категории автоматически - пользователь сам создаст

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
            'short_name': ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'][i],
            'weekday': i
        })

    week_number = today.isocalendar()[1]
    current_week = f"{today.year}-W{week_number:02d}"

    # Получаем категории пользователя (могут быть пустыми!)
    categories = Category.query.filter_by(user_id=current_user.id).all()
    categories_data = [{
        'id': cat.id,
        'name': cat.name,
        'color': cat.color,
        'description': cat.description
    } for cat in categories]

    return render_template('schedule.html',
                           days=days,
                           current_week=current_week,
                           categories=categories_data,
                           today=today.isoformat())


# ======== API РАСПИСАНИЯ ========


@schedule_api_bp.route('/categories', methods=['POST'])
@login_required
def create_category():
    """Создать новую категорию"""
    data = request.get_json()

    if not data or not data.get('name') or not data.get('color'):
        return jsonify({'error': 'Название и цвет обязательны'}), 400

    # Проверяем, нет ли уже такой категории
    existing = Category.query.filter_by(
        user_id=current_user.id,
        name=data['name'].strip()
    ).first()

    if existing:
        return jsonify({'error': 'Категория уже существует'}), 409

    # Создаем новую категорию
    category = Category(
        user_id=current_user.id,
        name=data['name'].strip(),
        color=data['color'],
        description=data.get('description', '')
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


@schedule_api_bp.route('/categories/<int:category_id>', methods=['PUT'])
@login_required
def update_category(category_id):
    """Обновить категорию"""
    category = Category.query.filter_by(
        id=category_id,
        user_id=current_user.id
    ).first()

    if not category:
        return jsonify({'error': 'Категория не найдена'}), 404

    data = request.get_json()

    if 'name' in data:
        category.name = data['name'].strip()

    if 'color' in data:
        category.color = data['color']

    if 'description' in data:
        category.description = data['description']

    db.session.commit()

    return jsonify({
        'status': 'success',
        'category': {
            'id': category.id,
            'name': category.name,
            'color': category.color,
            'description': category.description
        }
    })


@schedule_api_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@login_required
def delete_category(category_id):
    """Удалить категорию"""
    category = Category.query.filter_by(
        id=category_id,
        user_id=current_user.id
    ).first()

    if not category:
        return jsonify({'error': 'Категория не найдена'}), 404

    # Проверяем, нет ли событий с этой категорией
    events_count = Event.query.filter_by(category_id=category_id).count()
    if events_count > 0:
        return jsonify({
            'error': f'Нельзя удалить категорию. Есть {events_count} событий с этой категорией'
        }), 400

    db.session.delete(category)
    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Категория удалена'})


@schedule_api_bp.route('/events', methods=['POST'])
@login_required
def create_event():
    """Создание события с категорией"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    print(f"📨 Получено событие: {data}")

    # Проверяем обязательные поля
    required = ['category_id', 'start_time', 'end_time']
    missing = [field for field in required if field not in data]
    if missing:
        return jsonify({'error': f'Missing required fields: {missing}'}), 400

    # Проверяем, что категория принадлежит пользователю
    category = Category.query.filter_by(
        id=data['category_id'],
        user_id=current_user.id
    ).first()

    if not category:
        return jsonify({'error': 'Category not found'}), 404

    try:
        # Преобразуем время
        start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
    except ValueError as e:
        return jsonify({'error': f'Invalid time format: {str(e)}'}), 400

    # Проверяем тип (план или факт)
    event_type = data.get('type', 'plan')  # По умолчанию план

    # Создаём событие
    event = Event(
        user_id=current_user.id,
        category_id=data['category_id'],
        start_time=start_time,
        end_time=end_time,
        type=event_type,
        source=data.get('source', 'web'),
        title=data.get('title', f'{category.name} - {event_type}')
    )

    db.session.add(event)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'event_id': event.id,
        'message': 'Event created successfully',
        'type': event_type,
        'category': category.name
    }), 201


@schedule_api_bp.route('/events/cell', methods=['POST'])
@login_required
def update_cell_event():
    """Обновить или создать событие для ячейки таблицы (кликабельные ячейки)"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['date', 'hour', 'category_id']
    missing = [field for field in required if field not in data]
    if missing:
        return jsonify({'error': f'Missing required fields: {missing}'}), 400

    # Проверяем категорию
    category = Category.query.filter_by(
        id=data['category_id'],
        user_id=current_user.id
    ).first()

    if not category:
        return jsonify({'error': 'Category not found'}), 404

    try:
        # Преобразуем дату и время
        date_str = data['date']  # Формат 'YYYY-MM-DD'
        hour = int(data['hour'])

        start_time = datetime.strptime(date_str, '%Y-%m-%d').replace(hour=hour, minute=0)
        end_time = start_time + timedelta(hours=1)
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid date/time format: {str(e)}'}), 400

    # Ищем существующее событие на этот слот (план)
    event = Event.query.filter_by(
        user_id=current_user.id,
        start_time=start_time,
        type='plan'  # Только события плана
    ).first()

    if event:
        # Обновляем категорию
        event.category_id = data['category_id']
        event.title = f'{category.name} - план'
    else:
        # Создаем новое событие
        event = Event(
            user_id=current_user.id,
            category_id=data['category_id'],
            start_time=start_time,
            end_time=end_time,
            type='plan',
            source='table_click',
            title=f'{category.name} - план'
        )
        db.session.add(event)

    db.session.commit()

    return jsonify({
        'status': 'success',
        'event_id': event.id,
        'message': 'Cell updated successfully',
        'category': {
            'id': category.id,
            'name': category.name,
            'color': category.color
        }
    })


@schedule_api_bp.route('/events/week', methods=['GET'])
@login_required
def get_week_events():
    """Получить события текущей недели с разделением на план/факт"""
    # Получаем параметры недели
    year = request.args.get('year', type=int)
    week = request.args.get('week', type=int)

    # Если параметры не указаны, используем текущую неделю
    today = datetime.now().date()
    if not year or not week:
        year, week, _ = today.isocalendar()
        start_of_week = today - timedelta(days=today.weekday())
    else:
        # Находим дату по году и номеру недели
        start_of_week = datetime.strptime(f'{year}-W{week:02d}-1', "%Y-W%W-%w").date()

    end_of_week = start_of_week + timedelta(days=6)

    # Получаем события пользователя за эту неделю
    events = Event.query.filter(
        Event.user_id == current_user.id,
        Event.start_time >= start_of_week,
        Event.start_time <= end_of_week + timedelta(days=1)
    ).order_by(Event.start_time).all()

    # Разделяем на план и факт по дням
    events_by_day = {}
    for event in events:
        day_key = event.start_time.date().isoformat()
        if day_key not in events_by_day:
            events_by_day[day_key] = {'plan': [], 'fact': []}

        event_dict = {
            'id': event.id,
            'category_id': event.category_id,
            'category_name': event.category.name if event.category else None,
            'category_color': event.category.color if event.category else None,
            'start_time': event.start_time.isoformat(),
            'end_time': event.end_time.isoformat(),
            'title': event.title,
            'source': event.source
        }

        if event.type == 'plan':
            events_by_day[day_key]['plan'].append(event_dict)
        else:
            events_by_day[day_key]['fact'].append(event_dict)

    # Получаем категории для недели
    categories = Category.query.filter_by(user_id=current_user.id).all()
    categories_list = [{
        'id': cat.id,
        'name': cat.name,
        'color': cat.color,
        'description': cat.description
    } for cat in categories]

    return jsonify({
        'status': 'success',
        'week': {
            'year': year,
            'week_number': week,
            'start_date': start_of_week.isoformat(),
            'end_date': end_of_week.isoformat()
        },
        'categories': categories_list,
        'events_by_day': events_by_day,
        'total_events': len(events)
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


@schedule_api_bp.route('/health', methods=['GET'])
def health_check():
    """Проверка работы API"""
    return jsonify({
        'status': 'healthy',
        'backend': 'Time Tracker Schedule API',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0'
    })