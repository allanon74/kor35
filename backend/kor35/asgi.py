# kor35/asgi.py
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kor35.settings')

from django.core.asgi import get_asgi_application

# Inizializza Django prima di importare routing/consumers (evita AppRegistryNotReady).
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import personaggi.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            personaggi.routing.websocket_urlpatterns
        )
    ),
})
