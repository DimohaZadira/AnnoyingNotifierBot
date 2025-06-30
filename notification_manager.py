import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
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
            
            for chat_id, notification_data in saved_notifications.items():
                self.active_notifications[chat_id] = notification_data
                
                # Создаем новую задачу для восстановленного уведомления
                notification_data['task'] = asyncio.create_task(
                    self._notification_loop(chat_id, notification_data)
                )
                
                logger.info(f"Restored notification for chat {chat_id}: {notification_data['message']}")
            
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
        
    async def start_notification(self, chat_id: int, message: str, interval_minutes: int, start_time: str, 
                                tagged_users: Optional[List[int]] = None, message_thread_id: Optional[int] = None):
        """Запускает уведомления для чата (личного или группового)"""
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
                'task': None,
                'chat_id': chat_id,
                'message_thread_id': message_thread_id,  # ID топика
                'tagged_users': tagged_users or [],
                'responded_users': set()  # Пользователи, которые ответили
            }
            
            # Останавливаем предыдущие уведомления если есть
            if chat_id in self.active_notifications:
                await self.stop_notification(chat_id)
            
            self.active_notifications[chat_id] = notification_data
            notification_data['task'] = asyncio.create_task(
                self._notification_loop(chat_id, notification_data)
            )
            
            # Сохраняем в хранилище
            self._save_notifications()
            
            logger.info(f"Started notifications for chat {chat_id} (topic: {message_thread_id}): {message} every {interval_minutes} minutes starting at {start_time}")
            
        except Exception as e:
            logger.error(f"Error starting notification for chat {chat_id}: {e}")
            raise
    
    async def stop_notification(self, chat_id: int):
        """Останавливает уведомления для чата"""
        if chat_id in self.active_notifications:
            notification_data = self.active_notifications[chat_id]
            if notification_data['task']:
                notification_data['task'].cancel()
                try:
                    await notification_data['task']
                except asyncio.CancelledError:
                    pass
            
            del self.active_notifications[chat_id]
            
            # Сохраняем изменения в хранилище
            self._save_notifications()
            
            logger.info(f"Stopped notifications for chat {chat_id}")
    
    def pause_notifications(self, chat_id: int, user_id: Optional[int] = None):
        """Приостанавливает уведомления до следующего времени начала"""
        if chat_id in self.active_notifications:
            notification_data = self.active_notifications[chat_id]
            notification_data['active'] = False
            notification_data['last_response_time'] = datetime.now(self.moscow_tz)
            
            # Если указан пользователь и есть тегированные пользователи, добавляем его в список ответивших
            if user_id and notification_data.get('tagged_users'):
                notification_data['responded_users'].add(user_id)
                # Сбрасываем список ответивших если все тегированные пользователи ответили
                if notification_data['responded_users'] == set(notification_data['tagged_users']):
                    notification_data['responded_users'].clear()
            
            # Сохраняем изменения в хранилище
            self._save_notifications()
            
            logger.info(f"Paused notifications for chat {chat_id} until next start time")
    
    def handle_user_response(self, chat_id: int, user_id: int, username: str = None):
        """Обрабатывает ответ пользователя в групповом чате"""
        if chat_id in self.active_notifications:
            notification_data = self.active_notifications[chat_id]
            tagged_users = notification_data.get('tagged_users', [])
            responded_users = notification_data['responded_users']
            changed = False

            # Добавляем user_id, если он есть в tagged_users
            if user_id in tagged_users:
                responded_users.add(user_id)
                changed = True
            # Добавляем username, если он есть в tagged_users
            if username:
                username_clean = username.lstrip('@')
                if username_clean in tagged_users:
                    responded_users.add(username_clean)
                    changed = True

            if changed:
                # Если все тегированные пользователи ответили, приостанавливаем уведомления
                if set(tagged_users) == responded_users:
                    notification_data['active'] = False
                    notification_data['last_response_time'] = datetime.now(self.moscow_tz)
                    notification_data['responded_users'].clear()
                    logger.info(f"All tagged users responded in chat {chat_id}, pausing notifications until next start time")
                else:
                    logger.info(f"User {user_id} ({username}) responded in chat {chat_id}, {len(responded_users)}/{len(tagged_users)} users responded")
                self._save_notifications()
    
    async def _notification_loop(self, chat_id: int, notification_data: Dict):
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
                        
                        # Сбрасываем список ответивших пользователей при возобновлении
                        if notification_data.get('tagged_users'):
                            notification_data['responded_users'].clear()
                        
                        # Сохраняем изменения в хранилище
                        self._save_notifications()
                        
                        logger.info(f"Resumed notifications for chat {chat_id} at {next_start.strftime('%H:%M')}")
                
                if notification_data['active']:
                    # Проверяем, находимся ли мы в активном временном окне
                    if self._is_in_active_window(now, notification_data):
                        # Проверяем, нужно ли отправить уведомление
                        if self._should_send_notification(now, notification_data):
                            await self._send_notification(chat_id, notification_data)
                            notification_data['last_sent'] = now
                            
                            # Сохраняем время последней отправки
                            self._save_notifications()
                
                # Ждем 1 минуту перед следующей проверкой
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                logger.info(f"Notification loop cancelled for chat {chat_id}")
                break
            except Exception as e:
                logger.error(f"Error in notification loop for chat {chat_id}: {e}")
                await asyncio.sleep(60)
    
    def _get_next_start_time(self, notification_data: Dict) -> datetime:
        """Вычисляет время следующего запуска уведомлений"""
        # Используем время последнего ответа как базовое время
        if notification_data['last_response_time']:
            base_time = notification_data['last_response_time']
        else:
            base_time = datetime.now(self.moscow_tz)
        
        next_start = base_time.replace(
            hour=notification_data['start_hour'],
            minute=notification_data['start_minute'],
            second=0,
            microsecond=0
        )
        
        # Если время начала уже прошло в день последнего ответа, переносим на следующий день
        if next_start <= base_time:
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
    
    async def _send_notification(self, chat_id: int, notification_data: Dict):
        """Отправляет уведомление в чат"""
        try:
            message = notification_data['message']
            tagged_users = notification_data.get('tagged_users', [])
            responded_users = notification_data.get('responded_users', set())
            message_thread_id = notification_data.get('message_thread_id')
            
            # Если есть тегированные пользователи, добавляем теги только тех, кто ещё не ответил
            if tagged_users:
                user_tags = []
                for user in tagged_users:
                    # Пропускаем тех, кто уже ответил
                    if user in responded_users:
                        continue
                        
                    if isinstance(user, int):
                        # Это user_id (число)
                        try:
                            member = await self.bot.get_chat_member(chat_id, user)
                            if member.user.username:
                                user_tags.append(f"@{member.user.username}")
                            else:
                                user_tags.append(f'<a href="tg://user?id={user}">{member.user.first_name}</a>')
                        except TelegramError as e:
                            logger.warning(f"Could not get user info for {user}: {e}")
                            user_tags.append(f'<a href="tg://user?id={user}">Пользователь</a>')
                    elif isinstance(user, str):
                        # Это username (строка)
                        username = user.lstrip('@')  # Убираем @ если есть
                        user_tags.append(f"@{username}")
                    else:
                        logger.warning(f"Unknown user type: {type(user)} for user {user}")
                
                if user_tags:
                    message += f"\n\n{' '.join(user_tags)}"
            
            # Отправляем сообщение с учетом топика
            send_params = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            if message_thread_id is not None:
                send_params['message_thread_id'] = message_thread_id
            
            await self.bot.send_message(**send_params)
            logger.info(f"Sent notification to chat {chat_id} (topic: {message_thread_id}): {notification_data['message']}")
            
        except TelegramError as e:
            logger.error(f"Failed to send notification to chat {chat_id}: {e}")
            # Если HTML не сработал, пробуем без разметки
            try:
                send_params = {
                    'chat_id': chat_id,
                    'text': message
                }
                
                if message_thread_id is not None:
                    send_params['message_thread_id'] = message_thread_id
                
                await self.bot.send_message(**send_params)
                logger.info(f"Sent notification without markup to chat {chat_id}")
            except TelegramError as e2:
                logger.error(f"Failed to send notification without markup to chat {chat_id}: {e2}")
    
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
            for chat_id, notification_data in self.active_notifications.items():
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