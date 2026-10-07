"""
Istanze multiple di un innesco timer e conferma («Ok») della schermata di scadenza.

Le istanze dello stesso ``gruppo_id`` condividono nome, durata e destinatari.
QR, countdown, ack e cariche residue del giorno restano per singola istanza.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from kor35.syncing import touch_sync_updated_at

from .models import InnescoTimer, InnescoTimerAck

# Campi copiati su tutte le istanze del gruppo.
# QR, countdown e cariche residue del giorno restano sulla singola istanza.
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
# Lo staff aggiunge o toglie a passi piccoli; il pavimento del residuo resta 0.
MAX_DELTA_CARICHE = 20


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


def etichetta_istanza_pubblica(innesco: InnescoTimer) -> str:
    """Nome dell'istanza mostrato sul telefono insieme al nome del timer."""
    etichetta = (getattr(innesco, "etichetta_istanza", None) or "").strip()
    if etichetta:
        return etichetta
    ordine = int(getattr(innesco, "ordine_istanza", None) or 1)
    return f"Istanza {ordine}"


def cariche_residue_oggi(innesco: InnescoTimer, oggi=None) -> Optional[int]:
    """
    Residuo visibile oggi, senza scrivere.

    ``None`` se le cariche sono illimitate. Se il giorno è cambiato o il residuo
    non è ancora stato materializzato, vale ``max_cariche``.
    """
    max_c = int(innesco.max_cariche or 0)
    if max_c <= 0:
        return None
    oggi = oggi or timezone.localdate()
    if innesco.cariche_giorno == oggi and innesco.cariche_residue is not None:
        return int(innesco.cariche_residue)
    return max_c


def materializza_cariche_oggi(innesco: InnescoTimer, oggi=None) -> int:
    """Allinea in memoria il residuo al giorno corrente. Il chiamante salva."""
    oggi = oggi or timezone.localdate()
    max_c = int(innesco.max_cariche or 0)
    if innesco.cariche_giorno != oggi or innesco.cariche_residue is None:
        innesco.cariche_residue = max_c
        innesco.cariche_giorno = oggi
    return int(innesco.cariche_residue)


def prepara_consumo_carica_giorno(innesco: InnescoTimer) -> Optional[str]:
    """
    Scala una carica del giorno in memoria.

    Ritorna un messaggio se il residuo è a zero. Non salva: il chiamante,
    dentro la stessa transazione, persiste solo se l'attivazione prosegue.
    """
    if int(innesco.max_cariche or 0) <= 0:
        return None
    if materializza_cariche_oggi(innesco) <= 0:
        return "Cariche esaurite per oggi."
    innesco.cariche_residue = int(innesco.cariche_residue) - 1
    return None


def applica_delta_cariche_giorno(innesco_id: int, delta: int) -> Tuple[Optional[int], Optional[str]]:
    """
    Aggiunge o toglie cariche al residuo di oggi di una sola istanza.

    Il risultato può superare ``max_cariche`` (lo staff ricarica la giornata)
    e non scende sotto zero. A mezzanotte il prossimo accesso riparte dal massimo.
    """
    passo = int(delta)
    if passo == 0 or abs(passo) > MAX_DELTA_CARICHE:
        return None, "Indica quante cariche aggiungere o togliere (da -20 a 20, escluso 0)."
    with transaction.atomic():
        locked = InnescoTimer.objects.select_for_update().get(pk=innesco_id)
        if int(locked.max_cariche or 0) <= 0:
            return None, "Questo timer ha cariche illimitate: non c'è un residuo da modificare."
        materializza_cariche_oggi(locked)
        locked.cariche_residue = max(0, int(locked.cariche_residue) + passo)
        locked.save(update_fields=["cariche_residue", "cariche_giorno", "updated_at"])
        return int(locked.cariche_residue), None


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
