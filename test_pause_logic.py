#!/usr/bin/env python3
"""
Тест логики приостановки уведомлений при ответах пользователей
"""

import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
import sys
import os

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from notification_manager import NotificationManager
from storage import NotificationStorage

class TestPauseLogic:
    def __init__(self):
        self.storage = NotificationStorage("test_notifications.json")
        self.mock_bot = Mock()
        self.mock_bot.send_message = AsyncMock()
        self.notification_manager = NotificationManager(self.mock_bot, "test_notifications.json")
    
    def test_pause_on_user_response(self):
        """Тестирует приостановку уведомлений при ответе пользователя"""
        print("🧪 Тестируем приостановку уведомлений при ответе пользователя...")
        
        # Создаем тестовые данные
        chat_id = 12345
        user1_id = 111
        user2_id = 222
        
        # Имитируем активное уведомление с тегированными пользователями
        self.notification_manager.active_notifications[chat_id] = {
            'message': 'Тестовое сообщение',
            'interval_minutes': 30,
            'start_hour': 9,
            'start_minute': 0,
            'active': True,
            'tagged_users': [user1_id, user2_id],
            'responded_users': set(),
            'last_response_time': None,
            'task': None
        }
        
        print(f"📊 Начальное состояние: active={self.notification_manager.active_notifications[chat_id]['active']}")
        print(f"👥 Тегированные пользователи: {self.notification_manager.active_notifications[chat_id]['tagged_users']}")
        print(f"✅ Ответившие пользователи: {self.notification_manager.active_notifications[chat_id]['responded_users']}")
        
        # Симулируем ответ первого пользователя
        print(f"\n👤 Пользователь {user1_id} отвечает...")
        self.notification_manager.handle_user_response(chat_id, user1_id)
        
        notification = self.notification_manager.active_notifications[chat_id]
        print(f"📊 После ответа пользователя {user1_id}:")
        print(f"   active={notification['active']}")
        print(f"   responded_users={notification['responded_users']}")
        
        # Проверяем, что уведомления все еще активны
        assert notification['active'] == True, "Уведомления должны остаться активными после ответа первого пользователя"
        assert user1_id in notification['responded_users'], "Пользователь должен быть добавлен в список ответивших"
        
        # Симулируем ответ второго пользователя
        print(f"\n👤 Пользователь {user2_id} отвечает...")
        self.notification_manager.handle_user_response(chat_id, user2_id)
        
        notification = self.notification_manager.active_notifications[chat_id]
        print(f"📊 После ответа пользователя {user2_id}:")
        print(f"   active={notification['active']}")
        print(f"   responded_users={notification['responded_users']}")
        print(f"   last_response_time={notification['last_response_time']}")
        
        # Проверяем, что уведомления приостановлены
        assert notification['active'] == False, "Уведомления должны быть приостановлены после ответа всех пользователей"
        assert notification['last_response_time'] is not None, "Время последнего ответа должно быть установлено"
        assert len(notification['responded_users']) == 0, "Список ответивших должен быть очищен"
        
        print("✅ Тест приостановки уведомлений прошел успешно!")
    
    def test_pause_in_personal_chat(self):
        """Тестирует приостановку уведомлений в личном чате"""
        print("\n🧪 Тестируем приостановку уведомлений в личном чате...")
        
        # Создаем тестовые данные для личного чата
        chat_id = 54321
        user_id = 333
        
        # Имитируем активное уведомление без тегированных пользователей
        self.notification_manager.active_notifications[chat_id] = {
            'message': 'Тестовое сообщение',
            'interval_minutes': 30,
            'start_hour': 9,
            'start_minute': 0,
            'active': True,
            'tagged_users': None,
            'responded_users': set(),
            'last_response_time': None,
            'task': None
        }
        
        print(f"📊 Начальное состояние: active={self.notification_manager.active_notifications[chat_id]['active']}")
        
        # Симулируем ответ пользователя
        print(f"\n👤 Пользователь {user_id} отвечает в личном чате...")
        self.notification_manager.pause_notifications(chat_id, user_id)
        
        notification = self.notification_manager.active_notifications[chat_id]
        print(f"📊 После ответа пользователя:")
        print(f"   active={notification['active']}")
        print(f"   last_response_time={notification['last_response_time']}")
        
        # Проверяем, что уведомления приостановлены
        assert notification['active'] == False, "Уведомления должны быть приостановлены"
        assert notification['last_response_time'] is not None, "Время последнего ответа должно быть установлено"
        
        print("✅ Тест приостановки в личном чате прошел успешно!")
    
    def test_resume_logic(self):
        """Тестирует логику возобновления уведомлений"""
        print("\n🧪 Тестируем логику возобновления уведомлений...")
        
        # Создаем тестовые данные
        chat_id = 99999
        
        # Имитируем приостановленное уведомление
        now = datetime.now()
        self.notification_manager.active_notifications[chat_id] = {
            'message': 'Тестовое сообщение',
            'interval_minutes': 30,
            'start_hour': 9,
            'start_minute': 0,
            'active': False,
            'tagged_users': [111, 222],
            'responded_users': set(),
            'last_response_time': now - timedelta(hours=2),  # Ответ был 2 часа назад
            'task': None
        }
        
        print(f"📊 Начальное состояние: active={self.notification_manager.active_notifications[chat_id]['active']}")
        print(f"🕐 Время последнего ответа: {self.notification_manager.active_notifications[chat_id]['last_response_time']}")
        
        # Проверяем время следующего запуска
        notification = self.notification_manager.active_notifications[chat_id]
        next_start = self.notification_manager._get_next_start_time(notification)
        print(f"🕐 Время следующего запуска: {next_start}")
        
        # Проверяем, что время следующего запуска корректно
        assert next_start.hour == 9, "Время следующего запуска должно быть в 9:00"
        assert next_start.minute == 0, "Минуты следующего запуска должны быть 0"
        
        print("✅ Тест логики возобновления прошел успешно!")
    
    def cleanup(self):
        """Очищает тестовые данные"""
        try:
            os.remove("test_notifications.json")
        except FileNotFoundError:
            pass

def main():
    """Запускает все тесты"""
    print("🚀 Запуск тестов логики приостановки уведомлений...\n")
    
    tester = TestPauseLogic()
    
    try:
        tester.test_pause_on_user_response()
        tester.test_pause_in_personal_chat()
        tester.test_resume_logic()
        
        print("\n🎉 Все тесты прошли успешно!")
        print("✅ Логика приостановки уведомлений работает корректно")
        
    except Exception as e:
        print(f"\n❌ Тест не прошел: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main() 