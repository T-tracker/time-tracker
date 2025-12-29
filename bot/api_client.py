import requests
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class TimeTrackerAPI:
    """Клиент для работы с API веб-приложения TimeTracker"""
    
    def __init__(self, base_url: str = None):
        # На Render используем 127.0.0.1, так как бот и веб в одном контейнере
        self.base_url = base_url or 'http://127.0.0.1:10000'
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Оставляем кэш только для инициализации, но не для логики категорий
        self.user_cache = {}  
        self.categories_cache = {}  

    def authenticate_telegram_user(self, telegram_id: int, username: str = None) -> Tuple[bool, Dict]:
        """Авторизация/регистрация пользователя через Telegram"""
        try:
            # Принудительно очищаем локальный кэш перед авторизацией
            self.user_cache.pop(telegram_id, None)
            
            response = self.session.post(
                f'{self.base_url}/api/v1/telegram/auth',
                json={
                    'telegram_id': str(telegram_id),
                    'username': username
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                user_data = {
                    'user_id': data['user_id'],
                    'username': data['username'],
                    'has_categories': data.get('has_categories', False)
                }
                self.user_cache[telegram_id] = user_data
                logger.info(f"✅ Auth Success: ID {telegram_id} -> DB User {user_data['user_id']}")
                return True, user_data
                
            elif response.status_code == 404:
                logger.warning(f"ℹ️ User {telegram_id} needs registration")
                return False, response.json()
            else:
                logger.error(f"❌ Auth Error {response.status_code}: {response.text}")
                return False, {'error': f'Server error: {response.status_code}'}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"📡 Connection error during auth: {e}")
            return False, {'error': 'Connection to server failed'}

    def get_user_categories(self, user_id: int) -> List[Dict]:
        """Получить категории (БЕЗ КЭША, всегда актуальные данные)"""
        try:
            # Мы ВСЕГДА делаем запрос к серверу, игнорируя self.categories_cache
            response = self.session.get(
                f'{self.base_url}/api/v1/telegram/categories',
                headers={'X-Telegram-User-ID': str(user_id)},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                categories = data.get('categories', [])
                # Обновляем кэш просто для справки
                self.categories_cache[user_id] = categories
                logger.info(f"📊 Loaded {len(categories)} categories for user {user_id}")
                return categories
            else:
                logger.error(f"❌ Failed to get categories: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"📡 Connection error getting categories: {e}")
            return []

    def create_event(self, user_id: int, category_id: int, 
                     start_time: datetime, end_time: datetime,
                     event_type: str = 'fact', description: str = None) -> Tuple[bool, Dict]:
        """Создать событие"""
        try:
            event_data = {
                'category_id': category_id,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'type': event_type,
                'description': description or ""
            }
            
            response = self.session.post(
                f'{self.base_url}/api/v1/telegram/events',
                json=event_data,
                headers={'X-Telegram-User-ID': str(user_id)},
                timeout=10
            )
            
            if response.status_code == 201:
                return True, response.json()
            return False, response.json()
                
        except requests.exceptions.RequestException as e:
            logger.error(f"📡 Connection error creating event: {e}")
            return False, {'error': 'Connection failed'}

    def create_quick_event(self, user_id: int, code: str, duration_minutes: int = 90) -> Tuple[bool, Dict]:
        """Быстрое создание события"""
        try:
            response = self.session.post(
                f'{self.base_url}/api/v1/telegram/quick',
                json={'code': code, 'duration': duration_minutes},
                headers={'X-Telegram-User-ID': str(user_id)},
                timeout=10
            )
            return response.status_code == 200, response.json()
        except requests.exceptions.RequestException as e:
            return False, {'error': str(e)}

    def check_connection(self) -> bool:
        """Проверка связи"""
        try:
            response = self.session.get(f'{self.base_url}/api/v1/telegram/auth', timeout=5)
            return response.status_code == 200
        except:
            return False

# Создаем глобальный клиент
api_client = TimeTrackerAPI()
