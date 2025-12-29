from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy import text

# Создаем экземпляры
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
    
    # Регистрация blueprints
    from app.routes.main_routes import main_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.api_routes import api_bp
    from app.routes.web_routes import web_pages_bp, schedule_api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(web_pages_bp)
    app.register_blueprint(schedule_api_bp, url_prefix='/api/v1')
    
    with app.app_context():
        try:
            # 1. Создаём таблицы
            db.create_all()
            
            # 2. Пытаемся добавить колонку description, если её нет (исправленный SQL)
            try:
                # Используем text() для безопасности SQLAlchemy
                check_sql = text("SELECT column_name FROM information_schema.columns WHERE table_name='categories' AND column_name='description'")
                result = db.session.execute(check_sql).fetchone()
                
                if not result:
                    db.session.execute(text("ALTER TABLE categories ADD COLUMN description TEXT DEFAULT ''"))
                    db.session.commit()
                    print("✅ Column 'description' added")
            except Exception as e:
                db.session.rollback()
                print(f"ℹ️ Note: Description column check skipped: {e}")
            
            # 3. Настраиваем user_loader
            from app.models import User
            
            @login_manager.user_loader
            def load_user(user_id):
                return User.query.get(int(user_id))
                
        except Exception as e:
            print(f"❌ Ошибка при инициализации БД: {e}")
    
    return app
