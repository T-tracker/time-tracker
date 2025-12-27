from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app import db
from app.models import User
from app.auth import login_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Вход по Telegram ID или username + пароль"""
    if current_user.is_authenticated:
        return redirect(url_for('main.schedule'))  # ← Изменено с dashboard
    
    if request.method == 'POST':
        identifier = request.form.get('identifier')  # Может быть telegram_id или username
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        # Ищем пользователя по telegram_id или username
        user = User.query.filter(
            (User.telegram_id == identifier) | (User.username == identifier)
        ).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(next_page or url_for('main.schedule'))  # ← Изменено с dashboard
        else:
            flash('Неверный логин или пароль', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация нового пользователя"""
    if current_user.is_authenticated:
        return redirect(url_for('main.schedule'))  # ← Изменено с dashboard
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        telegram_id = request.form.get('telegram_id')  # Может быть пустым
        
        # Валидация
        if not username or not password:
            flash('Имя пользователя и пароль обязательны', 'danger')
            return render_template('register.html')
        
        if password != password_confirm:
            flash('Пароли не совпадают', 'danger')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов', 'danger')
            return render_template('register.html')
        
        # Проверяем уникальность
        if User.query.filter_by(username=username).first():
            flash('Это имя пользователя уже занято', 'danger')
            return render_template('register.html')
        
        if telegram_id and User.query.filter_by(telegram_id=telegram_id).first():
            flash('Этот Telegram ID уже привязан к другому аккаунту', 'danger')
            return render_template('register.html')
        
        # Создаем пользователя
        user = User(username=username, telegram_id=telegram_id or None)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Не авторизуем автоматически, просим войти
        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('auth.login'))
