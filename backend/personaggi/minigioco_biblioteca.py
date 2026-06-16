"""
Scarica e mantiene la libreria immagini open license per i minigiochi QR.
Sorgenti: Openverse (con OAuth2 su VPS) e fallback Wikimedia Commons.
"""
from __future__ import annotations

import logging
import random
import re
import time
import uuid
from io import BytesIO
from typing import Any

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

logger = logging.getLogger(__name__)

BIBLIOTECA_TARGET = 100
OPENVERSE_API = "https://api.openverse.org/v1/images/"
OPENVERSE_TOKEN_URL = "https://api.openverse.org/v1/auth_tokens/token/"
OPENVERSE_REGISTER_URL = "https://api.openverse.org/v1/auth_tokens/register/"
WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
OPENVERSE_TIMEOUT = 25
DOWNLOAD_TIMEOUT = 40
USER_AGENT = "KOR35-MinigiocoBiblioteca/1.0 (LARP event app; https://www.kor35.it)"

SEARCH_QUERIES = (
    "abstract texture pattern",
    "nature landscape",
    "fantasy illustration",
    "architecture detail",
    "space nebula stars",
    "forest moss",
    "geometric mosaic",
    "ocean waves",
    "mountains sky",
    "vintage engraving",
    "crystal mineral",
    "desert dunes",
)

_openverse_token_cache: dict[str, Any] = {"token": None, "expires_at": 0.0}


def _mask_client_id(client_id: str) -> str:
    cid = (client_id or "").strip()
    if len(cid) <= 8:
        return "***" if cid else ""
    return f"{cid[:4]}…{cid[-4:]}"


def _invalidate_openverse_token_cache() -> None:
    _openverse_token_cache["token"] = None
    _openverse_token_cache["expires_at"] = 0.0


def resolve_openverse_credentials() -> tuple[str, str, str]:
    """Ritorna (client_id, client_secret, source) con source in database|env|."""
    try:
        from personaggi.models import MinigiocoOpenverseConfig

        cfg = MinigiocoOpenverseConfig.objects.filter(singleton_id=1).first()
        if cfg and cfg.client_id and cfg.client_secret:
            return cfg.client_id.strip(), cfg.client_secret.strip(), "database"
    except Exception:
        logger.debug("Lettura MinigiocoOpenverseConfig fallita", exc_info=True)

    client_id = getattr(settings, "OPENVERSE_CLIENT_ID", "") or ""
    client_secret = getattr(settings, "OPENVERSE_CLIENT_SECRET", "") or ""
    if client_id.strip() and client_secret.strip():
        return client_id.strip(), client_secret.strip(), "env"
    return "", "", ""


def openverse_config_status() -> dict[str, Any]:
    client_id, _secret, source = resolve_openverse_credentials()
    configured = bool(client_id)
    payload: dict[str, Any] = {
        "configured": configured,
        "source": source or None,
        "client_id_masked": _mask_client_id(client_id) if configured else "",
    }
    if source == "database":
        try:
            from personaggi.models import MinigiocoOpenverseConfig

            cfg = MinigiocoOpenverseConfig.get_solo()
            payload.update(
                {
                    "app_name": cfg.app_name,
                    "contact_email": cfg.contact_email,
                    "api_message": cfg.api_message,
                    "registered_at": cfg.registered_at.isoformat() if cfg.registered_at else None,
                }
            )
        except Exception:
            pass
    return payload


def registra_openverse_app(*, name: str, description: str, email: str) -> dict[str, Any]:
    """Registra l'app su Openverse e salva le credenziali nel DB locale."""
    name = (name or "").strip()[:120]
    description = (description or "").strip()[:500]
    email = (email or "").strip()
    if not name:
        return {"ok": False, "error": "Nome applicazione obbligatorio."}
    if not email:
        return {"ok": False, "error": "Email di contatto obbligatoria."}

    try:
        resp = requests.post(
            OPENVERSE_REGISTER_URL,
            json={"name": name, "description": description, "email": email},
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=OPENVERSE_TIMEOUT,
        )
        if resp.status_code not in (200, 201):
            detail = resp.text[:300].strip() or resp.reason
            return {"ok": False, "error": f"Openverse HTTP {resp.status_code}: {detail}"}
        data = resp.json()
    except Exception as exc:
        logger.warning("Registrazione Openverse fallita: %s", exc)
        return {"ok": False, "error": f"Registrazione Openverse fallita: {exc}"}

    client_id = (data.get("client_id") or "").strip()
    client_secret = (data.get("client_secret") or "").strip()
    if not client_id or not client_secret:
        return {"ok": False, "error": "Risposta Openverse incompleta (mancano client_id o client_secret)."}

    from personaggi.models import MinigiocoOpenverseConfig

    cfg = MinigiocoOpenverseConfig.get_solo()
    cfg.client_id = client_id
    cfg.client_secret = client_secret
    cfg.app_name = name
    cfg.app_description = description
    cfg.contact_email = email
    cfg.api_message = (data.get("msg") or "")[:500]
    cfg.registered_at = timezone.now()
    cfg.save()
    _invalidate_openverse_token_cache()

    return {
        "ok": True,
        "client_id": client_id,
        "client_secret": client_secret,
        "message": cfg.api_message or "Applicazione registrata.",
        "email": email,
        "openverse": openverse_config_status(),
    }


def verifica_openverse_connessione() -> dict[str, Any]:
    """Ottiene un token e prova una ricerca immagini."""
    client_id, _secret, source = resolve_openverse_credentials()
    if not client_id:
        return {
            "ok": False,
            "configured": False,
            "error": "Openverse non configurato. Registra l'app o imposta OPENVERSE_CLIENT_ID/SECRET nel .env.",
        }

    token = _get_openverse_access_token()
    if not token:
        return {
            "ok": False,
            "configured": True,
            "source": source,
            "token_ok": False,
            "error": "Impossibile ottenere il token OAuth. Verifica l'email di conferma Openverse o le credenziali.",
        }

    search_ok = False
    search_status = None
    try:
        resp = requests.get(
            OPENVERSE_API,
            params={"format": "json", "page": 1, "page_size": 1, "q": "landscape"},
            headers=_openverse_request_headers(),
            timeout=OPENVERSE_TIMEOUT,
        )
        search_status = resp.status_code
        search_ok = resp.status_code == 200
    except Exception as exc:
        return {
            "ok": False,
            "configured": True,
            "source": source,
            "token_ok": True,
            "search_ok": False,
            "error": f"Token OK ma ricerca immagini fallita: {exc}",
        }

    if not search_ok:
        return {
            "ok": False,
            "configured": True,
            "source": source,
            "token_ok": True,
            "search_ok": False,
            "search_status": search_status,
            "error": f"Token OK ma Openverse ha risposto HTTP {search_status} alla ricerca immagini.",
        }

    return {
        "ok": True,
        "configured": True,
        "source": source,
        "token_ok": True,
        "search_ok": True,
        "message": "Connessione Openverse verificata.",
    }


def _strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value or "").strip()


def _license_ok_for_minigioco(licenza: str) -> bool:
    lic = (licenza or "").strip().lower().replace("_", "-")
    if not lic:
        return False
    compact = lic.replace(" ", "").replace("-", "")
    if "nc" in compact or "nd" in compact:
        return False
    allowed = (
        "cc0",
        "cc by",
        "cc-by",
        "public domain",
        "pd",
        "cc0 1.0",
        "cc by 1.0",
        "cc by 2.0",
        "cc by 3.0",
        "cc by 4.0",
        "cc by-sa",
    )
    return any(token in lic for token in allowed)


def _get_openverse_access_token() -> str | None:
    client_id, client_secret, _source = resolve_openverse_credentials()
    if not client_id or not client_secret:
        return None

    now = time.monotonic()
    cached = _openverse_token_cache.get("token")
    if cached and now < float(_openverse_token_cache.get("expires_at") or 0):
        return cached

    try:
        resp = requests.post(
            OPENVERSE_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": USER_AGENT,
            },
            timeout=OPENVERSE_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        token = payload.get("access_token")
        if not token:
            logger.warning("Openverse token senza access_token: %s", payload)
            return None
        expires_in = int(payload.get("expires_in") or 3600)
        _openverse_token_cache["token"] = token
        _openverse_token_cache["expires_at"] = now + max(60, expires_in - 120)
        return token
    except Exception as exc:
        logger.warning("Openverse OAuth fallito: %s", exc)
        return None


def _openverse_request_headers() -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT}
    token = _get_openverse_access_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _square_jpeg(content: bytes, size: int = 512) -> bytes:
    try:
        from PIL import Image

        img = Image.open(BytesIO(content))
        img = img.convert("RGB")
        w, h = img.size
        if w < 64 or h < 64:
            raise ValueError("immagine troppo piccola")
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        out = BytesIO()
        img.save(out, format="JPEG", quality=85)
        return out.getvalue()
    except Exception:
        return content


def _pick_download_url(item: dict) -> str:
    for key in ("url", "thumbnail"):
        raw = item.get(key)
        if isinstance(raw, str) and raw.startswith("http"):
            return raw
    return ""


def _fetch_openverse_page(query: str, page: int, page_size: int = 20) -> tuple[list[dict], str | None]:
    try:
        resp = requests.get(
            OPENVERSE_API,
            params={
                "format": "json",
                "page": page,
                "page_size": page_size,
                "license": "cc0,by,by-sa",
                "license_type": "commercial,modification",
                "q": query,
            },
            headers=_openverse_request_headers(),
            timeout=OPENVERSE_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return list(data.get("results") or []), None
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        logger.warning("Openverse page fallita q=%s p=%s: %s", query, page, exc)
        return [], msg


def _fetch_wikimedia_page(
    query: str, offset: int = 0, page_size: int = 20
) -> tuple[list[dict[str, Any]], str | None]:
    try:
        resp = requests.get(
            WIKIMEDIA_API,
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrnamespace": 6,
                "gsrsearch": f"filetype:bitmap {query}",
                "gsrlimit": page_size,
                "gsroffset": offset,
                "prop": "imageinfo",
                "iiprop": "url|extmetadata|mime",
                "iiurlwidth": 800,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=OPENVERSE_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        pages = (data.get("query") or {}).get("pages") or {}
        items: list[dict[str, Any]] = []
        for page in pages.values():
            imageinfo = (page.get("imageinfo") or [None])[0]
            if not imageinfo:
                continue
            mime = imageinfo.get("mime") or ""
            if not mime.startswith("image/"):
                continue
            metadata = imageinfo.get("extmetadata") or {}
            licenza = (metadata.get("LicenseShortName") or metadata.get("License") or {}).get("value", "")
            if not _license_ok_for_minigioco(licenza):
                continue
            url = imageinfo.get("thumburl") or imageinfo.get("url") or ""
            if not url.startswith("http"):
                continue
            titolo = (page.get("title") or "").replace("File:", "")[:200]
            autore = _strip_html((metadata.get("Artist") or {}).get("value", ""))[:200]
            items.append(
                {
                    "url": url,
                    "title": titolo,
                    "creator": autore,
                    "license": licenza[:32],
                    "id": str(page.get("pageid") or ""),
                    "foreign_landing_url": (imageinfo.get("descriptionurl") or url)[:500],
                }
            )
        return items, None
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        logger.warning("Wikimedia page fallita q=%s off=%s: %s", query, offset, exc)
        return [], msg


def _download_image(url: str) -> bytes | None:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=DOWNLOAD_TIMEOUT,
            stream=True,
        )
        resp.raise_for_status()
        raw = resp.content
        if len(raw) < 2048:
            return None
        if len(raw) > 8 * 1024 * 1024:
            return None
        return _square_jpeg(raw)
    except Exception as exc:
        logger.debug("Download fallito %s: %s", url, exc)
        return None


def _append_prepared_item(
    prepared: list[dict[str, Any]],
    *,
    blob: bytes,
    titolo: str,
    autore: str,
    licenza: str,
    fonte: str,
    source_id: str,
    source_page_url: str,
    search_query: str,
) -> None:
    fname = f"{slugify(titolo)[:40] or 'img'}-{uuid.uuid4().hex[:8]}.jpg"
    prepared.append(
        {
            "blob": blob,
            "titolo": titolo[:200],
            "autore": autore[:200],
            "licenza": licenza[:32],
            "fonte": fonte,
            "source_id": source_id[:64],
            "source_page_url": source_page_url[:500],
            "search_query": search_query[:120],
            "fname": fname,
        }
    )


def _raccogli_immagini_da_openverse(
    *,
    target: int,
    seen_urls: set[str],
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    prepared: list[dict[str, Any]] = []
    errors: list[str] = []
    openverse_errors: list[str] = []
    page_size = 20

    for query in SEARCH_QUERIES:
        if len(prepared) >= target:
            break
        page = 1
        while len(prepared) < target and page <= 8:
            batch, ov_err = _fetch_openverse_page(query, page, page_size=page_size)
            if ov_err:
                openverse_errors.append(f"openverse {query} p{page}: {ov_err}")
            if not batch:
                break
            for item in batch:
                if len(prepared) >= target:
                    break
                url = _pick_download_url(item)
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                blob = _download_image(url)
                if not blob:
                    errors.append(f"skip download: {url[:80]}")
                    continue
                titolo = (item.get("title") or query or "Openverse")[:200]
                _append_prepared_item(
                    prepared,
                    blob=blob,
                    titolo=titolo,
                    autore=(item.get("creator") or "")[:200],
                    licenza=(item.get("license") or "")[:32],
                    fonte="openverse",
                    source_id=str(item.get("id") or ""),
                    source_page_url=(item.get("foreign_landing_url") or url)[:500],
                    search_query=query,
                )
            page += 1

    return prepared, errors, openverse_errors


def _raccogli_immagini_da_wikimedia(
    *,
    target: int,
    seen_urls: set[str],
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    prepared: list[dict[str, Any]] = []
    errors: list[str] = []
    wikimedia_errors: list[str] = []
    page_size = 20

    for query in SEARCH_QUERIES:
        if len(prepared) >= target:
            break
        offset = 0
        page = 0
        while len(prepared) < target and page < 8:
            batch, wm_err = _fetch_wikimedia_page(query, offset=offset, page_size=page_size)
            if wm_err:
                wikimedia_errors.append(f"wikimedia {query} off{offset}: {wm_err}")
            if not batch:
                break
            for item in batch:
                if len(prepared) >= target:
                    break
                url = item.get("url") or ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                blob = _download_image(url)
                if not blob:
                    errors.append(f"skip download: {url[:80]}")
                    continue
                _append_prepared_item(
                    prepared,
                    blob=blob,
                    titolo=item.get("title") or query or "Wikimedia",
                    autore=item.get("creator") or "",
                    licenza=item.get("license") or "",
                    fonte="wikimedia",
                    source_id=item.get("id") or "",
                    source_page_url=item.get("foreign_landing_url") or url,
                    search_query=query,
                )
            offset += page_size
            page += 1

    return prepared, errors, wikimedia_errors


def _raccogli_immagini(*, target: int) -> tuple[list[dict[str, Any]], list[str], list[str], list[str], list[str]]:
    """Ritorna (prepared, download_errors, openverse_errors, wikimedia_errors, sources_used)."""
    seen_urls: set[str] = set()
    download_errors: list[str] = []
    openverse_errors: list[str] = []
    wikimedia_errors: list[str] = []
    sources_used: list[str] = []
    prepared: list[dict[str, Any]] = []

    ov_batch, ov_dl_err, ov_api_err = _raccogli_immagini_da_openverse(target=target, seen_urls=seen_urls)
    if ov_batch:
        sources_used.append("openverse")
    prepared.extend(ov_batch)
    download_errors.extend(ov_dl_err)
    openverse_errors.extend(ov_api_err)

    if len(prepared) < target:
        need = target - len(prepared)
        wm_batch, wm_dl_err, wm_api_err = _raccogli_immagini_da_wikimedia(target=need, seen_urls=seen_urls)
        if wm_batch:
            sources_used.append("wikimedia")
        prepared.extend(wm_batch)
        download_errors.extend(wm_dl_err)
        wikimedia_errors.extend(wm_api_err)

    return prepared, download_errors, openverse_errors, wikimedia_errors, sources_used


def aggiorna_biblioteca_immagini(*, target: int = BIBLIOTECA_TARGET) -> dict[str, Any]:
    """
    Sostituisce la libreria con fino a `target` immagini CC da Openverse e/o Wikimedia.
    Scarica prima in memoria: se nessuna sorgente risponde, la libreria esistente resta intatta.
    """
    from personaggi.models import MinigiocoBibliotecaImmagine

    started = time.monotonic()
    count_prima = biblioteca_immagine_count()
    prepared, errors, openverse_errors, wikimedia_errors, sources_used = _raccogli_immagini(target=target)
    elapsed_ms = int((time.monotonic() - started) * 1000)

    if not prepared:
        err_msg = (
            "Impossibile scaricare immagini da Openverse né da Wikimedia Commons. "
            "La libreria esistente non è stata modificata."
        )
        if openverse_errors:
            err_msg += f" Openverse: {openverse_errors[0]}."
        if wikimedia_errors:
            err_msg += f" Wikimedia: {wikimedia_errors[0]}."
        elif errors:
            err_msg += f" Dettaglio: {errors[0]}."
        if not openverse_config_status().get("configured"):
            err_msg += " Registra l'app Openverse dal pannello staff (QR Debug → Libreria minigioco)."
        return {
            "ok": False,
            "error": err_msg,
            "count": count_prima,
            "target": target,
            "errors_count": len(errors),
            "errors_sample": errors[:8],
            "openverse_errors": openverse_errors[:8],
            "wikimedia_errors": wikimedia_errors[:8],
            "sources_used": sources_used,
            "aggiornato_at": timezone.now().isoformat(),
            "elapsed_ms": elapsed_ms,
        }

    with transaction.atomic():
        for row in MinigiocoBibliotecaImmagine.objects.all():
            if row.immagine:
                row.immagine.delete(save=False)
        MinigiocoBibliotecaImmagine.objects.all().delete()

        for item in prepared:
            row = MinigiocoBibliotecaImmagine(
                titolo=item["titolo"],
                autore=item["autore"],
                licenza=item["licenza"],
                fonte=item["fonte"],
                source_id=item["source_id"],
                source_page_url=item["source_page_url"],
                search_query=item["search_query"],
            )
            row.immagine.save(item["fname"], ContentFile(item["blob"]), save=False)
            row.save()

    creati = len(prepared)
    return {
        "ok": True,
        "count": creati,
        "target": target,
        "errors_count": len(errors),
        "errors_sample": errors[:8],
        "openverse_errors": openverse_errors[:8],
        "wikimedia_errors": wikimedia_errors[:8],
        "sources_used": sources_used,
        "aggiornato_at": timezone.now().isoformat(),
        "elapsed_ms": elapsed_ms,
    }


def biblioteca_immagine_count() -> int:
    from personaggi.models import MinigiocoBibliotecaImmagine

    return MinigiocoBibliotecaImmagine.objects.count()


def scegli_immagine_biblioteca(seed: int):
    from personaggi.models import MinigiocoBibliotecaImmagine

    ids = list(MinigiocoBibliotecaImmagine.objects.values_list("pk", flat=True))
    if not ids:
        return None
    pick = random.Random(seed).choice(ids)
    return MinigiocoBibliotecaImmagine.objects.filter(pk=pick).first()


def immagine_biblioteca_url(row, request=None) -> str:
    if not row or not row.immagine:
        return ""
    try:
        url = row.immagine.url
    except Exception:
        return ""
    if request and url.startswith("/"):
        return request.build_absolute_uri(url)
    return url
