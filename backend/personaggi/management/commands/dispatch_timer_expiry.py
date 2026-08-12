"""
Worker: invia web push alla scadenza dei timer innesco.

Esecuzione:
- one-shot:  python manage.py dispatch_timer_expiry
- loop:      python manage.py dispatch_timer_expiry --loop --interval 5

In Docker: servizio compose `timer_dispatch` (vedi compose.base.yml).
"""
from __future__ import annotations

import time

from django.core.management.base import BaseCommand

from personaggi.timer_expiry_push import dispatch_expired_innesco_pushes


class Command(BaseCommand):
    help = "Invia web push per timer innesco scaduti (e affini)."

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true", help="Esegui in loop continuo.")
        parser.add_argument(
            "--interval",
            type=float,
            default=5.0,
            help="Secondi tra un ciclo e l'altro (solo con --loop).",
        )

    def handle(self, *args, **options):
        loop = bool(options["loop"])
        interval = max(1.0, float(options["interval"]))

        while True:
            try:
                stats = dispatch_expired_innesco_pushes()
                if stats.get("dispatched"):
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Timer expiry: dispatched={stats['dispatched']} "
                            f"push_attempts={stats['push_attempts']}"
                        )
                    )
            except Exception as exc:  # pragma: no cover
                self.stderr.write(self.style.ERROR(f"dispatch_timer_expiry errore: {exc}"))

            if not loop:
                return
            time.sleep(interval)
