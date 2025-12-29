from flask_login import LoginManager
from functools import wraps
from flask import redirect, url_for, flash, request
from flask_login import current_user
from app import db # Добавили импорт базы

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def telegram_auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        tg_id_val = request.headers.get('X-Telegram-User-ID') or \
                    request.headers.get('X-Telegram-ID') or \
                    request.args.get('telegram_id')
        
        if not tg_id_val:
            return {'error': 'Telegram ID required'}, 401
        
        from app.models import User
        
        # МАГИЯ: Ищем все аккаунты с этим ID
        all_users = User.query.filter_by(telegram_id=str(tg_id_val)).all()
        
        if len(all_users) > 1:
            # Если их много, находим самый новый
            newest_user = max(all_users, key=lambda u: u.id)
            # У всех остальных СТИРАЕМ этот ID, чтобы не мешались
            for old_user in all_users:
                if old_user.id != newest_user.id:
                    old_user.telegram_id = None 
            db.session.commit() # Сохраняем изменения в чужой базе
            user = newest_user
        else:
            user = User.query.filter_by(telegram_id=str(tg_id_val)).first()

        # Если всё еще не нашли, пробуем по ID
        if not user and str(tg_id_val).isdigit():
            user = User.query.get(int(tg_id_val))
        
        if not user:
            return {'error': f'User {tg_id_val} not found'}, 404
        
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function
