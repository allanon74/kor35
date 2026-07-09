from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from personaggi.carte_platform_models import CarteStudioTemplate
from personaggi.mse_style_import import _apply_parsed_style_to_layout, _parse_style_metadata
from personaggi.models import Campagna


class Command(BaseCommand):
    help = "Rigenera layout_spec.mse_v1 dai file style estratti (template già importati)."

    def add_arguments(self, parser):
        parser.add_argument("--campagna-slug", required=True)
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        campagna = Campagna.objects.filter(slug=options["campagna_slug"]).first()
        if not campagna:
            raise CommandError(f"Campagna non trovata: {options['campagna_slug']}")

        dry_run = bool(options["dry_run"])
        updated = 0
        skipped = 0

        for template in CarteStudioTemplate.objects.filter(campagna=campagna):
            if not template.mse_extracted_root:
                skipped += 1
                continue
            style_path = Path(settings.MEDIA_ROOT) / template.mse_extracted_root / "style"
            if not style_path.exists():
                skipped += 1
                continue
            style_text = style_path.read_text(encoding="utf-8", errors="replace")
            parsed_meta = _parse_style_metadata(style_text)
            new_layout = _apply_parsed_style_to_layout(template.layout_spec or {}, style_text, parsed_meta)
            if new_layout == (template.layout_spec or {}):
                skipped += 1
                continue
            updated += 1
            n_styles = len((new_layout.get("mse_v1") or {}).get("card_styles") or {})
            self.stdout.write(f"TPL {template.slug}: card_styles={n_styles}")
            if not dry_run:
                template.layout_spec = new_layout
                template.save(update_fields=["layout_spec", "updated_at"])

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING("Dry-run: rollback."))

        self.stdout.write(self.style.SUCCESS(f"Aggiornati: {updated}, saltati: {skipped}"))
