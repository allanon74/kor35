"""
Preset e merge opzioni di stile per i manuali PDF wiki.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from gestione_plot.models import ManualePdf

# Chiavi ammesse in ManualePdf.stile (override sul preset)
STYLE_KEYS = frozenset({
    "formato",
    "margini",
    "font_family",
    "font_size_pt",
    "line_height",
    "immagini",
    "widget_modalita",
    "capitolo_break",
    "indice",
    "indice_profondita",
    "colore",
    "copertina",
    "colophon",
})

PRESET_CHOICES = (
    ("giocatore", "Giocatore (A5, compatto)"),
    ("master", "Master (A4, completo)"),
    ("reference", "Reference tascabile (A5, testo)"),
    ("stampa_economica", "Stampa economica (A4, B/N)"),
    ("personalizzato", "Personalizzato (usa override JSON)"),
)

MARGINI_MM = {
    "stretto": (12, 11, 12, 11),
    "normale": (18, 16, 18, 16),
    "ampio": (22, 20, 22, 20),
}

FONT_STACK = {
    "serif": '"DejaVu Serif", Georgia, serif',
    "sans": '"DejaVu Sans", Helvetica, Arial, sans-serif',
}

MANUALE_PDF_STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "giocatore": {
        "formato": "A5",
        "margini": "normale",
        "font_family": "serif",
        "font_size_pt": 10,
        "line_height": 1.45,
        "immagini": "si",
        "widget_modalita": "compatto",
        "capitolo_break": "auto",
        "indice": True,
        "indice_profondita": 2,
        "colore": "accento",
        "copertina": "immagine",
        "colophon": "breve",
    },
    "master": {
        "formato": "A4",
        "margini": "normale",
        "font_family": "serif",
        "font_size_pt": 11,
        "line_height": 1.5,
        "immagini": "si",
        "widget_modalita": "completo",
        "capitolo_break": "auto",
        "indice": True,
        "indice_profondita": 3,
        "colore": "accento",
        "copertina": "immagine",
        "colophon": "dettagliato",
    },
    "reference": {
        "formato": "A5",
        "margini": "stretto",
        "font_family": "sans",
        "font_size_pt": 9,
        "line_height": 1.35,
        "immagini": "no",
        "widget_modalita": "solo_testo",
        "capitolo_break": "auto",
        "indice": True,
        "indice_profondita": 2,
        "colore": "bn",
        "copertina": "testo",
        "colophon": "off",
    },
    "stampa_economica": {
        "formato": "A4",
        "margini": "stretto",
        "font_family": "serif",
        "font_size_pt": 9,
        "line_height": 1.4,
        "immagini": "inline_piccole",
        "widget_modalita": "compatto",
        "capitolo_break": "auto",
        "indice": True,
        "indice_profondita": 2,
        "colore": "bn",
        "copertina": "minimal",
        "colophon": "breve",
    },
    "personalizzato": {
        "formato": "A4",
        "margini": "normale",
        "font_family": "serif",
        "font_size_pt": 10,
        "line_height": 1.5,
        "immagini": "si",
        "widget_modalita": "completo",
        "capitolo_break": "auto",
        "indice": True,
        "indice_profondita": 2,
        "colore": "accento",
        "copertina": "immagine",
        "colophon": "breve",
    },
}

DEFAULT_PRESET_BY_SLUG = {
    "completo": "master",
    "master": "master",
    "giocatore": "giocatore",
}


def default_preset_for_manuale(manuale: ManualePdf) -> str:
    return DEFAULT_PRESET_BY_SLUG.get(manuale.slug, "giocatore")


def merge_manuale_stile(preset_key: str, overrides: dict | None) -> dict[str, Any]:
    base = deepcopy(MANUALE_PDF_STYLE_PRESETS.get(preset_key, MANUALE_PDF_STYLE_PRESETS["giocatore"]))
    if overrides:
        for key, value in overrides.items():
            if key in STYLE_KEYS and value is not None and value != "":
                base[key] = value
    return enrich_stile_for_template(base)


def resolve_manuale_stile(manuale: ManualePdf) -> dict[str, Any]:
    preset = (manuale.stile_preset or "").strip() or default_preset_for_manuale(manuale)
    overrides = manuale.stile if isinstance(manuale.stile, dict) else {}
    return merge_manuale_stile(preset, overrides)


def enrich_stile_for_template(stile: dict[str, Any]) -> dict[str, Any]:
    """Aggiunge valori derivati per template WeasyPrint."""
    out = deepcopy(stile)
    margini_key = out.get("margini") or "normale"
    top, right, bottom, left = MARGINI_MM.get(margini_key, MARGINI_MM["normale"])
    out["margin_top_mm"] = top
    out["margin_right_mm"] = right
    out["margin_bottom_mm"] = bottom
    out["margin_left_mm"] = left
    out["font_stack"] = FONT_STACK.get(out.get("font_family") or "serif", FONT_STACK["serif"])
    out["font_size_pt"] = float(out.get("font_size_pt") or 10)
    out["line_height"] = float(out.get("line_height") or 1.5)
    out["indice_profondita"] = int(out.get("indice_profondita") or 2)
    out["indice"] = bool(out.get("indice", True))
    colore = out.get("colore") or "accento"
    if colore == "bn":
        out["accent_color"] = "#2a2a2a"
        out["accent_muted"] = "#555555"
    else:
        out["accent_color"] = "#5a1010"
        out["accent_muted"] = "#7a7a7a"
    immagini = out.get("immagini") or "si"
    out["hide_images"] = immagini == "no"
    out["images_small"] = immagini == "inline_piccole"
    out["widget_modalita"] = out.get("widget_modalita") or "completo"
    out["show_colophon"] = (out.get("colophon") or "breve") != "off"
    out["colophon_detailed"] = out.get("colophon") == "dettagliato"
    copertina = out.get("copertina") or "immagine"
    out["cover_minimal"] = copertina == "minimal"
    out["cover_text_only"] = copertina == "testo"
    out["capitolo_break_auto"] = (out.get("capitolo_break") or "auto") == "auto"
    return out
