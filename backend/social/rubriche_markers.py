"""Marker [[rubrica-img:<uuid>]] nel corpo articoli rubrica: parse e espansione HTML."""

from __future__ import annotations

import re
from html import escape

from .models_rubriche import (
    RUBRICA_IMG_LAYOUT_FLOAT_LEFT,
    RUBRICA_IMG_LAYOUT_FLOAT_RIGHT,
    RUBRICA_IMG_LAYOUT_FULL,
    RUBRICA_IMG_LAYOUT_GRID_PAIR,
    RUBRICA_IMG_LAYOUT_WIDE,
    RUBRICA_IMG_MARKER_RE,
)

_LAYOUT_CLASS = {
    RUBRICA_IMG_LAYOUT_FULL: "rubrica-img--full",
    RUBRICA_IMG_LAYOUT_WIDE: "rubrica-img--wide",
    RUBRICA_IMG_LAYOUT_FLOAT_LEFT: "rubrica-img--float-left",
    RUBRICA_IMG_LAYOUT_FLOAT_RIGHT: "rubrica-img--float-right",
    RUBRICA_IMG_LAYOUT_GRID_PAIR: "rubrica-img--grid-pair",
}


def extract_rubrica_img_ids(html: str) -> list[str]:
    """UUID (stringa) dei marker nell'ordine di comparsa, con duplicati se ripetuti."""
    if not html:
        return []
    return [m.group(1).lower() for m in RUBRICA_IMG_MARKER_RE.finditer(str(html))]


def _figure_html(*, src: str, didascalia: str, alt: str, layout: str) -> str:
    css = _LAYOUT_CLASS.get(layout or RUBRICA_IMG_LAYOUT_FULL, _LAYOUT_CLASS[RUBRICA_IMG_LAYOUT_FULL])
    cap = f"<figcaption>{escape(didascalia)}</figcaption>" if (didascalia or "").strip() else ""
    return (
        f'<figure class="rubrica-img {css}">'
        f'<img src="{escape(src)}" alt="{escape(alt or didascalia or "")}">'
        f"{cap}</figure>"
    )


def expand_corpo_markers(corpo: str, immagini_by_id: dict, *, titolo_fallback: str = "") -> str:
    """
    Sostituisce i marker nel corpo con <figure> HTML.
    ``immagini_by_id`` mappa uuid-str → dict con chiavi ``url``, ``didascalia``, ``layout``.
    Marker senza immagine corrispondente vengono rimossi.
    """

    def _replace(match: re.Match) -> str:
        img_id = match.group(1).lower()
        meta = immagini_by_id.get(img_id) or immagini_by_id.get(match.group(1))
        if not meta or not meta.get("url"):
            return ""
        return _figure_html(
            src=meta["url"],
            didascalia=meta.get("didascalia") or "",
            alt=meta.get("didascalia") or titolo_fallback,
            layout=meta.get("layout") or RUBRICA_IMG_LAYOUT_FULL,
        )

    if not corpo:
        return ""
    return RUBRICA_IMG_MARKER_RE.sub(_replace, str(corpo))


def immagini_non_posizionate(corpo: str, immagini) -> list:
    """Immagini della galleria non referenziate da alcun marker (appendice)."""
    referenziate = {i.lower() for i in extract_rubrica_img_ids(corpo)}
    out = []
    for riga in immagini:
        pk = str(getattr(riga, "id", "") or "").lower()
        if pk and pk not in referenziate:
            out.append(riga)
    return out
