from .interfaces.notification_channel_interface import INotificationChannel
from .properties.properties import TelegramNotificationProperties, NotificationChannelBaseProperties
from .channels.telegram_notification_channel import TelegramNotificationChannel

class NotificationService:
    
    def __init__(self, properties: NotificationChannelBaseProperties) -> None:
        """
        Initializes a new instance of the Notification class.

        Args:
            properties (NotificationChannelBaseProperties): The properties of the notification channel.

        Returns:
            None
        """
        self._channel = self._get_channel(properties)
        
    def _get_channel(self, properties: NotificationChannelBaseProperties) -> INotificationChannel:
        """
        Returns an instance of the appropriate notification channel based on the provided properties.

        Args:
            properties (NotificationChannelBaseProperties): The properties of the notification channel.

        Returns:
            INotificationChannel: An instance of the notification channel.

        Raises:
            Exception: If the selected communication channel does not exist.
        """
        if isinstance(properties, TelegramNotificationProperties):
            return TelegramNotificationChannel(properties)
        else:
            raise Exception("ERROR: El canal de comunicación seleccionado no existe")
    
    def send_notification(self, title: str, message: str):
        """
        Sends a notification with the specified title and message.

        Args:
            title (str): The title of the notification.
            message (str): The message of the notification.
        """
        self._channel.send_message(title, message)
