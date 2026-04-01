"""
Registry azioni a scadenza per TimerRuntime: action_key -> handler validato.

Ogni handler riceve il TimerRuntime (lockato) e ritorna None.
L'idempotenza è garantita da action_executed_at e select_for_update in process_due.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, Tuple

from django.db import transaction

logger = logging.getLogger(__name__)

Handler = Callable[..., None]


def _validate_payload_keys(payload: Dict[str, Any], required: Tuple[str, ...]) -> None:
    missing = [k for k in required if k not in payload]
    if missing:
        raise ValueError(f"Payload timer incompleto: mancano {missing}")


def handle_noop(timer, *, payload: Dict[str, Any]) -> None:
    """Nessuna azione di dominio (timer solo informativo / già gestito altrove)."""
    pass


def handle_recupero_risorsa_tick(timer, *, payload: Dict[str, Any]) -> None:
    """
    Tick recupero pool: delega a advance_recuperi_risorse e risincronizza il mirror TimerRuntime.
    """
    from .models import Personaggio, RecuperoRisorsaAttivo, TIMER_STATUS_ACTIVE, TIMER_STATUS_DONE
    from .timer_adapters import sync_recupero_risorsa_timer

    _validate_payload_keys(payload, ("recupero_sync_id",))

    sync_id = payload["recupero_sync_id"]
    try:
        rec = RecuperoRisorsaAttivo.objects.select_related("personaggio").get(sync_id=sync_id)
    except RecuperoRisorsaAttivo.DoesNotExist:
        logger.warning("recupero_risorsa_tick: RecuperoRisorsaAttivo assente sync_id=%s", sync_id)
        return

    pg: Personaggio = rec.personaggio
    pg.advance_recuperi_risorse(only_sigla=rec.statistica_sigla)
    rec.refresh_from_db()
    sync_recupero_risorsa_timer(rec)


def handle_sync_coma_state(timer, *, payload: Dict[str, Any]) -> None:
    """Ricalcola coma/rianimazione lato server (stesso codice del GET personaggio)."""
    from .models import Personaggio

    _validate_payload_keys(payload, ("personaggio_id",))
    try:
        pg = Personaggio.objects.get(pk=int(payload["personaggio_id"]))
    except Personaggio.DoesNotExist:
        return

    from .views import _sync_coma_state

    _sync_coma_state(pg)


def handle_forge_complete_reminder(timer, *, payload: Dict[str, Any]) -> None:
    """Solo audit: la forgiatura resta in coda fino al ritiro manuale."""
    _validate_payload_keys(payload, ("forgiatura_sync_id",))


def handle_consumabile_ready_reminder(timer, *, payload: Dict[str, Any]) -> None:
    """Solo audit: la creazione resta in coda fino a completa_creazione."""
    _validate_payload_keys(payload, ("creazione_sync_id",))


ACTION_REGISTRY: Dict[str, Handler] = {
    "noop": handle_noop,
    "recupero_risorsa_tick": handle_recupero_risorsa_tick,
    "sync_coma_state": handle_sync_coma_state,
    "forge_complete_reminder": handle_forge_complete_reminder,
    "consumabile_ready_reminder": handle_consumabile_ready_reminder,
}


def get_handler(action_key: str) -> Handler:
    if action_key not in ACTION_REGISTRY:
        logger.warning("action_key sconosciuta: %s — uso noop", action_key)
        return handle_noop
    return ACTION_REGISTRY[action_key]


def validate_and_run(timer) -> None:
    """Esegue l'handler per action_key con action_payload."""
    handler = get_handler(timer.action_key)
    payload = dict(timer.action_payload or {})
    handler(timer, payload=payload)
