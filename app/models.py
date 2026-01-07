from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(UserMixin, db.Model):
    tablename = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False)
    telegram_id = db.Column(db.String(64), unique=True, nullable=True)
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password) if self.password_hash else False
    
    def repr(self) -> str:
        return f'<User {self.username}>'


class Category(db.Model):
    tablename = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    color = db.Column(db.String(7), default='#4361ee')
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    table_args = (
        db.UniqueConstraint('user_id', 'name', name='unique_category_per_user'),
    )
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Event(db.Model):
    tablename = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    # 'plan' или 'fact'
    type = db.Column(db.String(10), nullable=False, default='plan')
    # 'web' или 'telegram'
    source = db.Column(db.String(10), nullable=False, default='web')
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Отношение к категории, чтобы получать цвет и имя сразу
    category = db.relationship('Category', backref='events')

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else 'Unknown',
            'category_color': self.category.color if self.category else '#ccc',
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'type': self.type,
            'source': self.source
        }


class Template(db.Model):
    """
    Шаблон события пользователя.
    Привязан к категории и имеет длительность, описание и владельца.
    """
    tablename = 'templates'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Пользователь, которому принадлежит шаблон
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Название шаблона
    name = db.Column(db.String(100), nullable=False)
    
    # Категория, с которой связан шаблон
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    
    # Длительность по умолчанию (в минутах)
    duration_minutes = db.Column(db.Integer, nullable=False, default=60)
    
    # Описание (необязательно)
    description = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связь с Category, чтобы в шаблонах писать template.category.name / template.category.color
    category = db.relationship('Category', backref='templates')
