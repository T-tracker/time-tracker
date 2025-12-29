from flask import Blueprint, request, jsonify
from flask_login import login_required
from app import db
from app.models import User, Category, Event, Template
from app.auth import telegram_auth_required
from datetime import datetime, timedelta
from flask_login import current_user
import re

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/telegram/auth', methods=['GET', 'POST'])
def telegram_auth():
    if request.method == 'GET':
        return jsonify({'status': 'ok', 'message': 'API is reachable'}), 200

    data = request.json
    telegram_id = data.get('telegram_id')
    
    user = User.query.filter_by(telegram_id=str(telegram_id)).first()
    
    if user:
        # Проверяем категории у него или у "Maria"
        has_cats = Category.query.filter_by(user_id=user.id).count() > 0
        if not has_cats:
            maria = User.query.filter_by(username='Maria').first()
            if maria:
                has_cats = Category.query.filter_by(user_id=maria.id).count() > 0

        return jsonify({
            'status': 'authenticated',
            'user_id': user.id,
            'username': user.username,
            'has_categories': has_cats
        }), 200
    else:
        reg_url = f'https://time-tracker-2-pfld.onrender.com/register?telegram_id={telegram_id}'
        return jsonify({'status': 'needs_registration', 'registration_url': reg_url}), 404

@api_bp.route('/telegram/categories', methods=['GET'])
@telegram_auth_required
def telegram_categories():
    user = request.current_user
    
    # 1. Сначала честно ищем категории текущего пользователя
    categories = Category.query.filter_by(user_id=user.id).all()
    
    # 2. Если пусто — ИЩЕМ АККАУНТ "Maria"
    if not categories:
        maria_user = User.query.filter_by(username='Maria').first()
        if maria_user:
            categories = Category.query.filter_by(user_id=maria_user.id).all()

    # 3. Если всё равно пусто — выводим диагностику на кнопки
    if not categories:
        return jsonify({
            'categories': [
                {'id': 999, 'name': f'Я вижу тебя как: {user.username}', 'color': '#FF0000'},
                {'id': 998, 'name': 'Нужна категория для Maria', 'color': '#00FF00'}
            ],
            'quick_replies': [
                {'text': f'Имя в базе: {user.username}', 'callback_data': 'debug'},
                {'text': '🔄 Проверить Maria', 'callback_data': 'cat_998'}
            ]
        })

    return jsonify({
        'categories': [{'id': cat.id, 'name': cat.name, 'color': cat.color} for cat in categories],
        'quick_replies': [{'text': cat.name, 'callback_data': f'cat_{cat.id}'} for cat in categories[:10]]
    })

@api_bp.route('/telegram/events', methods=['POST'])
@telegram_auth_required
def telegram_create_event():
    user = request.current_user
    data = request.json
    time_input = data.get('time', '')
    category_id = data.get('category_id')
    
    try:
        if '-' in time_input:
            start_str, end_str = time_input.split('-')
            start_time = parse_time(start_str.strip())
            end_time = parse_time(end_str.strip())
        else:
            duration = parse_duration(time_input)
            start_time = datetime.utcnow()
            end_time = start_time + duration
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    
    # Важно: разрешаем сохранять в категорию, даже если она от аккаунта Maria
    event = Event(
        user_id=user.id,
        category_id=category_id,
        type=data.get('type', 'fact'),
        start_time=start_time,
        end_time=end_time,
        source='telegram'
    )
    db.session.add(event)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Записано!'}), 201

@api_bp.route('/telegram/quick', methods=['POST'])
@telegram_auth_required
def telegram_quick_event():
    user = request.current_user
    data = request.json
    code = data.get('code')
    
    # Ищем категорию у текущего юзера или у Maria
    category = Category.query.filter(
        (Category.user_id == user.id) | 
        (Category.user_id == User.id) & (User.username == 'Maria')
    ).filter(Category.name.ilike(f'%{code}%')).first()
    
    if not category:
        return jsonify({'error': 'Not found'}), 404
    
    start_time = datetime.utcnow()
    event = Event(
        user_id=user.id,
        category_id=category.id,
        type='fact',
        start_time=start_time,
        end_time=start_time + timedelta(minutes=90),
        source='telegram_quick'
    )
    db.session.add(event)
    db.session.commit()
    return jsonify({'status': 'success', 'category': category.name})

def parse_time(time_str):
    if ':' in time_str:
        hours, minutes = map(int, time_str.split(':'))
        return datetime.utcnow().replace(hour=hours % 24, minute=minutes, second=0, microsecond=0)
    raise ValueError("Time format error")

def parse_duration(duration_str):
    match = re.search(r'[\d.]+', duration_str)
    val = float(match.group()) if match else 60
    return timedelta(hours=val) if 'час' in duration_str.lower() else timedelta(minutes=val)

@api_bp.route('/templates/<int:template_id>', methods=['DELETE'])
@login_required
def delete_template(template_id):
    t = Template.query.filter_by(id=template_id, user_id=current_user.id).first()
    if t:
        db.session.delete(t)
        db.session.commit()
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 404
