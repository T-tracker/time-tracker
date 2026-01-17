from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy import text

# Инициализируем расширения
db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Подключаем расширения
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Регистрируем blueprints
    from app.routes.main_routes import main_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.api_routes import api_bp
    from app.routes.web_routes import web_pages_bp, schedule_api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(web_pages_bp)
    app.register_blueprint(schedule_api_bp, url_prefix='/api/v1')

    # Работа с БД
    with app.app_context():
        from app.models import User  # важно импортировать здесь, чтобы модели были зарегистрированы

        # 1. Создаём таблицы (ничего не дропает, только create if not exists)
        try:
            db.create_all()
        except Exception as e:
            print(f"❌ Ошибка при db.create_all(): {e}")

        # 2. Лёгкие «миграции» через raw SQL
        # Они завернуты в try/except — если колонка уже есть или БД не Postgres, просто пропустим

        # 2.1. categories.description
        try:
            result = db.session.execute(
                text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='categories' AND column_name='description'
                """)
            ).fetchone()

            if not result:
                db.session.execute(text("ALTER TABLE categories ADD COLUMN description TEXT"))
                db.session.commit()
                print("✅ Column 'description' added to categories")
        except Exception as e:
            db.session.rollback()
            print(f"ℹ️ categories.description migration skipped: {e}")

        # 2.2. events.description
        try:
            result = db.session.execute(
                text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='events' AND column_name='description'
                """)
            ).fetchone()

            if not result:
                db.session.execute(text("ALTER TABLE events ADD COLUMN description TEXT"))
                db.session.commit()
                print("✅ Column 'description' added to events")
        except Exception as e:
            db.session.rollback()
            print(f"ℹ️ events.description migration skipped: {e}")

        # 2.3. templates.category_id
        try:
            result = db.session.execute(
                text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='templates' AND column_name='category_id'
                """)
            ).fetchone()

            if not result:
                db.session.execute(
                    text("ALTER TABLE templates ADD COLUMN category_id INTEGER REFERENCES categories(id)")
                )
                db.session.commit()
                print("✅ Column 'category_id' added to templates")
        except Exception as e:
            db.session.rollback()
            print(f"ℹ️ templates.category_id migration skipped: {e}")

        # 2.4. templates.duration_minutes
        try:
            result = db.session.execute(
                text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='templates' AND column_name='duration_minutes'
                """)
            ).fetchone()

            if not result:
                db.session.execute(
                    text("ALTER TABLE templates ADD COLUMN duration_minutes INTEGER DEFAULT 60")
                )
                db.session.commit()
                print("✅ Column 'duration_minutes' added to templates")
        except Exception as e:
            db.session.rollback()
            print(f"ℹ️ templates.duration_minutes migration skipped: {e}")

        # 2.5. templates.description
        try:
            result = db.session.execute(
                text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='templates' AND column_name='description'
                """)
            ).fetchone()

            if not result:
                db.session.execute(
                    text("ALTER TABLE templates ADD COLUMN description TEXT")
                )
                db.session.commit()
                print("✅ Column 'description' added to templates")
        except Exception as e:
            db.session.rollback()
            print(f"ℹ️ templates.description migration skipped: {e}")

        # 3. user_loader для Flask-Login
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))

    return app
