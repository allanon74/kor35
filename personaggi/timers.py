"""
Servizio unificato per TimerRuntime: creazione, mirror da legacy, processamento scadenze.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


class TimerService:
    """Facade per operazioni su TimerRuntime."""

    @staticmethod
    def start_or_update_mirror(
        *,
        source_kind: str,
        source_id: str,
        personaggio,
        end_at,
        label: str,
        render_slot: str,
        action_key: str = "noop",
        action_payload: Optional[Dict[str, Any]] = None,
        is_master_timer: bool = False,
        scope_kind: str = "all",
        scope_payload: Optional[Dict[str, Any]] = None,
    ):
        from .models import (
            TIMER_SCOPE_ALL,
            TIMER_STATUS_ACTIVE,
            TimerRuntime,
        )

        payload = dict(action_payload or {})
        sc = scope_kind if scope_kind else TIMER_SCOPE_ALL
        sp = dict(scope_payload or {})

        defaults = {
            "personaggio": personaggio,
            "end_at": end_at,
            "status": TIMER_STATUS_ACTIVE,
            "render_slot": render_slot,
            "scope_kind": sc,
            "scope_payload": sp,
            "label": label,
            "action_key": action_key,
            "action_payload": payload,
            "is_master_timer": is_master_timer,
            "action_executed_at": None,
        }
        tr, _ = TimerRuntime.objects.update_or_create(
            source_kind=source_kind,
            source_id=source_id,
            defaults=defaults,
        )
        return tr

    @staticmethod
    def pause(timer_id) -> None:
        from .models import TIMER_STATUS_PAUSED, TimerRuntime

        now = timezone.now()
        with transaction.atomic():
            t = TimerRuntime.objects.select_for_update().get(pk=timer_id)
            if t.status != TIMER_STATUS_PAUSED:
                t.status = TIMER_STATUS_PAUSED
                t.pause_started_at = now
                t.save(update_fields=["status", "pause_started_at", "updated_at"])

    @staticmethod
    def resume(timer_id) -> None:
        from .models import TIMER_STATUS_ACTIVE, TIMER_STATUS_PAUSED, TimerRuntime

        now = timezone.now()
        with transaction.atomic():
            t = TimerRuntime.objects.select_for_update().get(pk=timer_id)
            if t.status != TIMER_STATUS_PAUSED:
                return
            extra = 0
            if t.pause_started_at:
                extra = int((now - t.pause_started_at).total_seconds())
            t.accumulated_pause_seconds = (t.accumulated_pause_seconds or 0) + max(0, extra)
            t.end_at = t.end_at + timedelta(seconds=extra)
            t.status = TIMER_STATUS_ACTIVE
            t.pause_started_at = None
            t.save(
                update_fields=[
                    "end_at",
                    "status",
                    "pause_started_at",
                    "accumulated_pause_seconds",
                    "updated_at",
                ]
            )

    @staticmethod
    def cancel_by_source(source_kind: str, source_id: str) -> None:
        from .models import TIMER_STATUS_CANCELLED, TIMER_STATUS_ACTIVE, TIMER_STATUS_PAUSED, TimerRuntime

        TimerRuntime.objects.filter(
            source_kind=source_kind,
            source_id=source_id,
            status__in=[TIMER_STATUS_ACTIVE, TIMER_STATUS_PAUSED],
        ).update(status=TIMER_STATUS_CANCELLED, updated_at=timezone.now())

    @staticmethod
    def process_due(now=None, batch_limit: int = 100) -> int:
        """
        Esegue azioni per timer scaduti (idempotente per tick).
        Ritorna il numero di timer processati.
        """
        from .models import TIMER_STATUS_ACTIVE, TIMER_STATUS_DONE, TimerRuntime
        from .timer_actions import validate_and_run

        now = now or timezone.now()
        processed = 0

        candidate_ids = list(
            TimerRuntime.objects.filter(status=TIMER_STATUS_ACTIVE, end_at__lte=now)
            .order_by("end_at")
            .values_list("pk", flat=True)[:batch_limit]
        )

        for tid in candidate_ids:
            try:
                with transaction.atomic():
                    t = (
                        TimerRuntime.objects.select_for_update()
                        .filter(pk=tid, status=TIMER_STATUS_ACTIVE, end_at__lte=now)
                        .first()
                    )
                    if not t:
                        continue

                    validate_and_run(t)
                    t.refresh_from_db()

                    if t.status == TIMER_STATUS_ACTIVE and t.end_at > now:
                        t.action_executed_at = now
                        t.save(update_fields=["action_executed_at", "updated_at"])
                    elif t.status == TIMER_STATUS_ACTIVE:
                        t.status = TIMER_STATUS_DONE
                        t.action_executed_at = now
                        t.save(update_fields=["status", "action_executed_at", "updated_at"])
                    else:
                        t.action_executed_at = now
                        t.save(update_fields=["action_executed_at", "updated_at"])
                    processed += 1
            except Exception:
                logger.exception("process_due fallito per timer %s", tid)

        return processed
