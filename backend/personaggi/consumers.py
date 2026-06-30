# personaggi/consumers.py
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from personaggi.carte_collezionabili_models import DuelloCarte


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


class DuelloCarteConsumer(AsyncWebsocketConsumer):
    """WebSocket live per sincronizzare lo stato di un duello carte."""

    @database_sync_to_async
    def _user_can_watch(self, user, duello_id):
        if not user or not user.is_authenticated:
            return False
        duello = DuelloCarte.objects.filter(pk=duello_id).select_related("sfidante", "sfidato").first()
        if not duello:
            return False
        owner_ids = {duello.sfidante.proprietario_id}
        if duello.sfidato_id:
            owner_ids.add(duello.sfidato.proprietario_id)
        return user.id in owner_ids

    async def connect(self):
        self.duello_id = self.scope["url_route"]["kwargs"]["duello_id"]
        user = self.scope.get("user")
        if not await self._user_can_watch(user, self.duello_id):
            await self.close()
            return

        self.room_group_name = f"duello_{self.duello_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({
            "type": "duello_connected",
            "duello_id": str(self.duello_id),
        }))

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def duello_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "duello_update",
            "payload": event.get("payload") or {},
        }))