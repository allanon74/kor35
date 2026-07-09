"""
Import massivo dataset MSE da directory locale (default: ~/Scaricati/mse).

Ordine sorgenti: prefisso primo carattere cartella (1,2,3,4...).
Le sorgenti successive sovrascrivono i package omonimi già importati.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from personaggi.carte_platform_models import CarteGiocoDefinizione, CarteStudioTemplate
from personaggi.carte_platform_models import CarteMsePackageImport
from personaggi.mse_style_import import (
    import_generic_package_directory,
    import_mse_style_directory,
    parse_mse_game_spec,
    parse_generic_package_meta,
)
from personaggi.models import Campagna


PACKAGE_SUFFIXES = (
    ".mse-style",
    ".mse-game",
    ".mse-set",
    ".mse-symbol-font",
    ".mse-export-template",
    ".mse-include",
    ".mse-locale",
)


def _folder_rank(path: Path) -> tuple[int, str]:
    m = re.match(r"^(\d)", path.name)
    return (int(m.group(1)) if m else 999, path.name.lower())


def _iter_packages(root: Path):
    for candidate in root.rglob("*"):
        if candidate.is_dir() and candidate.name.endswith(PACKAGE_SUFFIXES):
            yield candidate


def _guess_model_from_name(name: str) -> str:
    s = name.lower()
    if "magic" in s or s.startswith("mtg"):
        return "mtg"
    if "kor35" in s:
        return "kor35"
    return "custom"


def _norm_game_key(raw: str) -> str:
    return slugify((raw or "").strip().lower())[:80]


def _guess_model_from_game_name(game_name: str) -> str:
    return _guess_model_from_name(game_name or "")


def _read_style_meta(style_dir: Path) -> tuple[str, str]:
    style_file = style_dir / "style"
    if not style_file.exists():
        return style_dir.stem, style_dir.stem
    txt = style_file.read_text(encoding="utf-8", errors="replace")
    short = ""
    full = ""
    for line in txt.splitlines():
        raw = line.strip()
        low = raw.lower()
        if low.startswith("short name:"):
            short = raw.split(":", 1)[1].strip()
        elif low.startswith("full name:"):
            full = raw.split(":", 1)[1].strip()
    return short or style_dir.stem, full or short or style_dir.stem


class Command(BaseCommand):
    help = "Import massivo package MSE da ~/Scaricati/mse con overwrite per priorità cartelle."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-root",
            default="~/Scaricati/mse",
            help="Directory radice dataset MSE (default: ~/Scaricati/mse).",
        )
        parser.add_argument(
            "--campagna-slug",
            required=True,
            help="Campagna target KOR35.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Analisi senza scrivere su DB/media.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        root = Path(options["source_root"]).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise CommandError(f"Root dataset non trovata: {root}")

        campagna = Campagna.objects.filter(slug=options["campagna_slug"]).first()
        if not campagna:
            raise CommandError(f"Campagna non trovata: {options['campagna_slug']}")

        source_dirs = sorted([d for d in root.iterdir() if d.is_dir()], key=_folder_rank)
        if not source_dirs:
            raise CommandError(f"Nessuna cartella sorgente trovata in {root}")

        summary = Counter()
        self.stdout.write(self.style.MIGRATE_HEADING("=== Import MSE dataset ==="))
        self.stdout.write(f"Root: {root}")
        self.stdout.write(
            "Ordine sorgenti: " + " -> ".join([f"{d.name} (rank {_folder_rank(d)[0]})" for d in source_dirs])
        )
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Modalità dry-run: nessuna scrittura."))

        game_map: dict[str, CarteGiocoDefinizione] = {}

        def resolve_game_for_package(
            *,
            package_path: Path,
            package_type: str,
            parsed_meta: dict | None = None,
            fallback_name: str = "",
        ):
            parsed_meta = parsed_meta or {}
            game_name = (parsed_meta.get("game") or fallback_name or "").strip()
            if not game_name:
                game_name = "KOR35 imported"
            game_key = _norm_game_key(game_name)
            if not game_key:
                game_key = "kor35-imported"
            modello = _guess_model_from_game_name(game_name)
            game_slug = game_key

            if options["dry_run"]:
                self.stdout.write(
                    f"DRY game resolve: pkg={package_path.name} type={package_type} game={game_name} slug={game_slug} model={modello}"
                )
                return None

            if game_key in game_map:
                return game_map[game_key]

            gioco = (
                CarteGiocoDefinizione.objects.filter(campagna=campagna, slug=game_slug).first()
                or CarteGiocoDefinizione.objects.filter(
                    campagna=campagna, mse_game_name__iexact=game_name
                ).first()
            )
            if not gioco:
                base_slug = game_slug or "mse-game"
                idx = 2
                while CarteGiocoDefinizione.objects.filter(campagna=campagna, slug=game_slug).exists():
                    suffix = f"-{idx}"
                    game_slug = f"{base_slug[: max(1, 80 - len(suffix))]}{suffix}"
                    idx += 1
                gioco = CarteGiocoDefinizione.objects.create(
                    campagna=campagna,
                    slug=game_slug,
                    nome=game_name[:120] or package_path.stem[:120],
                    modello_base=modello,
                    studio_abilitato=True,
                    arena_abilitata=False,
                    mse_game_name=game_name[:120],
                )
                summary["giochi_created"] += 1
            else:
                to_update = []
                if game_name and gioco.mse_game_name != game_name[:120]:
                    gioco.mse_game_name = game_name[:120]
                    to_update.append("mse_game_name")
                if modello and gioco.modello_base != modello:
                    gioco.modello_base = modello
                    to_update.append("modello_base")
                if to_update:
                    to_update.append("updated_at")
                    gioco.save(update_fields=to_update)
                    summary["giochi_updated"] += 1
            game_map[game_key] = gioco
            return gioco

        for src in source_dirs:
            self.stdout.write(self.style.HTTP_INFO(f"\n[SORGENTE] {src.name}"))
            for pkg in _iter_packages(src):
                suffix = next((s for s in PACKAGE_SUFFIXES if pkg.name.endswith(s)), "")
                summary[f"seen{suffix}"] += 1
                pkg_type = suffix.lstrip(".")
                if suffix == ".mse-style":
                    short_name, full_name = _read_style_meta(pkg)
                    slug = slugify(short_name)[:80] or slugify(pkg.stem)[:80] or "style"
                    style_meta = parse_generic_package_meta(
                        "mse-style",
                        (pkg / "style").read_text(encoding="utf-8", errors="replace")
                        if (pkg / "style").exists()
                        else "",
                    )
                    game_hint = style_meta.get("game") or full_name or short_name or pkg.stem
                    modello = _guess_model_from_game_name(game_hint)
                    if options["dry_run"]:
                        self.stdout.write(
                            f"DRY style: {pkg} -> slug={slug}, model={modello}, game={game_hint}"
                        )
                        summary["dry_style"] += 1
                        continue

                    gioco = resolve_game_for_package(
                        package_path=pkg,
                        package_type=pkg_type,
                        parsed_meta=style_meta,
                        fallback_name=full_name or short_name,
                    )

                    template = CarteStudioTemplate.objects.filter(
                        campagna=campagna,
                        gioco_definizione=gioco,
                        slug=slug,
                    ).first()
                    created = False
                    if not template:
                        template = CarteStudioTemplate(
                            campagna=campagna,
                            gioco_definizione=gioco,
                            slug=slug,
                        )
                        created = True
                    template.nome = full_name[:120]
                    imported = import_mse_style_directory(template=template, source_dir=pkg)
                    template.attivo = True
                    template.save()
                    summary["style_created" if created else "style_overwritten"] += 1
                    summary["style_assets_total"] += len(imported.assets_manifest)
                    self.stdout.write(
                        f"style {'CREATED' if created else 'OVERWRITE'}: {pkg.name} -> {template.slug} assets={len(imported.assets_manifest)}"
                    )
                else:
                    if options["dry_run"]:
                        self.stdout.write(f"DRY {pkg_type}: {pkg}")
                        summary[f"dry_{pkg_type}"] += 1
                        continue
                    dest_rel = f"card_studio/mse_packages/{campagna.slug}/{pkg_type}/{slugify(pkg.stem) or pkg.stem}"
                    extracted_root, manifest, parsed_meta = import_generic_package_directory(
                        source_dir=pkg,
                        package_type=pkg_type,
                        destination_root_rel=dest_rel,
                    )
                    if suffix == ".mse-game":
                        game_root = pkg / "game"
                        if game_root.exists():
                            game_text = game_root.read_text(encoding="utf-8", errors="replace")
                            parsed_meta = {**parsed_meta, "game_spec": parse_mse_game_spec(game_text)}
                    gioco = resolve_game_for_package(
                        package_path=pkg,
                        package_type=pkg_type,
                        parsed_meta=parsed_meta,
                        fallback_name=(
                            parsed_meta.get("full_name")
                            or parsed_meta.get("short_name")
                            or pkg.stem
                        ),
                    )
                    if suffix == ".mse-game" and gioco:
                        merged_meta = dict(gioco.meta or {})
                        if parsed_meta.get("game_spec"):
                            merged_meta["mse_game_spec"] = parsed_meta["game_spec"]
                        if parsed_meta.get("version"):
                            merged_meta["mse_game_version"] = parsed_meta["version"]
                        if merged_meta != (gioco.meta or {}):
                            gioco.meta = merged_meta
                            gioco.save(update_fields=["meta", "updated_at"])
                            summary["giochi_spec_updated"] += 1
                    obj, created = CarteMsePackageImport.objects.update_or_create(
                        campagna=campagna,
                        package_type=pkg_type,
                        package_name=pkg.stem,
                        defaults={
                            "gioco_definizione": gioco,
                            "source_priority": _folder_rank(src)[0],
                            "source_root": str(root),
                            "source_path": str(pkg),
                            "extracted_root": extracted_root,
                            "parsed_meta": parsed_meta,
                            "assets_manifest": manifest,
                            "imported": True,
                        },
                    )
                    summary[f"{pkg_type}_created" if created else f"{pkg_type}_overwritten"] += 1
                    summary[f"{pkg_type}_assets_total"] += len(manifest)
                    self.stdout.write(
                        f"{pkg_type} {'CREATED' if created else 'OVERWRITE'}: {pkg.name} assets={len(manifest)}"
                    )

        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Summary ==="))
        for key in sorted(summary.keys()):
            self.stdout.write(f"{key}: {summary[key]}")

