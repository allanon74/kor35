"""
Migrazione one-shot / periodica: popola TimerRuntime dai modelli legacy attivi.

Deprecazione progressiva: dopo il backfill, l'app usa TimerRuntime come fonte unificata
(mantenendo i record legacy finché necessario al dominio).
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from personaggi.models import (
    CreazioneConsumabileInCorso,
    ForgiaturaInCorso,
    RecuperoRisorsaAttivo,
    StatoTimerAttivo,
)
from personaggi.timer_adapters import (
    sync_creazione_consumabile_timer,
    sync_forgiatura_timer,
    sync_qr_global_timer_from_stato,
    sync_recupero_risorsa_timer,
)


class Command(BaseCommand):
    help = "Sincronizza TimerRuntime dai timer legacy attivi (QR, recupero, forgiatura, consumabili)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo conteggio, nessuna scrittura.",
        )

    def handle(self, *args, **options):
        dry = options["dry_run"]
        now = timezone.now()
        n = 0

        # QR globali
        for stato in StatoTimerAttivo.objects.filter(data_fine__gt=now).select_related("tipologia"):
            if dry:
                self.stdout.write(f"[dry-run] QR tipologia {stato.tipologia_id}")
            else:
                sync_qr_global_timer_from_stato(stato, stato.tipologia)
                n += 1

        for rec in RecuperoRisorsaAttivo.objects.filter(is_active=True):
            if dry:
                self.stdout.write(f"[dry-run] Recupero {rec.statistica_sigla} pg={rec.personaggio_id}")
            else:
                sync_recupero_risorsa_timer(rec)
                n += 1

        for f in ForgiaturaInCorso.objects.filter(completata=False, data_fine_prevista__gt=now):
            if dry:
                self.stdout.write(f"[dry-run] Forgiatura {f.pk}")
            else:
                sync_forgiatura_timer(f)
                n += 1

        for cc in CreazioneConsumabileInCorso.objects.filter(completata=False, data_fine_creazione__gt=now):
            if dry:
                self.stdout.write(f"[dry-run] Creazione consumabile {cc.pk}")
            else:
                sync_creazione_consumabile_timer(cc)
                n += 1

        if dry:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run: nessun record scritto. Rimuovi --dry-run per applicare."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"Operazioni TimerRuntime eseguite: {n}"))
