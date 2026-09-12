"""
Dispatcher unico per le notifiche utente: web push, Telegram, email.

Rispetta `NotificaPreferenze` (default: web push on, Telegram/email off).
"""
from __future__ import annotations

import logging
from typing import Iterable

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail

from personaggi.models import (
    NOTIFICA_CATEGORIE,
    NotificaPreferenze,
)

logger = logging.getLogger(__name__)


def get_or_create_preferenze(user) -> NotificaPreferenze:
    prefs, _ = NotificaPreferenze.objects.get_or_create(user=user)
    return prefs


def notify_user(user, *, category: str, head: str, body: str, url: str = "/") -> int:
    """Invia sui canali abilitati. Ritorna il numero di tentativi (non necessariamente consegnati)."""
    if not user or category not in NOTIFICA_CATEGORIE:
        return 0
    prefs = get_or_create_preferenze(user)
    attempts = 0
    if prefs.is_enabled("webpush", category):
        attempts += _send_webpush(user, head=head, body=body, url=url, category=category)
        attempts += _send_fcm(user, head=head, body=body, url=url, category=category)
    if prefs.is_enabled("telegram", category) and prefs.telegram_chat_id:
        attempts += _send_telegram(prefs.telegram_chat_id, head=head, body=body)
    if prefs.is_enabled("email", category) and (user.email or "").strip():
        attempts += _send_email(user, head=head, body=body)
    return attempts


def notify_users(users: Iterable, *, category: str, head: str, body: str, url: str = "/") -> int:
    seen = set()
    total = 0
    for user in users:
        if user is None:
            continue
        uid = getattr(user, "pk", None)
        if uid in seen:
            continue
        if uid is not None:
            seen.add(uid)
        total += notify_user(user, category=category, head=head, body=body, url=url)
    return total


def notify_user_ids(user_ids: Iterable, *, category: str, head: str, body: str, url: str = "/") -> int:
    ids = sorted({int(u) for u in user_ids if u})
    if not ids:
        return 0
    users = {u.pk: u for u in User.objects.filter(pk__in=ids)}
    return notify_users((users.get(i) for i in ids), category=category, head=head, body=body, url=url)


def _send_webpush(user, *, head: str, body: str, url: str, category: str = "messaggi") -> int:
    try:
        from webpush import send_user_notification
    except Exception as exc:  # pragma: no cover
        logger.warning("webpush non disponibile: %s", exc)
        return 0
    try:
        send_user_notification(
            user=user,
            payload={
                "head": head,
                "body": body,
                "icon": "/pwa-192x192.png",
                "url": url or "/?tab=messaggi",
                "tag": f"kor35-{category}",
                "renotify": True,
            },
            ttl=86400,
        )
        return 1
    except Exception as exc:
        logger.warning("Web push fallita per user=%s: %s", getattr(user, "pk", None), exc)
        return 0




def _send_fcm(user, *, head: str, body: str, url: str, category: str = "messaggi") -> int:
    """Invio FCM ai device token della shell Android. No-op senza FCM_SERVER_KEY."""
    from django.conf import settings
    from personaggi.models import FcmDeviceToken

    server_key = getattr(settings, "FCM_SERVER_KEY", "") or ""
    if not server_key.strip():
        return 0
    tokens = list(
        FcmDeviceToken.objects.filter(user=user, is_active=True).values_list("token", flat=True)
    )
    if not tokens:
        return 0

    import json
    from urllib import request as urlrequest
    from urllib.error import HTTPError, URLError

    sent = 0
    payload_base = {
        "notification": {
            "title": head,
            "body": body,
        },
        "data": {
            "url": url or "/",
            "category": category,
            "head": head,
            "body": body,
        },
        "priority": "high",
    }
    for token in tokens:
        body_bytes = json.dumps({**payload_base, "to": token}).encode("utf-8")
        req = urlrequest.Request(
            "https://fcm.googleapis.com/fcm/send",
            data=body_bytes,
            headers={
                "Authorization": f"key={server_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=8) as resp:
                if 200 <= getattr(resp, "status", 200) < 300:
                    sent += 1
                else:
                    logger.warning("FCM status non OK per user=%s: %s", getattr(user, "pk", None), resp.status)
        except HTTPError as exc:
            # Token non valido → disattiva
            if exc.code in (400, 404):
                FcmDeviceToken.objects.filter(token=token).update(is_active=False)
            logger.warning("FCM HTTPError user=%s: %s", getattr(user, "pk", None), exc)
        except URLError as exc:
            logger.warning("FCM URLError user=%s: %s", getattr(user, "pk", None), exc)
        except Exception as exc:
            logger.warning("FCM send fallita user=%s: %s", getattr(user, "pk", None), exc)
    return sent

def _send_telegram(chat_id: str, *, head: str, body: str) -> int:
    from personaggi.telegram_bot import send_telegram_message

    text = f"{head}\n\n{body}".strip()
    return 1 if send_telegram_message(chat_id, text) else 0


def _send_email(user, *, head: str, body: str) -> int:
    addr = (user.email or "").strip()
    if not addr:
        return 0
    try:
        send_mail(
            subject=f"[KOR35] {head}",
            message=(body or "").strip() or head,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[addr],
            fail_silently=True,
        )
        return 1
    except Exception as exc:
        logger.warning("Email notifica fallita per user=%s: %s", getattr(user, "pk", None), exc)
        return 0
