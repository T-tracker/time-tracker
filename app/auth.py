from flask_login import LoginManager
from functools import wraps
from flask import redirect, url_for, flash, request
from flask_login import current_user
from app import db 

# Настройка менеджера входа
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
login_manager.login_message_category = 'warning'

def login_required(f):
    """Декоратор для веб-страниц (нужен системе!)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def telegram_auth_required(f):
    """Декоратор для бота с функцией очистки дубликатов"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        tg_id_val = request.headers.get('X-Telegram-User-ID') or \
                    request.headers.get('X-Telegram-ID') or \
                    request.args.get('telegram_id')
        
        if not tg_id_val:
            return {'error': 'Telegram ID required'}, 401
        
        from app.models import User
        
        # 1. Ищем все аккаунты с этим Telegram ID
        all_users = User.query.filter_by(telegram_id=str(tg_id_val)).all()
        
        user = None
        if len(all_users) > 1:
            # Находим самый новый (с самым большим ID)
            user = max(all_users, key=lambda u: u.id)
            # У старых стираем ID, чтобы они не мешали
            for old_user in all_users:
                if old_user.id != user.id:
                    old_user.telegram_id = None
            try:
                db.session.commit()
            except:
                db.session.rollback()
        elif all_users:
            user = all_users[0]

        # 2. Если по Telegram ID не нашли, пробуем по системному ID
        if not user and str(tg_id_val).isdigit():
            user = User.query.get(int(tg_id_val))
        
        if not user:
            return {'error': f'User {tg_id_val} not found'}, 404
        
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function
