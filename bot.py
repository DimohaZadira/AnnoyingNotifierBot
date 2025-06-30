import logging
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN
from notification_manager import NotificationManager

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class AnnoyingBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.notification_manager = NotificationManager(self.application.bot)
        
        # Регистрируем обработчики
        self.application.add_handler(CommandHandler("begin_notif", self.begin_notif_command))
        self.application.add_handler(CommandHandler("stop_notif", self.stop_notif_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("storage", self.storage_command))
        self.application.add_handler(CommandHandler("clear_all", self.clear_all_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def begin_notif_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /begin_notif"""
        try:
            # Проверяем количество аргументов
            if len(context.args) < 3:
                await update.message.reply_text(
                    "❌ Неправильный формат команды!\n\n"
                    "Использование: /begin_notif <сообщение> <интервал_в_минутах> <время_начала> [@username1 @username2 ...]\n\n"
                    "Пример: /begin_notif \"Пора пить воду!\" 30 09:00\n"
                    "Пример с тегами: /begin_notif \"Пора пить воду!\" 30 09:00 @user1 @user2\n"
                    "Пример без кавычек: /begin_notif sosal 10 10:00 @user1 @user2\n\n"
                    "Время указывается в формате HH:MM по Москве\n"
                    "Теги пользователей опциональны и работают только в группах"
                )
                return
            
            # Ищем интервал и время среди аргументов
            interval_minutes = None
            start_time = None
            interval_index = -1
            time_index = -1
            
            for i, arg in enumerate(context.args):
                # Проверяем, является ли аргумент интервалом (число)
                if interval_minutes is None:
                    try:
                        potential_interval = int(arg)
                        if potential_interval > 0:
                            interval_minutes = potential_interval
                            interval_index = i
                            continue
                    except ValueError:
                        pass
                
                # Проверяем, является ли аргумент временем (формат HH:MM)
                if start_time is None and re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', arg):
                    start_time = arg
                    time_index = i
            
            # Проверяем, что нашли интервал и время
            if interval_minutes is None:
                await update.message.reply_text("❌ Не найден интервал! Укажите положительное число для интервала в минутах.")
                return
            
            if start_time is None:
                await update.message.reply_text("❌ Не найдено время! Укажите время в формате HH:MM (например, 09:00)")
                return
            
            # Проверяем порядок: интервал должен быть перед временем
            if interval_index > time_index:
                await update.message.reply_text("❌ Неправильный порядок аргументов! Интервал должен быть перед временем.")
                return
            
            # Собираем сообщение и теги
            message_parts = []
            tagged_users = []
            
            for i, arg in enumerate(context.args):
                if i == interval_index or i == time_index:
                    continue  # Пропускаем интервал и время
                
                if arg.startswith('@'):
                    # Это тег пользователя
                    username = arg[1:]  # Убираем @
                    try:
                        # Пытаемся найти пользователя по username
                        user = await context.bot.get_chat_member(update.effective_chat.id, f"@{username}")
                        tagged_users.append(user.user.id)
                    except Exception as e:
                        logger.warning(f"Could not find user with username @{username}: {e}")
                        # Сохраняем username без @ для последующего тегания
                        tagged_users.append(username)
                else:
                    # Это часть сообщения
                    message_parts.append(arg)
            
            # Собираем сообщение
            message = " ".join(message_parts)
            
            # Проверяем, что сообщение не пустое
            if not message.strip():
                await update.message.reply_text("❌ Сообщение не может быть пустым!")
                return
            
            # Запускаем уведомления
            chat_id = update.effective_chat.id
            message_thread_id = update.message.message_thread_id if update.message.message_thread_id else None
            
            await self.notification_manager.start_notification(
                chat_id, message, interval_minutes, start_time, tagged_users, message_thread_id
            )
            
            # Формируем ответное сообщение
            response_text = (
                f"✅ Уведомления запущены!\n\n"
                f"📝 Сообщение: {message}\n"
                f"⏰ Интервал: каждые {interval_minutes} минут\n"
                f"🕐 Время начала: {start_time} (МСК)\n"
                f"🕑 Время окончания: 02:00 следующего дня (МСК)\n\n"
            )
            
            if tagged_users:
                response_text += f"👥 Тегированные пользователи: {len(tagged_users)}\n"
                response_text += "💡 Когда все тегированные пользователи ответят, теги прекратятся до следующего времени начала\n\n"
            else:
                response_text += "💡 Отправьте любое сообщение, чтобы приостановить уведомления до следующего времени начала\n\n"
            
            response_text += "💾 Уведомления будут сохранены и восстановлены при перезагрузке бота"
            
            await update.message.reply_text(response_text)
            
        except Exception as e:
            logger.error(f"Error in begin_notif command: {e}")
            await update.message.reply_text("❌ Произошла ошибка при запуске уведомлений")
    
    async def stop_notif_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stop_notif"""
        try:
            chat_id = update.effective_chat.id
            await self.notification_manager.stop_notification(chat_id)
            
            await update.message.reply_text("✅ Уведомления остановлены!")
            
        except Exception as e:
            logger.error(f"Error in stop_notif command: {e}")
            await update.message.reply_text("❌ Произошла ошибка при остановке уведомлений")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        try:
            chat_id = update.effective_chat.id
            active_notifications = self.notification_manager.get_active_notifications()
            
            if chat_id in active_notifications:
                notification = active_notifications[chat_id]
                status = "🟢 Активны" if notification['active'] else "🟡 Приостановлены"
                
                status_text = (
                    f"📊 Статус уведомлений: {status}\n\n"
                    f"📝 Сообщение: {notification['message']}\n"
                    f"⏰ Интервал: каждые {notification['interval_minutes']} минут\n"
                    f"🕐 Время начала: {notification['start_hour']:02d}:{notification['start_minute']:02d} (МСК)\n"
                    f"🕑 Время окончания: 02:00 следующего дня (МСК)"
                )
                
                # Добавляем информацию о топике
                if notification.get('message_thread_id'):
                    status_text += f"\n📌 Топик: {notification['message_thread_id']}"
                else:
                    status_text += f"\n📌 Топик: основной чат"
                
                if notification.get('tagged_users'):
                    responded_count = len(notification.get('responded_users', set()))
                    total_count = len(notification['tagged_users'])
                    status_text += f"\n👥 Тегированные пользователи: {responded_count}/{total_count} ответили"
                
                await update.message.reply_text(status_text)
            else:
                await update.message.reply_text("📊 В этом чате нет активных уведомлений")
                
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await update.message.reply_text("❌ Произошла ошибка при получении статуса")
    
    async def storage_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /storage - показывает информацию о хранилище"""
        try:
            storage_info = self.notification_manager.get_storage_info()
            active_notifications = self.notification_manager.get_active_notifications()
            
            if storage_info['exists']:
                await update.message.reply_text(
                    f"💾 Информация о хранилище:\n\n"
                    f"📁 Файл: {storage_info['file_path']}\n"
                    f"📊 Размер: {storage_info['size']} байт\n"
                    f"🔢 Сохранено уведомлений: {storage_info['notifications_count']}\n"
                    f"🟢 Активных уведомлений: {len(active_notifications)}\n\n"
                    f"✅ Хранилище работает корректно"
                )
            else:
                await update.message.reply_text(
                    f"💾 Информация о хранилище:\n\n"
                    f"📁 Файл: не найден\n"
                    f"🟢 Активных уведомлений: {len(active_notifications)}\n\n"
                    f"ℹ️ Хранилище будет создано при первом уведомлении"
                )
                
        except Exception as e:
            logger.error(f"Error in storage command: {e}")
            await update.message.reply_text("❌ Произошла ошибка при получении информации о хранилище")
    
    async def clear_all_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /clear_all - очищает все уведомления"""
        try:
            await self.notification_manager.clear_all_notifications()
            
            await update.message.reply_text(
                "🗑️ Все уведомления очищены!\n\n"
                "✅ Все активные уведомления остановлены\n"
                "💾 Файл хранилища удален"
            )
            
        except Exception as e:
            logger.error(f"Error in clear_all command: {e}")
            await update.message.reply_text("❌ Произошла ошибка при очистке уведомлений")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
🤖 *Annoying Bot - Помощь*

*Доступные команды:*

/begin\\_notif <сообщение> <интервал> <время\\_начала> [@username1 @username2 ...]
Запускает уведомления с указанными параметрами

Пример: `/begin_notif "Пора пить воду!" 30 09:00`
Пример с тегами: `/begin_notif "Пора пить воду!" 30 09:00 @user1 @user2`
Пример без кавычек: `/begin_notif sosal 10 10:00 @user1 @user2`

/stop\\_notif
Полностью останавливает уведомления

/status
Показывает статус текущих уведомлений

/storage
Показывает информацию о хранилище

/clear\\_all
Очищает все уведомления (только для администратора)

/help
Показывает эту справку

*Как это работает:*
• Бот отправляет сообщение каждые N минут
• Работает с указанного времени до 02:00 следующего дня
• В личных чатах: если вы отвечаете на любое сообщение, уведомления приостанавливаются до следующего времени начала
• В группах: если указаны тегированные пользователи, бот тегает их в сообщениях
• Когда все тегированные пользователи ответят, теги прекращаются до следующего времени начала
• **Все уведомления отправляются в тот же топик, откуда была вызвана команда**
• Время указывается по Москве (МСК)
• **Уведомления сохраняются и восстанавливаются при перезагрузке бота**

*Параметры:*
• <сообщение> - текст для отправки
• <интервал> - интервал в минутах (положительное число)
• <время\\_начала> - время в формате HH:MM (например, 09:00)
• [@username1 @username2 ...] - опциональные теги пользователей (только для групп)

*Особенности:*
• 💾 Все уведомления автоматически сохраняются в файл
• 🔄 При перезагрузке бота уведомления восстанавливаются
• ⏸️ Приостановленные уведомления возобновляются в указанное время
• 👥 В группах можно тегать пользователей для отслеживания их ответов
• 📌 Поддержка топиков: уведомления отправляются в тот же топик, где была вызвана команда
        """
        
        await update.message.reply_text(help_text)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик всех текстовых сообщений"""
        try:
            chat_id = update.effective_chat.id
            user_id = update.effective_user.id
            username = update.effective_user.username
            
            # Проверяем, есть ли активные уведомления в этом чате
            active_notifications = self.notification_manager.get_active_notifications()
            if chat_id in active_notifications:
                notification = active_notifications[chat_id]
                
                # Если это групповой чат и есть тегированные пользователи
                if update.effective_chat.type in ['group', 'supergroup'] and notification.get('tagged_users'):
                    # Обрабатываем ответ пользователя (передаем username)
                    self.notification_manager.handle_user_response(chat_id, user_id, username)
                    
                    # Проверяем, ответили ли все тегированные пользователи
                    responded_users = notification.get('responded_users', set())
                    tagged_users = set(notification['tagged_users'])
                    
                    if responded_users == tagged_users:
                        await update.message.reply_text(
                            "✅ Все тегированные пользователи ответили!\n\n"
                            "⏸️ Уведомления приостановлены до следующего времени начала\n"
                            "💾 Состояние сохранено в хранилище"
                        )
                    else:
                        remaining = sum(1 for u in tagged_users if u not in responded_users)
                        await update.message.reply_text(
                            f"👥 Ответ засчитан! Осталось ответить: {remaining} пользователей"
                        )
                else:
                    # Для личных чатов или групп без тегов - приостанавливаем уведомления
                    self.notification_manager.pause_notifications(chat_id, user_id)
                    
                    await update.message.reply_text(
                        "⏸️ Уведомления приостановлены до следующего времени начала!\n\n"
                        "💡 Уведомления возобновятся автоматически в указанное время начала\n"
                        "💾 Состояние сохранено в хранилище"
                    )
            else:
                await update.message.reply_text(
                    "👋 Привет! Я Annoying Bot.\n\n"
                    "💡 Используйте /help для получения справки по командам\n"
                    "💾 Все уведомления сохраняются и восстанавливаются при перезагрузке"
                )
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def run(self):
        """Запускает бота"""
        logger.info("Starting Annoying Bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    bot = AnnoyingBot()
    bot.run() 