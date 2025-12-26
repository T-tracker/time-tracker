from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Создаем экземпляры ТОЛЬКО здесь
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # Инициализируем расширения
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Диагностика подключения к БД
    with app.app_context():
        database_url = app.config.get('SQLALCHEMY_DATABASE_URI', 'Не задана!')
        safe_url = database_url.replace('postgresql://', 'postgresql://(скрыто)@') if 'postgresql://' in database_url else database_url
        print(f" * Конфигурация БД: {safe_url}")
        
        # Создаем таблицы если их нет
        db.create_all()
        print(" * База данных проверена, таблицы готовы к работе.")
    
    # Регистрация blueprints (УПРОЩЕНО!)
    from app.routes.auth_routes import auth_bp
    from app.routes.main_routes import main_bp
    from app.routes.api_routes import api_bp
    # УДАЛЯЕМ web_routes.py - его функциональность перенесем в main_routes
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)  # Будет обрабатывать /schedule и API
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    
    # Настраиваем user_loader
    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    return app
