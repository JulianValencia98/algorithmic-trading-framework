from pydantic import BaseModel

class NotificationChannelBaseProperties(BaseModel):
    pass

class TelegramNotificationProperties(NotificationChannelBaseProperties):
    """
    Represents the properties required for sending notifications via Telegram.

    Attributes:
        chat_id (str): The ID of the chat where the notification will be sent.
        token (str): The authentication token for accessing the Telegram Bot API.
    """
    chat_id: str
    token: str
