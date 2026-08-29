"""
Bot Telegram KOR35: invio messaggi e collegamento account via /start CODE.

Il worker `dispatch_timer_expiry` chiama `process_telegram_updates` (getUpdates).
Nessuna dipendenza extra: HTTP via urllib.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

OFFSET_CACHE_KEY = "kor35_telegram_update_offset"
HELP_TEXT = (
    "Bot notifiche KOR35.\n\n"
    "Per collegare l'account: apri la console Notifiche nell'app, "
    "tocca «Collega Telegram» e premi Avvia qui.\n"
    "Scrivi /stop per scollegare."
)


def telegram_configured() -> bool:
    return bool((getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip())


def telegram_bot_username() -> str:
    raw = (getattr(settings, "TELEGRAM_BOT_USERNAME", "") or "").strip().lstrip("@")
    return raw


def start_url_for_code(code: str) -> str:
    username = telegram_bot_username()
    if not username or not code:
        return ""
    return f"https://t.me/{username}?start={code}"


def send_telegram_message(chat_id, text: str) -> bool:
    if not telegram_configured() or not chat_id or not text:
        return False
    data = _api(
        "sendMessage",
        {
            "chat_id": str(chat_id),
            "text": text[:3900],
            "disable_web_page_preview": True,
        },
    )
    return bool(data and data.get("ok"))


def process_telegram_updates() -> dict:
    """Consuma getUpdates e collega/scollega account. Ritorna stats per i log."""
    if not telegram_configured():
        return {"processed": 0, "linked": 0, "unlinked": 0}
    offset = cache.get(OFFSET_CACHE_KEY)
    params = {"timeout": 0, "allowed_updates": json.dumps(["message"])}
    if offset:
        params["offset"] = int(offset)
    payload = _api("getUpdates", params, http_get=True)
    if not payload or not payload.get("ok"):
        return {"processed": 0, "linked": 0, "unlinked": 0, "error": True}

    linked = 0
    unlinked = 0
    last_id = offset
    for update in payload.get("result") or []:
        upd_id = update.get("update_id")
        if upd_id is not None:
            last_id = int(upd_id) + 1
        message = update.get("message") or update.get("edited_message") or {}
        text = str(message.get("text") or "").strip()
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None or not text:
            continue
        from_user = message.get("from") or {}
        username = str(from_user.get("username") or "")
        if text.startswith("/stop"):
            if _unlink_chat(str(chat_id)):
                unlinked += 1
                send_telegram_message(chat_id, "Telegram scollegato da KOR35.")
            else:
                send_telegram_message(chat_id, "Nessun account KOR35 collegato a questa chat.")
            continue
        if text.startswith("/start"):
            parts = text.split()
            code = parts[1].strip() if len(parts) >= 2 else ""
            if not code:
                send_telegram_message(chat_id, HELP_TEXT)
                continue
            if _link_chat(code, str(chat_id), username):
                linked += 1
                send_telegram_message(
                    chat_id,
                    "Account KOR35 collegato. Scegli le categorie nella console Notifiche "
                    "dell'app, oppure scrivi /stop per scollegare.",
                )
            else:
                send_telegram_message(
                    chat_id,
                    "Codice non valido o scaduto. Generane uno nuovo dalla console Notifiche in KOR35.",
                )
            continue
        if text.startswith("/help"):
            send_telegram_message(chat_id, HELP_TEXT)

    if last_id:
        cache.set(OFFSET_CACHE_KEY, last_id, timeout=None)
    return {
        "processed": len(payload.get("result") or []),
        "linked": linked,
        "unlinked": unlinked,
    }


def _link_chat(code: str, chat_id: str, username: str) -> bool:
    from personaggi.models import NotificaPreferenze

    code = (code or "").strip()
    if not code:
        return False
    prefs = (
        NotificaPreferenze.objects.filter(telegram_link_code__iexact=code)
        .select_related("user")
        .first()
    )
    if not prefs:
        return False
    if prefs.telegram_link_expires and prefs.telegram_link_expires < timezone.now():
        return False
    # Una chat → un utente. Scollega eventuali duplicati.
    NotificaPreferenze.objects.filter(telegram_chat_id=str(chat_id)).exclude(pk=prefs.pk).update(
        telegram_chat_id="",
        telegram_username="",
    )
    prefs.telegram_chat_id = str(chat_id)
    prefs.telegram_username = (username or "")[:64]
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
    return True


def _unlink_chat(chat_id: str) -> bool:
    from personaggi.models import NotificaPreferenze

    prefs = NotificaPreferenze.objects.filter(telegram_chat_id=str(chat_id)).first()
    if not prefs:
        return False
    prefs.telegram_chat_id = ""
    prefs.telegram_username = ""
    prefs.save(update_fields=["telegram_chat_id", "telegram_username", "updated_at"])
    return True


def _api(method: str, payload=None, *, http_get: bool = False):
    token = (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()
    if not token:
        return None
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        if http_get:
            qs = urllib.parse.urlencode(payload or {})
            req = urllib.request.Request(f"{url}?{qs}" if qs else url)
        else:
            body = json.dumps(payload or {}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
            )
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, OSError) as exc:
        logger.warning("Telegram API %s fallita: %s", method, exc)
        return None
