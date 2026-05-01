"""
Authentication helper per la console pilota.

Il frontend pilot autentica le richieste via header:
    Authorization: PilotToken <token>

Il token e' un oggetto `PilotConsoleToken` rilasciato dopo un login QR
(scansione del QR personale del pilota con statistica 0PI >= 1).
"""
from __future__ import annotations

from typing import Optional, Tuple

from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from rest_framework import authentication, exceptions

from .models import PilotConsoleToken


class PilotConsoleTokenAuthentication(authentication.BaseAuthentication):
    """
    Autenticazione custom: legge "Authorization: PilotToken <token>".

    Restituisce `(AnonymousUser, token_obj)`: l'utente Django non viene usato
    (il pilota e' nel token), ma occorre comunque un oggetto utente non None
    per non rompere middleware downstream (es. cms.toolbar).
    Le viste pilota leggono il pilota da `request.auth.pilota`.
    """

    keyword = "PilotToken"

    def authenticate(self, request) -> Optional[Tuple[AnonymousUser, PilotConsoleToken]]:
        auth_header = (request.META.get("HTTP_AUTHORIZATION", "") or "").strip()
        if not auth_header.startswith(f"{self.keyword} "):
            return None
        provided = auth_header.replace(f"{self.keyword} ", "", 1).strip()
        if not provided:
            return None
        token_obj = PilotConsoleToken.objects.select_related("pilota").filter(
            token=provided, revocato_at__isnull=True
        ).first()
        if not token_obj:
            raise exceptions.AuthenticationFailed("Token console pilota non valido o revocato.")
        PilotConsoleToken.objects.filter(pk=token_obj.pk).update(
            last_seen_at=timezone.now()
        )
        return (AnonymousUser(), token_obj)

    def authenticate_header(self, request) -> str:
        return self.keyword


def get_pilot_from_request(request) -> Optional["personaggi.Personaggio"]:  # noqa: F821
    """Helper: restituisce il `Personaggio` collegato al token, o None."""
    token = getattr(request, "auth", None)
    if isinstance(token, PilotConsoleToken):
        return token.pilota
    return None
