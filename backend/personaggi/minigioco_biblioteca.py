"""
Scarica e mantiene la libreria immagini open license per i minigiochi QR (Openverse).
"""
from __future__ import annotations

import logging
import random
import time
import uuid
from io import BytesIO
from typing import Any

import requests
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

logger = logging.getLogger(__name__)

BIBLIOTECA_TARGET = 100
OPENVERSE_API = "https://api.openverse.org/v1/images/"
OPENVERSE_TIMEOUT = 25
DOWNLOAD_TIMEOUT = 40
USER_AGENT = "KOR35-MinigiocoBiblioteca/1.0 (LARP event app; staff sync)"

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
            headers={"User-Agent": USER_AGENT},
            timeout=OPENVERSE_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return list(data.get("results") or []), None
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        logger.warning("Openverse page fallita q=%s p=%s: %s", query, page, exc)
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


def _raccogli_immagini_da_openverse(*, target: int) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Scarica in memoria senza toccare il DB. Ritorna (prepared, download_errors, openverse_errors)."""
    prepared: list[dict[str, Any]] = []
    errors: list[str] = []
    openverse_errors: list[str] = []
    seen_urls: set[str] = set()
    page_size = 20

    for query in SEARCH_QUERIES:
        if len(prepared) >= target:
            break
        page = 1
        while len(prepared) < target and page <= 8:
            batch, ov_err = _fetch_openverse_page(query, page, page_size=page_size)
            if ov_err:
                openverse_errors.append(f"{query} p{page}: {ov_err}")
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
                prepared.append(
                    {
                        "blob": blob,
                        "titolo": titolo,
                        "autore": (item.get("creator") or "")[:200],
                        "licenza": (item.get("license") or "")[:32],
                        "source_id": str(item.get("id") or "")[:64],
                        "source_page_url": (item.get("foreign_landing_url") or url)[:500],
                        "search_query": query[:120],
                        "fname": f"{slugify(titolo)[:40] or 'img'}-{uuid.uuid4().hex[:8]}.jpg",
                    }
                )
            page += 1

    return prepared, errors, openverse_errors


def aggiorna_biblioteca_immagini(*, target: int = BIBLIOTECA_TARGET) -> dict[str, Any]:
    """
    Sostituisce la libreria con fino a `target` immagini CC da Openverse.
    Scarica prima in memoria: se Openverse non risponde, la libreria esistente resta intatta.
    """
    from personaggi.models import MinigiocoBibliotecaImmagine

    started = time.monotonic()
    count_prima = biblioteca_immagine_count()
    prepared, errors, openverse_errors = _raccogli_immagini_da_openverse(target=target)
    elapsed_ms = int((time.monotonic() - started) * 1000)

    if not prepared:
        err_msg = (
            "Impossibile scaricare immagini da Openverse. "
            "La libreria esistente non è stata modificata."
        )
        if openverse_errors:
            err_msg += f" Dettaglio: {openverse_errors[0]}"
        elif errors:
            err_msg += f" Dettaglio: {errors[0]}"
        return {
            "ok": False,
            "error": err_msg,
            "count": count_prima,
            "target": target,
            "errors_count": len(errors),
            "errors_sample": errors[:8],
            "openverse_errors": openverse_errors[:8],
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
                fonte="openverse",
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
