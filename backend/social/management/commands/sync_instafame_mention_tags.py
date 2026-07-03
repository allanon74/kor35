from django.core.management.base import BaseCommand
from django.db import transaction

from social.mention_tags import (
    post_ids_needing_tag_resync,
    suppress_mention_notify,
    sync_post_tags,
)
from social.models import SocialPost


class Command(BaseCommand):
    help = (
        "Riallinea SocialPostTag dai @mention in titolo/testo. "
        "Senza --apply: solo anteprima (nessuna modifica, nessuna notifica)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Esegue la riallineazione.",
        )
        parser.add_argument(
            "--post-id",
            type=int,
            action="append",
            dest="post_ids",
            help="Limita ai post indicati (ripetibile).",
        )

    def handle(self, *args, **options):
        apply = bool(options.get("apply"))
        post_ids = options.get("post_ids")

        if post_ids:
            target_ids = list(
                SocialPost.objects.filter(id__in=post_ids).values_list("id", flat=True)
            )
            missing = sorted(set(post_ids) - set(target_ids))
            if missing:
                self.stderr.write(self.style.ERROR(f"Post non trovati: {missing}"))
        else:
            target_ids = post_ids_needing_tag_resync()

        self.stdout.write(f"Post da riallineare: {len(target_ids)}")
        if target_ids:
            preview = ", ".join(str(i) for i in target_ids[:25])
            suffix = " …" if len(target_ids) > 25 else ""
            self.stdout.write(f"  id: {preview}{suffix}")

        if not apply:
            self.stdout.write(self.style.WARNING("Anteprima: aggiungi --apply per eseguire (notify=off)."))
            return

        fixed = 0
        with transaction.atomic():
            with suppress_mention_notify():
                for post in SocialPost.objects.filter(id__in=target_ids).iterator():
                    sync_post_tags(post, notify=False)
                    fixed += 1

        self.stdout.write(self.style.SUCCESS(f"Tag post riallineati: {fixed} (nessuna notifica push)."))
