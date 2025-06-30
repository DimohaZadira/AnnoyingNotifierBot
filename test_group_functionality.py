#!/usr/bin/env python3
"""
Тестовый файл для демонстрации групповой функциональности Annoying Bot

Этот файл показывает, как работает новая функциональность:
1. Поддержка групповых чатов
2. Тегание пользователей в команде begin_notif
3. Отслеживание ответов тегированных пользователей
4. Приостановка тегов до следующего времени начала
"""

import asyncio
import json
from datetime import datetime
from notification_manager import NotificationManager
from storage import NotificationStorage

class MockBot:
    """Мок-объект бота для тестирования"""
    
    async def send_message(self, chat_id: int, text: str, parse_mode: str = None):
        """Имитирует отправку сообщения"""
        print(f"🤖 Бот отправляет в чат {chat_id}:")
        print(f"   {text}")
        print()
    
    async def get_chat_member(self, chat_id: int, user_id):
        """Имитирует получение информации о пользователе"""
        # Создаем мок-пользователя
        class MockUser:
            def __init__(self, user_id):
                if isinstance(user_id, str):
                    # Если передана строка с @username
                    self.id = int(user_id.replace('@', '').replace('user', ''))
                    self.username = user_id.replace('@', '')
                else:
                    # Если передано число (user_id)
                    self.id = user_id
                    self.username = f"user{user_id}"
                self.first_name = f"User{self.id}"
        
        class MockChatMember:
            def __init__(self, user_id):
                self.user = MockUser(user_id)
        
        return MockChatMember(user_id)

async def test_group_functionality():
    """Тестирует групповую функциональность"""
    print("🧪 Тестирование групповой функциональности Annoying Bot")
    print("=" * 60)
    
    # Создаем мок-бот и менеджер уведомлений
    mock_bot = MockBot()
    notification_manager = NotificationManager(mock_bot, "test_group_notifications.json")
    
    # Тестовые данные
    group_chat_id = -1001234567890  # ID группового чата
    test_message = "Пора пить воду!"
    interval_minutes = 30
    start_time = "09:00"
    tagged_users = [123, 456, 789]  # ID тегированных пользователей
    
    print(f"📋 Тестовые параметры:")
    print(f"   Чат ID: {group_chat_id}")
    print(f"   Сообщение: {test_message}")
    print(f"   Интервал: {interval_minutes} минут")
    print(f"   Время начала: {start_time}")
    print(f"   Тегированные пользователи: {tagged_users}")
    print()
    
    # Запускаем уведомления
    print("🚀 Запуск уведомлений...")
    await notification_manager.start_notification(
        group_chat_id, test_message, interval_minutes, start_time, tagged_users
    )
    print("✅ Уведомления запущены!")
    print()
    
    # Симулируем отправку уведомления
    print("📤 Симуляция отправки уведомления...")
    active_notifications = notification_manager.get_active_notifications()
    notification_data = active_notifications[group_chat_id]
    await notification_manager._send_notification(group_chat_id, notification_data)
    print()
    
    # Симулируем ответы пользователей
    print("👥 Симуляция ответов пользователей...")
    
    # Пользователь 123 отвечает
    print("   Пользователь 123 отвечает...")
    notification_manager.handle_user_response(group_chat_id, 123)
    
    # Пользователь 456 отвечает
    print("   Пользователь 456 отвечает...")
    notification_manager.handle_user_response(group_chat_id, 456)
    
    # Пользователь 789 отвечает (последний)
    print("   Пользователь 789 отвечает...")
    notification_manager.handle_user_response(group_chat_id, 789)
    print()
    
    # Проверяем статус
    print("📊 Проверка статуса уведомлений...")
    notification = active_notifications[group_chat_id]
    responded_count = len(notification.get('responded_users', set()))
    total_count = len(notification['tagged_users'])
    print(f"   Ответили: {responded_count}/{total_count} пользователей")
    
    if responded_count == total_count:
        print("   ✅ Все тегированные пользователи ответили!")
    else:
        print(f"   ⏳ Осталось ответить: {total_count - responded_count} пользователей")
    print()
    
    # Симулируем приостановку уведомлений
    print("⏸️ Симуляция приостановки уведомлений...")
    notification_manager.pause_notifications(group_chat_id)
    print("✅ Уведомления приостановлены до следующего времени начала")
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

def test_storage_serialization():
    """Тестирует сериализацию данных в хранилище"""
    print("🧪 Тестирование сериализации данных")
    print("=" * 40)
    
    storage = NotificationStorage("test_serialization.json")
    
    # Тестовые данные
    test_notifications = {
        -1001234567890: {
            'message': 'Тестовое сообщение',
            'interval_minutes': 30,
            'start_hour': 9,
            'start_minute': 0,
            'active': True,
            'chat_id': -1001234567890,
            'tagged_users': [123, 456, 789],
            'responded_users': {123, 456},
            'last_response_time': datetime.now(),
            'last_sent': datetime.now()
        }
    }
    
    # Сохраняем
    print("💾 Сохранение данных...")
    success = storage.save_notifications(test_notifications)
    print(f"   Результат: {'✅ Успешно' if success else '❌ Ошибка'}")
    
    # Загружаем
    print("📂 Загрузка данных...")
    loaded_notifications = storage.load_notifications()
    print(f"   Загружено уведомлений: {len(loaded_notifications)}")
    
    # Проверяем данные
    if loaded_notifications:
        chat_id = list(loaded_notifications.keys())[0]
        notification = loaded_notifications[chat_id]
        print(f"   Сообщение: {notification['message']}")
        print(f"   Тегированные пользователи: {notification['tagged_users']}")
        print(f"   Ответившие пользователи: {list(notification['responded_users'])}")
    
    # Очищаем
    storage.delete_storage()
    print("✅ Тестовый файл удален")
    print()

if __name__ == "__main__":
    print("🤖 Annoying Bot - Тест групповой функциональности")
    print("=" * 60)
    print()
    
    # Тестируем сериализацию
    test_storage_serialization()
    
    # Тестируем групповую функциональность
    asyncio.run(test_group_functionality()) 