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

    # --- Пытаемся перейти на Postgres, но если не выходит — остаёмся на SQLite ---
    postgres_uri = app.config.get("POSTGRES_DATABASE_URI")

    if postgres_uri:
        # Попробуем несколько раз проверить коннект к Postgres
        def postgres_is_alive(max_attempts=5, sleep_seconds=2) -> bool:
            from sqlalchemy import create_engine
            engine = create_engine(
                postgres_uri,
                pool_pre_ping=True,
                pool_recycle=300,
                connect_args={
                    "sslmode": "require",
                    "connect_timeout": 10,
                },
            )
            for attempt in range(1, max_attempts + 1):
                try:
                    with engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                    return True
                except Exception as e:
                    print(f"⏳ Postgres недоступен (попытка {attempt}/{max_attempts}): {e}")
                    time.sleep(sleep_seconds)
            return False

        if postgres_is_alive():
            app.config["SQLALCHEMY_DATABASE_URI"] = postgres_uri
            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
                "pool_pre_ping": True,
                "pool_recycle": 300,
                "connect_args": {
                    "sslmode": "require",
                    "connect_timeout": 10,
                },
            }
            print("✅ Используем Postgres")
        else:
            print("⚠️ Postgres недоступен — запускаемся на SQLite временно")

    # --- Инициализация расширений ---
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
        from app.models import User

        # Создаём таблицы в той БД, которую выбрали (SQLite или Postgres)
        try:
            db.create_all()
            print("✅ db.create_all() ok")
        except Exception as e:
            print(f"❌ Ошибка при db.create_all(): {e}")

        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))

    return app
