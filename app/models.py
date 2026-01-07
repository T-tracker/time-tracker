from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False)
    telegram_id = db.Column(db.String(64), unique=True, nullable=True)
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password) if self.password_hash else False
    
    def __repr__(self):
        return f'<User {self.username}>'


class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    color = db.Column(db.String(7), default='#4361ee')
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='unique_category_per_user'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Event(db.Model):
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    type = db.Column(db.String(10), nullable=False, default='plan') # 'plan' или 'fact'
    source = db.Column(db.String(10), nullable=False, default='web')
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Отношение к категории, чтобы получать цвет и имя сразу
    category = db.relationship('Category', backref='events')

    def to_dict(self):
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
    tablename = 'templates'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # пользователь, которому принадлежит шаблон
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # название шаблона
    name = db.Column(db.String(100), nullable=False)
    
    # категория, с которой связан шаблон
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    
    # длительность по умолчанию (в минутах)
    duration_minutes = db.Column(db.Integer, nullable=False, default=60)
    
    # описание (опционально)
    description = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # связь с Category, чтобы в шаблонах писать template.category.name / .color
    category = db.relationship('Category', backref='templates')
