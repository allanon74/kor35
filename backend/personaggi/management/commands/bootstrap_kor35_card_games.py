from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from personaggi.carte_platform_models import MODELLO_BASE_KOR35, CarteGiocoDefinizione
from personaggi.mse_kor35_game_spec import merge_kor35_game_meta
from personaggi.models import Campagna


class Command(BaseCommand):
    help = "Popola meta.mse_game_spec per giochi KOR35 senza spec (Card Studio game-first)."

    def add_arguments(self, parser):
        parser.add_argument("--campagna-slug", required=True)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--force-refresh-spec",
            action="store_true",
            help="Riscrive meta.mse_game_spec con la spec canonica Sette Elegie (7 aure).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        campagna = Campagna.objects.filter(slug=options["campagna_slug"]).first()
        if not campagna:
            raise CommandError(f"Campagna non trovata: {options['campagna_slug']}")

        dry_run = bool(options["dry_run"])
        force_refresh = bool(options["force_refresh_spec"])
        updated = 0
        skipped = 0

        qs = CarteGiocoDefinizione.objects.filter(
            campagna=campagna,
            modello_base=MODELLO_BASE_KOR35,
        )
        for gioco in qs:
            merged = merge_kor35_game_meta(gioco.meta, force_refresh=force_refresh)
            if merged == (gioco.meta or {}):
                skipped += 1
                continue
            updated += 1
            self.stdout.write(f"SPEC {gioco.slug}: mse_game_spec KOR35")
            if not dry_run:
                gioco.meta = merged
                gioco.save(update_fields=["meta", "updated_at"])

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING("Dry-run: rollback."))

        self.stdout.write(self.style.SUCCESS(f"Aggiornati: {updated}, già ok: {skipped}"))
