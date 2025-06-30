#!/usr/bin/env python3
"""
Тест исправленной функциональности тегов
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
        # Если user_id - это число, возвращаем мок-пользователя
        if isinstance(user_id, int):
            class MockUser:
                def __init__(self, user_id):
                    self.id = user_id
                    self.username = f"user{user_id}"
                    self.first_name = f"User{user_id}"
            
            class MockChatMember:
                def __init__(self, user_id):
                    self.user = MockUser(user_id)
            
            return MockChatMember(user_id)
        else:
            # Если это строка с @username, симулируем ошибку
            raise Exception(f"User {user_id} not found in chat")

async def test_tags_fix():
    """Тестирует исправленную функциональность тегов"""
    print("🧪 Тестирование исправленной функциональности тегов")
    print("=" * 60)
    
    # Создаем мок-бот и менеджер уведомлений
    mock_bot = MockBot()
    notification_manager = NotificationManager(mock_bot, "test_tags_fix_notifications.json")
    
    # Тестовые данные
    group_chat_id = -1001234567890
    test_message = "Пора пить воду!"
    interval_minutes = 30
    start_time = "09:00"
    
    # Тестируем разные типы тегов
    test_cases = [
        {
            "name": "Только user_id (числа)",
            "tagged_users": [123, 456, 789],
            "description": "Пользователи, которые уже писали в чате"
        },
        {
            "name": "Только username (строки)",
            "tagged_users": ["dimoha_zadira", "ilya_savitsky", "test_user"],
            "description": "Пользователи, которые не писали в чате"
        },
        {
            "name": "Смешанные типы",
            "tagged_users": [123, "dimoha_zadira", 456, "test_user"],
            "description": "Комбинация user_id и username"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Тест {i}: {test_case['name']}")
        print(f"   Описание: {test_case['description']}")
        print(f"   Теги: {test_case['tagged_users']}")
        
        # Запускаем уведомления
        await notification_manager.start_notification(
            group_chat_id, test_message, interval_minutes, start_time, test_case['tagged_users']
        )
        
        # Симулируем отправку уведомления
        active_notifications = notification_manager.get_active_notifications()
        notification_data = active_notifications[group_chat_id]
        await notification_manager._send_notification(group_chat_id, notification_data)
        
        # Останавливаем уведомления для следующего теста
        await notification_manager.stop_notification(group_chat_id)
    
    print(f"\n🎉 Тестирование завершено!")

def test_storage_tags():
    """Тестирует сохранение тегов в хранилище"""
    print("🧪 Тестирование сохранения тегов в хранилище")
    print("=" * 50)
    
    storage = NotificationStorage("test_tags_storage.json")
    
    # Тестовые данные с разными типами тегов
    test_notifications = {
        -1001234567890: {
            'message': 'Тест с user_id',
            'interval_minutes': 30,
            'start_hour': 9,
            'start_minute': 0,
            'active': True,
            'chat_id': -1001234567890,
            'message_thread_id': None,
            'tagged_users': [123, 456, 789],
            'responded_users': {123}
        },
        -1009876543210: {
            'message': 'Тест с username',
            'interval_minutes': 15,
            'start_hour': 10,
            'start_minute': 0,
            'active': True,
            'chat_id': -1009876543210,
            'message_thread_id': None,
            'tagged_users': ["dimoha_zadira", "ilya_savitsky"],
            'responded_users': set()
        },
        -1005555555555: {
            'message': 'Тест со смешанными типами',
            'interval_minutes': 20,
            'start_hour': 11,
            'start_minute': 0,
            'active': True,
            'chat_id': -1005555555555,
            'message_thread_id': None,
            'tagged_users': [123, "dimoha_zadira", 456],
            'responded_users': {123}
        }
    }
    
    # Сохраняем
    print("💾 Сохранение данных с тегами...")
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
        print(f"     Тегированные пользователи: {notification['tagged_users']}")
        print(f"     Типы тегов: {[type(tag).__name__ for tag in notification['tagged_users']]}")
    
    # Очищаем
    storage.delete_storage()
    print("✅ Тестовый файл удален")
    print()

if __name__ == "__main__":
    print("🤖 Annoying Bot - Тест исправленной функциональности тегов")
    print("=" * 70)
    print()
    
    # Тестируем сохранение тегов
    test_storage_tags()
    
    # Тестируем исправленную функциональность тегов
    asyncio.run(test_tags_fix()) 