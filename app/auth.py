from flask_login import LoginManager
from functools import wraps
from flask import redirect, url_for, flash, request
from flask_login import current_user

# Инициализация менеджера входа
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
login_manager.login_message_category = 'warning'

def login_required(f):
    """Декоратор для обычной веб-аутентификации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Требуется вход в систему', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def telegram_auth_required(f):
    """Декоратор для проверки запросов от Telegram-бота"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Извлекаем ID из заголовков или аргументов
        # Бот может прислать его в разных полях, мы проверяем все
        tg_id_header = request.headers.get('X-Telegram-User-ID') or \
                       request.headers.get('X-Telegram-ID') or \
                       request.args.get('telegram_id')
        
        if not tg_id_header:
            return {'error': 'Telegram ID required'}, 401
        
        from app.models import User
        
        # 2. Поиск пользователя (Двойная проверка)
        # Сначала ищем по Telegram ID (длинные цифры, которые ты ввела на сайте)
        user = User.query.filter_by(telegram_id=str(tg_id_header)).first()
        
        # Если не нашли по Telegram ID, пробуем найти по внутреннему ID базы данных
        # Это подстраховка на случай, если бот присылает свой внутренний кэш
        if not user and str(tg_id_header).isdigit():
            user = User.query.get(int(tg_id_header))
        
        if not user:
            return {'error': f'User with ID {tg_id_header} not found'}, 404
        
        # 3. Сохраняем найденного пользователя в объект запроса
        request.current_user = user
        return f(*args, **kwargs)
        
    return decorated_function
