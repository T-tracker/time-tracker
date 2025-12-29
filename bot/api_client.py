import requests
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class TimeTrackerAPI:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or 'http://127.0.0.1:10000'
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.user_cache = {}  
        self.categories_cache = {}  

    def authenticate_telegram_user(self, telegram_id: int, username: str = None) -> Tuple[bool, Dict]:
        try:
            response = self.session.post(
                f'{self.base_url}/api/v1/telegram/auth',
                json={'telegram_id': str(telegram_id), 'username': username},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                user_data = {'user_id': data['user_id'], 'username': data['username'], 'has_categories': data.get('has_categories', False)}
                self.user_cache[telegram_id] = user_data
                return True, user_data
            return False, response.json()
        except Exception as e:
            return False, {'error': str(e)}

    def get_user_categories(self, user_id: int) -> List[Dict]:
        try:
            response = self.session.get(
                f'{self.base_url}/api/v1/telegram/categories',
                headers={'X-Telegram-User-ID': str(user_id)},
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get('categories', [])
            return []
        except:
            return []

    def create_event(self, user_id: int, category_id: int, start_time: datetime, end_time: datetime, event_type: str = 'fact', description: str = None) -> Tuple[bool, Dict]:
        try:
            event_data = {'category_id': category_id, 'start_time': start_time.isoformat(), 'end_time': end_time.isoformat(), 'type': event_type, 'description': description or ""}
            response = self.session.post(f'{self.base_url}/api/v1/telegram/events', json=event_data, headers={'X-Telegram-User-ID': str(user_id)}, timeout=10)
            return response.status_code == 201, response.json()
        except:
            return False, {'error': 'Connection error'}

    def create_quick_event(self, user_id: int, code: str, duration_minutes: int = 90) -> Tuple[bool, Dict]:
        try:
            response = self.session.post(f'{self.base_url}/api/v1/telegram/quick', json={'code': code, 'duration': duration_minutes}, headers={'X-Telegram-User-ID': str(user_id)}, timeout=10)
            return response.status_code == 200, response.json()
        except:
            return False, {'error': 'Connection error'}

    def check_connection(self) -> bool:
        try:
            return self.session.get(f'{self.base_url}/api/v1/telegram/auth', timeout=5).status_code == 200
        except:
            return False

# ВАЖНО: ЭТА СТРОКА В КОНЦЕ ФАЙЛА
api_client = TimeTrackerAPI()
