import requests

class APIClient:
    def __init__(self):
        self.base_url = "https://time-tracker-2-pfld.onrender.com/api/v1"

    def check_connection(self):
        try:
            return requests.get(f"{self.base_url}/telegram/categories").status_code < 500
        except: return False

    def authenticate_telegram_user(self, telegram_id, username):
        try:
            # Мы всегда будем пробовать найти тебя как 'Maria', если твой ник в ТГ другой
            res = requests.post(f"{self.base_url}/telegram/auth", 
                               json={"telegram_id": str(telegram_id), "username": "Maria"})
            return res.status_code == 200, res.json()
        except: return False, {}

    def get_user_categories(self, user_id):
        try:
            # Передаем заголовок X-Username: Maria
            res = requests.get(f"{self.base_url}/telegram/categories", 
                              headers={"X-Username": "Maria"})
            return res.json().get('categories', [])
        except: return []

api_client = APIClient()
