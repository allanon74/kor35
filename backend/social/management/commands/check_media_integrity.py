"""
Verifica che i FileField/ImageField dei modelli social (rubriche incluse)
puntino a file presenti su MEDIA_ROOT.

Utile sul mirror Pi dopo sync DB: i path arrivano nel JSON, i binari solo via rsync.

Uso:
  python manage.py check_media_integrity
  python manage.py check_media_integrity --prefix social/rubriche
  python manage.py check_media_integrity --prefix social/rubriche --limit 50
  make check-media ENV=mirror
"""

from __future__ import annotations

from django.apps import apps
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import models


# Modelli social con media rilevanti per edge/offline.
_DEFAULT_LABELS = (
    "social.rubrica",
    "social.rubricaarticolo",
    "social.rubricaarticoloimmagine",
    "social.socialprofile",
    "social.socialpost",
    "social.socialpostimage",
    "social.socialstory",
    "social.chatmessage",
)


def _file_fields(model):
    for field in model._meta.concrete_fields:
        if isinstance(field, (models.FileField, models.ImageField)):
            yield field


def _iter_missing(model, field, *, prefix: str, limit: int):
    qs = model.objects.exclude(**{f"{field.name}": ""}).exclude(
        **{f"{field.name}__isnull": True}
    )
    found = 0
    prefix_norm = prefix.replace("\\", "/").rstrip("/")
    for obj in qs.iterator(chunk_size=200):
        file_field = getattr(obj, field.name, None)
        name = (getattr(file_field, "name", None) or "").replace("\\", "/")
        if not name:
            continue
        if prefix_norm and not (
            name == prefix_norm or name.startswith(prefix_norm + "/")
        ):
            continue
        if default_storage.exists(name):
            continue
        yield obj, name
        found += 1
        if limit and found >= limit:
            return


class Command(BaseCommand):
    help = "Elenca path media mancanti su disco (rubriche e altri FileField social)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--prefix",
            default="social/rubriche",
            help="Filtra path che iniziano così (default: social/rubriche). Usa '' per tutti.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=30,
            help="Max path mancanti da stampare per modello (0 = illimitato).",
        )
        parser.add_argument(
            "--all-social",
            action="store_true",
            help="Controlla anche post/profili/story oltre alle rubriche.",
        )

    def handle(self, *args, **options):
        prefix = (options.get("prefix") or "").strip()
        limit = int(options.get("limit") or 0)
        labels = _DEFAULT_LABELS if options.get("all_social") else (
            "social.rubrica",
            "social.rubricaarticolo",
            "social.rubricaarticoloimmagine",
        )

        self.stdout.write(self.style.MIGRATE_HEADING("=== Media integrity ==="))
        self.stdout.write(f"MEDIA storage check | prefix={prefix!r} | limit={limit or '∞'}")

        total_missing = 0
        for label in labels:
            try:
                model = apps.get_model(label)
            except LookupError:
                self.stderr.write(self.style.WARNING(f"Modello assente: {label}"))
                continue
            for field in _file_fields(model):
                missing = list(_iter_missing(model, field, prefix=prefix, limit=limit))
                if not missing:
                    continue
                total_missing += len(missing)
                self.stdout.write("")
                self.stdout.write(
                    self.style.WARNING(
                        f"{label}.{field.name}: {len(missing)} mancanti"
                        + (" (truncate)" if limit and len(missing) >= limit else "")
                    )
                )
                for obj, name in missing:
                    pk = getattr(obj, "pk", "?")
                    sync_id = getattr(obj, "sync_id", None)
                    self.stdout.write(f"  pk={pk} sync_id={sync_id} → {name}")

        self.stdout.write("")
        if total_missing:
            self.stdout.write(
                self.style.ERROR(
                    f"Totale path mancanti elencati: {total_missing}. "
                    "Sul mirror: make sync-media (rsync) dopo aver corretto i path DB "
                    "oppure attendere kor35-mirror-media-sync.timer."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("Nessun path mancante per i filtri dati."))
