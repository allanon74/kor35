"""
Regole di disponibilità e legalità carte/espansioni.
"""
from __future__ import annotations

from django.utils import timezone


def espansione_in_vendita(espansione, now=None) -> bool:
    if not espansione:
        return True
    if not getattr(espansione, "attiva", True):
        return False
    if not getattr(espansione, "in_vendita", True):
        return False
    now = now or timezone.now()
    vendita_dal = getattr(espansione, "vendita_dal", None)
    vendita_al = getattr(espansione, "vendita_al", None)
    if vendita_dal and now < vendita_dal:
        return False
    if vendita_al and now > vendita_al:
        return False
    return True


def carta_disponibile_per_giocatori(carta) -> bool:
    if not getattr(carta, "attiva", True):
        return False
    esp = getattr(carta, "espansione", None)
    if esp and not getattr(esp, "attiva", True):
        return False
    return True


def carta_legale_duello(carta) -> bool:
    if not carta_disponibile_per_giocatori(carta):
        return False
    if getattr(carta, "bandita", False):
        return False
    if not getattr(carta, "legale_duello", True):
        return False
    esp = getattr(carta, "espansione", None)
    if esp and not getattr(esp, "legale_duello", True):
        return False
    return True


def motivo_illegalita_duello(carta) -> str:
    if not getattr(carta, "attiva", True):
        return "Carta non attiva."
    esp = getattr(carta, "espansione", None)
    if esp and not getattr(esp, "attiva", True):
        return f"Espansione «{esp.nome}» disattivata."
    if getattr(carta, "bandita", False):
        reason = (getattr(carta, "ban_reason", "") or "").strip()
        return f"Carta bandita. {reason}".strip()
    if not getattr(carta, "legale_duello", True):
        return "Carta non più legale nei duelli."
    if esp and not getattr(esp, "legale_duello", True):
        return f"Espansione «{esp.nome}» non legale nei duelli."
    return "Carta non legale."
