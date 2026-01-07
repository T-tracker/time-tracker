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
            # 1. Создаём таблицы (если их ещё нет)
            db.create_all()
            
            # 2. Грубая "миграция" для categories.description (у тебя уже была)
            try:
                check_sql = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='categories' AND column_name='description'
                """)
                result = db.session.execute(check_sql).fetchone()
                
                if not result:
                    db.session.execute(
                        text("ALTER TABLE categories ADD COLUMN description TEXT DEFAULT ''")
                    )
                    db.session.commit()
                    print("✅ Column 'description' added to categories")
            except Exception as e:
                db.session.rollback()
                print(f"ℹ️ Note: Description column check skipped: {e}")
            
            # 3. Грубая "миграция" для таблицы templates
            try:
                # Смотрим, есть ли вообще таблица templates и какие у неё колонки
                cols_result = db.session.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='templates'
                """)).fetchall()
                
                col_names = {row[0] for row in cols_result}
                
                if col_names:
                    # Если был старый столбец data — уберём
                    if 'data' in col_names:
                        try:
                            db.session.execute(text("ALTER TABLE templates DROP COLUMN data"))
                            print("✅ Dropped old 'data' column from templates")
                        except Exception as e:
                            print(f"ℹ️ Could not drop 'data' column (maybe already removed): {e}")
                    
                    # Добавляем нужные колонки, если их нет
                    if 'category_id' not in col_names:
                        db.session.execute(
                            text("ALTER TABLE templates ADD COLUMN category_id INTEGER")
                        )
                        print("✅ Column 'category_id' added to templates")
                    
                    if 'duration_minutes' not in col_names:
                        db.session.execute(
                            text("ALTER TABLE templates ADD COLUMN duration_minutes INTEGER DEFAULT 60")
                        )
                        print("✅ Column 'duration_minutes' added to templates")
                    
                    if 'description' not in col_names:
                        db.session.execute(
                            text("ALTER TABLE templates ADD COLUMN description TEXT")
                        )
                        print("✅ Column 'description' added to templates")
                    
                    db.session.commit()
                else:
                    # Если cols_result пустой — значит таблицы нет, её создаст create_all по новой модели
                    print("ℹ️ Table 'templates' not found in information_schema (will be created by create_all if needed)")
            
            except Exception as e:
                db.session.rollback()
                print(f"ℹ️ Templates migration skipped: {e}")
            
            # 4. user_loader
            from app.models import User
            
            @login_manager.user_loader
            def load_user(user_id):
                return User.query.get(int(user_id))
                
        except Exception as e:
            print(f"❌ Ошибка при инициализации БД: {e}")
    
    return app
