"""
Ripara path media rubriche sul nodo locale quando il file manca su disco.

Caso tipico (pre-fix normalize_media_field_path): dopo sync il DB punta a
``…/articoli/<pk-locale>/hero.jpg`` mentre rsync ha lasciato il file sotto
l'UUID del master. Cerca per basename sotto ``social/rubriche/`` e aggiorna.

Uso:
  python manage.py repair_rubriche_media_paths --dry-run
  python manage.py repair_rubriche_media_paths
  make repair-rubriche-media ENV=mirror
"""

from __future__ import annotations

import os
from collections import defaultdict

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from social.models_rubriche import Rubrica, RubricaArticolo, RubricaArticoloImmagine

_PREFIX = "social/rubriche"


def _basename(path: str) -> str:
    return os.path.basename((path or "").replace("\\", "/"))


def _index_files_under_prefix(prefix: str) -> dict[str, list[str]]:
    """basename → lista path relativi trovati nello storage."""
    index: dict[str, list[str]] = defaultdict(list)
    try:
        dirs, files = default_storage.listdir(prefix)
    except Exception:
        return index

    stack = [(prefix, dirs, files)]
    while stack:
        current, subdirs, filenames = stack.pop()
        for name in filenames:
            rel = f"{current.rstrip('/')}/{name}"
            index[_basename(rel)].append(rel)
        for sub in subdirs:
            child = f"{current.rstrip('/')}/{sub}"
            try:
                d2, f2 = default_storage.listdir(child)
            except Exception:
                continue
            stack.append((child, d2, f2))
    return index


def _candidates(index: dict[str, list[str]], path: str) -> list[str]:
    base = _basename(path)
    if not base:
        return []
    return list(index.get(base) or [])


class Command(BaseCommand):
    help = "Ripara path rubriche mancanti cercando lo stesso basename sotto social/rubriche/."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra le riparazioni senza scrivere sul DB.",
        )

    def handle(self, *args, **options):
        dry = bool(options.get("dry_run"))
        self.stdout.write(self.style.MIGRATE_HEADING("=== Repair rubriche media paths ==="))
        self.stdout.write("Indicizzazione storage…")
        index = _index_files_under_prefix(_PREFIX)
        self.stdout.write(f"File indicizzati sotto {_PREFIX}/: {sum(len(v) for v in index.values())}")

        repaired = 0
        ambiguous = 0
        still_missing = 0

        jobs = [
            (Rubrica, "logo"),
            (RubricaArticolo, "hero_immagine"),
            (RubricaArticolo, "video"),
            (RubricaArticoloImmagine, "immagine"),
        ]

        for model, field_name in jobs:
            qs = model.objects.exclude(**{field_name: ""}).exclude(**{f"{field_name}__isnull": True})
            for obj in qs.iterator(chunk_size=100):
                ff = getattr(obj, field_name, None)
                name = getattr(ff, "name", None) or ""
                if not name:
                    continue
                if default_storage.exists(name):
                    continue
                matches = _candidates(index, name)
                if not matches:
                    still_missing += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"MISSING {model._meta.label}.{field_name} pk={obj.pk} → {name}"
                        )
                    )
                    continue
                if len(matches) > 1:
                    ambiguous += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"AMBIGUOUS {model._meta.label}.{field_name} pk={obj.pk} "
                            f"basename={_basename(name)} candidates={matches}"
                        )
                    )
                    continue
                new_path = matches[0]
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{'DRY ' if dry else ''}FIX {model._meta.label}.{field_name} "
                        f"pk={obj.pk}\n  {name}\n  → {new_path}"
                    )
                )
                if not dry:
                    with transaction.atomic():
                        # Evita save() del modello (prepare_image_upload / side-effect wiki).
                        model.objects.filter(pk=obj.pk).update(
                            **{field_name: new_path, "updated_at": timezone.now()}
                        )
                repaired += 1

        self.stdout.write("")
        self.stdout.write(
            f"Riparati={repaired} ambigui={ambiguous} ancora_mancanti={still_missing} dry_run={dry}"
        )
        if still_missing and not dry:
            self.stdout.write(
                self.style.WARNING(
                    "Path ancora mancanti: eseguire make sync-media dal master, poi ritentare."
                )
            )
