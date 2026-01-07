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

    # Импорт blueprintов
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
        from app.models import User

        # Создаем недостающие таблицы
        db.create_all()

        # MIGRATION: categories.description
        try:
            result = db.session.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='categories' AND column_name='description'
            """)).fetchone()

            if not result:
                db.session.execute(
                    text("ALTER TABLE categories ADD COLUMN description TEXT")
                )
                db.session.commit()
                print("✅ Added categories.description")

        except Exception as e:
            db.session.rollback()
            print(f"⚠️ Failed to add categories.description: {e}")

        # MIGRATION: events.description
        try:
            result = db.session.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='events' AND column_name='description'
            """)).fetchone()

            if not result:
                db.session.execute(
                    text("ALTER TABLE events ADD COLUMN description TEXT")
                )
                db.session.commit()
                print("✅ Added events.description")

        except Exception as e:
            db.session.rollback()
            print(f"⚠️ Failed to add events.description: {e}")

        # Flask-Login user loader
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))

    return app
    
