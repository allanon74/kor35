"""
Dispatcher unico per le notifiche utente: web push, Telegram, email, FCM.

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


def _stringify_extra(extra: dict | None) -> dict[str, str]:
    """FCM data payload richiede valori stringa."""
    if not extra:
        return {}
    out: dict[str, str] = {}
    for key, value in extra.items():
        if value is None:
            continue
        out[str(key)] = str(value)
    return out


def notify_user(
    user,
    *,
    category: str,
    head: str,
    body: str,
    url: str = "/",
    extra: dict | None = None,
) -> int:
    """Invia sui canali abilitati. Ritorna il numero di tentativi (non necessariamente consegnati)."""
    if not user or category not in NOTIFICA_CATEGORIE:
        return 0
    prefs = get_or_create_preferenze(user)
    attempts = 0
    if prefs.is_enabled("webpush", category):
        attempts += _send_webpush(
            user, head=head, body=body, url=url, category=category, extra=extra
        )
        attempts += _send_fcm(
            user, head=head, body=body, url=url, category=category, extra=extra
        )
    if prefs.is_enabled("telegram", category) and prefs.telegram_chat_id:
        attempts += _send_telegram(prefs.telegram_chat_id, head=head, body=body)
    if prefs.is_enabled("email", category) and (user.email or "").strip():
        attempts += _send_email(user, head=head, body=body)
    return attempts


def notify_users(
    users: Iterable,
    *,
    category: str,
    head: str,
    body: str,
    url: str = "/",
    extra: dict | None = None,
) -> int:
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
        total += notify_user(
            user, category=category, head=head, body=body, url=url, extra=extra
        )
    return total


def notify_user_ids(
    user_ids: Iterable,
    *,
    category: str,
    head: str,
    body: str,
    url: str = "/",
    extra: dict | None = None,
) -> int:
    ids = sorted({int(u) for u in user_ids if u})
    if not ids:
        return 0
    users = {u.pk: u for u in User.objects.filter(pk__in=ids)}
    return notify_users(
        (users.get(i) for i in ids),
        category=category,
        head=head,
        body=body,
        url=url,
        extra=extra,
    )


def _send_webpush(
    user,
    *,
    head: str,
    body: str,
    url: str,
    category: str = "messaggi",
    extra: dict | None = None,
) -> int:
    try:
        from webpush import send_user_notification
    except Exception as exc:  # pragma: no cover
        logger.warning("webpush non disponibile: %s", exc)
        return 0
    try:
        payload = {
            "head": head,
            "body": body,
            "icon": "/pwa-192x192.png",
            "url": url or "/?tab=messaggi",
            "tag": f"kor35-{category}",
            "renotify": True,
            "category": category,
        }
        payload.update(_stringify_extra(extra))
        send_user_notification(
            user=user,
            payload=payload,
            ttl=86400,
        )
        return 1
    except Exception as exc:
        logger.warning("Web push fallita per user=%s: %s", getattr(user, "pk", None), exc)
        return 0


def _send_fcm(
    user,
    *,
    head: str,
    body: str,
    url: str,
    category: str = "messaggi",
    extra: dict | None = None,
) -> int:
    """
    Invio FCM ai device token della shell Android.

    Preferisce HTTP v1 (service account). La Legacy key (`FCM_SERVER_KEY`) resta
    solo come fallback per progetti vecchi: sui Firebase nuovi è disabilitata.
    """
    from personaggi.fcm_v1 import fcm_v1_configured, send_fcm_v1
    from personaggi.models import FcmDeviceToken

    tokens = list(
        FcmDeviceToken.objects.filter(user=user, is_active=True).values_list("token", flat=True)
    )
    if not tokens:
        return 0

    # Canali creati da MainActivity (shell Capacitor).
    channel_id = "kor35_incoming_calls" if category == "chiamate" else "kor35_default"
    data = {
        "url": url or "/",
        "category": category,
        "head": head,
        "body": body,
    }
    data.update(_stringify_extra(extra))

    if fcm_v1_configured():
        sent = 0
        for token in tokens:
            ok, err = send_fcm_v1(
                token=token,
                head=head,
                body=body,
                data=data,
                android_channel_id=channel_id,
            )
            if ok:
                sent += 1
                continue
            err_u = (err or "").upper()
            if any(code in err_u for code in ("UNREGISTERED", "NOT_FOUND", "INVALID_ARGUMENT")):
                FcmDeviceToken.objects.filter(token=token).update(is_active=False)
            logger.warning(
                "FCM v1 send fallita user=%s err=%s",
                getattr(user, "pk", None),
                err,
            )
        return sent

    return _send_fcm_legacy(
        user,
        tokens=tokens,
        head=head,
        body=body,
        data=data,
        channel_id=channel_id,
    )


def _send_fcm_legacy(
    user,
    *,
    tokens: list[str],
    head: str,
    body: str,
    data: dict[str, str],
    channel_id: str,
) -> int:
    """Fallback Legacy HTTP (spesso disabilitato su Firebase nuovi)."""
    from personaggi.models import FcmDeviceToken

    server_key = getattr(settings, "FCM_SERVER_KEY", "") or ""
    if not server_key.strip():
        return 0

    import json
    from urllib import request as urlrequest
    from urllib.error import HTTPError, URLError

    logger.warning(
        "FCM: uso Legacy FCM_SERVER_KEY (deprecata). Configura FCM_SERVICE_ACCOUNT_FILE "
        "per HTTP v1 — sui progetti Firebase nuovi la Legacy API è disabilitata."
    )

    sent = 0
    payload_base = {
        "notification": {
            "title": head,
            "body": body,
            "android_channel_id": channel_id,
            "sound": "default",
            # Niente click_action custom (rompe il tap → MainActivity / Capacitor).
        },
        "data": data,
        "priority": "high",
        "content_available": True,
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
                    logger.warning(
                        "FCM legacy status non OK per user=%s: %s",
                        getattr(user, "pk", None),
                        resp.status,
                    )
        except HTTPError as exc:
            if exc.code in (400, 404):
                FcmDeviceToken.objects.filter(token=token).update(is_active=False)
            logger.warning("FCM legacy HTTPError user=%s: %s", getattr(user, "pk", None), exc)
        except URLError as exc:
            logger.warning("FCM legacy URLError user=%s: %s", getattr(user, "pk", None), exc)
        except Exception as exc:
            logger.warning("FCM legacy send fallita user=%s: %s", getattr(user, "pk", None), exc)
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
