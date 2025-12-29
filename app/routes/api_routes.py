from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Category, Event
from app.auth import telegram_auth_required
from datetime import datetime

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/telegram/auth', methods=['POST'])
def telegram_auth():
    data = request.json
    telegram_id = str(data.get('telegram_id'))
    # Ищем по telegram_id или по имени Maria
    user = User.query.filter((User.telegram_id == telegram_id) | (User.username == 'Maria')).first()
    
    if user:
        if not user.telegram_id:
            user.telegram_id = telegram_id
            db.session.commit()
        return jsonify({'status': 'authenticated', 'user_id': user.id, 'username': user.username}), 200
    return jsonify({'status': 'needs_registration'}), 404

@api_bp.route('/telegram/categories', methods=['GET'])
@telegram_auth_required
def telegram_categories():
    user = request.current_user
    categories = Category.query.filter_by(user_id=user.id).all()
    
    # ЕСЛИ ПУСТО - СОЗДАЕМ ТЕСТОВЫЕ КАТЕГОРИИ АВТОМАТОМ
    if not categories:
        basic_cats = [
            {'name': 'Работа', 'color': '#FF5733'},
            {'name': 'Отдых', 'color': '#33FF57'},
            {'name': 'Учеба', 'color': '#3357FF'}
        ]
        for cat_data in basic_cats:
            new_cat = Category(name=cat_data['name'], color=cat_data['color'], user_id=user.id)
            db.session.add(new_cat)
        db.session.commit()
        categories = Category.query.filter_by(user_id=user.id).all()

    return jsonify({
        'categories': [{'id': c.id, 'name': c.name, 'color': c.color} for c in categories],
        'quick_replies': [{'text': c.name, 'callback_data': f'cat_{c.id}'} for c in categories]
    })
