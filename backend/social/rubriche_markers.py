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

# Stili inline: la Wiki non usa il CSS di ArticoloCorpoConImmagini; devono bastare da soli.
_LAYOUT_STYLE = {
    RUBRICA_IMG_LAYOUT_FULL: (
        "margin:1rem 0;max-width:100%;clear:both;"
    ),
    RUBRICA_IMG_LAYOUT_WIDE: (
        "margin:1.25rem 0;width:100%;max-width:100%;clear:both;"
    ),
    RUBRICA_IMG_LAYOUT_FLOAT_LEFT: (
        "float:left;width:min(16rem,48%);max-width:48%;"
        "margin:0.25rem 1rem 0.75rem 0;"
    ),
    RUBRICA_IMG_LAYOUT_FLOAT_RIGHT: (
        "float:right;width:min(16rem,48%);max-width:48%;"
        "margin:0.25rem 0 0.75rem 1rem;"
    ),
    RUBRICA_IMG_LAYOUT_GRID_PAIR: (
        "display:block;width:100%;margin:0;box-sizing:border-box;"
    ),
}

_IMG_STYLE = "width:100%;height:auto;display:block;border-radius:0.5rem;"
_FIGCAPTION_STYLE = "margin-top:0.35rem;font-size:0.8em;font-style:italic;opacity:0.85;"
_GRID_PAIR_WRAP_STYLE = (
    "display:flex;flex-wrap:wrap;gap:0.75rem;margin:1rem 0;clear:both;"
)
_GRID_PAIR_CELL_STYLE = "flex:1 1 14rem;min-width:min(100%,14rem);margin:0;box-sizing:border-box;"


def extract_rubrica_img_ids(html: str) -> list[str]:
    """UUID (stringa) dei marker nell'ordine di comparsa, con duplicati se ripetuti."""
    if not html:
        return []
    return [m.group(1).lower() for m in RUBRICA_IMG_MARKER_RE.finditer(str(html))]


def _normalize_layout(layout: str | None) -> str:
    if layout in _LAYOUT_CLASS:
        return layout
    return RUBRICA_IMG_LAYOUT_FULL


def _figure_html(
    *,
    src: str,
    didascalia: str,
    alt: str,
    layout: str,
    extra_figure_style: str = "",
) -> str:
    layout = _normalize_layout(layout)
    css = _LAYOUT_CLASS[layout]
    base_style = _LAYOUT_STYLE[layout]
    style = f"{base_style}{extra_figure_style}"
    cap = ""
    if (didascalia or "").strip():
        cap = (
            f'<figcaption style="{_FIGCAPTION_STYLE}">'
            f"{escape(didascalia)}</figcaption>"
        )
    return (
        f'<figure class="rubrica-img {css}" style="{style}">'
        f'<img src="{escape(src)}" alt="{escape(alt or didascalia or "")}" '
        f'style="{_IMG_STYLE}">'
        f"{cap}</figure>"
    )


def figure_html_for_meta(meta: dict, *, titolo_fallback: str = "", extra_figure_style: str = "") -> str:
    """HTML figure da un dict meta (url/didascalia/layout)."""
    if not meta or not meta.get("url"):
        return ""
    return _figure_html(
        src=meta["url"],
        didascalia=meta.get("didascalia") or "",
        alt=meta.get("didascalia") or titolo_fallback,
        layout=meta.get("layout") or RUBRICA_IMG_LAYOUT_FULL,
        extra_figure_style=extra_figure_style,
    )


def expand_corpo_markers(corpo: str, immagini_by_id: dict, *, titolo_fallback: str = "") -> str:
    """
    Sostituisce i marker nel corpo con <figure> HTML (classi + style inline).
    ``immagini_by_id`` mappa uuid-str → dict con chiavi ``url``, ``didascalia``, ``layout``.
    Marker senza immagine corrispondente vengono rimossi.
    Due marker consecutivi con layout ``grid_pair`` vengono avvolti in un flex row.
    """
    if not corpo:
        return ""

    text = str(corpo)
    parts: list[str] = []
    last = 0
    matches = list(RUBRICA_IMG_MARKER_RE.finditer(text))
    i = 0
    while i < len(matches):
        match = matches[i]
        parts.append(text[last:match.start()])

        def _meta_for(m: re.Match):
            img_id = m.group(1).lower()
            return immagini_by_id.get(img_id) or immagini_by_id.get(m.group(1))

        meta = _meta_for(match)
        layout = _normalize_layout((meta or {}).get("layout"))
        next_match = matches[i + 1] if i + 1 < len(matches) else None
        next_meta = _meta_for(next_match) if next_match else None
        next_layout = _normalize_layout((next_meta or {}).get("layout")) if next_meta else None

        # Pairing: marker adiacenti (solo whitespace/HTML vuoto tra loro) entrambi grid_pair.
        between = text[match.end() : next_match.start()] if next_match else ""
        between_pulito = re.sub(r"<[^>]+>", "", between)
        between_vuoto = not between_pulito.strip()

        if (
            meta
            and next_meta
            and layout == RUBRICA_IMG_LAYOUT_GRID_PAIR
            and next_layout == RUBRICA_IMG_LAYOUT_GRID_PAIR
            and between_vuoto
        ):
            fig_a = figure_html_for_meta(
                meta, titolo_fallback=titolo_fallback, extra_figure_style=_GRID_PAIR_CELL_STYLE
            )
            fig_b = figure_html_for_meta(
                next_meta, titolo_fallback=titolo_fallback, extra_figure_style=_GRID_PAIR_CELL_STYLE
            )
            parts.append(
                f'<div class="rubrica-img-pair" style="{_GRID_PAIR_WRAP_STYLE}">'
                f"{fig_a}{fig_b}</div>"
            )
            last = next_match.end()
            i += 2
            continue

        parts.append(figure_html_for_meta(meta, titolo_fallback=titolo_fallback) if meta else "")
        last = match.end()
        i += 1

    parts.append(text[last:])
    expanded = "".join(parts)
    # Evita che i float "mangino" l'appendice / sezioni successive.
    return f'{expanded}<div style="clear:both"></div>'


def immagini_non_posizionate(corpo: str, immagini) -> list:
    """Immagini della galleria non referenziate da alcun marker (appendice)."""
    referenziate = {i.lower() for i in extract_rubrica_img_ids(corpo)}
    out = []
    for riga in immagini:
        pk = str(getattr(riga, "id", "") or "").lower()
        if pk and pk not in referenziate:
            out.append(riga)
    return out
