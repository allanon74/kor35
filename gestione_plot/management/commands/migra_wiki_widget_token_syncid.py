import re

from django.core.management.base import BaseCommand
from django.db import transaction

from gestione_plot.models import (
    PaginaRegolamento,
    WikiButtonWidget,
    WikiImmagine,
    WikiMattoniWidget,
    WikiTierWidget,
)


TOKEN_RE = re.compile(r"\{\{WIDGET_([A-Z_]+):([A-Za-z0-9-]+)\}\}")


class Command(BaseCommand):
    help = (
        "Converte i token widget wiki da id numerico a sync_id stabile "
        "(es. {{WIDGET_TIER:123}} -> {{WIDGET_TIER:<uuid>}})."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra modifiche previste senza salvare.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))

        tier_map = {
            str(obj.id): str(obj.sync_id)
            for obj in WikiTierWidget.objects.only("id", "sync_id")
            if obj.sync_id
        }
        image_map = {
            str(obj.id): str(obj.sync_id)
            for obj in WikiImmagine.objects.only("id", "sync_id")
            if obj.sync_id
        }
        button_map = {
            str(obj.id): str(obj.sync_id)
            for obj in WikiButtonWidget.objects.only("id", "sync_id")
            if obj.sync_id
        }
        mattoni_map = {
            str(obj.id): str(obj.sync_id)
            for obj in WikiMattoniWidget.objects.only("id", "sync_id")
            if obj.sync_id
        }

        changed_pages = 0
        changed_tokens = 0
        unresolved_tokens = 0

        def _replace(match):
            nonlocal changed_tokens, unresolved_tokens
            raw_type = match.group(1)
            raw_key = match.group(2)

            # Se è già UUID/sync token non numerico, lascia invariato.
            if not raw_key.isdigit():
                return match.group(0)

            token_type = raw_type.upper()
            if token_type == "TIER":
                mapped = tier_map.get(raw_key)
            elif token_type in {"IMAGE", "IMMAGINE"}:
                mapped = image_map.get(raw_key)
            elif token_type in {"BUTTONS", "PULSANTI"}:
                mapped = button_map.get(raw_key)
            elif token_type == "MATTONI":
                mapped = mattoni_map.get(raw_key)
            else:
                mapped = None

            if not mapped:
                unresolved_tokens += 1
                return match.group(0)

            changed_tokens += 1
            return f"{{{{WIDGET_{token_type}:{mapped}}}}}"

        qs = PaginaRegolamento.objects.all().only("id", "titolo", "contenuto")
        with transaction.atomic():
            for page in qs.iterator():
                src = page.contenuto or ""
                dst = TOKEN_RE.sub(_replace, src)
                if dst == src:
                    continue
                changed_pages += 1
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[DRY-RUN] Pagina aggiornata: {page.id} - {page.titolo}"
                        )
                    )
                else:
                    page.contenuto = dst
                    page.save(update_fields=["contenuto", "updated_at"])

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Token convertiti: {changed_tokens}, pagine toccate: {changed_pages}, "
                f"token non risolti: {unresolved_tokens}, dry_run={dry_run}"
            )
        )
