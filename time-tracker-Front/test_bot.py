from bot.states import state_manager
from datetime import datetime, timedelta

def test_state_system():
    print("🧪 Тестирование системы состояний:")
    print("-" * 40)
    
    # Тест 1: Создание состояния
    test_user_id = 12345
    state = state_manager.get_state(test_user_id)
    print(f"✅ Создано состояние для user_id={test_user_id}")
    
    # Тест 2: Старт активности
    state.start_activity("Работа", datetime.now())
    print(f"✅ Начата активность: {state.current_category}")
    print(f"✅ Время начала: {state.start_time}")
    print(f"✅ is_tracking: {state.is_tracking}")
    
    # Тест 3: Сохранение и загрузка
    state_manager.save_states()
    print("✅ Состояния сохранены")
    
    # Тест 4: Проверка истечения срока
    print(f"✅ Просрочено?: {state.is_expired(timeout_minutes=0.1)}")
    
    print("-" * 40)
    print("Тест завершён! Проверь файл bot_data/states.pkl")

if __name__ == "__main__":
    test_state_system()