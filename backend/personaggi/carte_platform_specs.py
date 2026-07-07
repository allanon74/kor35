"""
Costanti e helper per contratti JSON Card Studio / Card Arena.
"""
from __future__ import annotations

from typing import Any

PLAYABLE_CARD_SPEC_VERSION = "1"
STUDIO_CARD_SPEC_VERSION = "1"
STUDIO_SET_SPEC_VERSION = "1"
STUDIO_LAYOUT_SPEC_VERSION = "1"
ARENA_DECK_SPEC_VERSION = "1"
DUEL_STATE_SPEC_VERSION = "1"
ACTION_PROTOCOL_VERSION = "1"


def empty_playable_card_spec() -> dict[str, Any]:
    """Struttura minima arena_playable_spec su CartaCollezionabile."""
    return {
        "version": PLAYABLE_CARD_SPEC_VERSION,
        "source": "kor35",
        "gameplay": {},
        "keywords": [],
        "effects": [],
    }


def empty_studio_card_spec() -> dict[str, Any]:
    return {
        "version": STUDIO_CARD_SPEC_VERSION,
        "layers": [],
        "print": {},
    }


def empty_studio_set_spec() -> dict[str, Any]:
    return {
        "version": STUDIO_SET_SPEC_VERSION,
        "symbol": None,
        "watermark": None,
    }


def empty_arena_deck_spec() -> dict[str, Any]:
    return {
        "version": ARENA_DECK_SPEC_VERSION,
        "formato": "standard_15",
        "sideboard": [],
    }


def build_playable_spec_from_carta(carta) -> dict[str, Any]:
    """
    Deriva playable_card_spec_v1 dai campi gameplay KOR35 esistenti.
    Usato da job export e da Card Arena in lettura diretta DB.
    """
    spec = empty_playable_card_spec()
    spec["gameplay"] = {
        "codice": carta.codice,
        "nome": carta.nome,
        "tipo": carta.tipo,
        "energia": carta.energia,
        "rarita": carta.rarita,
        "costo_gioco": carta.costo_gioco,
        "attacco": carta.attacco,
        "salute": carta.salute,
        "iniziativa": carta.iniziativa,
        "testo_gioco": carta.testo_gioco,
        "legale_duello": carta.legale_duello,
        "bandita": carta.bandita,
        "duplicabile": carta.duplicabile,
        "layout_versione": carta.layout_versione,
    }
    spec["effects"] = list(carta.effect_scripts or [])
    if carta.espansione_id:
        spec["espansione_slug"] = carta.espansione.slug
    return spec
