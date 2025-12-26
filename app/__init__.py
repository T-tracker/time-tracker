from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Создаем экземпляры ТОЛЬКО здесь
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Внутри create_app(), после app.config.from_object(...)
    print(f" * Подключение к БД: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Не задано!')}")
    print(f" * Переменная DATABASE_URL из окружения: {os.environ.get('DATABASE_URL', 'Не задана!')}")
    
    # Инициализируем расширения
    db.init_app(app)
    login_manager.init_app(app)
    
    # Диагностика подключения к БД
    with app.app_context():
        database_url = app.config.get('SQLALCHEMY_DATABASE_URI', 'Не задана!')
        safe_url = database_url.replace('postgres://', 'postgresql://(скрыто)@') if 'postgresql://' in database_url else database_url
        print(f" * Конфигурация БД: {safe_url}")
        
        # Создаем таблицы если их нет
        db.create_all()
        print(" * База данных проверена, таблицы готовы к работе.")
    
    # Настраиваем login_manager
    login_manager.login_view = 'auth.login'  # Указываем endpoint для логина
    
    # Регистрируем Blueprints (ИСПРАВЛЕНО - без auth_routes!)
    try:
        # Пробуем разные варианты импорта для надежности
        from app.routes.main_routes import main_bp
        from app.routes.api_routes import api_bp
        
        # Регистрируем main_bp (в нем уже есть все нужные маршруты)
        app.register_blueprint(main_bp)
        app.register_blueprint(api_bp, url_prefix='/api/v1')
        
    except ImportError as e:
        print(f"Import Error: {e}")
        # Минимальный маршрут для диагностики
        @app.route('/')
        def home():
            return "App loaded. Import issues detected. Check logs."
    
    # Настраиваем user_loader ДОЛЖЕН быть здесь
    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    return app
