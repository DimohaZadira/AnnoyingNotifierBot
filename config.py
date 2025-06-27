import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Moscow timezone
MOSCOW_TZ = 'Europe/Moscow'

# Default notification end time (02:00 next day)
DEFAULT_END_HOUR = 2 