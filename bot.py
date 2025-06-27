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
                    "Использование: /begin_notif <сообщение> <интервал_в_минутах> <время_начала>\n\n"
                    "Пример: /begin_notif \"Пора пить воду!\" 30 09:00\n\n"
                    "Время указывается в формате HH:MM по Москве"
                )
                return
            
            # Извлекаем аргументы
            interval_str = context.args[-2]
            start_time = context.args[-1]
            message = " ".join(context.args[:-2])
            
            # Проверяем интервал
            try:
                interval_minutes = int(interval_str)
                if interval_minutes <= 0:
                    raise ValueError("Интервал должен быть положительным числом")
            except ValueError:
                await update.message.reply_text("❌ Интервал должен быть положительным числом!")
                return
            
            # Проверяем формат времени
            if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', start_time):
                await update.message.reply_text("❌ Неправильный формат времени! Используйте HH:MM (например, 09:00)")
                return
            
            # Запускаем уведомления
            user_id = update.effective_user.id
            await self.notification_manager.start_notification(
                user_id, message, interval_minutes, start_time
            )
            
            await update.message.reply_text(
                f"✅ Уведомления запущены!\n\n"
                f"📝 Сообщение: {message}\n"
                f"⏰ Интервал: каждые {interval_minutes} минут\n"
                f"🕐 Время начала: {start_time} (МСК)\n"
                f"🕑 Время окончания: 02:00 следующего дня (МСК)\n\n"
                f"💡 Отправьте любое сообщение, чтобы приостановить уведомления до следующего дня\n"
                f"💾 Уведомления будут сохранены и восстановлены при перезагрузке бота"
            )
            
        except Exception as e:
            logger.error(f"Error in begin_notif command: {e}")
            await update.message.reply_text("❌ Произошла ошибка при запуске уведомлений")
    
    async def stop_notif_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stop_notif"""
        try:
            user_id = update.effective_user.id
            await self.notification_manager.stop_notification(user_id)
            
            await update.message.reply_text("✅ Уведомления остановлены!")
            
        except Exception as e:
            logger.error(f"Error in stop_notif command: {e}")
            await update.message.reply_text("❌ Произошла ошибка при остановке уведомлений")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        try:
            user_id = update.effective_user.id
            active_notifications = self.notification_manager.get_active_notifications()
            
            if user_id in active_notifications:
                notification = active_notifications[user_id]
                status = "🟢 Активны" if notification['active'] else "🟡 Приостановлены"
                
                await update.message.reply_text(
                    f"📊 Статус уведомлений: {status}\n\n"
                    f"📝 Сообщение: {notification['message']}\n"
                    f"⏰ Интервал: каждые {notification['interval_minutes']} минут\n"
                    f"🕐 Время начала: {notification['start_hour']:02d}:{notification['start_minute']:02d} (МСК)\n"
                    f"🕑 Время окончания: 02:00 следующего дня (МСК)"
                )
            else:
                await update.message.reply_text("📊 У вас нет активных уведомлений")
                
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

/begin\\_notif <сообщение> <интервал> <время\\_начала>
Запускает уведомления с указанными параметрами

Пример: `/begin_notif "Пора пить воду!" 30 09:00`

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
• Если вы отвечаете на любое сообщение, уведомления приостанавливаются до следующего дня
• Время указывается по Москве (МСК)
• **Уведомления сохраняются и восстанавливаются при перезагрузке бота**

*Параметры:*
• <сообщение> - текст для отправки
• <интервал> - интервал в минутах (положительное число)
• <время\\_начала> - время в формате HH:MM (например, 09:00)

*Особенности:*
• 💾 Все уведомления автоматически сохраняются в файл
• 🔄 При перезагрузке бота уведомления восстанавливаются
• ⏸️ Приостановленные уведомления возобновляются в указанное время
        """
        
        await update.message.reply_text(help_text, parse_mode='MarkdownV2')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик всех текстовых сообщений"""
        try:
            user_id = update.effective_user.id
            
            # Проверяем, есть ли активные уведомления у пользователя
            active_notifications = self.notification_manager.get_active_notifications()
            if user_id in active_notifications:
                # Приостанавливаем уведомления до следующего дня
                self.notification_manager.pause_notifications(user_id)
                
                await update.message.reply_text(
                    "⏸️ Уведомления приостановлены до следующего дня!\n\n"
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