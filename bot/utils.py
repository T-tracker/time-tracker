from datetime import datetime, timedelta
import math

def round_to_next_15(start_time: datetime) -> datetime:
    """
    Округляет время ВВЕРХ до ближайшего 15-минутного интервала.
    Пример: 15:17 → 15:30, 15:45 → 15:45, 15:00 → 15:00
    """
    minute = start_time.minute
    second = start_time.second
    microsecond = start_time.microsecond
    
    # Если уже на 15-минутной границе
    if minute % 15 == 0 and second == 0 and microsecond == 0:
        return start_time
    
    # Вычисляем минуты до следующего интервала
    minutes_to_add = 15 - (minute % 15)
    
    # Округляем
    rounded = start_time.replace(
        second=0,
        microsecond=0
    ) + timedelta(minutes=minutes_to_add)
    
    return rounded

def calculate_15min_slots(start: datetime, end: datetime) -> list:
    """
    Разбивает интервал на 15-минутные слоты.
    Возвращает список времён начала каждого слота.
    """
    slots = []
    current = round_to_next_15(start)
    end_rounded = round_to_next_15(end)
    
    while current < end_rounded:
        slots.append(current)
        current += timedelta(minutes=15)
    
    return slots

# Тестирующая функция
def test_rounding():
    """Запусти эту функцию чтобы проверить округление"""
    test_cases = [
        ("15:17:30", "15:30:00"),
        ("15:45:00", "15:45:00"),
        ("15:00:00", "15:00:00"),
        ("15:01:00", "15:15:00"),
        ("23:50:00", "00:00:00"),  # переход через полночь
    ]
    
    print("🔧 Тестирование округления времени:")
    print("-" * 40)
    
    for input_str, expected_str in test_cases:
        test_time = datetime.strptime(input_str, "%H:%M:%S")
        rounded = round_to_next_15(test_time)
        result = "✅" if rounded.strftime("%H:%M:%S") == expected_str else "❌"
        
        print(f"{result} {input_str} → {rounded.strftime('%H:%M:%S')} "
              f"(ожидалось: {expected_str})")

if __name__ == "__main__":
    test_rounding()