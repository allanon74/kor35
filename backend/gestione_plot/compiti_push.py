"""
Dispatch notifiche per preavviso e scadenza dei compiti staff.

Usa il dispatcher unificato (web push / Telegram / email secondo le preferenze).
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from django.db import transaction
from django.utils import timezone

from personaggi.notify import notify_user

logger = logging.getLogger(__name__)

COMPITO_HOME_URL = "/?tab=home"


def notify_compito_user(user, *, head: str, body: str, url: str = COMPITO_HOME_URL) -> int:
    """Invia la notifica di un compito sui canali scelti dall'utente."""
    if not user:
        return 0
    return notify_user(user, category="compiti", head=head, body=body, url=url)


def dispatch_compiti_scadenze(*, now=None) -> Dict[str, Any]:
    """
    Per ogni assegnazione aperta:
    - preavviso quando now >= preavviso_at
    - scadenza quando now >= scadenza (se crea_notifica_scadenza)
    """
    from gestione_plot.models import StaffCompitoAssegnazione

    now = now or timezone.now()
    dispatched = 0
    push_attempts = 0

    preavviso_ids = list(
        StaffCompitoAssegnazione.objects.filter(
            completato_at__isnull=True,
            push_preavviso_inviata=False,
            compito__attivo=True,
            compito__preavviso_at__isnull=False,
            compito__preavviso_at__lte=now,
        ).values_list("pk", flat=True)
    )
    scadenza_ids = list(
        StaffCompitoAssegnazione.objects.filter(
            completato_at__isnull=True,
            push_scadenza_inviata=False,
            compito__attivo=True,
            compito__crea_notifica_scadenza=True,
            compito__scadenza__lte=now,
        ).values_list("pk", flat=True)
    )

    seen = set()
    ordered = list(preavviso_ids) + [pk for pk in scadenza_ids if pk not in set(preavviso_ids)]

    for pk in ordered:
        if pk in seen:
            continue
        seen.add(pk)
        with transaction.atomic():
            locked = (
                StaffCompitoAssegnazione.objects.select_for_update()
                .select_related("compito", "user")
                .filter(pk=pk, completato_at__isnull=True)
                .first()
            )
            if not locked or not locked.compito or not locked.compito.attivo:
                continue
            compito = locked.compito
            sent_here = 0

            if (
                not locked.push_preavviso_inviata
                and compito.preavviso_at
                and compito.preavviso_at <= now
            ):
                sent_here += notify_compito_user(
                    locked.user,
                    head=f"Promemoria: {compito.titolo}",
                    body=f"Scade il compito «{compito.titolo}».",
                )
                locked.push_preavviso_inviata = True

            if (
                not locked.push_scadenza_inviata
                and compito.crea_notifica_scadenza
                and compito.scadenza
                and compito.scadenza <= now
            ):
                sent_here += notify_compito_user(
                    locked.user,
                    head=f"Scaduto: {compito.titolo}",
                    body=f"Il termine del compito «{compito.titolo}» è scaduto.",
                )
                locked.push_scadenza_inviata = True

            if locked.push_preavviso_inviata or locked.push_scadenza_inviata:
                locked.save(
                    update_fields=[
                        "push_preavviso_inviata",
                        "push_scadenza_inviata",
                        "updated_at",
                    ]
                )
            if sent_here:
                dispatched += 1
                push_attempts += sent_here

    return {
        "dispatched": dispatched,
        "push_attempts": push_attempts,
        "pending_found": len(ordered),
    }
