"""
Apertura negozi mercante: fasce orarie e requisiti.
"""
from __future__ import annotations

from datetime import datetime
from typing import Tuple

from django.utils import timezone

from personaggi.negozio_mercante_models import NEGOZIO_TIPO_CORPORATIVO
from personaggi.requisiti_accesso import (
    personaggio_soddisfa_requisiti,
    personaggio_soddisfa_requisiti_gruppo,
)


def _parse_hhmm(value: str):
    parts = (value or "").strip().split(":")
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except (TypeError, ValueError):
        return None


def _in_fascia_ricorrente(now: datetime, fascia: dict) -> bool:
    giorni = fascia.get("giorni") or []
    if giorni and now.weekday() not in giorni:
        return False
    start = _parse_hhmm(fascia.get("ora_inizio") or "")
    end = _parse_hhmm(fascia.get("ora_fine") or "")
    if not start or not end:
        return False
    cur = now.hour * 60 + now.minute
    s = start[0] * 60 + start[1]
    e = end[0] * 60 + end[1]
    if s <= e:
        return s <= cur < e
    return cur >= s or cur < e


def _in_fascia_episodica(now: datetime, fascia: dict) -> bool:
    from django.utils.dateparse import parse_datetime

    inizio = parse_datetime(fascia.get("inizio") or "")
    fine = parse_datetime(fascia.get("fine") or "")
    if not inizio or not fine:
        return False
    if timezone.is_naive(inizio):
        inizio = timezone.make_aware(inizio, timezone.get_current_timezone())
    if timezone.is_naive(fine):
        fine = timezone.make_aware(fine, timezone.get_current_timezone())
    return inizio <= now < fine


def negozio_e_aperto(negozio, personaggio, now=None) -> Tuple[bool, str]:
    """Valuta se il negozio è aperto per il personaggio (orari + requisiti)."""
    if not negozio.attivo:
        return False, "Negozio non attivo."

    now = now or timezone.now()

    if negozio.tipo_negozio == NEGOZIO_TIPO_CORPORATIVO:
        return personaggio_soddisfa_requisiti_gruppo(personaggio, negozio.regole_visibilita or {})

    regole = negozio.regole_apertura or {}
    modalita = (regole.get("modalita") or "sempre_aperto").strip().lower()

    if modalita == "fasce_orarie":
        fasce = regole.get("fasce") or []
        if not fasce:
            return False, "Negozio chiuso (nessuna fascia configurata)."
        for fascia in fasce:
            tipo = (fascia.get("tipo") or "ricorrente").strip().lower()
            if tipo == "episodica":
                if _in_fascia_episodica(now, fascia):
                    break
            else:
                if _in_fascia_ricorrente(now, fascia):
                    break
        else:
            return False, "Negozio chiuso: fuori orario."

    extra = regole.get("requisiti_extra") or []
    if extra:
        ok, msg = personaggio_soddisfa_requisiti(personaggio, extra)
        if not ok:
            return False, msg or "Requisiti di accesso non soddisfatti."

    return True, ""


def personaggio_puo_vedere_negozio_corporativo(negozio, personaggio) -> Tuple[bool, str]:
    if negozio.tipo_negozio != NEGOZIO_TIPO_CORPORATIVO:
        return False, "Non è un negozio corporativo."
    return negozio_e_aperto(negozio, personaggio)
