"""
Management command: tick periodico del motore pilotaggio.

Esegue `tick_sessione` su tutte le sessioni attive non terminate.

Esecuzione:
- one-shot:        python manage.py pilot_tick
- loop continuo:   python manage.py pilot_tick --loop --interval 5

In Docker tipicamente lo si lascia come worker dedicato (compose service).
"""
from __future__ import annotations

import time
from typing import Optional

from django.core.management.base import BaseCommand

from pilotaggio.engine import intervallo_loop_motore, sessioni_per_tick_motore, tick_sessione_se_dovuto
from django.utils import timezone

from pilotaggio.models import PilotRuntimeConfig, SessioneVolo


class Command(BaseCommand):
    help = "Avanza il motore della console pilotaggio (eventi/DEFCON/recovery)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--loop", action="store_true", help="Esegui in loop continuo."
        )
        parser.add_argument(
            "--interval", type=float, default=5.0, help="Secondi tra un tick e l'altro (loop)."
        )
        parser.add_argument(
            "--max-iterations",
            type=int,
            default=0,
            help="Numero massimo iterazioni (0 = infinito, solo con --loop).",
        )

    def handle(self, *args, **options):
        loop = options["loop"]
        fallback_interval = max(0.5, float(options["interval"]))
        max_iter = int(options["max_iterations"] or 0)
        last_interval: Optional[float] = None

        iterazione = 0
        while True:
            iterazione += 1
            runtime = PilotRuntimeConfig.get_solo()
            current_interval = intervallo_loop_motore()
            if loop and last_interval is not None and abs(current_interval - last_interval) > 1e-9:
                self.stdout.write(
                    f"[pilot_tick] interval changed: {last_interval:.3f}s -> {current_interval:.3f}s"
                )
            last_interval = current_interval
            runtime.tick_last_heartbeat = timezone.now()
            runtime.save(update_fields=["tick_last_heartbeat", "updated_at"])

            if not runtime.tick_enabled:
                if not loop:
                    self.stdout.write("Tick disabilitato da runtime config.")
                    return
                time.sleep(current_interval)
                continue

            attive = sessioni_per_tick_motore()
            for sessione in attive:
                try:
                    tick_sessione_se_dovuto(sessione)
                except Exception as exc:  # pragma: no cover - log informativo
                    self.stderr.write(self.style.ERROR(f"Tick errore {sessione.pk}: {exc}"))
            if not attive:
                runtime.tick_enabled = False
                runtime.save(update_fields=["tick_enabled", "updated_at"])
            if not loop:
                self.stdout.write(self.style.SUCCESS(f"Tick eseguito ({len(attive)} sessioni)."))
                return
            if max_iter and iterazione >= max_iter:
                return
            time.sleep(current_interval)
