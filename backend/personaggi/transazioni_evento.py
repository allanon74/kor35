"""Gate azioni di gioco live (furti, scambi, nodi, allibratore): solo con evento aperto."""
from __future__ import annotations

from django.utils import timezone

from gestione_plot.models import Evento

from personaggi.modificabilita import get_event_context

GIOCO_LIVE_BLOCCO_MSG = (
    "Furti, scambi, trasferimenti via messaggio, scansione nodi e codici allibratore "
    "sono disponibili solo durante un evento aperto."
)

# Alias retrocompatibilità test/codice esistente
TRANSazioni_GIOCATORE_BLOCCO_MSG = GIOCO_LIVE_BLOCCO_MSG


def _campagna_da_request(request):
    if not request:
        return None
    from personaggi.models import Campagna

    slug = (request.headers.get("X-Campagna") or request.query_params.get("campagna") or "kor35").strip().lower()
    campagna = Campagna.objects.filter(slug=slug, attiva=True).first()
    if campagna:
        return campagna
    return Campagna.objects.filter(slug="kor35").first() or Campagna.objects.filter(is_default=True).first()


def utente_ha_bypass_evento(user, campagna=None) -> bool:
    """Staff di campagna e master possono agire anche inter-evento."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser or getattr(user, "is_staff", False):
        return True
    if not campagna:
        return False
    from personaggi.models import (
        CAMPAGNA_ROLE_HEAD_MASTER,
        CAMPAGNA_ROLE_MASTER,
        CAMPAGNA_ROLE_STAFFER,
        CampagnaUtente,
    )

    ruolo = (
        CampagnaUtente.objects.filter(user=user, campagna=campagna, attivo=True)
        .values_list("ruolo", flat=True)
        .first()
    )
    return ruolo in (CAMPAGNA_ROLE_STAFFER, CAMPAGNA_ROLE_MASTER, CAMPAGNA_ROLE_HEAD_MASTER)


def evento_aperto_in_corso(now=None) -> bool:
    """True se c'è un evento avviato dallo staff o nella finestra data_inizio/data_fine."""
    return get_event_context(now)[0]


def gioco_live_consentito(user=None, campagna=None, now=None) -> bool:
    if utente_ha_bypass_evento(user, campagna):
        return True
    return evento_aperto_in_corso(now)


def get_evento_aperto_corso(now=None):
    now = now or timezone.now()
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


def gioco_stato_evento(request=None, now=None) -> dict:
    campagna = _campagna_da_request(request)
    user = getattr(request, "user", None) if request else None
    evento = get_evento_aperto_corso(now)
    bypass = utente_ha_bypass_evento(user, campagna)
    evento_aperto = evento is not None
    azioni_abilitate = gioco_live_consentito(user=user, campagna=campagna, now=now)
    return {
        "evento_aperto": evento_aperto,
        "evento_titolo": evento.titolo if evento else None,
        "azioni_live_abilitate": azioni_abilitate,
        "bypass_evento_gate": bypass,
        "transazioni_giocatore_abilitate": azioni_abilitate,
        "nodo_scan_abilitato": azioni_abilitate,
        "allibratore_codici_abilitati": azioni_abilitate,
    }
