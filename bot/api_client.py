import requests
import logging

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self):
        # ВАЖНО: Убедись, что этот URL совпадает с твоим сайтом на Render
        self.base_url = "https://time-tracker-2-pfld.onrender.com/api/v1"
        self.timeout = 10

    def check_connection(self):
        try:
            response = requests.get(f"{self.base_url}/telegram/categories", timeout=self.timeout)
            return response.status_code in [200, 401, 404]
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    def authenticate_telegram_user(self, telegram_id, username):
        try:
            url = f"{self.base_url}/telegram/auth"
            payload = {"telegram_id": str(telegram_id), "username": username}
            response = requests.post(url, json=payload, timeout=self.timeout)
            if response.status_code == 200:
                return True, response.json()
            return False, response.json()
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return False, {"error": "connection_failed"}

    def get_user_categories(self, user_id):
        try:
            # Используем user_id в заголовке для простоты или в параметрах
            url = f"{self.base_url}/telegram/categories"
            headers = {"X-User-Id": str(user_id)}
            response = requests.get(url, headers=headers, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                return data.get('categories', [])
            return []
        except Exception as e:
            logger.error(f"Get categories error: {e}")
            return []

    def create_event(self, user_id, category_id, start_time, end_time, event_type, description):
        try:
            url = f"{self.base_url}/telegram/events"
            payload = {
                "user_id": user_id,
                "category_id": category_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "event_type": event_type,
                "description": description
            }
            response = requests.post(url, json=payload, timeout=self.timeout)
            return response.status_code == 201, response.json()
        except Exception as e:
            logger.error(f"Create event error: {e}")
            return False, {"error": str(e)}

api_client = APIClient()
