"""
Autenticazione WebSocket via Token DRF (query string `?token=`).

L'app React usa TokenAuthentication su HTTP, non session cookie: senza questo
middleware `scope["user"]` resta Anonymous e non si possono usare room per-utente.
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def _user_from_token(raw_token):
    if not raw_token:
        return AnonymousUser()
    from rest_framework.authtoken.models import Token

    try:
        return Token.objects.select_related("user").get(key=raw_token).user
    except Token.DoesNotExist:
        return AnonymousUser()


class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query = parse_qs((scope.get("query_string") or b"").decode())
        raw = (query.get("token") or [None])[0]
        scope["user"] = await _user_from_token(raw)
        return await super().__call__(scope, receive, send)


def TokenAuthMiddlewareStack(inner):
    """Stack: Token query → AuthMiddleware (session fallback) → app."""
    from channels.auth import AuthMiddlewareStack

    return TokenAuthMiddleware(AuthMiddlewareStack(inner))


def user_notifications_group(user_id: int) -> str:
    return f"kor35_user_{int(user_id)}"
