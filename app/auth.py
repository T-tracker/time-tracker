from flask_login import LoginManager
from functools import wraps
from flask import redirect, url_for, flash, request
from flask_login import current_user

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
login_manager.login_message_category = 'warning'

def login_required(f):
    """Декоратор для проверки аутентификации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Требуется вход в систему', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def telegram_auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Ищем заголовок, который шлет бот
        telegram_id = request.headers.get('X-Telegram-User-ID') or \
                      request.headers.get('X-Telegram-ID') or \
                      request.args.get('telegram_id')
        
        if not telegram_id:
            return {'error': 'Telegram ID required'}, 401
        
        from app.models import User
        # Обязательно приводим к строке, так как в БД это String
        user = User.query.filter_by(telegram_id=str(telegram_id)).first()
        
        if not user:
            return {'error': 'User not found'}, 404
        
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function
