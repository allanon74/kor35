"""
Codice carta nel formato `{slug_espansione}-{NNN}` (es. sette-elegie-001).

Ordine stile Magic: per espansione si ordina per «colore» (energia KOR35)
poi alfabetico sul nome; i numeri progressivi seguono quell'ordine.
"""
from __future__ import annotations

import re
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from personaggi.carte_collezionabili_models import (
    CARTA_ENERGIA_ARCANA,
    CARTA_ENERGIA_INNATA,
    CARTA_ENERGIA_MAGICA,
    CARTA_ENERGIA_MARZIALE,
    CARTA_ENERGIA_PSIONICA,
    CARTA_ENERGIA_SACRA,
    CARTA_ENERGIA_TECNOLOGICA,
    CartaCollezionabile,
)

CARTA_CODICE_MAX_LEN = 40
_CARD_NUM_SUFFIX_RE = re.compile(r"-(\d{3})$")

# Aure KOR35: naturali → soprannaturali (come CARTA_ENERGIA_CHOICES / Card Studio).
ENERGIA_RANK = {
    CARTA_ENERGIA_MARZIALE: 10,
    CARTA_ENERGIA_TECNOLOGICA: 20,
    CARTA_ENERGIA_INNATA: 30,
    CARTA_ENERGIA_MAGICA: 40,
    CARTA_ENERGIA_SACRA: 50,
    CARTA_ENERGIA_PSIONICA: 60,
    CARTA_ENERGIA_ARCANA: 70,
}


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


def energia_rank(energia: str) -> int:
    return ENERGIA_RANK.get((energia or "").strip().upper(), 999)


def sort_key_carta_set_order(card) -> tuple:
    """Chiave ordinamento: colore (energia) → nome → codice → pk."""
    nome = (getattr(card, "nome", None) or "").strip().casefold()
    codice = (getattr(card, "codice", None) or "").strip().casefold()
    pk = str(getattr(card, "pk", "") or "")
    return (energia_rank(getattr(card, "energia", None)), nome, codice, pk)


def sorted_carte_for_set_order(cards: Iterable) -> list:
    return sorted(list(cards or []), key=sort_key_carta_set_order)


def suggest_carta_codice_for_espansione(
    campagna,
    espansione,
    *,
    exclude_carta_id=None,
) -> tuple[int, str]:
    """
    Restituisce (ordine_set, codice) provvisorio = max+1 nell'espansione.

    Preferire `renumber_carte_in_espansione` dopo create/update per allineare
    colore → alfabetico.
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


@transaction.atomic
def renumber_carte_in_espansione(campagna, espansione) -> dict:
    """
    Riassegna `ordine_set` e `codice` = `{slug}-{NNN}` ordinando per
    energia (colore) e poi nome alfabetico.

    Due passate sui codici per rispettare unique (campagna, codice).
    """
    if not campagna or not espansione:
        return {"updated": 0, "codici": []}

    cards = list(
        CartaCollezionabile.objects.filter(campagna=campagna, espansione=espansione).select_for_update()
    )
    if not cards:
        return {"updated": 0, "codici": []}

    ordered = sorted_carte_for_set_order(cards)
    set_slug = espansione.slug
    now = timezone.now()

    # Passata 1: codici temporanei univoci (evita collisioni unique_together).
    for idx, card in enumerate(ordered):
        card.codice = f"__rn_{card.pk.hex[:16]}_{idx}"[:CARTA_CODICE_MAX_LEN]
        card.ordine_set = idx + 1
        card.updated_at = now
    CartaCollezionabile.objects.bulk_update(ordered, ["codice", "ordine_set", "updated_at"])

    # Passata 2: codici finali `{slug}-{NNN}`.
    result_codici = []
    for idx, card in enumerate(ordered):
        number = idx + 1
        card.codice = build_carta_codice(set_slug, number)
        card.ordine_set = number
        card.updated_at = now
        result_codici.append({"id": str(card.pk), "codice": card.codice, "ordine_set": number})
    CartaCollezionabile.objects.bulk_update(ordered, ["codice", "ordine_set", "updated_at"])

    return {"updated": len(ordered), "codici": result_codici}
