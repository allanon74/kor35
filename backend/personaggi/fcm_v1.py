"""
Invio FCM via HTTP v1 (service account Google).

La Legacy API (`FCM_SERVER_KEY` + fcm/send) è deprecata/disabilitata sui progetti
Firebase nuovi: usare un service account con ruolo Firebase Cloud Messaging API.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

from django.conf import settings

logger = logging.getLogger(__name__)

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"


def fcm_v1_configured() -> bool:
    """True se service account + project id sono disponibili."""
    return bool(_service_account_info() and _project_id())


@lru_cache(maxsize=1)
def _service_account_info() -> dict[str, Any] | None:
    raw = (getattr(settings, "FCM_SERVICE_ACCOUNT_JSON", "") or "").strip()
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("client_email"):
                return data
        except json.JSONDecodeError:
            logger.warning("FCM_SERVICE_ACCOUNT_JSON non è JSON valido")
            return None

    path = (getattr(settings, "FCM_SERVICE_ACCOUNT_FILE", "") or "").strip()
    if not path:
        return None
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.warning("FCM_SERVICE_ACCOUNT_FILE non trovato: %s", path)
        return None
    except OSError as exc:
        logger.warning("Impossibile leggere FCM_SERVICE_ACCOUNT_FILE: %s", exc)
        return None
    except json.JSONDecodeError:
        logger.warning("FCM_SERVICE_ACCOUNT_FILE non è JSON valido: %s", path)
        return None
    if not isinstance(data, dict) or not data.get("client_email"):
        logger.warning("FCM_SERVICE_ACCOUNT_FILE senza client_email: %s", path)
        return None
    return data


def _project_id() -> str:
    explicit = (getattr(settings, "FCM_PROJECT_ID", "") or "").strip()
    if explicit:
        return explicit
    info = _service_account_info() or {}
    return str(info.get("project_id") or "").strip()


def _access_token() -> str | None:
    info = _service_account_info()
    if not info:
        return None
    try:
        from google.oauth2 import service_account
    except ImportError:
        logger.warning(
            "Pacchetto google-auth non installato: impossibile usare FCM HTTP v1. "
            "Aggiungi google-auth alle dipendenze del backend."
        )
        return None
    try:
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=[FCM_SCOPE]
        )
        # google-auth richiede un request object per il refresh
        from google.auth.transport.requests import Request

        creds.refresh(Request())
        return creds.token
    except Exception as exc:
        logger.warning("Impossibile ottenere access token FCM v1: %s", exc)
        return None


def clear_fcm_v1_cache() -> None:
    """Solo per test: invalida cache service account."""
    _service_account_info.cache_clear()


def send_fcm_v1(
    *,
    token: str,
    head: str,
    body: str,
    data: dict[str, str],
    android_channel_id: str,
) -> tuple[bool, str | None]:
    """
    Invia un messaggio a un device token.
    Ritorna (ok, error_code) dove error_code tipici: UNREGISTERED, NOT_FOUND, …
    """
    project_id = _project_id()
    access = _access_token()
    if not project_id or not access:
        return False, "not_configured"

    payload = {
        "message": {
            "token": token,
            "notification": {
                "title": head,
                "body": body,
            },
            "data": data,
            "android": {
                "priority": "HIGH",
                "notification": {
                    "channel_id": android_channel_id,
                    "sound": "default",
                    "click_action": "OPEN_KOR35_PUSH",
                },
            },
        }
    }
    body_bytes = json.dumps(payload).encode("utf-8")
    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    req = urlrequest.Request(
        url,
        data=body_bytes,
        headers={
            "Authorization": f"Bearer {access}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=8) as resp:
            if 200 <= getattr(resp, "status", 200) < 300:
                return True, None
            return False, f"status_{getattr(resp, 'status', '?')}"
    except HTTPError as exc:
        err_code = None
        try:
            err_body = exc.read().decode("utf-8", errors="replace")
            parsed = json.loads(err_body) if err_body else {}
            err_code = (
                (parsed.get("error") or {}).get("status")
                or (parsed.get("error") or {}).get("message")
                or str(exc.code)
            )
        except Exception:
            err_code = str(exc.code)
        return False, str(err_code)
    except URLError as exc:
        return False, f"url_error:{exc}"
    except Exception as exc:
        return False, str(exc)
