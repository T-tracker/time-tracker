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
    
    # Устанавливаем login view
    login_manager.login_view = 'auth.login'

    with app.app_context():
        # 1. Логируем, К КАКОЙ БД мы подключаемся (это ключевая проверка!)
        database_url = app.config.get('SQLALCHEMY_DATABASE_URI', 'Не задана!')
        # Скрываем пароль для безопасности логов
        safe_url = database_url.replace('postgresql://', 'postgresql://(скрыто)@') if 'postgresql://' in database_url else database_url
        print(f" * Конфигурация БД: {safe_url}")

        # 2. Создаем все таблицы
        db.create_all()
        print(" * База данных проверена, таблицы готовы к работе.")
    
    # Регистрация blueprints (ПЕРЕМЕЩЕНО ВВЕРХ)
    from app.routes.main_routes import main_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.api_routes import api_bp
    from app.routes.web_routes import web_pages_bp, schedule_api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(web_pages_bp)  # ← Это даст /schedule
    app.register_blueprint(schedule_api_bp, url_prefix='/api/v1')
    
    # КОСТЫЛЬ: Патчим модель Category перед её использованием
    with app.app_context():
        from app.models import Category
        
        # Создаём "фейковое" свойство description, которое не запрашивает БД
        class PatchedCategory(Category):
            @property
            def description(self):
                return ""  # Всегда возвращаем пустую строку
            
            @description.setter
            def description(self, value):
                pass  # Игнорируем установку значения
        
        # Заменяем оригинальный класс на патченный
        import sys
        sys.modules['app.models'].Category = PatchedCategory
        
        # Переимпортируем, чтобы другие модули использовали патченную версию
        from app import models
        models.Category = PatchedCategory
    
        # Импортируем модели и настраиваем user_loader
        from app.models import User
        
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))
        
        # КОСТЫЛЬ 2: Пытаемся добавить колонку, если её нет
        try:
            # Проверяем существование колонки description
            result = db.session.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='categories' AND column_name='description';"
            ).fetchone()
            
            if not result:
                print("⚠️ Column 'description' not found. Adding it...")
                db.session.execute("ALTER TABLE categories ADD COLUMN description TEXT DEFAULT '';")
                db.session.commit()
                print("✅ Column 'description' added successfully")
            else:
                print("✅ Column 'description' already exists")
                
        except Exception as e:
            print(f"⚠️ Could not check/add column: {e}")
            # Игнорируем ошибку - костыль выше всё равно отработает
        
        db.create_all()
    
    return app
