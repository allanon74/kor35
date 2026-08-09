# kor35/asgi.py
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kor35.settings')

from django.core.asgi import get_asgi_application

# Inizializza Django prima di importare routing/consumers (evita AppRegistryNotReady).
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
import personaggi.routing
from personaggi.ws_auth import TokenAuthMiddlewareStack

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": TokenAuthMiddlewareStack(
        URLRouter(
            personaggi.routing.websocket_urlpatterns
        )
    ),
})
