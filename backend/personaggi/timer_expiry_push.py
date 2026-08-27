"""
Dispatch web push alla scadenza dei timer innesco (e affini).

Eseguito dal worker `dispatch_timer_expiry` (compose) ogni pochi secondi.
"""
from __future__ import annotations

from typing import Any, Dict, List

from django.db import transaction
from django.utils import timezone


def _send_webpush_to_users(user_ids: List[int], *, head: str, body: str, url: str = "/") -> int:
    """Notifica i proprietari (web push / Telegram / email secondo preferenze)."""
    from personaggi.notify import notify_user_ids

    return notify_user_ids(user_ids, category="in_game", head=head, body=body, url=url)


def dispatch_expired_innesco_pushes(*, now=None) -> Dict[str, Any]:
    """
    Per ogni InnescoTimer con broadcast scaduto e push non ancora inviata:
    invia web push ai proprietari dei PG destinatari, poi marca inviata.
    """
    from personaggi.models import InnescoTimer, Personaggio
    from personaggi.qr_logic import recipient_personaggio_ids_for_innesco

    now = now or timezone.now()
    pending = list(
        InnescoTimer.objects.filter(
            broadcast_push_inviata=False,
            broadcast_data_fine__isnull=False,
            broadcast_data_fine__lte=now,
        ).order_by("broadcast_data_fine", "pk")
    )
    dispatched = 0
    push_attempts = 0

    for inn in pending:
        with transaction.atomic():
            locked = (
                InnescoTimer.objects.select_for_update()
                .filter(pk=inn.pk, broadcast_push_inviata=False)
                .first()
            )
            if not locked or not locked.broadcast_data_fine:
                continue
            if locked.broadcast_data_fine > now:
                continue

            pg_ids = recipient_personaggio_ids_for_innesco(locked)
            user_ids = list(
                Personaggio.objects.filter(pk__in=pg_ids)
                .exclude(proprietario_id__isnull=True)
                .values_list("proprietario_id", flat=True)
                .distinct()
            )
            head = f"Timer scaduto: {locked.nome}"
            body = f'Il countdown «{locked.nome}» è terminato.'
            push_attempts += _send_webpush_to_users(
                user_ids,
                head=head,
                body=body,
                url="/",
            )
            locked.broadcast_push_inviata = True
            locked.save(update_fields=["broadcast_push_inviata", "updated_at"])
            dispatched += 1

    return {
        "dispatched": dispatched,
        "push_attempts": push_attempts,
        "pending_found": len(pending),
    }
