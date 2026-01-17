from flask import Blueprint, jsonify, request, render_template
from flask_login import current_user, login_required
from app import db
from app.models import Category, Event
from datetime import datetime, timedelta

# ====== Blueprint для веб-страниц ======
web_pages_bp = Blueprint('web_pages', __name__)

# ====== Blueprint для API расписания ======
schedule_api_bp = Blueprint('schedule_api', __name__, url_prefix='/api/v1')


# ======== ВЕБ-СТРАНИЦЫ ========

@web_pages_bp.route('/schedule')
@login_required
def schedule_page():
    """
    Страница с недельным расписанием.
    Отдаём:
      - days: список из 7 дней недели с кратким названием, датой и ISO-датой
      - current_week: строка формата YYYY-Www (ISO-неделя)
    """
    today = datetime.now().date()
    iso_year, iso_week, _ = today.isocalendar()

    # понедельник текущей ISO-недели
    start_of_week = datetime.fromisocalendar(iso_year, iso_week, 1).date()

    days = []
    short_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    for i in range(7):
        day_date = start_of_week + timedelta(days=i)
        days.append({
            'short_name': short_names[i],
            'date': day_date.strftime('%d.%m.%Y'),
            'full_date': day_date.strftime('%Y-%m-%d'),
        })

    current_week = f"{iso_year}-W{iso_week:02d}"

    return render_template('schedule.html',
                           days=days,
                           current_week=current_week)


# ======== API РАСПИСАНИЯ ========

# ---- Категории ----

@schedule_api_bp.route('/categories', methods=['GET'])
@login_required
def get_categories():
    """Получить все категории текущего пользователя"""
    categories = Category.query.filter_by(user_id=current_user.id).all()
    categories_list = [cat.to_dict() for cat in categories]

    return jsonify({
        'status': 'success',
        'count': len(categories_list),
        'categories': categories_list
    })


@schedule_api_bp.route('/categories', methods=['POST'])
@login_required
def create_category():
    """Создать новую категорию"""
    data = request.get_json() or {}

    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Category name is required'}), 400

    # Проверка уникальности категории по имени для пользователя
    existing = Category.query.filter_by(
        user_id=current_user.id,
        name=name
    ).first()

    if existing:
        return jsonify({'error': 'Category already exists'}), 409

    category = Category(
        user_id=current_user.id,
        name=name,
        color=data.get('color', '#4361ee'),
        description=data.get('description', '')
    )

    db.session.add(category)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'category': category.to_dict(),
    }), 201


@schedule_api_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@login_required
def delete_category(category_id):
    """
    Удалить категорию пользователя и ВСЕ её события.
    Используется со страницы расписания (и потенциально в других местах).
    """
    category = Category.query.filter_by(
        id=category_id,
        user_id=current_user.id
    ).first()

    if not category:
        return jsonify({'error': 'Category not found'}), 404

    try:
        # удаляем все события этой категории для текущего пользователя
        Event.query.filter_by(
            user_id=current_user.id,
            category_id=category.id
        ).delete(synchronize_session=False)

        db.session.delete(category)
        db.session.commit()
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ---- События ----

@schedule_api_bp.route('/events', methods=['POST'])
@login_required
def create_event():
    """
    Создать новое событие из веб-интерфейса.
    Ожидается JSON:
      {
        "category_id": int,
        "start_time": "YYYY-MM-DDTHH:MM:SS",
        "end_time": "YYYY-MM-DDTHH:MM:SS",
        "type": "plan" | "fact",
        "source": "web" | "telegram" | ...
        "description": "..."
      }
    """
    data = request.get_json() or {}

    required = ['category_id', 'start_time', 'end_time']
    if not all(field in data for field in required):
        return jsonify({'error': 'Missing required fields'}), 400

    # Проверяем, что категория принадлежит текущему пользователю
    category = Category.query.filter_by(
        id=data['category_id'],
        user_id=current_user.id
    ).first()
    if not category:
        return jsonify({'error': 'Category not found'}), 404

    try:
        start_dt = datetime.fromisoformat(data['start_time'])
        end_dt = datetime.fromisoformat(data['end_time'])
    except Exception:
        return jsonify({'error': 'Invalid datetime format'}), 400

    if end_dt <= start_dt:
        return jsonify({'error': 'end_time must be greater than start_time'}), 400

    event_type = data.get('type', 'plan')
    if event_type not in ('plan', 'fact'):
        return jsonify({'error': 'Invalid event type'}), 400

    source = data.get('source', 'web')

    event = Event(
        user_id=current_user.id,
        category_id=category.id,
        start_time=start_dt,
        end_time=end_dt,
        type=event_type,
        source=source,
        description=data.get('description', '')
    )

    db.session.add(event)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'event': event.to_dict()
    }), 201


@schedule_api_bp.route('/events/<int:event_id>', methods=['DELETE'])
@login_required
def delete_event(event_id):
    """
    Удалить одно событие по id (только своё).
    Вызывается по клику на событие в сетке.
    """
    event = Event.query.filter_by(
        id=event_id,
        user_id=current_user.id
    ).first()

    if not event:
        return jsonify({'error': 'Event not found'}), 404

    try:
        db.session.delete(event)
        db.session.commit()
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ---- Текущая неделя (служебный эндпоинт, опционален на фронте) ----

@schedule_api_bp.route('/current_week', methods=['GET'])
@login_required
def get_current_week():
    """
    Вернуть информацию о текущей ISO-неделе:
      - iso_week: строка "YYYY-Www"
      - start_date / end_date: YYYY-MM-DD
      - days: массив из 7 дней (совпадает с тем, что отдаём в /schedule)
    """
    today = datetime.now().date()
    iso_year, iso_week, _ = today.isocalendar()
    start_of_week = datetime.fromisocalendar(iso_year, iso_week, 1).date()

    days = []
    short_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    for i in range(7):
        day_date = start_of_week + timedelta(days=i)
        days.append({
            'short_name': short_names[i],
            'date': day_date.strftime('%d.%m.%Y'),
            'full_date': day_date.strftime('%Y-%m-%d'),
        })

    current_week = f"{iso_year}-W{iso_week:02d}"

    return jsonify({
        'status': 'success',
        'week': {
            'year': iso_year,
            'week_number': iso_week,
            'iso_week': current_week,
            'start_date': start_of_week.strftime('%Y-%m-%d'),
            'end_date': (start_of_week + timedelta(days=6)).strftime('%Y-%m-%d'),
            'days': days
        }
    })


# ---- События за неделю ----

@schedule_api_bp.route('/events/week/<week_id>', methods=['GET'])
@schedule_api_bp.route('/events/week', methods=['GET'])
@login_required
def get_week_events(week_id=None):
    """
    Получить события за ISO-неделю.
    Поддерживает:
      - /api/v1/events/week/2026-W02
      - /api/v1/events/week?year=2026&week=2
      - без параметров => текущая неделя
    """
    if week_id:
        # формат "YYYY-Www"
        try:
            year_str, week_str = week_id.split('-W')
            iso_year = int(year_str)
            iso_week = int(week_str)
        except ValueError:
            return jsonify({'error': 'Invalid week format. Use: YYYY-Www'}), 400
    else:
        iso_year = request.args.get('year', type=int)
        iso_week = request.args.get('week', type=int)
        if not iso_year or not iso_week:
            today = datetime.now().date()
            iso_year, iso_week, _ = today.isocalendar()

    # понедельник данной ISO-недели
    start_of_week = datetime.fromisocalendar(iso_year, iso_week, 1)
    end_exclusive = start_of_week + timedelta(days=7)  # не включительно

    events = Event.query.filter(
        Event.user_id == current_user.id,
        Event.start_time >= start_of_week,
        Event.start_time < end_exclusive
    ).order_by(Event.start_time).all()

    events_list = [e.to_dict() for e in events]

    return jsonify({
        'status': 'success',
        'week': {
            'year': iso_year,
            'week_number': iso_week,
            'start_date': start_of_week.strftime('%Y-%m-%d'),
            'end_date': (start_of_week + timedelta(days=6)).strftime('%Y-%m-%d')
        },
        'count': len(events_list),
        'events': events_list
    })


# Простой health-check
@web_pages_bp.route('/health')
def health_check():
    return {"status": "ok"}, 200
