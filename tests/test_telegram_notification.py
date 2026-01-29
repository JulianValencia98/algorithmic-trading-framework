import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Añadir la raíz del proyecto al sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Cargar variables de entorno desde .env
dotenv_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path)

from notifications.channels.telegram_notification_channel import TelegramNotificationChannel
from notifications.properties.properties import TelegramNotificationProperties

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def test_telegram_notification():
    properties = TelegramNotificationProperties(chat_id=TELEGRAM_CHAT_ID, token=TELEGRAM_BOT_TOKEN)
    channel = TelegramNotificationChannel(properties)
    channel.send_message('Test de Telegram', 'Este es un mensaje de prueba desde el framework.')
    print('Mensaje de prueba enviado a Telegram.')

if __name__ == '__main__':
    test_telegram_notification()
