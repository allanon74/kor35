"""
Installa template MSE KOR35 completo e allinea template/stylesheet già importati nel DB.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from personaggi.carte_collezionabili_models import EspansioneCarte
from personaggi.carte_platform_models import (
    MODELLO_BASE_KOR35,
    CarteGiocoDefinizione,
    CarteStudioTemplate,
)
from personaggi.mse_kor35_game_spec import merge_kor35_game_meta
from personaggi.mse_kor35_style import (
    KOR35_STYLE_GAME,
    KOR35_TEMPLATE_NAME,
    KOR35_TEMPLATE_SLUG,
    build_kor35_mse_style_zip,
    kor35_campi_schema,
)
from personaggi.mse_kor35_symbol_font import install_kor35_aura_symbol_font
from personaggi.mse_style_import import (
    _apply_parsed_style_to_layout,
    _parse_style_metadata,
    import_mse_style_package,
)
from personaggi.models import Campagna


class Command(BaseCommand):
    help = (
        "Crea/aggiorna il template MSE KOR35 standard (kor35-standard), "
        "allinea campi_schema e rigenera layout_spec.mse_v1 sui template già estratti."
    )

    def add_arguments(self, parser):
        parser.add_argument("--campagna-slug", required=True, help="Slug campagna (es. kor35).")
        parser.add_argument(
            "--gioco-slug",
            default="",
            help="Slug CarteGiocoDefinizione KOR35 (default: primo gioco modello_base=kor35).",
        )
        parser.add_argument(
            "--template-slug",
            default=KOR35_TEMPLATE_SLUG,
            help=f"Slug template da creare/aggiornare (default: {KOR35_TEMPLATE_SLUG}).",
        )
        parser.add_argument(
            "--set-default",
            action="store_true",
            help="Imposta il template KOR35 come default per nuove carte del gioco.",
        )
        parser.add_argument(
            "--skip-align-existing",
            action="store_true",
            help="Non rigenerare mse_v1 / campi_schema sui template già importati.",
        )
        parser.add_argument(
            "--link-expansions",
            action="store_true",
            help="Espansioni KOR35 senza default_studio_template → template KOR35.",
        )
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        campagna = Campagna.objects.filter(slug=options["campagna_slug"]).first()
        if not campagna:
            raise CommandError(f"Campagna non trovata: {options['campagna_slug']}")

        dry_run = bool(options["dry_run"])
        gioco = self._resolve_gioco(campagna, options["gioco_slug"])
        template_slug = (options["template_slug"] or KOR35_TEMPLATE_SLUG).strip()

        if dry_run:
            self.stdout.write(self.style.WARNING("Modalità dry-run: rollback a fine comando."))

        self.stdout.write(self.style.MIGRATE_HEADING(f"== KOR35 MSE template ({campagna.slug} / {gioco.slug}) =="))

        if not dry_run:
            merged = merge_kor35_game_meta(gioco.meta)
            if merged != (gioco.meta or {}):
                gioco.meta = merged
                gioco.save(update_fields=["meta", "updated_at"])
                self.stdout.write("Gioco: meta.mse_game_spec KOR35 aggiornato.")

            pkg, pkg_created = install_kor35_aura_symbol_font(campagna=campagna, gioco=gioco)
            if pkg:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Symbol font 7 Aure: {pkg.package_name} "
                        f"({'creato' if pkg_created else 'aggiornato'}, "
                        f"{len((pkg.parsed_meta or {}).get('symbols') or {})} simboli)"
                    )
                )

        template = CarteStudioTemplate.objects.filter(
            campagna=campagna, gioco_definizione=gioco, slug=template_slug
        ).first()
        created = False
        if not template:
            if dry_run:
                self.stdout.write(f"Template {template_slug}: verrebbe creato.")
            else:
                template = CarteStudioTemplate.objects.create(
                    campagna=campagna,
                    gioco_definizione=gioco,
                    slug=template_slug,
                    nome=KOR35_TEMPLATE_NAME,
                    attivo=True,
                    is_default_for_new_cards=bool(options["set_default"]),
                    layout_spec={"version": "1", "width_mm": 63, "height_mm": 88, "dpi": 300},
                    campi_schema=kor35_campi_schema(),
                )
                created = True
                self.stdout.write(self.style.SUCCESS(f"Template creato: {template_slug}"))
        else:
            self.stdout.write(f"Template esistente: {template_slug}")

        if template and not dry_run:
            upload = SimpleUploadedFile(
                "kor35-standard.mse-style",
                build_kor35_mse_style_zip(),
                content_type="application/zip",
            )
            imported = import_mse_style_package(template=template, upload_file=upload)
            template.nome = KOR35_TEMPLATE_NAME
            template.campi_schema = kor35_campi_schema()
            template.attivo = True
            if options["set_default"]:
                template.is_default_for_new_cards = True
            if imported.parsed_meta.get("full_name"):
                template.nome = imported.parsed_meta["full_name"][:120]
            template.save()
            n_styles = len((template.layout_spec.get("mse_v1") or {}).get("card_styles") or {})
            self.stdout.write(
                self.style.SUCCESS(
                    f"Import MSE: {len(imported.assets_manifest)} asset, {n_styles} card styles, "
                    f"root={imported.extracted_root}"
                )
            )

        if options["set_default"] and template and not dry_run:
            (
                CarteStudioTemplate.objects.filter(gioco_definizione=gioco)
                .exclude(pk=template.pk)
                .update(is_default_for_new_cards=False)
            )
            self.stdout.write(f"Default nuove carte → {template_slug}")

        if not options["skip_align_existing"]:
            refreshed, schema_patched = self._align_existing_templates(campagna, gioco, dry_run)
            self.stdout.write(f"Template allineati: layout refresh={refreshed}, campi_schema={schema_patched}")

        if options["link_expansions"] and template and not dry_run:
            linked = (
                EspansioneCarte.objects.filter(campagna=campagna, gioco_definizione=gioco)
                .filter(default_studio_template__isnull=True)
                .update(default_studio_template=template)
            )
            self.stdout.write(f"Espansioni collegate al template: {linked}")

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING("Dry-run: nessuna modifica persistita."))
        elif created:
            self.stdout.write(self.style.SUCCESS("Bootstrap KOR35 MSE template completato."))

    def _resolve_gioco(self, campagna, gioco_slug: str) -> CarteGiocoDefinizione:
        if gioco_slug:
            gioco = CarteGiocoDefinizione.objects.filter(campagna=campagna, slug=gioco_slug).first()
            if not gioco:
                raise CommandError(f"Gioco non trovato: {gioco_slug}")
            return gioco
        gioco = (
            CarteGiocoDefinizione.objects.filter(campagna=campagna, modello_base=MODELLO_BASE_KOR35)
            .order_by("nome")
            .first()
        )
        if not gioco:
            raise CommandError(
                "Nessun gioco modello_base=kor35 nella campagna. "
                "Crea il gioco o passa --gioco-slug."
            )
        return gioco

    def _align_existing_templates(self, campagna, gioco, dry_run: bool) -> tuple[int, int]:
        refreshed = 0
        schema_patched = 0
        schema = kor35_campi_schema()

        for template in CarteStudioTemplate.objects.filter(campagna=campagna).select_related(
            "gioco_definizione"
        ):
            style_game = self._style_game_name(template)
            is_kor35_style = style_game == KOR35_STYLE_GAME
            is_kor35_gioco = template.gioco_definizione_id == gioco.id or (
                template.gioco_definizione and template.gioco_definizione.modello_base == MODELLO_BASE_KOR35
            )

            if template.mse_extracted_root:
                style_path = Path(settings.MEDIA_ROOT) / template.mse_extracted_root / "style"
                if style_path.exists():
                    style_text = style_path.read_text(encoding="utf-8", errors="replace")
                    parsed_meta = _parse_style_metadata(style_text)
                    new_layout = _apply_parsed_style_to_layout(
                        template.layout_spec or {}, style_text, parsed_meta
                    )
                    if new_layout != (template.layout_spec or {}):
                        refreshed += 1
                        n = len((new_layout.get("mse_v1") or {}).get("card_styles") or {})
                        self.stdout.write(f"  refresh {template.slug}: card_styles={n}")
                        if not dry_run:
                            template.layout_spec = new_layout
                            template.save(update_fields=["layout_spec", "updated_at"])

            if is_kor35_style or is_kor35_gioco:
                needs_schema = (template.campi_schema or {}).get("mapping") != schema.get("mapping")
                needs_game_link = template.gioco_definizione_id != gioco.id and is_kor35_style
                if needs_schema or needs_game_link:
                    schema_patched += 1
                    self.stdout.write(f"  schema/link {template.slug}")
                    if not dry_run:
                        template.campi_schema = schema
                        if needs_game_link:
                            template.gioco_definizione = gioco
                        template.save(
                            update_fields=["campi_schema", "gioco_definizione", "updated_at"]
                        )

        return refreshed, schema_patched

    def _style_game_name(self, template: CarteStudioTemplate) -> str:
        mse = (template.layout_spec or {}).get("mse_v1") or {}
        game = (mse.get("game") or "").strip().lower()
        if game:
            return game
        if not template.mse_extracted_root:
            return ""
        style_path = Path(settings.MEDIA_ROOT) / template.mse_extracted_root / "style"
        if not style_path.exists():
            return ""
        parsed = _parse_style_metadata(style_path.read_text(encoding="utf-8", errors="replace"))
        return (parsed.get("game") or "").strip().lower()
