# personaggi/routing.py
from django.urls import re_path
from . import consumers
from personaggi.chiamate_ws import ChiamataVocaleConsumer

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/duello/(?P<duello_id>[0-9a-f-]+)/$', consumers.DuelloCarteConsumer.as_asgi()),
    re_path(r'ws/chiamate/$', ChiamataVocaleConsumer.as_asgi()),
]