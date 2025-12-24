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

    # Регистрация blueprints
    from app.routes.main_routes import main_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.api_routes import api_bp
    from app.routes.web_routes import web_pages_bp, schedule_api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # ВАЖНО: Разделяем API маршруты
    # api_bp - для Telegram бота и общего API
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    # schedule_api_bp - ТОЛЬКО для расписания (планировщика)
    app.register_blueprint(schedule_api_bp, url_prefix='/api/schedule')

    # web_pages_bp - для веб-страниц (без префикса)
    app.register_blueprint(web_pages_bp)  # ← Это даст /schedule

    # Импортируем модели и настраиваем user_loader внутри контекста
    with app.app_context():
        from app.models import User, Category, Event

        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))

        # Создаем таблицы если их нет
        db.create_all()

        # Функция для инициализации категорий по умолчанию
        def init_default_categories_for_all_users():
            """Добавить категории по умолчанию для всех пользователей без категорий"""
            users = User.query.all()
            for user in users:
                if Category.query.filter_by(user_id=user.id).count() == 0:
                    default_categories = [
                        {'name': 'РАБОТА', 'color': '#FF0000', 'code': 'WORK'},
                        {'name': 'УЧЁБА', 'color': '#00FF00', 'code': 'STUDY'},
                        {'name': 'ОТДЫХ', 'color': '#0000FF', 'code': 'REST'},
                        {'name': 'СПОРТ', 'color': '#FF00FF', 'code': 'SPORT'},
                        {'name': 'ХОББИ', 'color': '#FFFF00', 'code': 'HOBBY'}
                    ]

                    for cat_data in default_categories:
                        category = Category(
                            user_id=user.id,
                            name=cat_data['name'],
                            color=cat_data['color'],
                            code=cat_data['code']
                        )
                        db.session.add(category)

                    db.session.commit()
                    print(f"✅ Созданы категории по умолчанию для пользователя {user.username}")

        # Вызываем инициализацию категорий
        init_default_categories_for_all_users()

    return app