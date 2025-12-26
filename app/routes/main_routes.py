# app/routes/main_routes.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_user, logout_user, current_user, login_required
from app import db
from app.models import User, Category, Event, Template
from datetime import datetime, timedelta
import json

# Создаем основной Blueprint
main_bp = Blueprint('main', __name__)

# ==================== МАРШРУТЫ АУТЕНТИФИКАЦИИ ====================

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Вход в систему"""
    # Если пользователь уже авторизован - перенаправляем на главную
    if current_user.is_authenticated:
        return redirect(url_for('main.schedule'))
    
    if request.method == 'POST':
        identifier = request.form.get('identifier')  # telegram_id или username
        password = request.form.get('password')
        remember = 'remember' in request.form  # Чекбокс "запомнить меня"
        
        # Ищем пользователя
        user = User.query.filter(
            (User.telegram_id == identifier) | (User.username == identifier)
        ).first()
        
        # Проверяем пароль
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash('Вы успешно вошли в систему!', 'success')
            
            # Перенаправляем на запрашиваемую страницу или расписание
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.schedule'))
        else:
            flash('Неверный логин или пароль', 'danger')
    
    return render_template('login.html')


@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация нового пользователя"""
    if current_user.is_authenticated:
        return redirect(url_for('main.schedule'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        telegram_id = request.form.get('telegram_id', '').strip()
        
        # Валидация
        errors = []
        
        if not username or len(username) < 3:
            errors.append('Имя пользователя должно быть не менее 3 символов')
        
        if not password or len(password) < 6:
            errors.append('Пароль должен быть не менее 6 символов')
        elif password != password_confirm:
            errors.append('Пароли не совпадают')
        
        if User.query.filter_by(username=username).first():
            errors.append('Это имя пользователя уже занято')
        
        if telegram_id and User.query.filter_by(telegram_id=telegram_id).first():
            errors.append('Этот Telegram ID уже привязан к другому аккаунту')
        
        # Если есть ошибки - показываем их
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html')
        
        # Создаем пользователя
        user = User(username=username)
        if telegram_id:
            user.telegram_id = telegram_id
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('main.login'))
    
    return render_template('register.html')


@main_bp.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('main.login'))


# ==================== ОСНОВНЫЕ ВЕБ-СТРАНИЦЫ ====================

@main_bp.route('/')
def index():
    """Главная страница - перенаправляет на расписание или логин"""
    if current_user.is_authenticated:
        return redirect(url_for('main.schedule'))
    return redirect(url_for('main.login'))


@main_bp.route('/schedule')
@login_required
def schedule():
    """Страница с недельным расписанием"""
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    
    # Формируем дни недели
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


@main_bp.route('/profile')
@login_required
def profile():
    """Страница профиля пользователя"""
    # Получаем статистику пользователя
    categories_count = Category.query.filter_by(user_id=current_user.id).count()
    events_count = Event.query.filter_by(user_id=current_user.id).count()
    today_events = Event.query.filter(
        Event.user_id == current_user.id,
        Event.start_time >= datetime.now().date()
    ).count()
    
    return render_template('profile.html', 
                          user=current_user,
                          categories_count=categories_count,
                          events_count=events_count,
                          today_events=today_events)


@main_bp.route('/categories')
@login_required
def categories_page():
    """Страница управления категориями"""
    user_categories = Category.query.filter_by(user_id=current_user.id).all()
    return render_template('categories.html', categories=user_categories)


# ==================== API ДЛЯ ФРОНТЕНДА ====================

# --- Категории ---
@main_bp.route('/api/v1/categories', methods=['GET'])
@main_bp.route('/api/categories', methods=['GET'])  # Поддержка двух версий
@login_required
def get_categories_api():
    """Получить все категории текущего пользователя"""
    categories = Category.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': cat.id,
        'name': cat.name,
        'color': cat.color
    } for cat in categories])


@main_bp.route('/api/v1/categories', methods=['POST'])
@main_bp.route('/api/categories', methods=['POST'])  # Поддержка двух версий
@login_required
def create_category_api():
    """Создать новую категорию"""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'error': 'Название категории обязательно'}), 400
        
        name = data['name'].strip()
        if not name:
            return jsonify({'error': 'Название не может быть пустым'}), 400
        
        # Проверяем уникальность
        existing = Category.query.filter_by(
            user_id=current_user.id,
            name=name
        ).first()
        
        if existing:
            return jsonify({'error': 'Категория с таким названием уже существует'}), 409
        
        # Создаем категорию
        category = Category(
            user_id=current_user.id,
            name=name,
            color=data.get('color', '#4361ee')
        )
        
        db.session.add(category)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'category': {
                'id': category.id,
                'name': category.name,
                'color': category.color
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500


@main_bp.route('/api/categories/<int:category_id>', methods=['DELETE'])
@login_required
def delete_category_api(category_id):
    """Удалить категорию"""
    category = Category.query.filter_by(
        id=category_id,
        user_id=current_user.id
    ).first()
    
    if not category:
        return jsonify({'error': 'Категория не найдена'}), 404
    
    db.session.delete(category)
    db.session.commit()
    
    return jsonify({'success': True})


# --- События ---
@main_bp.route('/api/events', methods=['GET'])
@login_required
def get_events_api():
    """Получить события с фильтрацией"""
    # Параметры фильтрации
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category_id = request.args.get('category_id')
    
    # Базовый запрос
    query = Event.query.filter_by(user_id=current_user.id)
    
    # Применяем фильтры
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(Event.start_time >= start_dt)
        except ValueError:
            return jsonify({'error': 'Неверный формат начальной даты'}), 400
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(Event.end_time <= end_dt)
        except ValueError:
            return jsonify({'error': 'Неверный формат конечной даты'}), 400
    
    if category_id:
        query = query.filter(Event.category_id == category_id)
    
    # Выполняем запрос
    events = query.order_by(Event.start_time).all()
    
    return jsonify([{
        'id': e.id,
        'category_id': e.category_id,
        'category_name': e.category.name if e.category else '',
        'category_color': e.category.color if e.category else '#4361ee',
        'start_time': e.start_time.isoformat() + 'Z' if e.start_time else None,
        'end_time': e.end_time.isoformat() + 'Z' if e.end_time else None,
        'type': e.type,
        'source': e.source
    } for e in events])


@main_bp.route('/api/v1/events', methods=['POST'])
@main_bp.route('/api/events', methods=['POST'])  # Поддержка двух версий
@login_required
def create_event_api():
    """Создать или обновить событие"""
    try:
        data = request.get_json()
        
        # Проверяем обязательные поля
        required_fields = ['category_id', 'start_time', 'end_time', 'type']
        missing = [field for field in required_fields if field not in data]
        if missing:
            return jsonify({'error': f'Отсутствуют обязательные поля: {", ".join(missing)}'}), 400
        
        # Проверяем, что категория принадлежит пользователю
        category = Category.query.filter_by(
            id=data['category_id'],
            user_id=current_user.id
        ).first()
        
        if not category:
            return jsonify({'error': 'Категория не найдена'}), 404
        
        # Парсим время
        start_str = data['start_time'].replace('Z', '+00:00')
        end_str = data['end_time'].replace('Z', '+00:00')
        
        try:
            start_time = datetime.fromisoformat(start_str)
            end_time = datetime.fromisoformat(end_str)
        except ValueError:
            return jsonify({'error': 'Неверный формат времени'}), 400
        
        # Проверяем, что конец позже начала
        if end_time <= start_time:
            return jsonify({'error': 'Время окончания должно быть позже времени начала'}), 400
        
        # Ищем существующее событие
        existing_event = Event.query.filter_by(
            user_id=current_user.id,
            category_id=data['category_id'],
            start_time=start_time,
            type=data['type']
        ).first()
        
        if existing_event:
            # Обновляем существующее
            existing_event.end_time = end_time
            message = 'Событие обновлено'
            event_id = existing_event.id
        else:
            # Создаем новое
            new_event = Event(
                user_id=current_user.id,
                category_id=data['category_id'],
                start_time=start_time,
                end_time=end_time,
                type=data['type'],
                source='web'
            )
            db.session.add(new_event)
            message = 'Событие создано'
            event_id = new_event.id
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message,
            'event_id': event_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500


@main_bp.route('/api/events/<int:event_id>', methods=['DELETE'])
@login_required
def delete_event_api(event_id):
    """Удалить событие"""
    event = Event.query.filter_by(
        id=event_id,
        user_id=current_user.id
    ).first()
    
    if not event:
        return jsonify({'error': 'Событие не найдено'}), 404
    
    db.session.delete(event)
    db.session.commit()
    
    return jsonify({'success': True})


# --- События по неделям ---
@main_bp.route('/api/v1/events/week/<week_id>', methods=['GET'])
@main_bp.route('/api/events/week/<week_id>', methods=['GET'])  # Поддержка двух версий
@login_required
def get_week_events_api(week_id):
    """Получить события за неделю - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        # Определяем неделю
        year_str, week_str = week_id.split('-W')
        year = int(year_str)
        week = int(week_str)
        
        # ПРАВИЛЬНЫЙ расчет начала недели (ISO неделя)
        import datetime
        first_day = datetime.date(year, 1, 1)
        # Находим первый четверг года
        if first_day.weekday() > 3:  # Если первый день года после четверга
            first_thursday = first_day + datetime.timedelta(days=(3 - first_day.weekday() + 7) % 7)
        else:
            first_thursday = first_day + datetime.timedelta(days=(3 - first_day.weekday()))
        
        # Начало недели (понедельник)
        start_of_week = first_thursday + datetime.timedelta(days=(week - 1) * 7 - 3)
        end_of_week = start_of_week + datetime.timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        # Преобразуем в datetime
        start_dt = datetime.datetime.combine(start_of_week, datetime.time.min)
        end_dt = datetime.datetime.combine(end_of_week, datetime.time.max)
        
        # Получаем события за неделю
        events = Event.query.filter(
            Event.user_id == current_user.id,
            Event.start_time >= start_dt,
            Event.start_time <= end_dt
        ).order_by(Event.start_time).all()
        
        # Форматируем ответ
        events_list = []
        for event in events:
            events_list.append({
                'id': event.id,
                'category_id': event.category_id,
                'category_name': event.category.name if event.category else '',
                'category_color': event.category.color if event.category else '#4361ee',
                'start_time': event.start_time.isoformat() + 'Z' if event.start_time else None,
                'end_time': event.end_time.isoformat() + 'Z' if event.end_time else None,
                'type': event.type,
                'duration': int((event.end_time - event.start_time).total_seconds() / 60) if event.end_time and event.start_time else 0
            })
        
        return jsonify({
            'success': True,
            'week': {
                'year': year,
                'week': week,
                'start_date': start_of_week.strftime('%Y-%m-%d'),
                'end_date': end_of_week.strftime('%Y-%m-%d')
            },
            'events': events_list
        })
        
    except ValueError as e:
        return jsonify({'error': f'Неверный формат недели: {str(e)}'}), 400
    except Exception as e:
        import traceback
        print(f"ERROR in get_week_events_api: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500


# ==================== СТАТИСТИКА ====================

@main_bp.route('/api/stats')
@login_required
def get_stats_api():
    """Получить статистику пользователя"""
    # Общая статистика
    categories_count = Category.query.filter_by(user_id=current_user.id).count()
    total_events = Event.query.filter_by(user_id=current_user.id).count()
    
    # Статистика по типам
    plan_events = Event.query.filter_by(user_id=current_user.id, type='plan').count()
    fact_events = Event.query.filter_by(user_id=current_user.id, type='fact').count()
    
    # События за сегодня
    today_start = datetime.now().date()
    today_end = today_start + timedelta(days=1)
    today_events = Event.query.filter(
        Event.user_id == current_user.id,
        Event.start_time >= today_start,
        Event.start_time < today_end
    ).count()
    
    return jsonify({
        'success': True,
        'stats': {
            'categories': categories_count,
            'total_events': total_events,
            'plan_events': plan_events,
            'fact_events': fact_events,
            'today_events': today_events,
            'productivity': round(fact_events / plan_events * 100, 1) if plan_events > 0 else 0
        }
    })


# ==================== ШАБЛОНЫ ====================

@main_bp.route('/api/templates', methods=['GET'])
@login_required
def get_templates_api():
    """Получить шаблоны пользователя"""
    templates = Template.query.filter_by(user_id=current_user.id).all()
    
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'data': t.data,
        'created_at': t.created_at.isoformat() + 'Z' if t.created_at else None
    } for t in templates])


@main_bp.route('/api/templates', methods=['POST'])
@login_required
def create_template_api():
    """Создать шаблон"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data or 'data' not in data:
            return jsonify({'error': 'Название и данные шаблона обязательны'}), 400
        
        template = Template(
            user_id=current_user.id,
            name=data['name'].strip(),
            data=data['data']
        )
        
        db.session.add(template)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'template_id': template.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500


# ==================== ТЕСТОВЫЙ МАРШРУТ ====================

@main_bp.route('/api/health')
def health_check():
    """Проверка работоспособности API"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'authenticated': current_user.is_authenticated
    })
