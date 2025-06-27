import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import pytz
from telegram import Bot
from telegram.error import TelegramError
from storage import NotificationStorage

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self, bot: Bot, storage_file: str = "notifications.json"):
        self.bot = bot
        self.storage = NotificationStorage(storage_file)
        self.active_notifications: Dict[int, Dict] = {}
        self.moscow_tz = pytz.timezone('Europe/Moscow')
        
        # Загружаем сохраненные уведомления при инициализации
        self._load_saved_notifications()
    
    def _load_saved_notifications(self):
        """Загружает сохраненные уведомления и восстанавливает задачи"""
        try:
            saved_notifications = self.storage.load_notifications()
            
            for user_id, notification_data in saved_notifications.items():
                self.active_notifications[user_id] = notification_data
                
                # Создаем новую задачу для восстановленного уведомления
                notification_data['task'] = asyncio.create_task(
                    self._notification_loop(user_id, notification_data)
                )
                
                logger.info(f"Restored notification for user {user_id}: {notification_data['message']}")
            
            if saved_notifications:
                logger.info(f"Restored {len(saved_notifications)} notifications from storage")
                
        except Exception as e:
            logger.error(f"Error loading saved notifications: {e}")
    
    def _save_notifications(self):
        """Сохраняет текущие уведомления в хранилище"""
        try:
            self.storage.save_notifications(self.active_notifications)
        except Exception as e:
            logger.error(f"Error saving notifications: {e}")
        
    async def start_notification(self, user_id: int, message: str, interval_minutes: int, start_time: str):
        """Запускает уведомления для пользователя"""
        try:
            # Парсим время начала (формат HH:MM)
            start_hour, start_minute = map(int, start_time.split(':'))
            
            notification_data = {
                'message': message,
                'interval_minutes': interval_minutes,
                'start_hour': start_hour,
                'start_minute': start_minute,
                'active': True,
                'last_response_time': None,
                'task': None
            }
            
            # Останавливаем предыдущие уведомления если есть
            if user_id in self.active_notifications:
                await self.stop_notification(user_id)
            
            self.active_notifications[user_id] = notification_data
            notification_data['task'] = asyncio.create_task(
                self._notification_loop(user_id, notification_data)
            )
            
            # Сохраняем в хранилище
            self._save_notifications()
            
            logger.info(f"Started notifications for user {user_id}: {message} every {interval_minutes} minutes starting at {start_time}")
            
        except Exception as e:
            logger.error(f"Error starting notification for user {user_id}: {e}")
            raise
    
    async def stop_notification(self, user_id: int):
        """Останавливает уведомления для пользователя"""
        if user_id in self.active_notifications:
            notification_data = self.active_notifications[user_id]
            if notification_data['task']:
                notification_data['task'].cancel()
                try:
                    await notification_data['task']
                except asyncio.CancelledError:
                    pass
            
            del self.active_notifications[user_id]
            
            # Сохраняем изменения в хранилище
            self._save_notifications()
            
            logger.info(f"Stopped notifications for user {user_id}")
    
    def pause_notifications(self, user_id: int):
        """Приостанавливает уведомления до следующего дня"""
        if user_id in self.active_notifications:
            self.active_notifications[user_id]['active'] = False
            self.active_notifications[user_id]['last_response_time'] = datetime.now(self.moscow_tz)
            
            # Сохраняем изменения в хранилище
            self._save_notifications()
            
            logger.info(f"Paused notifications for user {user_id} until next day")
    
    async def _notification_loop(self, user_id: int, notification_data: Dict):
        """Основной цикл отправки уведомлений"""
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
                        
                        logger.info(f"Resumed notifications for user {user_id}")
                
                if notification_data['active']:
                    # Проверяем, находимся ли мы в активном временном окне
                    if self._is_in_active_window(now, notification_data):
                        # Проверяем, нужно ли отправить уведомление
                        if self._should_send_notification(now, notification_data):
                            await self._send_notification(user_id, notification_data['message'])
                            notification_data['last_sent'] = now
                            
                            # Сохраняем время последней отправки
                            self._save_notifications()
                
                # Ждем 1 минуту перед следующей проверкой
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                logger.info(f"Notification loop cancelled for user {user_id}")
                break
            except Exception as e:
                logger.error(f"Error in notification loop for user {user_id}: {e}")
                await asyncio.sleep(60)
    
    def _get_next_start_time(self, notification_data: Dict) -> datetime:
        """Вычисляет время следующего запуска уведомлений"""
        now = datetime.now(self.moscow_tz)
        next_start = now.replace(
            hour=notification_data['start_hour'],
            minute=notification_data['start_minute'],
            second=0,
            microsecond=0
        )
        
        # Если время уже прошло сегодня, переносим на завтра
        if next_start <= now:
            next_start += timedelta(days=1)
        
        return next_start
    
    def _is_in_active_window(self, now: datetime, notification_data: Dict) -> bool:
        """Проверяет, находимся ли мы в активном временном окне"""
        start_time = now.replace(
            hour=notification_data['start_hour'],
            minute=notification_data['start_minute'],
            second=0,
            microsecond=0
        )
        
        end_time = start_time + timedelta(days=1)
        end_time = end_time.replace(hour=2, minute=0, second=0, microsecond=0)
        
        return start_time <= now < end_time
    
    def _should_send_notification(self, now: datetime, notification_data: Dict) -> bool:
        """Проверяет, нужно ли отправить уведомление"""
        if 'last_sent' not in notification_data:
            return True
        
        time_since_last = now - notification_data['last_sent']
        return time_since_last.total_seconds() >= notification_data['interval_minutes'] * 60
    
    async def _send_notification(self, user_id: int, message: str):
        """Отправляет уведомление пользователю"""
        try:
            await self.bot.send_message(chat_id=user_id, text=message)
            logger.info(f"Sent notification to user {user_id}: {message}")
        except TelegramError as e:
            logger.error(f"Failed to send notification to user {user_id}: {e}")
    
    def get_active_notifications(self) -> Dict[int, Dict]:
        """Возвращает активные уведомления"""
        return self.active_notifications.copy()
    
    def get_storage_info(self) -> Dict:
        """Возвращает информацию о хранилище"""
        return self.storage.get_storage_info()
    
    async def clear_all_notifications(self):
        """Очищает все уведомления"""
        try:
            # Останавливаем все задачи
            for user_id, notification_data in self.active_notifications.items():
                if notification_data['task']:
                    notification_data['task'].cancel()
                    try:
                        await notification_data['task']
                    except asyncio.CancelledError:
                        pass
            
            self.active_notifications.clear()
            
            # Очищаем хранилище
            self.storage.delete_storage()
            
            logger.info("Cleared all notifications")
            
        except Exception as e:
            logger.error(f"Error clearing notifications: {e}") 