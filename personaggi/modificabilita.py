from __future__ import annotations

from django.utils import timezone
from gestione_plot.models import Evento

from .models import abilita_prerequisito


def get_event_context(now=None):
    """
    Restituisce:
    - event_in_corso: True se ESISTE almeno un Evento attivo al momento (data_inizio <= now <= data_fine)
    - latest_event_start: l'ultima data di inizio Evento (max(data_inizio)) fino a now, oppure None
    """
    now = now or timezone.now()
    event_in_corso = Evento.objects.filter(data_inizio__lte=now, data_fine__gte=now).exists()
    latest_event_start = (
        Evento.objects.filter(data_inizio__lte=now)
        .order_by("-data_inizio")
        .values_list("data_inizio", flat=True)
        .first()
    )
    return event_in_corso, latest_event_start


def is_modificabile_per_eventi(acquisizione_dt, event_in_corso: bool, latest_event_start):
    """
    Regole richieste:
    - se siamo nel periodo inizio-fine di un evento: NON modificabile
    - se tra acquisto e oggi non c'è un inizio evento: modificabile
      (equivalente a: acquisizione_dt > latest_event_start, se presente)
    """
    if event_in_corso:
        return False
    if not latest_event_start:
        return True
    if not acquisizione_dt:
        return False
    return acquisizione_dt > latest_event_start


def get_abilita_bloccate_da_prerequisito(abilita_possedute_ids):
    """
    True per un'abilità A se A è prerequisito di almeno un'altra abilità B posseduta dal PG.
    """
    abilita_possedute_ids = set(abilita_possedute_ids or [])
    if not abilita_possedute_ids:
        return set()

    locked_ids = (
        abilita_prerequisito.objects.filter(
            prerequisito_id__in=abilita_possedute_ids,
            abilita_id__in=abilita_possedute_ids,
        )
        .values_list("prerequisito_id", flat=True)
        .distinct()
    )
    return set(locked_ids)

