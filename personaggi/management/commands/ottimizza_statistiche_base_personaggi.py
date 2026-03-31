from django.core.management.base import BaseCommand
from django.db import transaction

from personaggi.models import PersonaggioStatisticaBase


class Command(BaseCommand):
    help = (
        "Rimuove i record PersonaggioStatisticaBase ridondanti "
        "(valore_base uguale a statistica.valore_base_predefinito)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Applica davvero le cancellazioni. Senza flag esegue solo dry-run.",
        )

    def handle(self, *args, **options):
        apply_changes = options.get("apply", False)

        qs = PersonaggioStatisticaBase.objects.select_related("statistica").all()
        ridondanti_ids = [
            row.id
            for row in qs
            if row.valore_base == row.statistica.valore_base_predefinito
        ]

        totale = len(ridondanti_ids)
        self.stdout.write(f"Record ridondanti trovati: {totale}")

        if not apply_changes:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run completato. Usa --apply per eliminare i record."
                )
            )
            return

        if totale == 0:
            self.stdout.write(self.style.SUCCESS("Nessun record da eliminare."))
            return

        with transaction.atomic():
            eliminati, _ = PersonaggioStatisticaBase.objects.filter(
                id__in=ridondanti_ids
            ).delete()

        self.stdout.write(self.style.SUCCESS(f"Eliminazioni completate: {eliminati}"))
