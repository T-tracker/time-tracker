from flask_login import LoginManager
from functools import wraps
from flask import redirect, url_for, flash, request
from flask_login import current_user

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
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
        # ХИТРЫЙ ПОИСК: Берем самый новый аккаунт (DESC)
        user = User.query.filter_by(telegram_id=str(tg_id_val)).order_by(User.id.desc()).first()
        
        if not user and str(tg_id_val).isdigit():
            user = User.query.get(int(tg_id_val))
        
        if not user:
            return {'error': f'User {tg_id_val} not found'}, 404
        
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function
