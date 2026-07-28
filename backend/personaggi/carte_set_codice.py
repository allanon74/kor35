"""
Codice carta nel formato `{SIGLA}-{NNN}` (es. KBE-002).

La SIGLA è il campo `EspansioneCarte.sigla` (es. KBE per «KOR: the beginning»).
Ordine stile Magic: per espansione si ordina per «colore» (energia KOR35)
poi alfabetico sul nome; i numeri progressivi seguono quell'ordine.
"""
from __future__ import annotations

import re
import unicodedata
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
SIGLA_MAX_LEN = 8
_CARD_NUM_SUFFIX_RE = re.compile(r"-(\d{3})$")
_NON_ALNUM_RE = re.compile(r"[^A-Za-z0-9]+")

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "at",
        "by",
        "da",
        "dei",
        "del",
        "della",
        "delle",
        "di",
        "e",
        "for",
        "from",
        "il",
        "in",
        "into",
        "la",
        "le",
        "lo",
        "of",
        "on",
        "or",
        "the",
        "to",
        "un",
        "una",
        "uno",
    }
)

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


def normalize_sigla(raw: str) -> str:
    """Normalizza sigla set: solo A-Z0-9, maiuscolo, max SIGLA_MAX_LEN."""
    s = unicodedata.normalize("NFD", str(raw or ""))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[^A-Za-z0-9]", "", s).upper()
    return s[:SIGLA_MAX_LEN]


def suggest_sigla_from_nome(nome: str, *, max_len: int = 3) -> str:
    """
    Suggerisce una sigla corta dal titolo set.

    Esempio: «KOR: the beginning» → KBE
    (iniziali parole significative; se < 3 lettere, continua dall'ultima parola).
    """
    max_len = max(2, min(int(max_len or 3), SIGLA_MAX_LEN))
    raw = unicodedata.normalize("NFD", str(nome or ""))
    raw = "".join(ch for ch in raw if unicodedata.category(ch) != "Mn")
    tokens = [t for t in _NON_ALNUM_RE.split(raw) if t]
    words = [t for t in tokens if t.lower() not in _STOPWORDS]
    if not words:
        words = tokens
    if not words:
        return "SET"

    if len(words) == 1:
        return normalize_sigla(words[0])[:max_len] or "SET"

    initials = "".join(w[0] for w in words if w)
    initials = normalize_sigla(initials)
    if len(initials) >= max_len:
        return initials[:max_len]

    # Completa dall'ultima parola (es. K+B → KBE da «beginning»).
    last = re.sub(r"[^A-Za-z0-9]", "", words[-1])
    extra = last[1:]
    while len(initials) < max_len and extra:
        initials += extra[0].upper()
        extra = extra[1:]
    if len(initials) < max_len and words:
        first = re.sub(r"[^A-Za-z0-9]", "", words[0])
        for ch in first[1:]:
            if len(initials) >= max_len:
                break
            initials += ch.upper()
    return normalize_sigla(initials)[:max_len] or "SET"


def set_code_prefix(espansione) -> str:
    """
    Prefisso codice carta: sigla espansione (KBE), altrimenti suggerita da nome/slug.
    """
    if espansione is None:
        return "SET"
    sigla = normalize_sigla(getattr(espansione, "sigla", None) or "")
    if sigla:
        return sigla
    nome = getattr(espansione, "nome", None) or ""
    if nome.strip():
        return suggest_sigla_from_nome(nome)
    slug = getattr(espansione, "slug", None) or ""
    if slug.strip():
        # slug corto già tipo "kbe" → KBE; altrimenti iniziali
        clean = normalize_sigla(slug.replace("-", ""))
        if 2 <= len(clean) <= SIGLA_MAX_LEN and "-" not in slug:
            return clean
        return suggest_sigla_from_nome(slug.replace("-", " "))
    return "SET"


def build_carta_codice(set_prefix: str, number: int) -> str:
    """Costruisce `{SIGLA}-{NNN}` rispettando max_length=40."""
    num = f"{int(number):03d}"
    prefix = normalize_sigla(set_prefix) or "SET"
    max_prefix_len = CARTA_CODICE_MAX_LEN - 1 - len(num)
    if max_prefix_len < 1:
        max_prefix_len = 1
    if len(prefix) > max_prefix_len:
        prefix = prefix[:max_prefix_len]
    return f"{prefix}-{num}"


def _card_number_from_codice(codice: str, set_prefix: str) -> int:
    prefix = normalize_sigla(set_prefix)
    raw = (codice or "").strip().upper()
    if not prefix or not raw.startswith(f"{prefix}-"):
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
    prefix = set_code_prefix(espansione)
    if not espansione:
        return 1, build_carta_codice(prefix, 1)

    qs = CartaCollezionabile.objects.filter(campagna=campagna, espansione=espansione)
    if exclude_carta_id:
        qs = qs.exclude(pk=exclude_carta_id)

    max_num = 0
    for row in qs.only("codice", "ordine_set"):
        max_num = max(
            max_num,
            int(row.ordine_set or 0),
            _card_number_from_codice(row.codice, prefix),
        )
    next_num = max_num + 1
    return next_num, build_carta_codice(prefix, next_num)


@transaction.atomic
def renumber_carte_in_espansione(campagna, espansione) -> dict:
    """
    Riassegna `ordine_set` e `codice` = `{SIGLA}-{NNN}` ordinando per
    energia (colore) e poi nome alfabetico.

    Due passate sui codici per rispettare unique (campagna, codice).
    """
    if not campagna or not espansione:
        return {"updated": 0, "codici": [], "sigla": ""}

    cards = list(
        CartaCollezionabile.objects.filter(campagna=campagna, espansione=espansione).select_for_update()
    )
    prefix = set_code_prefix(espansione)
    if not cards:
        return {"updated": 0, "codici": [], "sigla": prefix}

    ordered = sorted_carte_for_set_order(cards)
    now = timezone.now()

    # Passata 1: codici temporanei univoci (evita collisioni unique_together).
    for idx, card in enumerate(ordered):
        card.codice = f"__rn_{card.pk.hex[:16]}_{idx}"[:CARTA_CODICE_MAX_LEN]
        card.ordine_set = idx + 1
        card.updated_at = now
    CartaCollezionabile.objects.bulk_update(ordered, ["codice", "ordine_set", "updated_at"])

    # Passata 2: codici finali `{SIGLA}-{NNN}`.
    result_codici = []
    for idx, card in enumerate(ordered):
        number = idx + 1
        card.codice = build_carta_codice(prefix, number)
        card.ordine_set = number
        card.updated_at = now
        result_codici.append({"id": str(card.pk), "codice": card.codice, "ordine_set": number})
    CartaCollezionabile.objects.bulk_update(ordered, ["codice", "ordine_set", "updated_at"])

    return {"updated": len(ordered), "codici": result_codici, "sigla": prefix}
