import requests
import logging

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self):
        # Убедись, что ссылка правильная (без пробелов в конце)
        self.base_url = "https://time-tracker-2-pfld.onrender.com/api/v1"

    def check_connection(self):
        try:
            # Просто пингуем любой открытый эндпоинт или корень
            return requests.get(f"{self.base_url}/telegram/categories").status_code < 500
        except: 
            return False

    def authenticate_telegram_user(self, telegram_id, username):
        try:
            payload = {
                "telegram_id": str(telegram_id), 
                "username": username
            }
            res = requests.post(f"{self.base_url}/telegram/auth", json=payload)
            
            if res.status_code == 200:
                return True, res.json()
            return False, {}
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return False, {}

    def get_user_categories(self, telegram_id):
        try:
            # Передаем ID в заголовке
            headers = {"X-Telegram-ID": str(telegram_id)}
            res = requests.get(f"{self.base_url}/telegram/categories", headers=headers)
            
            if res.status_code == 200:
                return res.json().get('categories', [])
            return []
        except Exception as e:
            logger.error(f"Categories error: {e}")
            return []

    def save_event(self, telegram_id, category_id, start_time, end_time):
        """Отправляет данные о завершенном событии"""
        try:
            payload = {
                "telegram_id": str(telegram_id),
                "category_id": category_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
            res = requests.post(f"{self.base_url}/telegram/event", json=payload)
            return res.status_code == 201
        except Exception as e:
            logger.error(f"Save event error: {e}")
            return False

api_client = APIClient()
