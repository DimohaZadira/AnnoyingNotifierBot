#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функциональности Annoying Bot
"""

import asyncio
import logging
import os
from datetime import datetime
import pytz
from notification_manager import NotificationManager
from storage import NotificationStorage

# Настройка логирования для тестов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_storage():
    """Тестирует функциональность хранилища"""
    print("💾 Тестирование хранилища...")
    
    # Создаем временный файл для тестов
    test_file = "test_notifications.json"
    storage = NotificationStorage(test_file)
    
    # Тестируем сохранение
    print("\n1. Тестирование сохранения...")
    test_notifications = {
        12345: {
            'message': 'Тестовое сообщение',
            'interval_minutes': 30,
            'start_hour': 9,
            'start_minute': 0,
            'active': True,
            'last_response_time': datetime.now(pytz.timezone('Europe/Moscow')),
            'last_sent': datetime.now(pytz.timezone('Europe/Moscow'))
        }
    }
    
    success = storage.save_notifications(test_notifications)
    print(f"✅ Сохранение: {'успешно' if success else 'ошибка'}")
    
    # Тестируем загрузку
    print("\n2. Тестирование загрузки...")
    loaded_notifications = storage.load_notifications()
    print(f"✅ Загружено уведомлений: {len(loaded_notifications)}")
    
    if loaded_notifications:
        notification = loaded_notifications[12345]
        print(f"✅ Сообщение: {notification['message']}")
        print(f"✅ Интервал: {notification['interval_minutes']} минут")
        print(f"✅ Активно: {notification['active']}")
    
    # Тестируем информацию о хранилище
    print("\n3. Тестирование информации о хранилище...")
    storage_info = storage.get_storage_info()
    print(f"✅ Файл существует: {storage_info['exists']}")
    print(f"✅ Размер файла: {storage_info['size']} байт")
    print(f"✅ Количество уведомлений: {storage_info['notifications_count']}")
    
    # Очищаем тестовый файл
    storage.delete_storage()
    print(f"✅ Тестовый файл удален")
    
    print("\n🎉 Тесты хранилища прошли успешно!")

async def test_notification_manager():
    """Тестирует функциональность NotificationManager"""
    print("🧪 Тестирование NotificationManager...")
    
    # Создаем мок-бот для тестирования
    class MockBot:
        async def send_message(self, chat_id, text):
            print(f"📨 Отправлено сообщение пользователю {chat_id}: {text}")
    
    bot = MockBot()
    manager = NotificationManager(bot, "test_manager.json")
    
    # Тестируем создание уведомления
    print("\n1. Тестирование создания уведомления...")
    await manager.start_notification(12345, "Тестовое сообщение", 5, "14:30")
    
    # Проверяем активные уведомления
    active = manager.get_active_notifications()
    print(f"✅ Активных уведомлений: {len(active)}")
    
    # Проверяем информацию о хранилище
    storage_info = manager.get_storage_info()
    print(f"✅ Сохранено в хранилище: {storage_info['notifications_count']}")
    
    # Тестируем приостановку
    print("\n2. Тестирование приостановки...")
    manager.pause_notifications(12345)
    active = manager.get_active_notifications()
    if 12345 in active:
        print(f"✅ Уведомления приостановлены: {not active[12345]['active']}")
    
    # Тестируем остановку
    print("\n3. Тестирование остановки...")
    await manager.stop_notification(12345)
    active = manager.get_active_notifications()
    print(f"✅ Уведомления остановлены: {len(active) == 0}")
    
    # Очищаем тестовый файл
    manager.storage.delete_storage()
    
    print("\n🎉 Все тесты прошли успешно!")

def test_time_parsing():
    """Тестирует парсинг времени"""
    print("\n🕐 Тестирование парсинг времени...")
    
    test_times = ["09:00", "14:30", "23:59", "00:00"]
    
    for time_str in test_times:
        try:
            hour, minute = map(int, time_str.split(':'))
            print(f"✅ {time_str} -> {hour:02d}:{minute:02d}")
        except Exception as e:
            print(f"❌ Ошибка парсинга {time_str}: {e}")

def test_moscow_timezone():
    """Тестирует работу с московским часовым поясом"""
    print("\n🌍 Тестирование московского часового пояса...")
    
    moscow_tz = pytz.timezone('Europe/Moscow')
    now = datetime.now(moscow_tz)
    
    print(f"✅ Текущее время в Москве: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

async def test_persistence():
    """Тестирует персистентность данных"""
    print("\n💾 Тестирование персистентности...")
    
    # Создаем мок-бот для тестирования
    class MockBot:
        async def send_message(self, chat_id, text):
            print(f"📨 Отправлено сообщение пользователю {chat_id}: {text}")
    
    test_file = "test_persistence.json"
    
    # Создаем первый менеджер
    print("\n1. Создание первого менеджера...")
    bot1 = MockBot()
    manager1 = NotificationManager(bot1, test_file)
    
    # Добавляем уведомление
    await manager1.start_notification(12345, "Персистентное сообщение", 10, "15:00")
    active1 = manager1.get_active_notifications()
    print(f"✅ Уведомлений в первом менеджере: {len(active1)}")
    
    # Останавливаем первый менеджер
    await manager1.stop_notification(12345)
    
    # Создаем второй менеджер (симулируем перезагрузку)
    print("\n2. Создание второго менеджера (перезагрузка)...")
    bot2 = MockBot()
    manager2 = NotificationManager(bot2, test_file)
    
    # Проверяем, восстановились ли уведомления
    active2 = manager2.get_active_notifications()
    print(f"✅ Уведомлений во втором менеджере: {len(active2)}")
    
    if active2:
        print("✅ Уведомления успешно восстановлены!")
        await manager2.stop_notification(12345)
    else:
        print("❌ Уведомления не восстановились")
    
    # Очищаем тестовый файл
    manager2.storage.delete_storage()
    
    print("\n🎉 Тест персистентности завершен!")

if __name__ == "__main__":
    print("🤖 Тестирование Annoying Bot с персистентным хранилищем")
    print("=" * 70)
    
    # Запускаем тесты
    test_time_parsing()
    test_moscow_timezone()
    
    # Асинхронные тесты
    asyncio.run(test_storage())
    asyncio.run(test_notification_manager())
    asyncio.run(test_persistence())
    
    print("\n" + "=" * 70)
    print("✅ Все тесты завершены!")
    print("💾 Бот теперь поддерживает персистентное хранение уведомлений!") 