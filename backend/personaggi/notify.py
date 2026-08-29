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
        attempts += _send_webpush(user, head=head, body=body, url=url)
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


def _send_webpush(user, *, head: str, body: str, url: str) -> int:
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
                "url": url or "/",
            },
            ttl=1000,
        )
        return 1
    except Exception as exc:
        logger.warning("Web push fallita per user=%s: %s", getattr(user, "pk", None), exc)
        return 0


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
