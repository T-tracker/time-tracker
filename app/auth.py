from flask_login import LoginManager
from functools import wraps
from flask import redirect, url_for, flash, request
from flask_login import current_user

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
login_manager.login_message_category = 'warning'

def login_required(f):
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
        tg_id_val = request.headers.get('X-Telegram-User-ID') or \
                    request.headers.get('X-Telegram-ID') or \
                    request.args.get('telegram_id')
        
        if not tg_id_val:
            return {'error': 'Telegram ID required'}, 401
        
        from app.models import User
        
        # 1. Сначала ищем по настоящему длинному Telegram ID (6730973279)
        # Мы берем .order_by(User.id.desc()), чтобы если их вдруг два, взялся НОВЫЙ
        user = User.query.filter_by(telegram_id=str(tg_id_val)).order_by(User.id.desc()).first()
        
        # 2. Если не нашли (значит бот прислал внутренний ID, например "7")
        if not user and str(tg_id_val).isdigit():
            # Пробуем найти пользователя по системному ID
            user = User.query.get(int(tg_id_val))
            
            # Если нашли пользователя по системному ID, но у него НЕТ категорий,
            # а в базе есть кто-то другой с таким же Telegram ID, переключаемся на него!
            if user and user.telegram_id:
                better_user = User.query.filter_by(telegram_id=user.telegram_id).order_by(User.id.desc()).first()
                if better_user:
                    user = better_user
        
        if not user:
            return {'error': f'User {tg_id_val} not found'}, 404
        
        request.current_user = user
        return f(*args, **kwargs)
        
    return decorated_function
