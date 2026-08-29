"""API preferenze notifiche + token feed iCal per tutti i giocatori."""
from __future__ import annotations

import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from personaggi.models import (
    NOTIFICA_CANALI,
    NOTIFICA_CATEGORIA_LABELS,
    NOTIFICA_CATEGORIE,
    NotificaPreferenze,
)
from personaggi.notify import get_or_create_preferenze
from personaggi.telegram_bot import start_url_for_code, telegram_bot_username, telegram_configured


def _email_configured() -> bool:
    return bool(
        (getattr(settings, "SMTP_EMAIL", "") or "").strip()
        and (getattr(settings, "EMAIL_HOST", "") or "").strip()
    )


def _serialize_prefs(prefs: NotificaPreferenze, request) -> dict:
    from gestione_plot.compiti_ics import calendario_feed_payload

    user = prefs.user
    bot_username = telegram_bot_username()
    return {
        "canali": prefs.normalized_canali(),
        "categorie": [
            {"id": key, "label": NOTIFICA_CATEGORIA_LABELS[key]} for key in NOTIFICA_CATEGORIE
        ],
        "telegram": {
            "linked": bool(prefs.telegram_chat_id),
            "username": prefs.telegram_username or "",
            "bot_username": bot_username,
            "bot_configured": telegram_configured() and bool(bot_username),
        },
        "email": {
            "address": (user.email or "").strip(),
            "configured": _email_configured(),
        },
        "calendario": calendario_feed_payload(user),
    }


class NotificaPreferenzeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        prefs = get_or_create_preferenze(request.user)
        return Response(_serialize_prefs(prefs, request))

    def patch(self, request):
        prefs = get_or_create_preferenze(request.user)
        canali = request.data.get("canali")
        if not isinstance(canali, dict):
            return Response(
                {"detail": "Payload atteso: { canali: { webpush|telegram|email: {categoria: bool} } }."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        current = prefs.normalized_canali()
        for canale in NOTIFICA_CANALI:
            src = canali.get(canale)
            if not isinstance(src, dict):
                continue
            for cat in NOTIFICA_CATEGORIE:
                if cat in src:
                    current[canale][cat] = bool(src[cat])
        prefs.canali = current
        prefs.save(update_fields=["canali", "updated_at"])
        return Response(_serialize_prefs(prefs, request))


class TelegramLinkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not telegram_configured() or not telegram_bot_username():
            return Response(
                {
                    "detail": "Telegram non è configurato sul server (mancano TELEGRAM_BOT_TOKEN e TELEGRAM_BOT_USERNAME).",
                    "bot_configured": False,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        prefs = get_or_create_preferenze(request.user)
        code = secrets.token_hex(4)
        prefs.telegram_link_code = code
        prefs.telegram_link_expires = timezone.now() + timedelta(minutes=30)
        prefs.save(update_fields=["telegram_link_code", "telegram_link_expires", "updated_at"])
        url = start_url_for_code(code)
        return Response(
            {
                "code": code,
                "start_url": url,
                "expires_at": prefs.telegram_link_expires.isoformat(),
                "bot_username": telegram_bot_username(),
                "instructions": (
                    "Apri il link (o cerca @"
                    f"{telegram_bot_username()} su Telegram), premi Avvia. "
                    "Il collegamento scade tra 30 minuti."
                ),
            }
        )


class TelegramUnlinkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        prefs = get_or_create_preferenze(request.user)
        prefs.telegram_chat_id = ""
        prefs.telegram_username = ""
        prefs.telegram_link_code = ""
        prefs.telegram_link_expires = None
        prefs.save(
            update_fields=[
                "telegram_chat_id",
                "telegram_username",
                "telegram_link_code",
                "telegram_link_expires",
                "updated_at",
            ]
        )
        return Response(_serialize_prefs(prefs, request))


class CalendarioFeedTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from gestione_plot.compiti_ics import calendario_feed_payload

        return Response(calendario_feed_payload(request.user))

    def post(self, request):
        from gestione_plot.models import CalendarioFeedToken
        from gestione_plot.compiti_ics import calendario_feed_payload

        token_row, _ = CalendarioFeedToken.objects.get_or_create(user=request.user)
        token_row.rigenera()
        return Response(calendario_feed_payload(request.user))
