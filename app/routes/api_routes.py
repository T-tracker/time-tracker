from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user, login_user, logout_user
from app import db
from app.models import User, Category, Event
from datetime import datetime, timedelta

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


# ====== АВТОРИЗАЦИЯ ======

@api_bp.route('/auth/register', methods=['POST'])
def register():
    try:
        data = request.json

        if not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Нужны имя и пароль'}), 400

        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user:
            return jsonify({'error': 'Имя уже занято'}), 400

        user = User(
            username=data['username'],
            email=data.get('email')
        )
        user.set_password(data['password'])

        db.session.add(user)
        db.session.commit()

        login_user(user)

        return jsonify({
            'success': True,
            'user': {'id': user.id, 'username': user.username}
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/auth/login', methods=['POST'])
def login():
    try:
        data = request.json

        user = User.query.filter_by(username=data.get('username')).first()

        if not user or not user.check_password(data.get('password')):
            return jsonify({'error': 'Неверные данные'}), 401

        login_user(user)

        return jsonify({
            'success': True,
            'user': {'id': user.id, 'username': user.username}
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ====== КАТЕГОРИИ ======

@api_bp.route('/categories', methods=['GET'])
@login_required
def get_categories():
    """ОДНА функция получения категорий"""
    categories = Category.query.filter_by(user_id=current_user.id).all()

    result = []
    for cat in categories:
        result.append({
            'id': cat.id,
            'name': cat.name,
            'color': cat.color
        })

    return jsonify(result)


# ====== СОБЫТИЯ ======

@api_bp.route('/events/week', methods=['GET'])
@login_required
def get_week_events():
    """Получить события текущей недели"""
    # Получаем параметры недели
    year = request.args.get('year', type=int)
    week = request.args.get('week', type=int)

    # Если параметры не указаны, используем текущую неделю
    today = datetime.now().date()
    if not year or not week:
        year, week, _ = today.isocalendar()
        start_of_week = today - timedelta(days=today.weekday())
    else:
        # Находим дату по году и номеру недели
        start_of_week = datetime.strptime(f'{year}-W{week:02d}-1', "%Y-W%W-%w").date()

    end_of_week = start_of_week + timedelta(days=6)

    # Получаем события пользователя за эту неделю
    events = Event.query.filter(
        Event.user_id == current_user.id,
        Event.start_time >= start_of_week,
        Event.start_time <= end_of_week + timedelta(days=1)
    ).order_by(Event.start_time).all()

    # Форматируем ответ
    result = []
    for event in events:
        result.append({
            'id': event.id,
            'category_id': event.category_id,
            'start_time': event.start_time.isoformat(),
            'end_time': event.end_time.isoformat(),
            'type': event.type,
            'source': event.source,
            'title': event.title
        })

    return jsonify(result)

@api_bp.route('/categories', methods=['POST'])
@login_required
def create_category():
    try:
        data = request.json

        if not data or not data.get('name'):
            return jsonify({'error': 'Введите название'}), 400

        existing = Category.query.filter_by(
            user_id=current_user.id,
            name=data['name']
        ).first()

        if existing:
            return jsonify({
                'id': existing.id,
                'name': existing.name,
                'color': existing.color
            }), 200

        category = Category(
            user_id=current_user.id,
            name=data['name'],
            color=data.get('color', '#FF6B6B')
        )

        db.session.add(category)
        db.session.commit()

        return jsonify({
            'id': category.id,
            'name': category.name,
            'color': category.color
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@login_required
def delete_category(category_id):
    category = Category.query.filter_by(
        id=category_id,
        user_id=current_user.id
    ).first()

    if not category:
        return jsonify({'error': 'Не найдено'}), 404

    db.session.delete(category)
    db.session.commit()

    return jsonify({'success': True})


# ====== ДРУГИЕ ФУНКЦИИ ======

@api_bp.route('/auth/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'success': True})


@api_bp.route('/auth/me', methods=['GET'])
@login_required
def get_current_user():
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email
    })