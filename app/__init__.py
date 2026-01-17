import time

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # Регистрируем blueprints
    from app.routes.main_routes import main_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.api_routes import api_bp
    from app.routes.web_routes import web_pages_bp, schedule_api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    app.register_blueprint(web_pages_bp)
    app.register_blueprint(schedule_api_bp, url_prefix="/api/v1")

    with app.app_context():
        from app.models import User  # важно импортировать здесь, чтобы модели были зарегистрированы

        def wait_for_db(max_attempts=20, sleep_seconds=2):
            for attempt in range(1, max_attempts + 1):
                try:
                    db.session.execute(text("SELECT 1"))
                    return True
                except OperationalError as e:
                    print(f"⏳ БД недоступна (попытка {attempt}/{max_attempts}): {e}")
                    time.sleep(sleep_seconds)
            return False

        db_ready = wait_for_db()

        if not db_ready:
            print("❌ БД не поднялась — пропускаем db.create_all() и миграции")
        else:
            # 1) Создаём таблицы
            try:
                db.create_all()
                print("✅ db.create_all() ok")
            except Exception as e:
                print(f"❌ Ошибка при db.create_all(): {e}")

            # 2) Мягкие миграции
            def ensure_column(table: str, column: str, ddl: str):
                try:
                    result = db.session.execute(
                        text("""
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_name=:t AND column_name=:c
                        """),
                        {"t": table, "c": column}
                    ).fetchone()

                    if not result:
                        db.session.execute(text(ddl))
                        db.session.commit()
                        print(f"✅ Column '{column}' added to {table}")
                except Exception as e:
                    db.session.rollback()
                    print(f"ℹ️ {table}.{column} migration skipped: {e}")

            ensure_column("categories", "description",
                          "ALTER TABLE categories ADD COLUMN description TEXT")

            ensure_column("events", "description",
                          "ALTER TABLE events ADD COLUMN description TEXT")

            ensure_column("templates", "category_id",
                          "ALTER TABLE templates ADD COLUMN category_id INTEGER REFERENCES categories(id)")

            ensure_column("templates", "duration_minutes",
                          "ALTER TABLE templates ADD COLUMN duration_minutes INTEGER DEFAULT 60")

            ensure_column("templates", "description",
                          "ALTER TABLE templates ADD COLUMN description TEXT")

        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))

    return app
