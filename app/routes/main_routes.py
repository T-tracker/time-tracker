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
    
    # Формат для input type="week"
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
        'color': cat.color,
        'is_default': cat.is_default
    } for cat in categories])


@main_bp.route('/api/v1/categories', methods=['POST'])
@login_required
def create_category_api():
    """Создать новую категорию - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        # 1. Получаем данные с проверкой
        data = request.get_json()
        print(f"DEBUG CREATE CATEGORY: Данные от фронтенда: {data}")
        
        if not data:
            return jsonify({'error': 'Нет данных'}), 400
        
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'error': 'Название категории обязательно'}), 400
        
        # 2. Проверяем пользователя
        print(f"DEBUG: Текущий пользователь ID: {current_user.id}, имя: {current_user.username}")
        
        # 3. Проверяем уникальность (поиск по user_id + name)
        existing = Category.query.filter_by(
            user_id=current_user.id,
            name=name
        ).first()
        
        if existing:
            return jsonify({
                'error': f'Категория "{name}" уже существует',
                'existing_id': existing.id
            }), 409
        
        # 4. СОЗДАЕМ категорию
        category = Category(
            user_id=current_user.id,
            name=name,
            color=data.get('color', '#4361ee')
        )
        
        db.session.add(category)
        db.session.flush()  # Получаем ID без коммита
        print(f"DEBUG: Категория создана (пока не сохранена). ID: {category.id}")
        
        # 5. КОММИТИМ транзакцию
        db.session.commit()
        print(f"DEBUG: Транзакция ЗАКОММИТЕНА! Категория {category.id} сохранена в БД")
        
        # 6. ПРОВЕРЯЕМ, что категория реально есть в БД
        category_check = Category.query.filter_by(id=category.id).first()
        print(f"DEBUG: Проверка после коммита: категория найдена? {bool(category_check)}")
        
        # 7. Возвращаем УСПЕШНЫЙ ответ
        return jsonify({
            'success': True,
            'message': f'Категория "{name}" создана',
            'category': {
                'id': category.id,
                'name': category.name,
                'color': category.color,
                'user_id': category.user_id
            }
        }), 201
        
    except Exception as e:
        print(f"DEBUG: ОШИБКА при создании категории: {str(e)}")
        import traceback
        print(traceback.format_exc())  # Полный traceback
        db.session.rollback()
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500


@main_bp.route('/debug/categories')
@login_required
def debug_user_categories():
    """Показать все категории пользователя (для отладки)"""
    categories = Category.query.filter_by(user_id=current_user.id).all()
    
    return jsonify({
        'user_id': current_user.id,
        'username': current_user.username,
        'categories_count': len(categories),
        'categories': [{
            'id': c.id,
            'name': c.name,
            'color': c.color,
            'created_at': c.created_at.isoformat() if c.created_at else None
        } for c in categories]
    })


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
        
        # Парсим время (поддерживаем два формата)
        start_str = data['start_time']
        end_str = data['end_time']
        
        # Отладочная информация
        print(f"DEBUG: Получено start_time: {start_str}")
        print(f"DEBUG: Получено end_time: {end_str}")
        
        try:
            # Формат 1: '2024-01-01 14:30:00' (наш фронтенд)
            if ' ' in start_str and 'T' not in start_str:
                start_time = datetime.strptime(start_str, '%Y-%m-%d %H:%M:%S')
                end_time = datetime.strptime(end_str, '%Y-%m-%d %H:%M:%S')
            # Формат 2: ISO с 'Z' или без
            else:
                # Убираем 'Z' если есть и добавляем +00:00 для UTC
                start_str_clean = start_str.replace('Z', '+00:00').replace(' ', 'T')
                end_str_clean = end_str.replace('Z', '+00:00').replace(' ', 'T')
                start_time = datetime.fromisoformat(start_str_clean)
                end_time = datetime.fromisoformat(end_str_clean)
                
        except ValueError as e:
            print(f"DEBUG: Ошибка парсинга времени: {e}")
            return jsonify({'error': f'Неверный формат времени. Используйте формат "YYYY-MM-DD HH:MM:SS". Получено: {start_str}'}), 400
        
        # Проверяем, что конец позже начала
        if end_time <= start_time:
            return jsonify({'error': 'Время окончания должно быть позже времени начала'}), 400
        
        print(f"DEBUG: Парсинг успешен. start_time: {start_time}, end_time: {end_time}")
        
        # Проверяем, нет ли перекрывающихся событий (опционально)
        overlapping_event = Event.query.filter(
            Event.user_id == current_user.id,
            Event.start_time < end_time,
            Event.end_time > start_time,
            Event.type == data['type']
        ).first()
        
        if overlapping_event:
            return jsonify({'error': 'Событие перекрывается с существующим'}), 400
        
        # Создаем новое событие
        new_event = Event(
            user_id=current_user.id,
            category_id=data['category_id'],
            start_time=start_time,
            end_time=end_time,
            type=data['type'],
            source='web'
        )
        
        db.session.add(new_event)
        db.session.commit()
        
        print(f"DEBUG: Событие создано. ID: {new_event.id}")
        
        # Возвращаем полную информацию о событии
        return jsonify({
            'success': True,
            'message': 'Событие создано',
            'event': {
                'id': new_event.id,
                'category_id': new_event.category_id,
                'start_time': new_event.start_time.isoformat() + 'Z',
                'end_time': new_event.end_time.isoformat() + 'Z',
                'type': new_event.type,
                'source': new_event.source
            }
        }), 201
        
    except Exception as e:
        print(f"DEBUG: Ошибка в create_event_api: {str(e)}")
        import traceback
        print(traceback.format_exc())
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


# И добавьте функцию для обновления события:
@main_bp.route('/api/events/<int:event_id>', methods=['PUT'])
@login_required
def update_event_api(event_id):
    """Обновить событие"""
    try:
        event = Event.query.filter_by(
            id=event_id,
            user_id=current_user.id
        ).first()
        
        if not event:
            return jsonify({'error': 'Событие не найдено'}), 404
        
        data = request.get_json()
        
        # Обновляем поля если они переданы
        if 'category_id' in data:
            # Проверяем, что категория принадлежит пользователю
            category = Category.query.filter_by(
                id=data['category_id'],
                user_id=current_user.id
            ).first()
            if not category:
                return jsonify({'error': 'Категория не найдена'}), 404
            event.category_id = data['category_id']
        
        if 'start_time' in data:
            start_str = data['start_time']
            if ' ' in start_str and 'T' not in start_str:
                event.start_time = datetime.strptime(start_str, '%Y-%m-%d %H:%M:%S')
            else:
                start_str_clean = start_str.replace('Z', '+00:00').replace(' ', 'T')
                event.start_time = datetime.fromisoformat(start_str_clean)
        
        if 'end_time' in data:
            end_str = data['end_time']
            if ' ' in end_str and 'T' not in end_str:
                event.end_time = datetime.strptime(end_str, '%Y-%m-%d %H:%M:%S')
            else:
                end_str_clean = end_str.replace('Z', '+00:00').replace(' ', 'T')
                event.end_time = datetime.fromisoformat(end_str_clean)
        
        if 'type' in data:
            event.type = data['type']
        
        # Проверяем, что конец позже начала
        if event.end_time <= event.start_time:
            return jsonify({'error': 'Время окончания должно быть позже времени начала'}), 400
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Событие обновлено',
            'event': {
                'id': event.id,
                'category_id': event.category_id,
                'start_time': event.start_time.isoformat() + 'Z',
                'end_time': event.end_time.isoformat() + 'Z',
                'type': event.type
            }
        }), 200
        
    except Exception as e:
        print(f"DEBUG: Ошибка в update_event_api: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500


# --- События по неделям ---
@main_bp.route('/api/v1/events/week/<week_id>', methods=['GET'])
@main_bp.route('/api/events/week/<week_id>', methods=['GET'])  # Поддержка двух версий
@login_required
def get_week_events_api(week_id):
    """Получить события за неделю"""
    try:
        # Определяем неделю
        year_str, week_str = week_id.split('-W')
        year = int(year_str)
        week = int(week_str)
        
        # Получаем даты недели
        from datetime import datetime, timedelta
        
        # Простой расчет недели
        jan1 = datetime(year, 1, 1)
        start_date = jan1 + timedelta(days=(week - 1) * 7 - jan1.weekday())
        end_date = start_date + timedelta(days=7)
        
        print(f"DEBUG: Загрузка событий для недели {week_id}")
        print(f"DEBUG: Диапазон: {start_date} - {end_date}")
        
        # Получаем события за неделю
        events = Event.query.filter(
            Event.user_id == current_user.id,
            Event.start_time >= start_date,
            Event.start_time < end_date
        ).order_by(Event.start_time).all()
        
        print(f"DEBUG: Найдено событий: {len(events)}")
        
        # Форматируем ответ
        events_list = []
        for event in events:
            category = Category.query.get(event.category_id)
            events_list.append({
                'id': event.id,
                'category_id': event.category_id,
                'category_name': category.name if category else 'Без категории',
                'category_color': category.color if category else '#4361ee',
                'start_time': event.start_time.isoformat() + 'Z',
                'end_time': event.end_time.isoformat() + 'Z',
                'type': event.type,
                'description': '',  # Можно добавить поле description в модель
                'duration': int((event.end_time - event.start_time).total_seconds() / 60)
            })
        
        return jsonify({
            'success': True,
            'week': {
                'year': year,
                'week': week,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': (end_date - timedelta(seconds=1)).strftime('%Y-%m-%d')
            },
            'events': events_list
        })
        
    except ValueError as e:
        print(f"DEBUG: Неверный формат недели: {week_id}, ошибка: {e}")
        return jsonify({'error': f'Неверный формат недели. Используйте формат "YYYY-Www"'}), 400
    except Exception as e:
        print(f"DEBUG: Ошибка в get_week_events_api: {str(e)}")
        import traceback
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

@main_bp.route('/debug/db')
@login_required
def debug_database():
    """Полная диагностика базы данных"""
    from app.models import User, Category, Event
    
    # Получаем текущего пользователя
    current_user_id = current_user.id
    
    # 1. Проверяем таблицы
    users = User.query.all()
    categories = Category.query.filter_by(user_id=current_user_id).all()
    events = Event.query.filter_by(user_id=current_user_id).all()
    
    # 2. Пробуем создать тестовую категорию
    test_category = None
    try:
        test_category = Category(
            user_id=current_user_id,
            name="ТЕСТОВАЯ-" + datetime.now().strftime("%H:%M:%S"),
            color="#FF0000"
        )
        db.session.add(test_category)
        db.session.commit()
        category_created = True
    except Exception as e:
        category_created = False
        db.session.rollback()
        category_error = str(e)
    
    # 3. Удаляем тестовую категорию (если создана)
    if test_category and test_category.id:
        try:
            db.session.delete(test_category)
            db.session.commit()
            category_deleted = True
        except:
            category_deleted = False
            db.session.rollback()
    
    return jsonify({
        'current_user': {
            'id': current_user_id,
            'username': current_user.username,
            'telegram_id': current_user.telegram_id
        },
        'database_stats': {
            'total_users': len(users),
            'user_categories': len(categories),
            'user_events': len(events),
            'all_categories': Category.query.count(),
            'all_events': Event.query.count()
        },
        'test_operation': {
            'category_created': category_created,
            'category_error': category_error if not category_created else None,
            'category_deleted': category_deleted if test_category else None
        },
        'api_endpoints': {
            '/api/v1/categories': f"https://time-tracker-z6co.onrender.com/api/v1/categories",
            '/api/events/week/2025-W52': f"https://time-tracker-z6co.onrender.com/api/events/week/2025-W52"
        }
    })
