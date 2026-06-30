"""
Sincronizza bozza regolamento carte da docs/wiki/carte/.

Uso:
    python manage.py sync_wiki_carte_regolamento
    python manage.py sync_wiki_carte_regolamento --force

Docker / Make:
    make wiki-carte-sync ENV=dev-home
    make wiki-carte-sync ENV=dev-home WIKI_CARTE_FORCE=1
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from gestione_plot.wiki_carte_regolamento import sync_wiki_carte_regolamento


class Command(BaseCommand):
    help = "Aggiorna pagine Wiki regolamento carte da docs/wiki/carte/"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Sovrascrive pagine esistenti con lo stesso slug",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)
        self.stdout.write(self.style.SUCCESS("Sync Wiki regolamento carte (docs/wiki/carte/)"))
        with transaction.atomic():
            results = sync_wiki_carte_regolamento(force=force)
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
