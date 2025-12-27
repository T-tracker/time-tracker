from datetime import datetime, timedelta
from typing import Optional, Dict
import pickle
import os
import logging

logger = logging.getLogger(__name__)

class UserState:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.current_category: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.is_tracking = False
        self.last_update = datetime.now()
    
    def start_activity(self, category: str, start_time: datetime):
        self.current_category = category
        self.start_time = start_time
        self.is_tracking = True
        self.last_update = datetime.now()
        logger.info(f"User {self.user_id} started '{category}' at {start_time}")
    
    def stop_activity(self):
        self.is_tracking = False
        self.last_update = datetime.now()
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'category': self.current_category,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'is_tracking': self.is_tracking,
            'last_update': self.last_update.isoformat()
        }
    
    def is_expired(self, timeout_minutes=30):
        return (datetime.now() - self.last_update) > timedelta(minutes=timeout_minutes)

class StateManager:
    def __init__(self, storage_file='bot_data/states.pkl'):
        self.storage_file = storage_file
        self.user_states: Dict[int, UserState] = {}
        self.load_states()
    
    def load_states(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'rb') as f:
                    data = pickle.load(f)
                    self.user_states = {}
                    for user_id, state_data in data.items():
                        state = UserState(user_id)
                        state.current_category = state_data.get('category')
                        start_time = state_data.get('start_time')
                        state.start_time = datetime.fromisoformat(start_time) if start_time else None
                        state.is_tracking = state_data.get('is_tracking', False)
                        last_update = state_data.get('last_update')
                        state.last_update = datetime.fromisoformat(last_update) if last_update else datetime.now()
                        self.user_states[user_id] = state
                logger.info(f"Загружено {len(self.user_states)} состояний")
            except Exception as e:
                logger.error(f"Ошибка загрузки состояний: {e}")
                self.user_states = {}
    
    def save_states(self):
        os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
        data = {uid: state.to_dict() for uid, state in self.user_states.items()}
        with open(self.storage_file, 'wb') as f:
            pickle.dump(data, f)
    
    def get_state(self, user_id: int) -> UserState:
        if user_id not in self.user_states:
            self.user_states[user_id] = UserState(user_id)
        return self.user_states[user_id]
    
    def cleanup_expired(self):
        expired = []
        for user_id, state in self.user_states.items():
            if state.is_expired() and state.is_tracking:
                logger.info(f"Очистка просроченного состояния user_id={user_id}")
                expired.append(user_id)
        
        for user_id in expired:
            del self.user_states[user_id]
        
        if expired:
            self.save_states()

# Важная строка! Создаём глобальный экземпляр менеджера
state_manager = StateManager()