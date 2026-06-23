"""Evento LARP in corso — prerequisito per ritiro contanti dalla riserva scommesse."""
from django.utils import timezone

from gestione_plot.evento_premi import _evento_in_finestra_presenza
from gestione_plot.models import Evento


def get_evento_scommesse_in_corso(reference_dt=None):
    now = reference_dt or timezone.now()
    manuale = (
        Evento.objects.filter(started_at__isnull=False, ended_at__isnull=True)
        .order_by("started_at")
        .first()
    )
    if manuale:
        return manuale
    return (
        Evento.objects.filter(data_inizio__lte=now, data_fine__gte=now)
        .order_by("data_inizio")
        .first()
    )


def personaggio_in_evento_attivo(personaggio, reference_dt=None) -> Evento | None:
    """
    Evento in corso in cui il PG è iscritto come partecipante.
    None se non può ritirare dalla riserva in contanti.
    """
    now = reference_dt or timezone.now()
    evento = get_evento_scommesse_in_corso(now)
    if not evento:
        return None
    if not _evento_in_finestra_presenza(evento, now):
        return None
    if not evento.partecipanti.filter(pk=personaggio.pk).exists():
        return None
    return evento
