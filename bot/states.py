from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import pickle
import os
import logging

logger = logging.getLogger(__name__)

class UserState:
    def __init__(self, user_id: int, telegram_id: int = None):
        self.user_id = user_id  # ID из БД приложения
        self.telegram_id = telegram_id  # ID Telegram
        self.current_category_id: Optional[int] = None
        self.current_category_name: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.is_tracking = False
        self.last_update = datetime.now()
        self.categories = []  # Кэш категорий пользователя
        self.api_user_data: Optional[Dict] = None  # Данные из API
    
    def start_activity(self, category_id: int, category_name: str, start_time: datetime):
        self.current_category_id = category_id
        self.current_category_name = category_name
        self.start_time = start_time
        self.is_tracking = True
        self.last_update = datetime.now()
        logger.info(f"User {self.user_id} started '{category_name}' (id={category_id}) at {start_time}")
    
    def stop_activity(self):
        self.is_tracking = False
        self.current_category_id = None
        self.current_category_name = None
        self.start_time = None
        self.last_update = datetime.now()
    
    def set_categories(self, categories: list):
        """Обновить список категорий пользователя"""
        self.categories = categories
    
    def set_api_user_data(self, user_data: dict):
        """Сохранить данные пользователя из API"""
        self.api_user_data = user_data
    
    def get_category_by_name(self, name: str) -> Optional[Dict]:
        """Найти категорию по имени"""
        for cat in self.categories:
            if cat.get('name') == name:
                return cat
        return None
    
    def get_category_by_id(self, cat_id: int) -> Optional[Dict]:
        """Найти категорию по ID"""
        for cat in self.categories:
            if cat.get('id') == cat_id:
                return cat
        return None
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'telegram_id': self.telegram_id,
            'category_id': self.current_category_id,
            'category_name': self.current_category_name,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'is_tracking': self.is_tracking,
            'last_update': self.last_update.isoformat(),
            'has_categories': len(self.categories) > 0
        }
    
    def is_expired(self, timeout_minutes=30):
        return (datetime.now() - self.last_update) > timedelta(minutes=timeout_minutes)

class StateManager:
    def __init__(self, storage_file='bot_data/states.pkl'):
        self.storage_file = storage_file
        self.user_states: Dict[int, UserState] = {}  # key: telegram_id
        self.load_states()
    
    def load_states(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'rb') as f:
                    data = pickle.load(f)
                    self.user_states = {}
                    for telegram_id_str, state_data in data.items():
                        telegram_id = int(telegram_id_str)
                        user_id = state_data.get('user_id', telegram_id)
                        state = UserState(user_id, telegram_id)
                        state.current_category_id = state_data.get('category_id')
                        state.current_category_name = state_data.get('category_name')
                        
                        start_time = state_data.get('start_time')
                        state.start_time = datetime.fromisoformat(start_time) if start_time else None
                        
                        state.is_tracking = state_data.get('is_tracking', False)
                        state.last_update = datetime.fromisoformat(
                            state_data.get('last_update', datetime.now().isoformat())
                        )
                        self.user_states[telegram_id] = state
                logger.info(f"Loaded {len(self.user_states)} states")
            except Exception as e:
                logger.error(f"Error loading states: {e}")
                self.user_states = {}
    
    def save_states(self):
        os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
        data = {}
        for telegram_id, state in self.user_states.items():
            data[str(telegram_id)] = state.to_dict()
        with open(self.storage_file, 'wb') as f:
            pickle.dump(data, f)
        logger.debug(f"Saved {len(data)} states")
    
    def get_state(self, telegram_id: int) -> UserState:
        """Получить состояние по Telegram ID"""
        if telegram_id not in self.user_states:
            self.user_states[telegram_id] = UserState(
                user_id=telegram_id,  # временно, пока не авторизуемся
                telegram_id=telegram_id
            )
        return self.user_states[telegram_id]
    
    def update_user_data(self, telegram_id: int, api_user_data: dict):
        """Обновить данные пользователя после авторизации через API"""
        state = self.get_state(telegram_id)
        state.user_id = api_user_data.get('user_id', telegram_id)
        state.set_api_user_data(api_user_data)
        self.save_states()
    
    def update_categories(self, telegram_id: int, categories: list):
        """Обновить категории пользователя"""
        state = self.get_state(telegram_id)
        state.set_categories(categories)
        self.save_states()
    
    def cleanup_expired(self):
        expired = []
        for telegram_id, state in self.user_states.items():
            if state.is_expired() and state.is_tracking:
                logger.info(f"Cleaning expired state for telegram_id={telegram_id}")
                expired.append(telegram_id)
        
        for telegram_id in expired:
            del self.user_states[telegram_id]
        
        if expired:
            self.save_states()

# Важная строка! Создаём глобальный экземпляр менеджера
state_manager = StateManager()
