"""
Istanze multiple di un innesco timer e conferma («Ok») della schermata di scadenza.

Le istanze dello stesso ``gruppo_id`` condividono nome, durata e destinatari.
QR, countdown e ack restano per singola istanza.
"""
from __future__ import annotations

from typing import List

from django.db.models import Max
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from kor35.syncing import touch_sync_updated_at

from .models import InnescoTimer, InnescoTimerAck

# Campi copiati su tutte le istanze del gruppo. QR e countdown restano locali.
CAMPI_CONDIVISI = (
    "nome",
    "testo",
    "modalita_target",
    "durata_secondi",
    "max_cariche",
    "rigenera_cariche_ogni_secondi",
    "segnale_luminoso",
    "target_evento_id",
)

MAX_ISTANZE_PER_RICHIESTA = 20


def _copia_destinatari(src: InnescoTimer, dst: InnescoTimer) -> None:
    dst.target_ere.set(src.target_ere.all())
    dst.target_regioni.set(src.target_regioni.all())
    dst.target_korps.set(src.target_korps.all())
    dst.target_personaggi.set(src.target_personaggi.all())
    touch_sync_updated_at(InnescoTimer, dst.pk)


def prossimo_ordine_istanza(gruppo_id) -> int:
    attuale = (
        InnescoTimer.objects.filter(gruppo_id=gruppo_id).aggregate(m=Max("ordine_istanza")).get("m")
        or 0
    )
    return int(attuale) + 1


def clone_innesco_istanza(source: InnescoTimer) -> InnescoTimer:
    """Nuova istanza identica, senza QR e senza countdown attivo."""
    ordine = prossimo_ordine_istanza(source.gruppo_id)
    clone = InnescoTimer.objects.create(
        nome=source.nome,
        testo=source.testo,
        modalita_target=source.modalita_target,
        durata_secondi=source.durata_secondi,
        max_cariche=source.max_cariche,
        rigenera_cariche_ogni_secondi=source.rigenera_cariche_ogni_secondi,
        segnale_luminoso=source.segnale_luminoso,
        campagna_id=source.campagna_id,
        gruppo_id=source.gruppo_id,
        etichetta_istanza=f"Istanza {ordine}",
        ordine_istanza=ordine,
        target_evento_id=source.target_evento_id,
        broadcast_data_fine=None,
        broadcast_push_inviata=True,
    )
    _copia_destinatari(source, clone)
    return clone


def propaga_campi_gruppo(source: InnescoTimer) -> List[int]:
    """Allinea nome, durata e destinatari alle altre istanze. Non tocca QR né countdown."""
    aggiornati: List[int] = []
    fratelli = InnescoTimer.objects.filter(gruppo_id=source.gruppo_id).exclude(pk=source.pk)
    for dst in fratelli:
        for campo in CAMPI_CONDIVISI:
            setattr(dst, campo, getattr(source, campo))
        dst.save()
        _copia_destinatari(source, dst)
        aggiornati.append(dst.pk)
    touch_sync_updated_at(InnescoTimer, source.pk)
    return aggiornati


def aggiungi_istanze(source: InnescoTimer, quante: int) -> List[InnescoTimer]:
    n = max(1, min(int(quante or 1), MAX_ISTANZE_PER_RICHIESTA))
    return [clone_innesco_istanza(source) for _ in range(n)]


def ack_innesco_timer_scaduto(personaggio, innesco: InnescoTimer, data_fine_raw) -> InnescoTimerAck:
    """
    Registra l'Ok del giocatore sulla scadenza indicata.
    Se il client manda la stessa fine del broadcast corrente, si usa il timestamp del server.
    """
    parsed = data_fine_raw
    if isinstance(data_fine_raw, str):
        parsed = parse_datetime(data_fine_raw)
    if parsed is not None and timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())

    fine = innesco.broadcast_data_fine
    if fine is not None and parsed is not None:
        if abs((fine - parsed).total_seconds()) <= 5:
            parsed = fine
    if parsed is None:
        parsed = fine or timezone.now()

    ack, _created = InnescoTimerAck.objects.get_or_create(
        personaggio=personaggio,
        innesco_timer=innesco,
        data_fine=parsed,
    )
    return ack
