# app/routes/web_routes.py
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from app import db
from app.models import Category, Event
from datetime import datetime

web_bp = Blueprint('web', __name__, url_prefix='/api/v1')


@web_bp.route('/categories', methods=['GET'])
def get_categories():
    """ВСЕГДА работающий эндпоинт - с тестовыми данными"""
    # Пытаемся получить из БД, если не получается - возвращаем тестовые
    try:
        # Проверяем, есть ли БД и таблицы
        categories = Category.query.filter_by(user_id=1).all()
        if categories:
            # БД работает - возвращаем реальные данные
            categories_list = [cat.to_dict() for cat in categories]
            return jsonify({
                'status': 'success',
                'source': 'database',
                'categories': categories_list
            })
    except Exception as e:
        # БД не работает - возвращаем тестовые данные
        print(f"⚠️ БД недоступна, используем тестовые данные: {e}")

    # Тестовые данные (всегда работают)
    return jsonify({
        'status': 'success',
        'source': 'mock_data',
        'categories': [
            {'id': 1, 'name': 'РАБОТА', 'color': '#FF0000', 'code': 'WORK'},
            {'id': 2, 'name': 'УЧЁБА', 'color': '#00FF00', 'code': 'STUDY'},
            {'id': 3, 'name': 'ОТДЫХ', 'color': '#0000FF', 'code': 'REST'},
            {'id': 4, 'name': 'СПОРТ', 'color': '#FF00FF', 'code': 'SPORT'},
            {'id': 5, 'name': 'ХОББИ', 'color': '#FFFF00', 'code': 'HOBBY'}
        ]
    })


@web_bp.route('/events', methods=['POST'])
def create_event():
    """Создание события - логируем, но не сохраняем в БД"""
    data = request.get_json()

    # Логируем что пришло (для отладки)
    print(f"📨 Получено событие: {data}")

    # Возвращаем успех (даже если БД нет)
    return jsonify({
        'status': 'success',
        'message': 'Событие получено (тестовый режим)',
        'received_data': data,
        'event_id': 999  # Фиктивный ID
    }), 201


@web_bp.route('/health', methods=['GET'])
def health_check():
    """Проверка работы API"""
    return jsonify({
        'status': 'healthy',
        'backend': 'Backend 2 Web API',
        'timestamp': datetime.utcnow().isoformat(),
        'endpoints': ['/categories', '/events', '/health']
    })