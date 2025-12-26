from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user, login_required
from app import db
from app.models import User, Category, Event, Template
from app.auth import login_required
from datetime import datetime, timedelta
import json

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    """Главная страница - теперь это расписание"""
    return redirect(url_for('main.schedule'))

@main_bp.route('/schedule')
@login_required
def schedule():
    """Страница с недельным расписанием и графиками"""
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    
    # Создаем список дней недели
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
    
    # Формат для input type="week"
    week_number = today.isocalendar()[1]
    current_week = f"{today.year}-W{week_number:02d}"
    
    return render_template('schedule.html', 
                          days=days, 
                          current_week=current_week)

# ... остальные функции (profile, manage_categories и т.д.) оставьте без изменений

@main_bp.route('/profile')
@login_required
def profile():
    """Страница профиля пользователя"""
    return render_template('profile.html', user=current_user)

@main_bp.route('/categories', methods=['GET', 'POST'])
@login_required
def manage_categories():
    """Управление категориями пользователя"""
    if request.method == 'POST':
        name = request.form.get('name')
        color = request.form.get('color', '#007bff')
        
        if not name:
            flash('Название категории обязательно', 'danger')
            return redirect(url_for('main.manage_categories'))
        
        # Проверяем уникальность для этого пользователя
        existing = Category.query.filter_by(
            user_id=current_user.id, 
            name=name
        ).first()
        
        if existing:
            flash('Категория с таким названием уже существует', 'warning')
            return redirect(url_for('main.manage_categories'))
        
        category = Category(
            name=name,
            color=color,
            user_id=current_user.id
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash(f'Категория "{name}" создана!', 'success')
        return redirect(url_for('main.dashboard'))
    
    # все категории пользователя
    categories = Category.query.filter_by(user_id=current_user.id).all()
    return render_template('categories.html', categories=categories)

@main_bp.route('/events', methods=['GET', 'POST'])
@login_required
def manage_events():
    """Управление событиями пользователя"""
    if request.method == 'POST':
        category_id = request.form.get('category_id')
        event_type = request.form.get('type')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        description = request.form.get('description', '')
        
        # Валидация
        category = Category.query.filter_by(
            id=category_id, 
            user_id=current_user.id
        ).first()
        
        if not category:
            flash('Выберите корректную категорию', 'danger')
            return redirect(url_for('main.manage_events'))
        
        try:
            start_dt = datetime.fromisoformat(start_time.replace('T', ' '))
            end_dt = datetime.fromisoformat(end_time.replace('T', ' '))
            
            if end_dt <= start_dt:
                flash('Время окончания должно быть позже времени начала', 'danger')
                return redirect(url_for('main.manage_events'))
            
            event = Event(
                user_id=current_user.id,
                category_id=category_id,
                type=event_type,
                start_time=start_dt,
                end_time=end_dt,
                source='web'
            )
            
            db.session.add(event)
            db.session.commit()
            
            flash('Событие успешно добавлено!', 'success')
            return redirect(url_for('main.dashboard'))
            
        except ValueError:
            flash('Неверный формат времени', 'danger')
            return redirect(url_for('main.manage_events'))
    
    # показать форму с категориями пользователя
    categories = Category.query.filter_by(user_id=current_user.id).all()
    return render_template('events.html', categories=categories)

@main_bp.route('/templates', methods=['GET', 'POST'])
@login_required
def manage_templates():
    """Управление шаблонами пользователя"""
    if request.method == 'POST':
        name = request.form.get('name')
        category_id = request.form.get('category_id')
        duration_minutes = request.form.get('duration_minutes', 60)
        description = request.form.get('description', '')
        
        if not name or not category_id:
            flash('Название и категория обязательны', 'danger')
            return redirect(url_for('main.manage_templates'))
        
        # Проверяем, что категория принадлежит пользователю
        category = Category.query.filter_by(
            id=category_id, 
            user_id=current_user.id
        ).first()
        
        if not category:
            flash('Выберите корректную категорию', 'danger')
            return redirect(url_for('main.manage_templates'))
        
        template = Template(
            name=name,
            category_id=category_id,
            duration_minutes=int(duration_minutes),
            description=description,
            user_id=current_user.id
        )
        
        db.session.add(template)
        db.session.commit()
        
        flash(f'Шаблон "{name}" создан!', 'success')
        return redirect(url_for('main.dashboard'))
    
    # Получаем все шаблоны пользователя
    templates = Template.query.filter_by(user_id=current_user.id).all()
    categories = Category.query.filter_by(user_id=current_user.id).all()
    
    return render_template('templates.html', 
                         templates=templates, 
                         categories=categories)
    
@main_bp.route('/api/my/stats')
@login_required
def api_my_stats():
    """Статистика текущего пользователя"""
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)
    
    return jsonify({
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'telegram_linked': bool(current_user.telegram_id)
        },
        'stats': {
            'categories': Category.query.filter_by(user_id=current_user.id).count(),
            'events_today': Event.query.filter(
                Event.user_id == current_user.id,
                Event.start_time >= today,
                Event.start_time < tomorrow
            ).count(),
            'events_total': Event.query.filter_by(user_id=current_user.id).count(),
            'plans_vs_facts': {
                'plan': Event.query.filter_by(user_id=current_user.id, type='plan').count(),
                'fact': Event.query.filter_by(user_id=current_user.id, type='fact').count()
            }
        }
    })

@main_bp.route('/api/my/events')
@login_required
def api_my_events():
    """События текущего пользователя с фильтрацией"""
    # Параметры фильтрации
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category_id = request.args.get('category_id')
    event_type = request.args.get('type')
    
    query = Event.query.filter_by(user_id=current_user.id)
    
    if start_date:
        query = query.filter(Event.start_time >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(Event.start_time <= datetime.fromisoformat(end_date))
    if category_id:
        query = query.filter(Event.category_id == category_id)
    if event_type:
        query = query.filter(Event.type == event_type)
    
    events = query.order_by(Event.start_time.desc()).limit(100).all()
    
    return jsonify([{
        'id': e.id,
        'category': e.category.name,
        'category_color': e.category.color,
        'type': e.type,
        'start_time': e.start_time.isoformat(),
        'end_time': e.end_time.isoformat(),
        'duration_minutes': int((e.end_time - e.start_time).total_seconds() / 60),
        'source': e.source,
        'created_at': e.created_at.isoformat()
    } for e in events])

@main_bp.route('/api/categories', methods=['GET'])
@login_required
def api_get_categories():
    """Получить ВСЕ категории текущего пользователя"""
    categories = Category.query.filter_by(user_id=current_user.id).all()
    categories_list = [cat.to_dict() for cat in categories]

    return jsonify({
        'status': 'success',
        'count': len(categories_list),
        'categories': categories_list
    })

@main_bp.route('/api/categories', methods=['POST'])
@login_required
def api_create_category():
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

@main_bp.route('/api/events', methods=['POST'])
@login_required
def api_create_event():
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

    # Парсим даты с учетом возможного формата с 'Z'
    start_str = data['start_time'].replace('Z', '+00:00')
    end_str = data['end_time'].replace('Z', '+00:00')
    
    event = Event(
        user_id=current_user.id,
        category_id=data['category_id'],
        start_time=datetime.fromisoformat(start_str),
        end_time=datetime.fromisoformat(end_str),
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

@main_bp.route('/api/events/week/<week_id>', methods=['GET'])
@main_bp.route('/api/events/week', methods=['GET'])
@login_required
def api_get_week_events(week_id=None):
    """Получить события недели"""
    if week_id:
        try:
            year_str, week_str = week_id.split('-W')
            year = int(year_str)
            week = int(week_str)
        except ValueError:
            return jsonify({'error': 'Invalid week format. Use: YYYY-Www'}), 400
    else:
        year = request.args.get('year', type=int)
        week = request.args.get('week', type=int)
        
        if not year or not week:
            today = datetime.now().date()
            year, week, _ = today.isocalendar()
    
    # Рассчитываем начало недели (понедельник)
    start_of_week = datetime.strptime(f'{year}-{week:02d}-1', "%Y-%W-%w")
    end_of_week = start_of_week + timedelta(days=6)
    
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
