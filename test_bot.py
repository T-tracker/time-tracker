# test_bot.py - тестовый скрипт
import sys
import os
import logging
from datetime import datetime, timedelta

# Добавляем путь для импорта
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_api_connection():
    """Тестирование подключения к API"""
    print("=" * 50)
    print("🔧 ТЕСТИРОВАНИЕ ПОДКЛЮЧЕНИЯ К API")
    print("=" * 50)
    
    from bot.api_client import api_client
    
    # Тест 1: Проверка соединения
    print("\n1. Проверка соединения с API...")
    if api_client.check_connection():
        print("✅ API доступен")
    else:
        print("❌ API недоступен")
        return False
    
    # Тест 2: Авторизация тестового пользователя
    print("\n2. Тест авторизации...")
    
    # Тестовые данные (замените на реальные)
    test_telegram_id = 123456789  # Замените на ваш telegram_id
    test_username = "TestUser"
    
    success, result = api_client.authenticate_telegram_user(
        telegram_id=test_telegram_id,
        username=test_username
    )
    
    if success:
        print(f"✅ Авторизация успешна")
        print(f"   User ID: {result['user_id']}")
        print(f"   Username: {result['username']}")
        print(f"   Has categories: {result['has_categories']}")
        
        # Тест 3: Получение категорий
        print("\n3. Тест получения категорий...")
        categories = api_client.get_user_categories(result['user_id'])
        
        if categories:
            print(f"✅ Получено {len(categories)} категорий:")
            for i, cat in enumerate(categories[:5], 1):  # Показываем первые 5
                print(f"   {i}. {cat['name']} (ID: {cat['id']})")
            if len(categories) > 5:
                print(f"   ... и ещё {len(categories) - 5} категорий")
        else:
            print("⚠️ Категорий нет - пользователь должен создать их в веб-интерфейсе")
        
        # Тест 4: Создание тестового события
        print("\n4. Тест создания события...")
        if categories:
            test_category = categories[0]
            start_time = datetime.now() - timedelta(hours=1)
            end_time = datetime.now()
            
            success, event_result = api_client.create_event(
                user_id=result['user_id'],
                category_id=test_category['id'],
                start_time=start_time,
                end_time=end_time,
                event_type='fact',
                description='Тестовое событие из бота'
            )
            
            if success:
                print(f"✅ Событие создано: {event_result.get('message', 'OK')}")
                print(f"   Event ID: {event_result.get('event_id')}")
            else:
                print(f"❌ Ошибка создания: {event_result.get('error', 'Unknown')}")
    
    elif 'needs_registration' in result:
        print("⚠️ Пользователь не зарегистрирован в веб-приложении")
        print(f"   Регистрация: {result.get('registration_url')}")
    else:
        print(f"❌ Ошибка авторизации: {result.get('error', 'Unknown')}")
    
    return True

def test_utils():
    """Тестирование утилит"""
    print("\n" + "=" * 50)
    print("🔧 ТЕСТИРОВАНИЕ УТИЛИТ")
    print("=" * 50)
    
    from bot.utils import round_to_next_15, calculate_15min_slots
    
    test_cases = [
        ("14:32", "14:45"),
        ("14:45", "14:45"),
        ("14:00", "14:00"),
        ("23:50", "00:00"),  # Переход через полночь
    ]
    
    print("\n1. Тест округления времени:")
    for input_time, expected in test_cases:
        dt = datetime.strptime(input_time, "%H:%M")
        rounded = round_to_next_15(dt)
        result = "✅" if rounded.strftime("%H:%M") == expected else "❌"
        print(f"   {result} {input_time} → {rounded.strftime('%H:%M')} (ожидалось: {expected})")
    
    print("\n2. Тест расчёта интервалов:")
    start = datetime.strptime("14:45", "%H:%M")
    end = datetime.strptime("16:15", "%H:%M")
    slots = calculate_15min_slots(start, end)
    
    print(f"   Интервал: {start.strftime('%H:%M')} - {end.strftime('%H:%M')}")
    print(f"   Слотов: {len(slots)}")
    print(f"   Времена: {[s.strftime('%H:%M') for s in slots]}")

def test_state_manager():
    """Тестирование менеджера состояний"""
    print("\n" + "=" * 50)
    print("🔧 ТЕСТИРОВАНИЕ STATE MANAGER")
    print("=" * 50)
    
    from bot.states import state_manager
    
    # Тестовые данные
    test_telegram_id = 999888777
    test_user_id = 100
    
    print("\n1. Тест создания состояния...")
    state = state_manager.get_state(test_telegram_id)
    state.user_id = test_user_id
    state.telegram_id = test_telegram_id
    
    print(f"   Создано состояние для telegram_id={test_telegram_id}")
    print(f"   User ID в состоянии: {state.user_id}")
    
    print("\n2. Тест сохранения состояния...")
    state_manager.save_states()
    print("   ✅ Состояния сохранены")
    
    print("\n3. Тест загрузки состояний...")
    # Создаем новый менеджер для проверки загрузки
    from bot.states import StateManager
    new_manager = StateManager()
    loaded_state = new_manager.get_state(test_telegram_id)
    
    if loaded_state.user_id == test_user_id:
        print(f"   ✅ Состояние загружено корректно")
        print(f"   User ID после загрузки: {loaded_state.user_id}")
    else:
        print("   ❌ Ошибка загрузки состояния")

def main():
    """Основная функция тестирования"""
    print("🚀 ЗАПУСК ТЕСТОВ ИНТЕГРАЦИИ БОТА")
    print("=" * 60)
    
    try:
        # Проверяем наличие токена
        from bot.config import BOT_TOKEN
        if not BOT_TOKEN:
            print("❌ BOT_TOKEN не найден!")
            print("Добавьте BOT_TOKEN в переменные окружения или .env файл")
            return
        
        print(f"✅ BOT_TOKEN найден ({len(BOT_TOKEN)} символов)")
        
        # Запускаем тесты
        test_api_connection()
        test_utils()
        test_state_manager()
        
        print("\n" + "=" * 60)
        print("🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        print("\nСледующие шаги:")
        print("1. Запустите бота: python start_bot.py")
        print("2. Проверьте команду /start в Telegram")
        print("3. Убедитесь, что категории загружаются из веб-приложения")
        
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

#if __name__ == '__main__':
  #  main()
