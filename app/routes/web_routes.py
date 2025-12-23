from flask import Blueprint, jsonify, request, render_template
from flask_login import current_user, login_required
from app import db
from app.models import Category, Event
from datetime import datetime, timedelta

# ====== Blueprint для веб-страниц ======
web_pages_bp = Blueprint('web_pages', __name__)

# ====== Blueprint для API расписания ======
schedule_api_bp = Blueprint('schedule_api', __name__)

# ======== ВЕБ-СТРАНИЦЫ ========

@web_pages_bp.route('/schedule')
@login_required
def schedule_page():
    """Страница с недельным расписанием"""
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    
    days = []
    for i in range(7):
        day_date = start_of_week + timedelta(days=i)
        days.append({
            'name': ['Понедельник', 'Вторник', 'Среда', 'Четверг', 
                    'Пятница', 'Суббота', 'Воскресенье'][i],
            'date': day_date.strftime('%d.%m.%Y'),
            'full_date': day_date.strftime('%Y-%m-%d'),
            'short_name': ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'][i]
        })
    
    week_number = today.isocalendar()[1]
    current_week = f"{today.year}-W{week_number:02d}"
    
    return render_template('schedule.html', 
                          days=days, 
                          current_week=current_week)

# ... остальной код API ...
