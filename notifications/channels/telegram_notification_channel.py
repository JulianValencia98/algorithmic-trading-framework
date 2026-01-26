from ..interfaces.notification_channel_interface import INotificationChannel
from ..properties.properties import TelegramNotificationProperties
import telegram
import asyncio

class TelegramNotificationChannel(INotificationChannel):
    
    def __init__(self, properties: TelegramNotificationProperties) -> None:
        """
        Initializes a new instance of the TelegramNotificationChannel class.

        Args:
            properties (TelegramNotificationProperties): The properties for the Telegram notification channel.

        """
        self._chat_id = properties.chat_id
        self._token = properties.token
        self._bot = telegram.Bot(self._token)
    
    async def async_send_message(self, title: str, message: str):
        """
        Sends a message to the Telegram chat.

        Args:
            title (str): The title of the message.
            message (str): The content of the message.
        """
        async with self._bot:
            await self._bot.send_message(text=f'{title}\n{message}', chat_id=self._chat_id)
    
    def send_message(self, title: str, message: str):
        """
        Sends a message to the Telegram channel.

        Args:
            title (str): The title of the message.
            message (str): The content of the message.
        """
        asyncio.run(self.async_send_message(title, message))
