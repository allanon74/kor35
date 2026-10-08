"""
Accredito di PC, crediti e prestigio d'evento ai PG iscritti.

L'accredito è una tantum per avvio ufficiale (``Evento.started_at``), non per
sempre sullo stesso record evento. Un evento riusato (prova estiva, poi evento
vero) non deve risultare «consegnato» solo perché esiste una riga premio vecchia.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from personaggi.models import (
    CreditoMovimento,
    Personaggio,
    PersonaggioCarrieraMembership,
    PersonaggioLog,
    PuntiCaratteristicaMovimento,
)

from .models import Evento, EventoPremioPersonaggio

logger = logging.getLogger(__name__)


def descrizione_premio_evento(evento: Evento) -> str:
    return f"Inizio evento «{evento.titolo}»"[:198]


def _accredito_avvio_gia_scritto(evento: Evento, personaggio: Personaggio) -> bool:
    """
    True se il ledger di questo avvio ha già la riga premio.

    Copre il caso in cui l'accredito è stato riparato a mano prima che la riga
    ``EventoPremioPersonaggio.avvio_at`` indicasse l'avvio corrente: senza questo
    controllo un deploy successivo pagherebbe due volte.
    """
    started = getattr(evento, "started_at", None)
    if started is None:
        return False
    desc = descrizione_premio_evento(evento)
    if PuntiCaratteristicaMovimento.objects.filter(
        personaggio=personaggio,
        descrizione=desc,
        data__gte=started,
    ).exists():
        return True
    if CreditoMovimento.objects.filter(
        personaggio=personaggio,
        descrizione=desc,
        data__gte=started,
    ).exists():
        return True
    return PersonaggioLog.objects.filter(
        personaggio=personaggio,
        data__gte=started,
        testo_log__contains=desc,
    ).exists()


def premio_copre_avvio_corrente(row, evento: Evento, personaggio: Personaggio | None = None) -> bool:
    """True se questo PG ha già ricevuto PC/crediti/prestigio dell'avvio corrente."""
    started = getattr(evento, "started_at", None)
    if row is not None:
        if started is None:
            return True
        avvio = getattr(row, "avvio_at", None)
        if avvio is not None and avvio == started:
            return True
        if avvio is None and row.created_at >= started:
            return True
    pg = personaggio if personaggio is not None else getattr(row, "personaggio", None)
    if pg is not None and _accredito_avvio_gia_scritto(evento, pg):
        return True
    return False


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
            totale += Decimal(getattr(carica, "bonus_stipendio_evento", 0) or 0)
            totale += Decimal(getattr(carica, "bonus_crediti_evento", 0) or 0)
    return totale


def dettaglio_crediti_premio_evento(evento: Evento, personaggio: Personaggio, ts=None) -> dict:
    when = ts or timezone.now()
    base_evento = Decimal(evento.crediti_base_inizio_evento or 0)
    righe = []
    totale_bonus = Decimal("0")
    for membership in _membership_attive_evento(personaggio, when).select_related("carriera", "carica"):
        carriera_bonus = Decimal(getattr(membership.carriera, "bonus_crediti_evento", 0) or 0)
        carica_stipendio = (
            Decimal(getattr(membership.carica, "bonus_stipendio_evento", 0) or 0)
            if membership.carica_id
            else Decimal("0")
        )
        carica_crediti = (
            Decimal(getattr(membership.carica, "bonus_crediti_evento", 0) or 0)
            if membership.carica_id
            else Decimal("0")
        )
        carica_bonus = carica_stipendio + carica_crediti
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
                "carica_bonus_stipendio": str(carica_stipendio),
                "carica_bonus_crediti": str(carica_crediti),
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


def _accredita_importo_premio(evento: Evento, pg: Personaggio, ts) -> None:
    desc = descrizione_premio_evento(evento)
    n_pc = int(evento.pc_guadagnati or 0)
    if n_pc > 0:
        pg.modifica_pc(n_pc, desc)
    cred = calcola_crediti_premio_evento(evento, pg, ts=ts)
    if cred > 0:
        from personaggi.economia_crediti import CONTO_CORRENTE

        pg.modifica_crediti(cred, desc, conto=CONTO_CORRENTE, evento=evento)
    n_pr = int(getattr(evento, "prestigio_base_inizio_evento", 0) or 0)
    if n_pr != 0:
        pg.modifica_prestigio(n_pr, desc)


def _segna_avvio_premio(row: EventoPremioPersonaggio, started) -> None:
    row.avvio_at = started
    row.save(update_fields=["avvio_at", "updated_at"])


def applica_premio_presenza_personaggio(evento: Evento, pg: Personaggio, when=None) -> bool:
    """
    Accredita il premio dell'avvio corrente.

    Ritorna True solo se questo giro ha scritto PC/crediti/prestigio.
    Una riga premio di un avvio precedente non blocca il nuovo avvio.
    """
    ts = when or timezone.now()
    started = getattr(evento, "started_at", None)
    with transaction.atomic():
        row = (
            EventoPremioPersonaggio.objects.select_for_update()
            .filter(evento=evento, personaggio=pg)
            .first()
        )
        if premio_copre_avvio_corrente(row, evento, pg):
            return False
        if row is None:
            try:
                with transaction.atomic():
                    row = EventoPremioPersonaggio.objects.create(
                        evento=evento,
                        personaggio=pg,
                        avvio_at=started,
                    )
            except IntegrityError:
                row = (
                    EventoPremioPersonaggio.objects.select_for_update()
                    .get(evento=evento, personaggio=pg)
                )
                if premio_copre_avvio_corrente(row, evento, pg):
                    return False
                _segna_avvio_premio(row, started)
        else:
            _segna_avvio_premio(row, started)
        _accredita_importo_premio(evento, pg, ts)
        return True


def partecipanti_premio_gia_assegnato(evento: Evento) -> list[Personaggio]:
    """Iscritti che hanno già incassato il premio di questo evento (anche a un avvio precedente).

    Serve all'avvio evento: lo staff decide se riattribuire il bonus o saltarli.
    """
    premiati = set(
        EventoPremioPersonaggio.objects.filter(evento=evento).values_list(
            "personaggio_id", flat=True
        )
    )
    if not premiati:
        return []
    return [pg for pg in evento.partecipanti.all().order_by("nome") if pg.id in premiati]


def salta_premio_presenza_personaggio(evento: Evento, pg: Personaggio) -> bool:
    """Marca il premio come già coperto dall'avvio corrente senza accreditare nulla.

    Usato quando lo staff avvia l'evento scegliendo di non riattribuire il bonus:
    così nemmeno «Accredita mancanti» lo paga di nuovo.
    """
    started = getattr(evento, "started_at", None)
    with transaction.atomic():
        row = (
            EventoPremioPersonaggio.objects.select_for_update()
            .filter(evento=evento, personaggio=pg)
            .first()
        )
        if row is None:
            return False
        if premio_copre_avvio_corrente(row, evento, pg):
            return False
        _segna_avvio_premio(row, started)
        return True


def report_ricompense_evento(evento: Evento, ts=None) -> dict:
    when = ts or evento.started_at or timezone.now()
    rows = []
    partecipanti = evento.partecipanti.all().select_related("tipologia")
    premi = {
        row.personaggio_id: row
        for row in EventoPremioPersonaggio.objects.filter(evento=evento)
    }
    for pg in partecipanti:
        row = premi.get(pg.id)
        coperto = premio_copre_avvio_corrente(row, evento, pg)
        dettagli_crediti = dettaglio_crediti_premio_evento(evento, pg, ts=when)
        rows.append(
            {
                "personaggio_id": pg.id,
                "personaggio_nome": pg.nome,
                "premio_gia_assegnato": coperto,
                "premio_avvio_precedente": bool(row) and not coperto,
                "pc_evento": int(evento.pc_guadagnati or 0),
                "prestigio_evento": int(getattr(evento, "prestigio_base_inizio_evento", 0) or 0),
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
    accredita PC/crediti/prestigio dell'avvio corrente se non risultano già scritti.

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
