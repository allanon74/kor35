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

from pilotaggio.engine import tick_sessione
from pilotaggio.models import SessioneVolo


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
        interval = max(0.5, float(options["interval"]))
        max_iter = int(options["max_iterations"] or 0)

        iterazione = 0
        while True:
            iterazione += 1
            attive = SessioneVolo.objects.exclude(stato__in=["arrivata", "crashed"])
            for sessione in attive:
                try:
                    tick_sessione(sessione)
                except Exception as exc:  # pragma: no cover - log informativo
                    self.stderr.write(self.style.ERROR(f"Tick errore {sessione.pk}: {exc}"))
            if not loop:
                self.stdout.write(self.style.SUCCESS(f"Tick eseguito ({attive.count()} sessioni)."))
                return
            if max_iter and iterazione >= max_iter:
                return
            time.sleep(interval)
