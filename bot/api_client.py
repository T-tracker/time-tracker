import requests
import logging

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self):
        self.base_url = "https://time-tracker-2-pfld.onrender.com/api/v1"

    def check_connection(self):
        try:
            # Проверяем health, а не категории, чтобы не получать 400 ошибку
            requests.get("https://time-tracker-2-pfld.onrender.com/health", timeout=5)
            return True
        except: 
            return False

    def authenticate_telegram_user(self, telegram_id, username):
        try:
            payload = {
                "telegram_id": str(telegram_id), 
                "username": username
            }
            res = requests.post(f"{self.base_url}/telegram/auth", json=payload)
            return res.status_code == 200, res.json()
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return False, {}

    def get_user_categories(self, telegram_id):
        try:
            # Передаем ID прямо в ссылке, это надежнее
            params = {"telegram_id": str(telegram_id)}
            res = requests.get(f"{self.base_url}/telegram/categories", params=params)
            
            if res.status_code == 200:
                data = res.json().get('categories', [])
                logger.info(f"Loaded {len(data)} categories for {telegram_id}")
                return data
            else:
                logger.error(f"Error getting categories: {res.status_code} - {res.text}")
                return []
        except Exception as e:
            logger.error(f"Categories exception: {e}")
            return []

    def save_event(self, telegram_id, category_id, start_time, end_time):
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
