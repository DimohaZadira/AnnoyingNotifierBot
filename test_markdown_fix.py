#!/usr/bin/env python3
"""
Тест исправления ошибки парсинга Markdown
"""

import asyncio
from notification_manager import NotificationManager

class MockBot:
    """Мок-объект бота для тестирования"""
    
    def __init__(self):
        self.send_count = 0
        self.fail_first = True  # Первая попытка с HTML может "упасть"
    
    async def send_message(self, chat_id: int, text: str, parse_mode: str = None, message_thread_id: int = None):
        """Имитирует отправку сообщения"""
        self.send_count += 1
        
        # Симулируем ошибку парсинга при первой попытке с HTML
        if self.fail_first and parse_mode == 'HTML' and self.send_count == 1:
            self.fail_first = False
            raise Exception("Can't parse entities: can't find end of the entity starting at byte offset 15")
        
        topic_info = f" (topic: {message_thread_id})" if message_thread_id else " (main chat)"
        parse_info = f" [{parse_mode}]" if parse_mode else " [no markup]"
        print(f"🤖 Бот отправляет в чат {chat_id}{topic_info}{parse_info}:")
        print(f"   {text}")
        print()
    
    async def get_chat_member(self, chat_id: int, user_id):
        """Имитирует получение информации о пользователе"""
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
            raise Exception(f"User {user_id} not found in chat")

async def test_markdown_fix():
    """Тестирует исправление ошибки парсинга Markdown"""
    print("🧪 Тестирование исправления ошибки парсинга Markdown")
    print("=" * 60)
    
    # Создаем мок-бот и менеджер уведомлений
    mock_bot = MockBot()
    notification_manager = NotificationManager(mock_bot, "test_markdown_fix_notifications.json")
    
    # Тестовые данные с проблемными символами
    test_cases = [
        {
            "name": "Сообщение с обычным текстом",
            "message": "Пора пить воду!",
            "tagged_users": [123, "dimoha_zadira"]
        },
        {
            "name": "Сообщение с Markdown символами",
            "message": "Пора пить воду! *жирный* _курсив_ [ссылка](http://example.com)",
            "tagged_users": [456, "test_user"]
        },
        {
            "name": "Сообщение с HTML символами",
            "message": "Пора пить воду! <b>жирный</b> <i>курсив</i>",
            "tagged_users": [789, "html_user"]
        },
        {
            "name": "Сообщение с специальными символами",
            "message": "Пора пить воду! (скобки) [квадратные] {фигурные}",
            "tagged_users": [111, "special_user"]
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Тест {i}: {test_case['name']}")
        print(f"   Сообщение: {test_case['message']}")
        print(f"   Теги: {test_case['tagged_users']}")
        
        # Запускаем уведомления
        await notification_manager.start_notification(
            -1001234567890, test_case['message'], 30, "09:00", test_case['tagged_users']
        )
        
        # Симулируем отправку уведомления
        active_notifications = notification_manager.get_active_notifications()
        notification_data = active_notifications[-1001234567890]
        await notification_manager._send_notification(-1001234567890, notification_data)
        
        # Останавливаем уведомления для следующего теста
        await notification_manager.stop_notification(-1001234567890)
        
        # Сбрасываем счетчик для следующего теста
        mock_bot.send_count = 0
        mock_bot.fail_first = True
    
    print(f"\n🎉 Тестирование завершено!")

if __name__ == "__main__":
    print("🤖 Annoying Bot - Тест исправления ошибки парсинга Markdown")
    print("=" * 70)
    print()
    
    # Тестируем исправление ошибки парсинга
    asyncio.run(test_markdown_fix()) 