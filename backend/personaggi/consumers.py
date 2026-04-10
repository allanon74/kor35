# personaggi/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'kor35_notifications'

        # Unisciti al gruppo
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Lascia il gruppo
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Ricevi messaggio dal gruppo (inviato dal signal)
    async def send_notification(self, event):
        message = event['message']

        # Invia messaggio al WebSocket (al frontend React)
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'payload': message
        }))