import json
import os
import logging
from datetime import datetime
from typing import Dict, Any
import pytz

logger = logging.getLogger(__name__)

class NotificationStorage:
    def __init__(self, storage_file: str = "notifications.json"):
        self.storage_file = storage_file
        self.moscow_tz = pytz.timezone('Europe/Moscow')
    
    def save_notifications(self, notifications: Dict[int, Dict[str, Any]]) -> bool:
        """Сохраняет уведомления в JSON файл"""
        try:
            # Подготавливаем данные для сохранения
            serializable_notifications = {}
            
            for user_id, notification_data in notifications.items():
                # Создаем копию данных без асинхронных задач
                serializable_data = {
                    'message': notification_data['message'],
                    'interval_minutes': notification_data['interval_minutes'],
                    'start_hour': notification_data['start_hour'],
                    'start_minute': notification_data['start_minute'],
                    'active': notification_data['active']
                }
                
                # Сохраняем время последнего ответа если есть
                if notification_data.get('last_response_time'):
                    serializable_data['last_response_time'] = notification_data['last_response_time'].isoformat()
                
                # Сохраняем время последней отправки если есть
                if notification_data.get('last_sent'):
                    serializable_data['last_sent'] = notification_data['last_sent'].isoformat()
                
                serializable_notifications[str(user_id)] = serializable_data
            
            # Сохраняем в файл
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_notifications, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(serializable_notifications)} notifications to {self.storage_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving notifications: {e}")
            return False
    
    def load_notifications(self) -> Dict[int, Dict[str, Any]]:
        """Загружает уведомления из JSON файла"""
        try:
            if not os.path.exists(self.storage_file):
                logger.info(f"Storage file {self.storage_file} not found, starting with empty notifications")
                return {}
            
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Восстанавливаем данные
            notifications = {}
            
            for user_id_str, notification_data in data.items():
                user_id = int(user_id_str)
                
                # Восстанавливаем datetime объекты
                restored_data = {
                    'message': notification_data['message'],
                    'interval_minutes': notification_data['interval_minutes'],
                    'start_hour': notification_data['start_hour'],
                    'start_minute': notification_data['start_minute'],
                    'active': notification_data['active'],
                    'task': None  # Задача будет создана заново
                }
                
                # Восстанавливаем время последнего ответа
                if notification_data.get('last_response_time'):
                    try:
                        restored_data['last_response_time'] = datetime.fromisoformat(
                            notification_data['last_response_time']
                        ).replace(tzinfo=self.moscow_tz)
                    except Exception as e:
                        logger.warning(f"Error parsing last_response_time for user {user_id}: {e}")
                        restored_data['last_response_time'] = None
                
                # Восстанавливаем время последней отправки
                if notification_data.get('last_sent'):
                    try:
                        restored_data['last_sent'] = datetime.fromisoformat(
                            notification_data['last_sent']
                        ).replace(tzinfo=self.moscow_tz)
                    except Exception as e:
                        logger.warning(f"Error parsing last_sent for user {user_id}: {e}")
                        restored_data['last_sent'] = None
                
                notifications[user_id] = restored_data
            
            logger.info(f"Loaded {len(notifications)} notifications from {self.storage_file}")
            return notifications
            
        except Exception as e:
            logger.error(f"Error loading notifications: {e}")
            return {}
    
    def delete_storage(self) -> bool:
        """Удаляет файл хранилища"""
        try:
            if os.path.exists(self.storage_file):
                os.remove(self.storage_file)
                logger.info(f"Deleted storage file {self.storage_file}")
            return True
        except Exception as e:
            logger.error(f"Error deleting storage file: {e}")
            return False
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Возвращает информацию о хранилище"""
        try:
            if not os.path.exists(self.storage_file):
                return {
                    'exists': False,
                    'size': 0,
                    'notifications_count': 0
                }
            
            size = os.path.getsize(self.storage_file)
            notifications = self.load_notifications()
            
            return {
                'exists': True,
                'size': size,
                'notifications_count': len(notifications),
                'file_path': os.path.abspath(self.storage_file)
            }
        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            return {
                'exists': False,
                'size': 0,
                'notifications_count': 0,
                'error': str(e)
            } 