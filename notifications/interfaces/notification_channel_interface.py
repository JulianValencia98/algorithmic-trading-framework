
from typing import Protocol

class INotificationChannel(Protocol):
    
    def send_message(self, title: str, message: str):
        ...