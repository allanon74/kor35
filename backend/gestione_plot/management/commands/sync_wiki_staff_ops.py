"""
Sincronizza le pagine Wiki staff da docs/wiki/staff/ (manifest + markdown).

Uso:
    python manage.py sync_wiki_staff_ops
    python manage.py sync_wiki_staff_ops --force

Docker (dev-home):
    make wiki-staff-sync ENV=dev-home
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from gestione_plot.wiki_staff_ops import sync_wiki_staff_ops


class Command(BaseCommand):
    help = "Aggiorna pagine Wiki staff da docs/wiki/staff/ (Operatività tecnica)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Sovrascrive pagine esistenti con lo stesso slug",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)
        self.stdout.write(self.style.SUCCESS("Sync Wiki staff (docs/wiki/staff/)"))
        with transaction.atomic():
            results = sync_wiki_staff_ops(force=force)
        for row in results:
            action = row["action"]
            slug = row["slug"]
            titolo = row["titolo"]
            if action == "created":
                self.stdout.write(self.style.SUCCESS(f"  ✓ creata: {slug} ({titolo})"))
            elif action == "updated":
                self.stdout.write(self.style.WARNING(f"  ↻ aggiornata: {slug} ({titolo})"))
            else:
                self.stdout.write(f"  ⊘ invariata: {slug} (usa --force)")
        self.stdout.write(self.style.SUCCESS("Sync completata."))
