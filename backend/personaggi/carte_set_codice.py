"""
Codice carta nel formato `{slug_espansione}-{NNN}` (es. sette-elegie-001).

Il numero progressivo è per espansione; il prefisso è il codice set (slug EspansioneCarte).
"""
from __future__ import annotations

import re

from personaggi.carte_collezionabili_models import CartaCollezionabile

CARTA_CODICE_MAX_LEN = 40
_CARD_NUM_SUFFIX_RE = re.compile(r"-(\d{3})$")


def normalize_set_slug(slug: str) -> str:
    return (slug or "").strip().lower() or "set"


def build_carta_codice(set_slug: str, number: int) -> str:
    """Costruisce codice rispettando max_length=40 su CartaCollezionabile.codice."""
    num = f"{int(number):03d}"
    slug = normalize_set_slug(set_slug)
    max_slug_len = CARTA_CODICE_MAX_LEN - 1 - len(num)
    if max_slug_len < 1:
        max_slug_len = 1
    if len(slug) > max_slug_len:
        slug = slug[:max_slug_len].rstrip("-")
    return f"{slug}-{num}"


def _card_number_from_codice(codice: str, set_slug: str) -> int:
    slug = normalize_set_slug(set_slug)
    raw = (codice or "").strip().lower()
    if not raw.startswith(f"{slug}-"):
        return 0
    m = _CARD_NUM_SUFFIX_RE.search(raw)
    return int(m.group(1)) if m else 0


def suggest_carta_codice_for_espansione(
    campagna,
    espansione,
    *,
    exclude_carta_id=None,
) -> tuple[int, str]:
    """
    Restituisce (ordine_set, codice) per la prossima carta nell'espansione.
    """
    if not espansione or not getattr(espansione, "slug", None):
        return 1, build_carta_codice("set", 1)

    set_slug = espansione.slug
    qs = CartaCollezionabile.objects.filter(campagna=campagna, espansione=espansione)
    if exclude_carta_id:
        qs = qs.exclude(pk=exclude_carta_id)

    max_num = 0
    for row in qs.only("codice", "ordine_set"):
        max_num = max(
            max_num,
            int(row.ordine_set or 0),
            _card_number_from_codice(row.codice, set_slug),
        )
    next_num = max_num + 1
    return next_num, build_carta_codice(set_slug, next_num)
