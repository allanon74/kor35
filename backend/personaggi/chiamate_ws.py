"""Segnalazione WebRTC (SDP / ICE / hangup) per chiamate vocali."""
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from personaggi.chiamate_vocali import (
    altro_user_id,
    chiudi_chiamata,
    utente_puo_partecipare,
    voce_user_group,
)
from personaggi.models import ChiamataVocale


class ChiamataVocaleConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return
        self.user_id = user.id
        self.user_group = voce_user_group(user.id)
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({"type": "voce_connected"}))

    async def disconnect(self, close_code):
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
        msg_type = (data.get("type") or "").strip().lower()
        call_id = data.get("call_id")
        if not call_id or msg_type not in ("sdp", "ice", "hangup"):
            return
        user = self.scope.get("user")
        call = await self._get_call(call_id)
        if not call:
            return
        if not await self._can_join(call, user):
            return
        if msg_type == "hangup":
            await self._hangup(call, user)
            return
        target = await self._other(call, user)
        if not target:
            return
        payload = {
            "type": msg_type,
            "call_id": str(call.id),
        }
        if msg_type == "sdp":
            payload["sdp"] = data.get("sdp")
        else:
            payload["candidate"] = data.get("candidate")
        await self.channel_layer.group_send(
            voce_user_group(target),
            {"type": "voce_signal", "message": payload},
        )

    async def voce_signal(self, event):
        message = event.get("message") or {}
        await self.send(text_data=json.dumps(message))

    @database_sync_to_async
    def _get_call(self, call_id):
        return (
            ChiamataVocale.objects.select_related(
                "chiamante", "chiamato", "campagna", "accettata_da"
            )
            .filter(pk=call_id)
            .first()
        )

    @database_sync_to_async
    def _can_join(self, call, user):
        return utente_puo_partecipare(call, user)

    @database_sync_to_async
    def _other(self, call, user):
        return altro_user_id(call, user)

    @database_sync_to_async
    def _hangup(self, call, user):
        try:
            chiudi_chiamata(call, user)
        except ValueError:
            return
