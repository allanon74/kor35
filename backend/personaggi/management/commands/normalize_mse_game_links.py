from __future__ import annotations

from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from personaggi.carte_platform_models import (
    CarteGiocoDefinizione,
    CarteMsePackageImport,
    CarteStudioTemplate,
)
from personaggi.mse_style_import import parse_generic_package_meta
from personaggi.mse_style_import import parse_mse_game_spec
from personaggi.models import Campagna


def _norm_key(raw: str) -> str:
    return slugify((raw or "").strip().lower())[:80]


def _guess_model_from_name(name: str) -> str:
    s = (name or "").lower()
    if "magic" in s or s.startswith("mtg"):
        return "mtg"
    if "kor35" in s:
        return "kor35"
    return "custom"


class Command(BaseCommand):
    help = "Riallinea template/package MSE ai giochi corretti dopo import legacy."

    def add_arguments(self, parser):
        parser.add_argument("--campagna-slug", required=True, help="Slug campagna target.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Analizza senza scrivere modifiche.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        campagna = Campagna.objects.filter(slug=options["campagna_slug"]).first()
        if not campagna:
            raise CommandError(f"Campagna non trovata: {options['campagna_slug']}")

        dry_run = bool(options["dry_run"])
        if dry_run:
            self.stdout.write(self.style.WARNING("Modalita dry-run: nessuna scrittura."))

        summary = Counter()
        game_cache: dict[str, object] = {}
        dry_game_sentinel: dict[str, str] = {"dry": "1"}

        def resolve_game(game_name: str):
            game_name = (game_name or "").strip()
            if not game_name:
                return None
            key = _norm_key(game_name)
            if not key:
                return None
            if key in game_cache:
                return game_cache[key]

            gioco = (
                CarteGiocoDefinizione.objects.filter(campagna=campagna, slug=key).first()
                or CarteGiocoDefinizione.objects.filter(
                    campagna=campagna, mse_game_name__iexact=game_name
                ).first()
                or CarteGiocoDefinizione.objects.filter(campagna=campagna, nome__iexact=game_name).first()
            )
            if not gioco:
                if dry_run:
                    summary["giochi_would_create"] += 1
                    game_cache[key] = dry_game_sentinel
                    return dry_game_sentinel
                base_slug = key
                slug = base_slug
                idx = 2
                while CarteGiocoDefinizione.objects.filter(campagna=campagna, slug=slug).exists():
                    suffix = f"-{idx}"
                    slug = f"{base_slug[: max(1, 80 - len(suffix))]}{suffix}"
                    idx += 1
                gioco = CarteGiocoDefinizione.objects.create(
                    campagna=campagna,
                    slug=slug,
                    nome=game_name[:120],
                    modello_base=_guess_model_from_name(game_name),
                    studio_abilitato=True,
                    arena_abilitata=False,
                    mse_game_name=game_name[:120],
                )
                summary["giochi_created"] += 1
            game_cache[key] = gioco
            return gioco

        def parse_style_game_name(template: CarteStudioTemplate) -> str:
            style_path = (
                Path(settings.MEDIA_ROOT) / template.mse_extracted_root / "style"
                if template.mse_extracted_root
                else None
            )
            if style_path and style_path.exists():
                txt = style_path.read_text(encoding="utf-8", errors="replace")
                meta = parse_generic_package_meta("mse-style", txt)
                return (meta.get("game") or "").strip()
            return ""

        self.stdout.write(self.style.MIGRATE_HEADING("== Normalize MSE game links =="))

        packages = CarteMsePackageImport.objects.filter(campagna=campagna).select_related("gioco_definizione")
        for pkg in packages:
            game_name = (pkg.parsed_meta or {}).get("game", "").strip()
            if not game_name and pkg.package_type == "mse-game":
                game_name = (
                    (pkg.parsed_meta or {}).get("full_name")
                    or (pkg.parsed_meta or {}).get("short_name")
                    or pkg.package_name
                )
            if not game_name:
                continue
            gioco = resolve_game(game_name)
            if not gioco:
                summary["package_game_unresolved"] += 1
                continue
            if gioco is dry_game_sentinel:
                summary["package_would_relink"] += 1
                self.stdout.write(f"PKG {pkg.package_type}:{pkg.package_name} -> {_norm_key(game_name)}")
                continue
            if pkg.gioco_definizione_id != gioco.id:
                summary["package_relinked" if not dry_run else "package_would_relink"] += 1
                self.stdout.write(f"PKG {pkg.package_type}:{pkg.package_name} -> {gioco.slug}")
                if not dry_run:
                    pkg.gioco_definizione = gioco
                    pkg.save(update_fields=["gioco_definizione", "updated_at"])
            if pkg.package_type == "mse-game" and pkg.extracted_root:
                game_file = Path(settings.MEDIA_ROOT) / pkg.extracted_root / "game"
                if game_file.exists():
                    game_text = game_file.read_text(encoding="utf-8", errors="replace")
                    game_spec = parse_mse_game_spec(game_text)
                    if gioco is dry_game_sentinel:
                        summary["game_spec_would_update"] += 1
                    else:
                        merged_meta = dict(gioco.meta or {})
                        if merged_meta.get("mse_game_spec") != game_spec:
                            summary["game_spec_updated" if not dry_run else "game_spec_would_update"] += 1
                            if not dry_run:
                                merged_meta["mse_game_spec"] = game_spec
                                gioco.meta = merged_meta
                                gioco.save(update_fields=["meta", "updated_at"])

        templates = CarteStudioTemplate.objects.filter(campagna=campagna).select_related("gioco_definizione")
        for template in templates:
            schema = template.campi_schema or {}
            game_name = (schema.get("mse_game") or "").strip()
            if not game_name:
                game_name = parse_style_game_name(template)
            if not game_name:
                continue
            gioco = resolve_game(game_name)
            if not gioco:
                summary["template_game_unresolved"] += 1
                continue
            if gioco is dry_game_sentinel:
                summary["template_would_relink"] += 1
                self.stdout.write(f"TPL {template.slug} -> {_norm_key(game_name)}")
                continue
            if template.gioco_definizione_id != gioco.id:
                summary["template_relinked" if not dry_run else "template_would_relink"] += 1
                self.stdout.write(f"TPL {template.slug} -> {gioco.slug}")
                if not dry_run:
                    template.gioco_definizione = gioco
                    template.save(update_fields=["gioco_definizione", "updated_at"])

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING("Dry-run concluso (rollback eseguito)."))

        self.stdout.write(self.style.MIGRATE_HEADING("== Summary =="))
        for key in sorted(summary.keys()):
            self.stdout.write(f"{key}: {summary[key]}")
