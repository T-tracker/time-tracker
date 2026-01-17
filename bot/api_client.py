import requests
import logging
import os

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self):
        # 1. Сначала проверяем, задан ли порт переменной окружения (как на Render)
        port = os.environ.get("PORT", "10000")
        
        # Мы используем localhost, потому что бот и сайт живут в одном контейнере
        # Это мгновенная связь без выхода в интернет
        self.base_url = f"http://127.0.0.1:{port}/api/v1"
        
        logger.info(f"🔌 API Client настроен на: {self.base_url}")

    def check_connection(self):
        try:
            # Стучимся в корень API или health
            requests.get(self.base_url.replace('/api/v1', '/health'), timeout=5)
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
            params = {"telegram_id": str(telegram_id)}
            # Важно: добавляем таймаут, чтобы бот не вис
            res = requests.get(f"{self.base_url}/telegram/categories", params=params, timeout=10)
            
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
            res = requests.post(f"{self.base_url}/telegram/event", json=payload, timeout=10)
            return res.status_code == 201
        except Exception as e:
            logger.error(f"Save event error: {e}")
            return False

api_client = APIClient()
