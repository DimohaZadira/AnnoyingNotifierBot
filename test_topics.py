#!/usr/bin/env python3
"""
Тест работы с топиками в Annoying Bot
"""

import asyncio
from notification_manager import NotificationManager
from storage import NotificationStorage

class MockBot:
    """Мок-объект бота для тестирования"""
    
    async def send_message(self, chat_id: int, text: str, parse_mode: str = None, message_thread_id: int = None):
        """Имитирует отправку сообщения"""
        topic_info = f" (topic: {message_thread_id})" if message_thread_id else " (main chat)"
        print(f"🤖 Бот отправляет в чат {chat_id}{topic_info}:")
        print(f"   {text}")
        print()
    
    async def get_chat_member(self, chat_id: int, user_id):
        """Имитирует получение информации о пользователе"""
        class MockUser:
            def __init__(self, user_id):
                if isinstance(user_id, str):
                    self.id = int(user_id.replace('@', '').replace('user', ''))
                    self.username = user_id.replace('@', '')
                else:
                    self.id = user_id
                    self.username = f"user{user_id}"
                self.first_name = f"User{self.id}"
        
        class MockChatMember:
            def __init__(self, user_id):
                self.user = MockUser(user_id)
        
        return MockChatMember(user_id)

async def test_topics():
    """Тестирует работу с топиками"""
    print("🧪 Тестирование работы с топиками")
    print("=" * 50)
    
    # Создаем мок-бот и менеджер уведомлений
    mock_bot = MockBot()
    notification_manager = NotificationManager(mock_bot, "test_topics_notifications.json")
    
    # Тестовые данные
    group_chat_id = -1001234567890
    topic_id = 12345  # ID топика
    test_message = "Пора пить воду!"
    interval_minutes = 30
    start_time = "09:00"
    tagged_users = [123, 456]
    
    print(f"📋 Тестовые параметры:")
    print(f"   Чат ID: {group_chat_id}")
    print(f"   Топик ID: {topic_id}")
    print(f"   Сообщение: {test_message}")
    print(f"   Интервал: {interval_minutes} минут")
    print(f"   Время начала: {start_time}")
    print(f"   Тегированные пользователи: {tagged_users}")
    print()
    
    # Запускаем уведомления в топике
    print("🚀 Запуск уведомлений в топике...")
    await notification_manager.start_notification(
        group_chat_id, test_message, interval_minutes, start_time, tagged_users, topic_id
    )
    print("✅ Уведомления запущены в топике!")
    print()
    
    # Симулируем отправку уведомления
    print("📤 Симуляция отправки уведомления в топик...")
    active_notifications = notification_manager.get_active_notifications()
    notification_data = active_notifications[group_chat_id]
    await notification_manager._send_notification(group_chat_id, notification_data)
    print()
    
    # Проверяем, что message_thread_id сохранен
    print("💾 Проверка сохранения message_thread_id...")
    saved_thread_id = notification_data.get('message_thread_id')
    if saved_thread_id == topic_id:
        print(f"   ✅ message_thread_id сохранен корректно: {saved_thread_id}")
    else:
        print(f"   ❌ Ошибка: ожидался {topic_id}, получен {saved_thread_id}")
    print()
    
    # Тестируем уведомления без топика (основной чат)
    print("📤 Симуляция отправки уведомления в основной чат...")
    main_chat_id = -1009876543210
    
    await notification_manager.start_notification(
        main_chat_id, "Тест в основном чате", 15, "10:00", None, None
    )
    
    main_notification = notification_manager.get_active_notifications()[main_chat_id]
    await notification_manager._send_notification(main_chat_id, main_notification)
    print()
    
    # Проверяем сохранение в хранилище
    print("💾 Проверка сохранения в хранилище...")
    storage_info = notification_manager.get_storage_info()
    print(f"   Файл: {storage_info['file_path']}")
    print(f"   Размер: {storage_info['size']} байт")
    print(f"   Уведомлений: {storage_info['notifications_count']}")
    print()
    
    # Очищаем тестовые данные
    print("🧹 Очистка тестовых данных...")
    await notification_manager.clear_all_notifications()
    print("✅ Тестовые данные очищены")
    print()
    
    print("🎉 Тестирование завершено!")

def test_storage_topics():
    """Тестирует сохранение топиков в хранилище"""
    print("🧪 Тестирование сохранения топиков в хранилище")
    print("=" * 50)
    
    storage = NotificationStorage("test_topics_storage.json")
    
    # Тестовые данные с топиками
    test_notifications = {
        -1001234567890: {
            'message': 'Уведомление в топике',
            'interval_minutes': 30,
            'start_hour': 9,
            'start_minute': 0,
            'active': True,
            'chat_id': -1001234567890,
            'message_thread_id': 12345,
            'tagged_users': [123, 456],
            'responded_users': {123}
        },
        -1009876543210: {
            'message': 'Уведомление в основном чате',
            'interval_minutes': 15,
            'start_hour': 10,
            'start_minute': 0,
            'active': True,
            'chat_id': -1009876543210,
            'message_thread_id': None,
            'tagged_users': [],
            'responded_users': set()
        }
    }
    
    # Сохраняем
    print("💾 Сохранение данных с топиками...")
    success = storage.save_notifications(test_notifications)
    print(f"   Результат: {'✅ Успешно' if success else '❌ Ошибка'}")
    
    # Загружаем
    print("📂 Загрузка данных...")
    loaded_notifications = storage.load_notifications()
    print(f"   Загружено уведомлений: {len(loaded_notifications)}")
    
    # Проверяем данные
    for chat_id, notification in loaded_notifications.items():
        print(f"   Чат {chat_id}:")
        print(f"     Сообщение: {notification['message']}")
        print(f"     Топик ID: {notification['message_thread_id']}")
        print(f"     Тегированные пользователи: {notification['tagged_users']}")
    
    # Очищаем
    storage.delete_storage()
    print("✅ Тестовый файл удален")
    print()

if __name__ == "__main__":
    print("🤖 Annoying Bot - Тест работы с топиками")
    print("=" * 60)
    print()
    
    # Тестируем сохранение топиков
    test_storage_topics()
    
    # Тестируем работу с топиками
    asyncio.run(test_topics()) 