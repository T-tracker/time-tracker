# create_tables.py
import os
import sys

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Установите ваш DATABASE_URL здесь или через .env
# os.environ['DATABASE_URL'] = 'ваш_postgresql_url_от_базиста'

from app import create_app, db
from app.models import User, Category, Event

print("Создание таблиц в базе данных...")

app = create_app()

with app.app_context():
    try:
        # Создаем все таблицы
        db.create_all()
        print("✅ Таблицы успешно созданы!")

        # Проверяем, что таблицы существуют
        tables = db.engine.table_names()
        print(f"✅ Созданные таблицы: {tables}")

        # Проверяем подключение
        result = db.session.execute('SELECT 1')
        print("✅ Подключение к базе данных работает")

        # Показываем, какая база используется
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        print(f"📊 Используемая база данных: {db_url}")

    except Exception as e:
        print(f"❌ Ошибка при создании таблиц: {e}")
        import traceback

        traceback.print_exc()