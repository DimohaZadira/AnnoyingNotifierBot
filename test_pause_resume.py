#!/usr/bin/env python3
"""
Быстрый тест флоу приостановки и возобновления уведомлений
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict
import pytz
from notification_manager import NotificationManager

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockBot:
    def __init__(self):
        self.sent_messages = []
    
    async def send_message(self, chat_id, text):
        timestamp = datetime.now(pytz.timezone('Europe/Moscow'))
        self.sent_messages.append({
            'chat_id': chat_id,
            'text': text,
            'timestamp': timestamp
        })
        print(f"📨 [{timestamp.strftime('%H:%M:%S')}] Отправлено пользователю {chat_id}: {text}")

class TestNotificationManager(NotificationManager):
    """Расширенный менеджер для тестирования с короткими интервалами"""
    
    async def _notification_loop(self, user_id: int, notification_data: Dict):
        """Основной цикл отправки уведомлений с коротким интервалом для тестов"""
        while True:
            try:
                now = datetime.now(self.moscow_tz)
                
                # Проверяем, нужно ли возобновить уведомления
                if not notification_data['active'] and notification_data['last_response_time']:
                    next_start = self._get_next_start_time(notification_data)
                    if now >= next_start:
                        notification_data['active'] = True
                        notification_data['last_response_time'] = None
                        
                        # Сохраняем изменения в хранилище
                        self._save_notifications()
                        
                        logger.info(f"Resumed notifications for user {user_id} at {next_start.strftime('%H:%M')}")
                
                if notification_data['active']:
                    # Проверяем, находимся ли мы в активном временном окне
                    if self._is_in_active_window(now, notification_data):
                        # Проверяем, нужно ли отправить уведомление
                        if self._should_send_notification(now, notification_data):
                            await self._send_notification(user_id, notification_data['message'])
                            notification_data['last_sent'] = now
                            
                            # Сохраняем время последней отправки
                            self._save_notifications()
                
                # Ждем 2 секунды для тестов (вместо 60)
                await asyncio.sleep(2)
                
            except asyncio.CancelledError:
                logger.info(f"Notification loop cancelled for user {user_id}")
                break
            except Exception as e:
                logger.error(f"Error in notification loop for user {user_id}: {e}")
                await asyncio.sleep(2)

async def test_quick_pause_resume():
    """Быстрый тест приостановки и возобновления"""
    print("🧪 Быстрый тест приостановки и возобновления")
    print("=" * 60)
    
    bot = MockBot()
    manager = TestNotificationManager(bot, "test_quick.json")
    
    # Запускаем уведомления с текущим временем
    now = datetime.now(pytz.timezone('Europe/Moscow'))
    start_time = now.strftime('%H:%M')
    
    print(f"🕐 Время начала: {start_time}")
    print(f"⏰ Интервал: каждые 10 секунд")
    
    # Запускаем уведомления с очень коротким интервалом
    await manager.start_notification(12345, "Быстрый тест", 1, start_time)
    
    # Ждем 5 секунд для первого сообщения
    print("\n⏳ Ожидание 5 секунд для первого сообщения...")
    await asyncio.sleep(5)
    print(f"📊 Сообщений после запуска: {len(bot.sent_messages)}")
    
    # Приостанавливаем
    print("\n⏸️ Приостанавливаем уведомления...")
    manager.pause_notifications(12345)
    
    # Ждем 10 секунд - сообщения не должны отправляться
    print("⏳ Ожидание 10 секунд (сообщения не должны отправляться)...")
    await asyncio.sleep(10)
    messages_before = len(bot.sent_messages)
    print(f"📊 Сообщений после приостановки: {messages_before}")
    
    # Проверяем статус
    active_notifications = manager.get_active_notifications()
    if 12345 in active_notifications:
        notification = active_notifications[12345]
        print(f"📊 Статус: {'активны' if notification['active'] else 'приостановлены'}")
        
        # Вычисляем следующее время начала
        next_start = manager._get_next_start_time(notification)
        print(f"🕐 Следующее время начала: {next_start.strftime('%H:%M:%S')}")
        
        # Если следующее время - завтра, то изменим его на сегодня
        if next_start.date() > now.date():
            print("🔄 Изменяем время начала на сегодня для быстрого теста...")
            # Создаем новое уведомление с временем через 10 секунд
            new_start_time = (now + timedelta(seconds=10)).strftime('%H:%M')
            await manager.stop_notification(12345)
            await manager.start_notification(12345, "Быстрый тест", 1, new_start_time)
            
            # Ждем до нового времени начала
            wait_seconds = 15  # 10 секунд + 5 секунд буфер
            print(f"⏳ Ожидание {wait_seconds} секунд до возобновления...")
            await asyncio.sleep(wait_seconds)
        else:
            # Ждем до следующего времени начала
            wait_seconds = (next_start - datetime.now(pytz.timezone('Europe/Moscow'))).total_seconds()
            if wait_seconds > 0:
                print(f"⏳ Ожидание {wait_seconds:.0f} секунд до возобновления...")
                await asyncio.sleep(wait_seconds + 5)
        
        # Ждем еще 10 секунд для проверки возобновления
        print("⏳ Ожидание 10 секунд для проверки возобновления...")
        await asyncio.sleep(10)
        
        messages_after = len(bot.sent_messages)
        print(f"📊 Сообщений после ожидания: {messages_after}")
        
        # Проверяем статус после ожидания
        active_notifications = manager.get_active_notifications()
        if 12345 in active_notifications:
            notification = active_notifications[12345]
            print(f"📊 Финальный статус: {'активны' if notification['active'] else 'приостановлены'}")
        
        if messages_after > messages_before:
            print("✅ Тест ПРОЙДЕН: Уведомления корректно возобновились")
        else:
            print("❌ Тест НЕ ПРОЙДЕН: Уведомления не возобновились")
    
    # Показываем все сообщения
    print("\n📋 Все отправленные сообщения:")
    for i, msg in enumerate(bot.sent_messages, 1):
        print(f"   {i}. [{msg['timestamp'].strftime('%H:%M:%S')}] {msg['text']}")
    
    # Останавливаем
    await manager.stop_notification(12345)
    manager.storage.delete_storage()
    
    print("\n🎉 Быстрый тест завершен!")

async def test_logic_verification():
    """Тест логики без ожидания времени"""
    print("\n🧪 Тест логики приостановки/возобновления")
    print("=" * 50)
    
    bot = MockBot()
    manager = TestNotificationManager(bot, "test_logic.json")
    
    # Запускаем уведомления
    now = datetime.now(pytz.timezone('Europe/Moscow'))
    start_time = now.strftime('%H:%M')
    
    await manager.start_notification(12345, "Тест логики", 1, start_time)
    
    # Проверяем начальный статус
    active_notifications = manager.get_active_notifications()
    if 12345 in active_notifications:
        notification = active_notifications[12345]
        print(f"✅ Начальный статус: {'активны' if notification['active'] else 'приостановлены'}")
    
    # Приостанавливаем
    manager.pause_notifications(12345)
    
    # Проверяем статус после приостановки
    active_notifications = manager.get_active_notifications()
    if 12345 in active_notifications:
        notification = active_notifications[12345]
        print(f"⏸️ Статус после приостановки: {'активны' if notification['active'] else 'приостановлены'}")
        print(f"🕐 Время последнего ответа: {notification['last_response_time'].strftime('%H:%M:%S')}")
    
    # Проверяем вычисление следующего времени
    next_start = manager._get_next_start_time(notification)
    print(f"🕐 Следующее время начала: {next_start.strftime('%H:%M:%S')}")
    
    # Симулируем время после следующего начала
    print("🔄 Симуляция времени после следующего начала...")
    # Временно изменяем время последнего ответа на вчера
    notification['last_response_time'] = now - timedelta(days=1)
    
    # Проверяем, что уведомления должны возобновиться
    next_start = manager._get_next_start_time(notification)
    should_resume = now >= next_start
    print(f"🕐 Должны ли возобновиться: {should_resume}")
    
    # Останавливаем
    await manager.stop_notification(12345)
    manager.storage.delete_storage()
    
    print("✅ Тест логики завершен!")

async def test_detailed_logic():
    """Детальный тест логики вычисления следующего времени начала"""
    print("\n🧪 Детальный тест логики вычисления времени")
    print("=" * 60)
    
    bot = MockBot()
    manager = TestNotificationManager(bot, "test_detailed.json")
    
    # Тест 1: Ответ до времени начала
    print("📋 Тест 1: Ответ до времени начала (09:00)")
    now = datetime.now(pytz.timezone('Europe/Moscow'))
    
    # Создаем уведомление с временем начала 09:00
    await manager.start_notification(12345, "Тест 1", 1, "09:00")
    
    # Симулируем ответ в 08:30
    response_time = now.replace(hour=8, minute=30, second=0, microsecond=0)
    manager.active_notifications[12345]['last_response_time'] = response_time
    manager.active_notifications[12345]['active'] = False
    
    next_start = manager._get_next_start_time(manager.active_notifications[12345])
    expected = response_time.replace(hour=9, minute=0, second=0, microsecond=0)
    
    print(f"   Время ответа: {response_time.strftime('%H:%M')}")
    print(f"   Время начала: 09:00")
    print(f"   Ожидаемое время возобновления: {expected.strftime('%H:%M')}")
    print(f"   Вычисленное время: {next_start.strftime('%H:%M')}")
    print(f"   ✅ Правильно: {next_start == expected}")
    
    # Тест 2: Ответ после времени начала
    print("\n📋 Тест 2: Ответ после времени начала (09:00)")
    
    # Симулируем ответ в 14:30
    response_time = now.replace(hour=14, minute=30, second=0, microsecond=0)
    manager.active_notifications[12345]['last_response_time'] = response_time
    
    next_start = manager._get_next_start_time(manager.active_notifications[12345])
    expected = response_time.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    print(f"   Время ответа: {response_time.strftime('%H:%M')}")
    print(f"   Время начала: 09:00")
    print(f"   Ожидаемое время возобновления: {expected.strftime('%H:%M')} (следующий день)")
    print(f"   Вычисленное время: {next_start.strftime('%H:%M')}")
    print(f"   ✅ Правильно: {next_start == expected}")
    
    # Тест 3: Ответ точно в время начала
    print("\n📋 Тест 3: Ответ точно в время начала (09:00)")
    
    # Симулируем ответ в 09:00
    response_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
    manager.active_notifications[12345]['last_response_time'] = response_time
    
    next_start = manager._get_next_start_time(manager.active_notifications[12345])
    expected = response_time.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    print(f"   Время ответа: {response_time.strftime('%H:%M')}")
    print(f"   Время начала: 09:00")
    print(f"   Ожидаемое время возобновления: {expected.strftime('%H:%M')} (следующий день)")
    print(f"   Вычисленное время: {next_start.strftime('%H:%M')}")
    print(f"   ✅ Правильно: {next_start == expected}")
    
    # Останавливаем
    await manager.stop_notification(12345)
    manager.storage.delete_storage()
    
    print("\n✅ Детальный тест завершен!")

if __name__ == "__main__":
    print("🤖 Быстрое тестирование флоу приостановки и возобновления")
    print("=" * 70)
    
    # Запускаем быстрые тесты
    asyncio.run(test_logic_verification())
    asyncio.run(test_quick_pause_resume())
    asyncio.run(test_detailed_logic())
    
    print("\n" + "=" * 70)
    print("✅ Все тесты завершены!") 