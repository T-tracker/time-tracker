from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Category, Event

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/telegram/auth', methods=['POST'])
def telegram_auth():
    data = request.json
    username = data.get('username', 'Maria') # Если не передано, ищем Maria
    
    # Ищем тебя просто по имени, которое ты создала на сайте
    user = User.query.filter_by(username=username).first()
    
    if user:
        # Принудительно связываем ID, если его нет
        if not user.telegram_id:
            user.telegram_id = str(data.get('telegram_id'))
            db.session.commit()
            
        return jsonify({
            'status': 'authenticated', 
            'user_id': user.id, 
            'username': user.username
        }), 200
    
    return jsonify({'status': 'needs_registration'}), 404

@api_bp.route('/telegram/categories', methods=['GET'])
def telegram_categories():
    # Бот пришлет нам username в заголовке
    username = request.headers.get('X-Username', 'Maria')
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({'categories': []})

    # Берем ВСЕ категории этого пользователя
    cats = Category.query.filter_by(user_id=user.id).all()
    result = [{'id': c.id, 'name': c.name, 'color': c.color} for c in cats]
    return jsonify({'categories': result})
