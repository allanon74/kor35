"""
Applicazione runtime delle errata carta.
"""
from __future__ import annotations

from django.utils import timezone


def _errata_attiva(carta, *, when=None):
    when = when or timezone.now()
    try:
        return carta.errata.filter(attiva=True, effective_from__lte=when).order_by("-effective_from", "-updated_at").first()
    except Exception:
        return None


def gameplay_view(carta, *, when=None) -> dict:
    """Valori gameplay effettivi carta (base + eventuale errata attiva)."""
    err = _errata_attiva(carta, when=when)
    out = {
        "costo_gioco": carta.costo_gioco,
        "attacco": carta.attacco,
        "salute": carta.salute,
        "iniziativa": carta.iniziativa,
        "testo_gioco": carta.testo_gioco,
        "effect_scripts": carta.effect_scripts or [],
        "errata": None,
    }
    if not err:
        return out
    if err.costo_gioco_override is not None:
        out["costo_gioco"] = err.costo_gioco_override
    if err.attacco_override is not None:
        out["attacco"] = err.attacco_override
    if err.salute_override is not None:
        out["salute"] = err.salute_override
    if err.iniziativa_override is not None:
        out["iniziativa"] = err.iniziativa_override
    if (err.testo_gioco_override or "").strip():
        out["testo_gioco"] = err.testo_gioco_override
    if err.effect_scripts_override:
        out["effect_scripts"] = err.effect_scripts_override
    out["errata"] = {
        "id": str(err.id),
        "effective_from": err.effective_from.isoformat(),
        "titolo": err.titolo,
        "descrizione": err.descrizione,
    }
    return out
