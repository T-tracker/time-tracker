from datetime import datetime, timedelta
import math

# Сдвиг относительно UTC.
# У тебя всё уезжало на -3 часа, поэтому ставим +3.
# Если потом поймёшь, что нужно +2 или +1 — просто поменяй число здесь.
LOCAL_UTC_OFFSET_HOURS = 3


def get_local_now() -> datetime:
    """
    Текущее ЛОКАЛЬНОЕ время пользователя.

    Сервер обычно живёт в UTC, поэтому берём utcnow() и смещаем.
    Возвращаем naive datetime (без таймзоны), чтобы он совпадал
    по логике с тем временем, которое потом интерпретируется в браузере.
    """
    return datetime.utcnow() + timedelta(hours=LOCAL_UTC_OFFSET_HOURS)


def round_to_next_15(start_time: datetime) -> datetime:
    """
    Округляет время ВВЕРХ до ближайшего 15-минутного интервала.

    Примеры:
      15:00:00 -> 15:00:00
      15:14:59 -> 15:15:00
      15:17:00 -> 15:30:00
      15:45:00 -> 15:45:00
      23:50:00 -> 00:00:00 следующего дня
    """
    minute = start_time.minute
    second = start_time.second
    microsecond = start_time.microsecond

    # Уже на 15-минутной границе и без секунд/микросекунд — ничего не делаем
    if minute % 15 == 0 and second == 0 and microsecond == 0:
        return start_time.replace(second=0, microsecond=0)

    total_minutes = start_time.hour * 60 + minute
    next_slot = math.ceil(total_minutes / 15) * 15

    # Переход через полночь
    if next_slot >= 24 * 60:
        next_slot -= 24 * 60
        new_date = start_time.date() + timedelta(days=1)
    else:
        new_date = start_time.date()

    new_hour = next_slot // 60
    new_minute = next_slot % 60

    return datetime(
        year=new_date.year,
        month=new_date.month,
        day=new_date.day,
        hour=new_hour,
        minute=new_minute,
        second=0,
        microsecond=0,
    )
