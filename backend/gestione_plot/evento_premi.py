"""
Accredito una tantum di PC e crediti d'evento ai PG iscritti, al login in sessione
durante un giorno d'evento (finestra GiornoEvento; se non ci sono giorni, usa data_inizio/data_fine evento).
"""

from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from personaggi.models import Personaggio

from .models import Evento, EventoPremioPersonaggio

logger = logging.getLogger(__name__)


def _evento_in_finestra_presenza(evento: Evento, now) -> bool:
    giorni = list(evento.giorni.all())
    if giorni:
        return any(g.data_ora_inizio <= now <= g.data_ora_fine for g in giorni)
    return evento.data_inizio <= now <= evento.data_fine


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
                    _row, created = EventoPremioPersonaggio.objects.get_or_create(
                        evento=ev,
                        personaggio=pg,
                    )
                    if not created:
                        gia_presenti += 1
                        continue
                    desc = f"Presenza evento «{ev.titolo}»"[:198]
                    n_pc = int(ev.pc_guadagnati or 0)
                    if n_pc > 0:
                        pg.modifica_pc(n_pc, desc)
                    cred = ev.crediti_guadagnati
                    if cred is not None and Decimal(cred) > 0:
                        pg.modifica_crediti(Decimal(cred), desc)
                    premi_applicati += 1
            except Exception:
                logger.exception(
                    "Errore applicazione premio evento ev=%s pg=%s",
                    getattr(ev, "id", None),
                    getattr(pg, "id", None),
                )

    return {"premi_applicati": premi_applicati, "gia_presenti": gia_presenti}
