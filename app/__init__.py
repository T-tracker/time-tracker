from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy import text

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(name)
    app.config.from_object('config.Config')

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Импорты и регистрация blueprints
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
        # ВАЖНО: импорт моделей внутри контекста приложения
        from app.models import User

        # Создаём таблицы, если их ещё нет
        db.create_all()

        # --- МИГРАЦИИ ЧЕРЕЗ ALTER TABLE ---

        # 1) categories.description (то, что уже было)
        try:
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'categories'
                  AND column_name = 'description'
            """)).fetchone()

            if not result:
                db.session.execute(
                    text("ALTER TABLE categories ADD COLUMN description TEXT")
                )
                db.session.commit()
                print("✅ Column 'description' added to categories")
        except Exception as e:
            db.session.rollback()
            print(f"⚠️ Migration error (categories.description): {e}")

        # 2) events.description — ДОБАВЛЯЕМ ЭТУ ЧАСТЬ
        try:
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'events'
                  AND column_name = 'description'
            """)).fetchone()

            if not result:
                db.session.execute(
                    text("ALTER TABLE events ADD COLUMN description TEXT")
                )
                db.session.commit()
                print("✅ Column 'description' added to events")
        except Exception as e:
            db.session.rollback()
            print(f"⚠️ Migration error (events.description): {e}")

        # Лоадер пользователя для Flask-Login
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))

    return app
