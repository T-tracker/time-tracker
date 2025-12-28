# bot/api_client.py
import requests
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class TimeTrackerAPI:
    """Клиент для работы с API веб-приложения TimeTracker"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or 'https://time-tracker-z6co.onrender.com'
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Кэш для пользователей и категорий
        self.user_cache = {}  # telegram_id -> {user_id, username, has_categories}
        self.categories_cache = {}  # user_id -> [categories]
    
    def authenticate_telegram_user(self, telegram_id: int, username: str = None) -> Tuple[bool, Dict]:
        """
        Авторизация/регистрация пользователя через Telegram
        Возвращает (success, user_data)
        """
        try:
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
                    'has_categories': data['has_categories']
                }
                self.user_cache[telegram_id] = user_data
                logger.info(f"User authenticated: {telegram_id} -> user_id={user_data['user_id']}")
                return True, user_data
                
            elif response.status_code == 404:
                # Пользователь не найден, нужно зарегистрироваться через веб
                data = response.json()
                logger.warning(f"User needs registration: {telegram_id}")
                return False, data
                
            else:
                logger.error(f"Auth failed: {response.status_code} - {response.text}")
                return False, {'error': f'API error: {response.status_code}'}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during auth: {e}")
            return False, {'error': f'Network error: {str(e)}'}
    
    def get_user_categories(self, user_id: int) -> List[Dict]:
        """Получить категории пользователя"""
        try:
            # Используем API для Telegram-бота
            response = self.session.get(
                f'{self.base_url}/api/v1/telegram/categories',
                headers={'X-Telegram-User-ID': str(user_id)},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                categories = data.get('categories', [])
                self.categories_cache[user_id] = categories
                logger.info(f"Loaded {len(categories)} categories for user_id={user_id}")
                return categories
            else:
                logger.error(f"Failed to get categories: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error getting categories: {e}")
            return []
    
    def create_event(self, user_id: int, category_id: int, 
                     start_time: datetime, end_time: datetime,
                     event_type: str = 'fact', description: str = None) -> Tuple[bool, Dict]:
        """
        Создать событие через API
        """
        try:
            # Форматируем время для API
            event_data = {
                'category_id': category_id,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'type': event_type,
                'description': description
            }
            
            # Используем Telegram API эндпоинт
            response = self.session.post(
                f'{self.base_url}/api/v1/telegram/events',
                json=event_data,
                headers={'X-Telegram-User-ID': str(user_id)},
                timeout=10
            )
            
            if response.status_code == 201:
                data = response.json()
                logger.info(f"Event created: {data}")
                return True, data
            else:
                logger.error(f"Failed to create event: {response.status_code} - {response.text}")
                return False, response.json()
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error creating event: {e}")
            return False, {'error': f'Network error: {str(e)}'}
    
    def create_quick_event(self, user_id: int, code: str, duration_minutes: int = 90) -> Tuple[bool, Dict]:
        """
        Быстрое создание события по коду категории
        """
        try:
            response = self.session.post(
                f'{self.base_url}/api/v1/telegram/quick',
                json={'code': code, 'duration': duration_minutes},
                headers={'X-Telegram-User-ID': str(user_id)},
                timeout=10
            )
            
            if response.status_code == 200:
                return True, response.json()
            else:
                logger.error(f"Quick event failed: {response.status_code}")
                return False, response.json()
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error quick event: {e}")
            return False, {'error': f'Network error: {str(e)}'}
    
    def check_connection(self) -> bool:
        """Проверка соединения с API"""
        try:
            response = self.session.get(f'{self.base_url}/api/v1/telegram/auth', timeout=5)
            return response.status_code < 500
        except:
            return False


# Глобальный экземпляр API клиента
api_client = TimeTrackerAPI()
