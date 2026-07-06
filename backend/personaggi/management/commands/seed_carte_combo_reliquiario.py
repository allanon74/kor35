"""
Seed combo reliquiario legacy (Triade Naturale, Quadrifoglio, legami/set da catalogo).

Uso:
  python manage.py seed_carte_combo_reliquiario
  python manage.py seed_carte_combo_reliquiario --campagna-slug kor35
  python manage.py seed_carte_combo_reliquiario --force

Docker:
  make seed-carte-combo-reliquiario ENV=dev-home
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from personaggi.carte_combo_reliquiario_seed import seed_combo_reliquiario


class Command(BaseCommand):
    help = "Crea combo reliquiario legacy (idempotente) per la campagna."

    def add_arguments(self, parser):
        parser.add_argument(
            "--campagna-slug",
            default="",
            help="Slug campagna (default: prima campagna attiva).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Aggiorna combo già presenti (stesso codice).",
        )
        parser.add_argument(
            "--no-catalog-derived",
            action="store_true",
            help="Solo combo fisse (Triade/Quadrifoglio), senza legame/set dal catalogo.",
        )

    def handle(self, *args, **options):
        slug = (options.get("campagna_slug") or "").strip() or None
        try:
            stats = seed_combo_reliquiario(
                campagna_slug=slug,
                force=options.get("force", False),
                include_catalog_derived=not options.get("no_catalog_derived", False),
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Combo reliquiario — campagna {stats['campagna_nome']}: "
                f"{stats['created']} create, {stats['updated']} aggiornate, "
                f"{stats['skipped']} già presenti (tot. {stats['total']} definite)."
            )
        )
