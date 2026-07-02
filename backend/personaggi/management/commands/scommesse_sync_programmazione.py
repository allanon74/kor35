"""
Sincronizza le programmazioni torneo scommesse con i prossimi eventi LARP.

Uso cron/timer (es. ogni notte o dopo creazione evento):
  python manage.py scommesse_sync_programmazione
  python manage.py scommesse_sync_programmazione --max-per-sport 2
"""
from django.core.management.base import BaseCommand

from personaggi.scommesse_scheduling import sincronizza_tutte_programmazioni


class Command(BaseCommand):
    help = "Genera automaticamente giornate scommesse per i prossimi eventi (programmazioni attive)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-per-sport",
            type=int,
            default=1,
            help="Massimo calendari da creare per sport (default 1).",
        )

    def handle(self, *args, **options):
        max_per = max(1, min(int(options["max_per_sport"]), 10))
        report = sincronizza_tutte_programmazioni(max_crea_per_sport=max_per)
        creati = report.get("creati", [])
        errori = report.get("errori", [])
        if creati:
            self.stdout.write(self.style.SUCCESS(f"Creati {len(creati)} calendari:"))
            for row in creati:
                self.stdout.write(f"  · {row['sport']}: {row['titolo']} (evento: {row.get('evento')})")
        else:
            self.stdout.write("Nessun nuovo calendario creato.")
        for err in errori:
            self.stdout.write(self.style.WARNING(f"  ! {err['sport']}: {err['errore']}"))
