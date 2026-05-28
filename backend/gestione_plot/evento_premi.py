"""
Accredito una tantum di PC e crediti d'evento ai PG iscritti, al login in sessione
durante un giorno d'evento (finestra GiornoEvento; se non ci sono giorni, usa data_inizio/data_fine evento).
"""

from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from personaggi.models import Personaggio, PersonaggioCarrieraMembership

from .models import Evento, EventoPremioPersonaggio

logger = logging.getLogger(__name__)


def _evento_in_finestra_presenza(evento: Evento, now) -> bool:
    if getattr(evento, "started_at", None) is not None and getattr(evento, "ended_at", None) is None:
        return True
    giorni = list(evento.giorni.all())
    if giorni:
        return any(g.data_ora_inizio <= now <= g.data_ora_fine for g in giorni)
    return evento.data_inizio <= now <= evento.data_fine


def _membership_attive_evento(personaggio: Personaggio, ts):
    return PersonaggioCarrieraMembership.objects.filter(
        personaggio=personaggio,
        data_da__lte=ts,
    ).filter(
        Q(data_a__isnull=True) | Q(data_a__gt=ts),
    )


def calcola_crediti_premio_evento(evento: Evento, personaggio: Personaggio, ts=None) -> Decimal:
    when = ts or timezone.now()
    totale = Decimal(evento.crediti_base_inizio_evento or 0)
    for membership in _membership_attive_evento(personaggio, when).select_related("carriera", "carica"):
        totale += Decimal(getattr(membership.carriera, "bonus_crediti_evento", 0) or 0)
        carica = getattr(membership, "carica", None)
        if carica:
            totale += Decimal(getattr(carica, "bonus_crediti_evento", 0) or 0)
    return totale


def dettaglio_crediti_premio_evento(evento: Evento, personaggio: Personaggio, ts=None) -> dict:
    when = ts or timezone.now()
    base_evento = Decimal(evento.crediti_base_inizio_evento or 0)
    righe = []
    totale_bonus = Decimal("0")
    for membership in _membership_attive_evento(personaggio, when).select_related("carriera", "carica"):
        carriera_bonus = Decimal(getattr(membership.carriera, "bonus_crediti_evento", 0) or 0)
        carica_bonus = Decimal(getattr(membership.carica, "bonus_crediti_evento", 0) or 0) if membership.carica_id else Decimal("0")
        totale_riga = carriera_bonus + carica_bonus
        totale_bonus += totale_riga
        righe.append(
            {
                "membership_id": membership.id,
                "tipo_carriera": getattr(membership.tipo_carriera, "codice", ""),
                "carriera_id": membership.carriera_id,
                "carriera_nome": getattr(membership.carriera, "nome", ""),
                "carriera_bonus": str(carriera_bonus),
                "carica_id": membership.carica_id,
                "carica_nome": getattr(membership.carica, "nome", "") if membership.carica_id else "",
                "carica_bonus": str(carica_bonus),
                "totale_riga": str(totale_riga),
            }
        )
    totale = base_evento + totale_bonus
    return {
        "base_evento": str(base_evento),
        "bonus_totale": str(totale_bonus),
        "totale_crediti": str(totale),
        "righe_membership": righe,
    }


def applica_premio_presenza_personaggio(evento: Evento, pg: Personaggio, when=None) -> bool:
    ts = when or timezone.now()
    with transaction.atomic():
        _row, created = EventoPremioPersonaggio.objects.get_or_create(
            evento=evento,
            personaggio=pg,
        )
        if not created:
            return False
        desc = f"Inizio evento «{evento.titolo}»"[:198]
        n_pc = int(evento.pc_guadagnati or 0)
        if n_pc > 0:
            pg.modifica_pc(n_pc, desc)
        cred = calcola_crediti_premio_evento(evento, pg, ts=ts)
        if cred > 0:
            pg.modifica_crediti(cred, desc)
        return True


def report_ricompense_evento(evento: Evento, ts=None) -> dict:
    when = ts or timezone.now()
    rows = []
    partecipanti = evento.partecipanti.all().select_related("tipologia")
    premi_ids = set(
        EventoPremioPersonaggio.objects.filter(evento=evento).values_list("personaggio_id", flat=True)
    )
    for pg in partecipanti:
        dettagli_crediti = dettaglio_crediti_premio_evento(evento, pg, ts=when)
        rows.append(
            {
                "personaggio_id": pg.id,
                "personaggio_nome": pg.nome,
                "premio_gia_assegnato": pg.id in premi_ids,
                "pc_evento": int(evento.pc_guadagnati or 0),
                **dettagli_crediti,
            }
        )
    return {
        "evento_id": evento.id,
        "evento_titolo": evento.titolo,
        "started_at": evento.started_at,
        "ended_at": evento.ended_at,
        "partecipanti_count": len(rows),
        "ricompense": rows,
    }


def applica_premi_presenza_eventi(user):
    """
    Per ogni personaggio del proprietario iscritto a un evento la cui finestra di presenza include ``now``,
    crea (se assente) il record premio e accredita PC/crediti dell'evento.

    Ritorna un dict con conteggi diagnostici (idempotente).
    """
    if not user or not getattr(user, "is_authenticated", False):
        return {"premi_applicati": 0, "gia_presenti": 0}

    now = timezone.now()
    premi_applicati = 0
    gia_presenti = 0

    pgs = Personaggio.objects.filter(proprietario=user).prefetch_related(
        "eventi_partecipati",
        "eventi_partecipati__giorni",
    )

    for pg in pgs:
        for ev in pg.eventi_partecipati.all():
            if not _evento_in_finestra_presenza(ev, now):
                continue
            try:
                with transaction.atomic():
                    created = applica_premio_presenza_personaggio(ev, pg, when=now)
                    if not created:
                        gia_presenti += 1
                        continue
                    premi_applicati += 1
            except Exception:
                logger.exception(
                    "Errore applicazione premio evento ev=%s pg=%s",
                    getattr(ev, "id", None),
                    getattr(pg, "id", None),
                )

    return {"premi_applicati": premi_applicati, "gia_presenti": gia_presenti}
