"""
Broadcast aggiornamenti duello carte via Channels.
"""
from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_duello_update(duello_id, payload: dict):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(
        f"duello_{duello_id}",
        {
            "type": "duello_update",
            "payload": payload,
        },
    )
